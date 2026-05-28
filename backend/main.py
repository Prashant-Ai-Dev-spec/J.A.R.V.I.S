from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import hmac
import os, json, threading, time, uuid

app = FastAPI(title="JARVIS Backend")

TOKENS_FILE = os.path.join(os.path.dirname(__file__), "integrations_tokens.json")
TASKS_FILE = os.path.join(os.path.dirname(__file__), "agent_tasks.json")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jarvis_config.json")
MIN_BACKEND_TOKEN_LENGTH = 24
SUPPORTED_OAUTH_PROVIDERS = {"slack"}


def _load_config_token() -> str:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            cfg = json.load(f)
        return str(cfg.get("web_api_token", "") or "").strip()
    except Exception:
        return ""


def _backend_token() -> str:
    return (
        os.getenv("JARVIS_BACKEND_TOKEN", "").strip()
        or os.getenv("JARVIS_WEB_TOKEN", "").strip()
        or os.getenv("ADMIN_API_KEY", "").strip()
        or _load_config_token()
    )


def _token_is_strong(token: str) -> bool:
    token = str(token or "").strip()
    return len(token) >= MIN_BACKEND_TOKEN_LENGTH and token.lower() not in {"jarvis", "1234", "password", "admin"}


def _token_matches(provided: str) -> bool:
    expected = _backend_token()
    return bool(_token_is_strong(expected) and provided and hmac.compare_digest(expected, str(provided).strip()))


def require_backend_auth(
    authorization: str | None = Header(default=None),
    x_jarvis_token: str | None = Header(default=None),
) -> None:
    bearer = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization[7:].strip()
    if _token_matches(bearer) or _token_matches(x_jarvis_token or ""):
        return
    raise HTTPException(status_code=401, detail="unauthorized")


async def _require_ws_auth(ws: WebSocket) -> bool:
    token = str(ws.query_params.get("token", "") or "")
    auth = str(ws.headers.get("Authorization", "") or "")
    bearer = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    header_token = str(ws.headers.get("X-Jarvis-Token", "") or "")
    if _token_matches(token) or _token_matches(bearer) or _token_matches(header_token):
        return True
    await ws.close(code=1008)
    return False

# Simple token storage
def _load_tokens():
    try:
        with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_tokens(d):
    with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2)

@app.get("/")
def root():
    return {"status": "jarvis backend running"}

@app.post("/integrations/{provider}/install")
def install(provider: str, _auth: None = Depends(require_backend_auth)):
    base = os.getenv('BASE_URL', 'http://127.0.0.1:8000')
    client = os.getenv(f"{provider.upper()}_CLIENT_ID", '')
    if provider.lower() == 'slack':
        scope = 'chat:write,users:read'
        redirect = f"{base}/integrations/slack/oauth_callback"
        url = f"https://slack.com/oauth/v2/authorize?client_id={client}&scope={scope}&redirect_uri={redirect}"
        return {"url": url}
    return JSONResponse({"error": "unsupported provider"}, status_code=400)

@app.get("/integrations/{provider}/oauth_callback")
def oauth_callback(provider: str, code: str = None):
    if provider.lower() not in SUPPORTED_OAUTH_PROVIDERS:
        return JSONResponse({"error": "unsupported provider"}, status_code=400)
    if not code:
        return JSONResponse({"error": "missing code"}, status_code=400)
    tokens = _load_tokens()
    tokens[provider] = {"code": code, "saved_at": time.time()}
    _save_tokens(tokens)
    return {"status": "ok", "provider": provider}

# Tasks for autonomous runner
@app.post('/tasks')
def create_task(payload: dict, _auth: None = Depends(require_backend_auth)):
    tasks = []
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
    except Exception:
        tasks = []
    task = {"id": str(uuid.uuid4()), "payload": payload, "status": "pending", "created_at": time.time()}
    tasks.append(task)
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2)
    return {"id": task['id']}

@app.get('/tasks')
def list_tasks(_auth: None = Depends(require_backend_auth)):
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

# Approvals API for agentic tasks
APPROVALS_FILE = os.path.join(os.path.dirname(__file__), 'agent_approvals.json')

def _load_approvals():
    try:
        with open(APPROVALS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_approvals(d):
    with open(APPROVALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2)

@app.get('/approvals')
def list_approvals(_auth: None = Depends(require_backend_auth)):
    return _load_approvals()

@app.post('/approvals/{task_id}/approve')
def approve_task(task_id: str, _auth: None = Depends(require_backend_auth)):
    a = _load_approvals()
    a[task_id] = True
    _save_approvals(a)
    return {'status': 'approved', 'task_id': task_id}

@app.post('/approvals/{task_id}/deny')
def deny_task(task_id: str, _auth: None = Depends(require_backend_auth)):
    a = _load_approvals()
    a[task_id] = False
    _save_approvals(a)
    return {'status': 'denied', 'task_id': task_id}

# Simple WebSocket signaling for meetings
rooms = {}
@app.websocket('/ws/meet/{room_id}')
async def ws_meet(ws: WebSocket, room_id: str):
    if not await _require_ws_auth(ws):
        return
    await ws.accept()
    rooms.setdefault(room_id, []).append(ws)
    try:
        while True:
            data = await ws.receive_text()
            # broadcast to other peers
            for conn in list(rooms.get(room_id, [])):
                if conn is not ws:
                    await conn.send_text(data)
    except WebSocketDisconnect:
        rooms[room_id].remove(ws)

# Simple chat websocket (text-only)
chat_rooms = {}
@app.websocket('/ws/chat/{room_id}')
async def ws_chat(ws: WebSocket, room_id: str):
    if not await _require_ws_auth(ws):
        return
    await ws.accept()
    chat_rooms.setdefault(room_id, []).append(ws)
    try:
        while True:
            data = await ws.receive_text()
            for conn in list(chat_rooms.get(room_id, [])):
                if conn is not ws:
                    await conn.send_text(data)
    except WebSocketDisconnect:
        chat_rooms[room_id].remove(ws)

# Serve static meeting page
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
app.mount('/static', StaticFiles(directory=os.path.join(os.path.dirname(__file__), 'static')), name='static')

@app.get('/meeting')
def meeting_page():
    try:
        path = os.path.join(os.path.dirname(__file__), 'static', 'meeting.html')
        with open(path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except Exception:
        return HTMLResponse(content='<h1>Meeting page not available</h1>', status_code=404)

# Agent control endpoints (kill-switch & audit)
AGENT_KILL_FILE = os.path.join(os.path.dirname(__file__), 'agent_kill_switch.json')
AGENT_AUDIT_FILE = os.path.join(os.path.dirname(__file__), 'agent_actions.log')

@app.post('/agent/kill')
def set_kill(payload: dict, _auth: None = Depends(require_backend_auth)):
    # payload: {"kill": true/false}
    try:
        with open(AGENT_KILL_FILE, 'w', encoding='utf-8') as f:
            json.dump({'kill': bool(payload.get('kill', False)), 'ts': time.time()}, f)
        return {'status': 'ok', 'kill': bool(payload.get('kill', False))}
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get('/agent/status')
def agent_status(_auth: None = Depends(require_backend_auth)):
    status = {'runner': 'unknown'}
    try:
        import backend.agentic as agentic
        status['runner'] = 'started' if getattr(agentic, 'RUNNER_STARTED', False) else 'stopped'
    except Exception:
        status['runner'] = 'unknown'
    status['kill'] = False
    try:
        if os.path.exists(AGENT_KILL_FILE):
            with open(AGENT_KILL_FILE, 'r', encoding='utf-8') as f:
                status['kill'] = json.load(f).get('kill', False)
    except Exception:
        status['kill'] = False
    return status

@app.get('/agent/audit')
def get_audit(limit: int = 200, _auth: None = Depends(require_backend_auth)):
    try:
        if not os.path.exists(AGENT_AUDIT_FILE):
            return []
        with open(AGENT_AUDIT_FILE, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        out = []
        for l in lines[-limit:]:
            try:
                out.append(json.loads(l))
            except Exception:
                out.append({'raw': l})
        return out
    except Exception:
        return JSONResponse({'error': 'failed to read audit'}, status_code=500)

# Start agentic background runner
try:
    import backend.agentic as agentic
    agentic.start_background_runner()
except Exception:
    pass

# Include admin API endpoints
try:
    from backend.admin import app_admin
    app.mount("/", app_admin)
except Exception as e:
    print(f"Warning: Could not load admin API: {e}")
