from fastapi import FastAPI, Depends, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
import uvicorn
from .chat import manager
from .auth import authenticate_user, create_access_token, get_current_user
from .database import init_db, get_db
from .schemas import UserCreate, UserOut, Token
from .crud import get_user_by_username, create_user, save_message, get_messages, save_file_metadata, get_user_files, get_file_by_id
from sqlalchemy.orm import Session

# import token endpoints (registers /token/refresh)
import backend.token_endpoint as token_endpoint

app = FastAPI(title="J.A.R.V.I.S CoWork - Phase1")

@app.on_event("startup")
def startup():
    init_db()

# register token routes and meeting router
try:
    token_endpoint.register(app)
    import backend.login_endpoint as login_endpoint
    login_endpoint.register(app)
    import backend.meetings as meetings
    app.include_router(meetings.router)
    import backend.integrations.slack as slack_integration
    app.include_router(slack_integration.router, prefix='/integrations')
    import backend.integrations.drive as drive_integration
    app.include_router(drive_integration.router, prefix='/integrations')
    import backend.integrations.github as github_integration
    app.include_router(github_integration.router, prefix='/integrations')
    import backend.tasks as tasks
    app.include_router(tasks.router)
    import backend.analytics as analytics
    app.include_router(analytics.router)
except Exception:
    pass

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_username(db, user.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    created = create_user(db, user)
    return created

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserOut)
def read_users_me(current_user = Depends(get_current_user)):
    return current_user

@app.get('/chat/history')
def chat_history(limit: int = 100, q: str = None, db: Session = Depends(get_db)):
    msgs = get_messages(db, limit=limit, q=q)
    return {"history": [
        {"id": m.id, "username": m.username, "content": m.content, "created_at": m.created_at.isoformat()} for m in msgs
    ]}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    # save file to uploads directory and record metadata
    import os
    safe_name = file.filename.replace('..', '_')
    os.makedirs('uploads', exist_ok=True)
    path = os.path.join('uploads', safe_name)
    content = await file.read()
    with open(path, 'wb') as f:
        f.write(content)
    fm = save_file_metadata(db, current_user, safe_name, path, content_type=file.content_type, size=len(content))
    return {"id": fm.id, "filename": fm.filename, "path": fm.path}

@app.get('/files')
def list_files(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    files = get_user_files(db, current_user.id)
    return {"files": [{"id": f.id, "filename": f.filename, "created_at": f.created_at.isoformat()} for f in files]}

from fastapi.responses import FileResponse

@app.get('/files/{file_id}')
def download_file(file_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    f = get_file_by_id(db, file_id)
    if not f:
        raise HTTPException(status_code=404, detail='File not found')
    if f.user_id != current_user.id and not getattr(current_user, 'is_superuser', False):
        raise HTTPException(status_code=403, detail='Forbidden')
    return FileResponse(f.path, filename=f.filename)

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    # expect token in query params: ws://.../ws/chat?token=...
    token = websocket.query_params.get('token')
    if not token:
        await websocket.close(code=1008)
        return
    from jose import JWTError, jwt
    from backend.auth import SECRET_KEY, ALGORITHM
    from backend.database import SessionLocal
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get('sub')
        if username is None:
            await websocket.close(code=1008)
            return
    except JWTError:
        await websocket.close(code=1008)
        return
    db = SessionLocal()
    user = get_user_by_username(db, username)
    if not user:
        await websocket.close(code=1008)
        db.close()
        return
    await manager.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_text()
            # persist message
            save_message(db, user, data)
            # broadcast JSON payload
            import json
            await manager.broadcast(json.dumps({"username": username, "content": data}))
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    finally:
        db.close()

from fastapi.responses import FileResponse

@app.get('/demo')
def demo():
    return FileResponse('backend/static/index.html')

@app.get('/client.js')
def client_js():
    return FileResponse('backend/static/client.js')

@app.get('/editor')
def editor():
    return FileResponse('backend/static/editor.html')

@app.get('/editor.js')
def editor_js():
    return FileResponse('backend/static/editor.js')

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
