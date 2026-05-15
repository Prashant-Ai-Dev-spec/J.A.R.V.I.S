from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
import os, requests
from typing import Optional
from datetime import datetime, timedelta
from backend.database import get_db
from sqlalchemy.orm import Session
from backend.crud import get_user_by_username, save_integration_token, get_integration_token

router = APIRouter()
SLACK_CLIENT_ID = os.getenv('SLACK_CLIENT_ID')
SLACK_CLIENT_SECRET = os.getenv('SLACK_CLIENT_SECRET')
SLACK_REDIRECT_URI = os.getenv('SLACK_REDIRECT_URI', '/integrations/slack/oauth_callback')

@router.get('/slack/install')
def install(request: Request, state: Optional[str] = None):
    if not SLACK_CLIENT_ID:
        return {'status': 'not-configured', 'detail': 'Set SLACK_CLIENT_ID'}
    host = request.base_url.scheme + '://' + request.base_url.netloc
    redirect_uri = host + SLACK_REDIRECT_URI
    url = f'https://slack.com/oauth/v2/authorize?client_id={SLACK_CLIENT_ID}&scope=chat:write,files:write,channels:read&redirect_uri={redirect_uri}'
    if state:
        url += f'&state={state}'
    return RedirectResponse(url)

@router.get('/slack/oauth_callback')
def oauth_callback(request: Request, code: str = None, state: Optional[str] = None, db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail='Missing code')
    if not SLACK_CLIENT_ID or not SLACK_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail='Slack not configured')
    
    # Exchange code for token
    host = request.base_url.scheme + '://' + request.base_url.netloc
    data = {
        'client_id': SLACK_CLIENT_ID,
        'client_secret': SLACK_CLIENT_SECRET,
        'code': code,
        'redirect_uri': host + SLACK_REDIRECT_URI
    }
    resp = requests.post('https://slack.com/api/oauth.v2.access', data=data)
    j = resp.json()
    if not j.get('ok'):
        raise HTTPException(status_code=400, detail=str(j))
    
    # Map to user via state if provided
    user = None
    if state:
        user = get_user_by_username(db, state)
    user_id = user.id if user else None
    
    token_info = {
        'access_token': j.get('access_token'),
        'expires_at': datetime.utcnow() + timedelta(hours=12)
    }
    save_integration_token(db, user_id, 'slack', token_info)
    return {'status': 'ok', 'user': user.username if user else None}

@router.post('/slack/post_message')
def post_message(request: Request, channel: str, message: str, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    token_info = get_integration_token(db, user_id, 'slack')
    if not token_info or not token_info.get('access_token'):
        raise HTTPException(status_code=401, detail='Slack token not found')
    
    data = {'channel': channel, 'text': message}
    headers = {'Authorization': f"Bearer {token_info['access_token']}"}
    resp = requests.post('https://slack.com/api/chat.postMessage', json=data, headers=headers)
    j = resp.json()
    if not j.get('ok'):
        raise HTTPException(status_code=400, detail=str(j))
    return j
