from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
import os, requests
from typing import Optional
from datetime import datetime, timedelta
from backend.database import get_db
from sqlalchemy.orm import Session
from backend.crud import get_user_by_username, save_integration_token, get_integration_token

router = APIRouter()
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
GITHUB_REDIRECT_URI = os.getenv('GITHUB_REDIRECT_URI', '/integrations/github/oauth_callback')

@router.get('/github/install')
def install(request: Request, state: Optional[str] = None):
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail='GITHUB_CLIENT_ID not configured')
    host = request.base_url.scheme + '://' + request.base_url.netloc
    redirect_uri = host + GITHUB_REDIRECT_URI
    url = f'https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo,read:user&redirect_uri={redirect_uri}'
    if state:
        url += f'&state={state}'
    return RedirectResponse(url)

@router.get('/github/oauth_callback')
def oauth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail='Missing code')
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail='GitHub not configured')
    
    data = {
        'client_id': GITHUB_CLIENT_ID,
        'client_secret': GITHUB_CLIENT_SECRET,
        'code': code
    }
    headers = {'Accept': 'application/json'}
    resp = requests.post('https://github.com/login/oauth/access_token', data=data, headers=headers)
    j = resp.json()
    if 'error' in j:
        raise HTTPException(status_code=400, detail=str(j))
    
    user = None
    if state:
        user = get_user_by_username(db, state)
    user_id = user.id if user else None
    
    token_info = {
        'access_token': j.get('access_token'),
        'expires_at': datetime.utcnow() + timedelta(hours=8)
    }
    save_integration_token(db, user_id, 'github', token_info)
    return {'status':'ok', 'user': user.username if user else None}

@router.get('/github/repos')
def list_repos(db: Session = Depends(get_db), owner_user: Optional[str] = None):
    # owner_user may be username; default to global token
    user_obj = None
    if owner_user:
        user_obj = get_user_by_username(db, owner_user)
    user_id = user_obj.id if user_obj else None
    token_info = get_integration_token(db, user_id, 'github')
    if not token_info or not token_info.get('access_token'):
        raise HTTPException(status_code=400, detail='No GitHub token configured')
    headers = {'Authorization': f'token {token_info.get("access_token")}', 'Accept': 'application/vnd.github.v3+json'}
    r = requests.get('https://api.github.com/user/repos', headers=headers)
    return r.json()

@router.post('/github/create_issue')
def create_issue(owner: str, repo: str, title: str, body: Optional[str] = None, db: Session = Depends(get_db), owner_user: Optional[str] = None):
    user_obj = None
    if owner_user:
        user_obj = get_user_by_username(db, owner_user)
    user_id = user_obj.id if user_obj else None
    token_info = get_integration_token(db, user_id, 'github')
    if not token_info or not token_info.get('access_token'):
        raise HTTPException(status_code=400, detail='No GitHub token configured')
    headers = {'Authorization': f'token {token_info.get("access_token")}', 'Accept': 'application/vnd.github.v3+json'}
    payload = {'title': title, 'body': body}
    r = requests.post(f'https://api.github.com/repos/{owner}/{repo}/issues', json=payload, headers=headers)
    return r.json()
