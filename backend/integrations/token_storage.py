"""
Simple token storage with optional Fernet encryption.
If cryptography.Fernet is unavailable, falls back to plain JSON storage (not secure).
"""
from pathlib import Path
import json

KEY_FILE = Path(__file__).parent / "token_key.key"
TOKENS_FILE = Path(__file__).parent / "tokens.json"

try:
    from cryptography.fernet import Fernet
    _HAS_FERNET = True
except Exception:
    Fernet = None
    _HAS_FERNET = False


def _ensure_key():
    if not KEY_FILE.exists() and _HAS_FERNET:
        KEY_FILE.write_bytes(Fernet.generate_key())
    return KEY_FILE.exists()


def _load_key():
    if _HAS_FERNET and KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    return None


def encrypt_token(provider: str, token: dict):
    TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _HAS_FERNET:
        if not _ensure_key():
            raise RuntimeError('Could not create key')
        key = _load_key()
        f = Fernet(key)
        payload = json.dumps(token).encode('utf-8')
        enc = f.encrypt(payload).decode('utf-8')
        data = load_all() or {}
        data[provider] = {'enc': enc}
        TOKENS_FILE.write_text(json.dumps(data, indent=2))
    else:
        data = load_all() or {}
        data[provider] = {'plain': token}
        TOKENS_FILE.write_text(json.dumps(data, indent=2))


def decrypt_token(provider: str):
    data = load_all() or {}
    entry = data.get(provider)
    if not entry:
        return None
    if 'enc' in entry and _HAS_FERNET:
        key = _load_key()
        f = Fernet(key)
        try:
            return json.loads(f.decrypt(entry['enc'].encode('utf-8')).decode('utf-8'))
        except Exception:
            return None
    return entry.get('plain')


def load_all():
    if TOKENS_FILE.exists():
        try:
            return json.loads(TOKENS_FILE.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}
