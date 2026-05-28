"""
Slack integration helpers (skeleton). Use /integrations/slack/install to build the install URL.
This module is a helper; the FastAPI endpoints live in backend/main.py.
"""
from urllib.parse import urlencode
import os
from .token_storage import encrypt_token, decrypt_token

CLIENT_ID = os.getenv('SLACK_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('SLACK_CLIENT_SECRET', '')


def build_install_url(base_url: str):
    scope = 'chat:write,users:read'
    redirect = f"{base_url}/integrations/slack/oauth_callback"
    params = {'client_id': CLIENT_ID, 'scope': scope, 'redirect_uri': redirect}
    return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"


def save_authorization(provider: str, code: str, token_payload: dict):
    # token_payload would normally include access_token, scopes, team
    encrypt_token(provider, token_payload)


def get_token(provider: str):
    return decrypt_token(provider)

# Placeholder: implement server-side exchange if you have client_secret and code
def exchange_code_for_token(code: str):
    # Use OAuth exchange endpoint here if needed
    return {'access_token': 'xoxp-placeholder', 'code': code}
