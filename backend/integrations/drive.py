from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
import os, json, requests, time
from typing import Optional
from backend.integrations.token_storage import encrypt_token, decrypt_token
from backend.database import get_db
from sqlalchemy.orm import Session
from backend.crud import get_user_by_username, save_integration_token, get_integration_token
from backend.auth import get_current_user

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
REDIRECT_PATH = '/integrations/drive/oauth_callback'
SCOPES = 'https://www.googleapis.com/auth/drive.file'

@router.get('/drive/install')
def install(request: Request, state: Optional[str] = None):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail='GOOGLE_CLIENT_ID not configured')
    host = request.base_url.scheme + '://' + request.base_url.netloc
    redirect_uri = host + REDIRECT_PATH
    url = (
        'https://accounts.google.com/o/oauth2/v2/auth'
        f'?client_id={GOOGLE_CLIENT_ID}&response_type=code&scope={SCOPES}&access_type=offline&prompt=consent&redirect_uri={redirect_uri}'
    )
    if state:
        url += f'&state={state}'
    return RedirectResponse(url)

@router.get('/drive/oauth_callback')
def oauth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail='Missing code')
    host = request.base_url.scheme + '://' + request.base_url.netloc
    redirect_uri = host + REDIRECT_PATH
    data = {
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    resp = requests.post('https://oauth2.googleapis.com/token', data=data)
    j = resp.json()
    if 'error' in j:
        raise HTTPException(status_code=400, detail=j)
    # determine target user from state (optional)
    user = None
    if state:
        user = get_user_by_username(db, state)
    user_id = user.id if user else None
    info = {
        'access_token': j.get('access_token'),
        'refresh_token': j.get('refresh_token'),
    }
    if j.get('expires_in'):
        from datetime import datetime, timedelta
        info['expires_at'] = datetime.utcnow() + timedelta(seconds=int(j.get('expires_in')))
    save_integration_token(db, user_id, 'google_drive', info)
    return {'status':'ok', 'user': user.username if user else None}

@router.get('/drive/files')
def list_files(team_id: Optional[str] = None, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    token_info = get_integration_token(db, current_user.id, 'google_drive')
    if not token_info:
        raise HTTPException(status_code=400, detail='No Google token configured for user')
    # attempt refresh if needed
    # reuse earlier refresh logic
    exp = token_info.get('expires_at')
    if exp and exp < time.time():
        # try refresh
        refresh = token_info.get('refresh_token')
        if refresh:
            data = {
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'refresh_token': refresh,
                'grant_type': 'refresh_token'
            }
            r = requests.post('https://oauth2.googleapis.com/token', data=data)
            j = r.json()
            if 'access_token' in j:
                token_info['access_token'] = j.get('access_token')
                if j.get('expires_in'):
                    from datetime import datetime, timedelta
                    token_info['expires_at'] = datetime.utcnow() + timedelta(seconds=int(j.get('expires_in')))
                save_integration_token(db, current_user.id, 'google_drive', token_info)
    access = token_info.get('access_token')
    if not access:
        raise HTTPException(status_code=401, detail='No access token')
    headers = {'Authorization': f'Bearer {access}'}
    r = requests.get('https://www.googleapis.com/drive/v3/files', headers=headers, params={'pageSize': 50})
    if r.status_code == 401:
        raise HTTPException(status_code=401, detail='Token expired')
    return r.json()

@router.post('/drive/upload')
def upload_file(request: Request, file: bytes = None, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    token_info = get_integration_token(db, current_user.id, 'google_drive')
    if not token_info:
        raise HTTPException(status_code=400, detail='No Google token configured for user')
    access = token_info.get('access_token')
    if not access:
        raise HTTPException(status_code=401, detail='No access token')
    headers = {'Authorization': f'Bearer {access}'}
    filename = request.query_params.get('filename', 'upload.bin')
    body = request.body()
    r = requests.post(f'https://www.googleapis.com/upload/drive/v3/files?name={filename}', headers=headers, data=body)
    return r.json()
