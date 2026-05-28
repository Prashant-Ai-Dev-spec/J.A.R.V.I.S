# GitHub integration skeleton
import os
from .token_storage import encrypt_token, decrypt_token

CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET', '')


def build_install_url(base_url: str):
    redirect = f"{base_url}/integrations/github/oauth_callback"
    url = f"https://github.com/login/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={redirect}&scope=repo"
    return url


def save_authorization(provider: str, token_payload: dict):
    encrypt_token(provider, token_payload)


def get_token(provider: str):
    return decrypt_token(provider)
