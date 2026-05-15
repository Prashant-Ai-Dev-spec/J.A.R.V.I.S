import os
import base64
import warnings

KEY_ENV = 'INTEGRATIONS_ENCRYPTION_KEY'
KEY_FILE = os.path.join(os.path.dirname(__file__), '.integration_key')

try:
    from cryptography.fernet import Fernet

    def _persist_key_to_file(key: str):
        try:
            with open(KEY_FILE, 'w') as f:
                f.write(key)
        except Exception:
            # best-effort only
            pass

    def get_key():
        # 1) prefer explicit env var
        k = os.getenv(KEY_ENV)
        if k:
            return k
        # 2) try key file
        try:
            if os.path.isfile(KEY_FILE):
                with open(KEY_FILE, 'r') as f:
                    return f.read().strip()
        except Exception:
            pass
        # 3) generate and persist
        k = base64.urlsafe_b64encode(os.urandom(32)).decode()
        try:
            _persist_key_to_file(k)
            warnings.warn(f'No {KEY_ENV} set; generated key saved to {KEY_FILE}. Store it securely and set {KEY_ENV} in production.')
        except Exception:
            warnings.warn(f'No {KEY_ENV} set and could not write key file; using ephemeral key for this run.')
        return k

    def encrypt_token(token: str) -> str:
        key = get_key()
        f = Fernet(key)
        return f.encrypt(token.encode()).decode()

    def decrypt_token(token_enc: str) -> str:
        key = get_key()
        f = Fernet(key)
        return f.decrypt(token_enc.encode()).decode()
except Exception:
    warnings.warn('cryptography not available — token encryption disabled; install cryptography for secure storage')

    def get_key():
        k = os.getenv(KEY_ENV)
        if k:
            return k
        try:
            if os.path.isfile(KEY_FILE):
                with open(KEY_FILE, 'r') as f:
                    return f.read().strip()
        except Exception:
            pass
        k = base64.urlsafe_b64encode(os.urandom(32)).decode()
        return k

    def encrypt_token(token: str) -> str:
        # no-op fallback
        return token

    def decrypt_token(token_enc: str) -> str:
        return token_enc
