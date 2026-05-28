# Google Drive integration skeleton
import os
from .token_storage import encrypt_token, decrypt_token

CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')


def build_install_url(base_url: str):
    redirect = f"{base_url}/integrations/drive/oauth_callback"
    url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}&redirect_uri={redirect}&response_type=code&scope=https://www.googleapis.com/auth/drive.readonly"
    return url


def save_authorization(provider: str, token_payload: dict):
    encrypt_token(provider, token_payload)


def get_token(provider: str):
    return decrypt_token(provider)
