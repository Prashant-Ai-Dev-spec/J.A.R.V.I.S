import os
import time
import threading
from fastapi import Request
from fastapi.responses import JSONResponse

# Simple in-memory rate limiter per IP (demo only)
_LOCK = threading.Lock()
_BUCKETS = {}

RATE_LIMIT_REQ = int(os.getenv('RATE_LIMIT_REQ', '60'))  # requests
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))  # seconds


def _now():
    return int(time.time())


def rate_limit(request: Request):
    """Return None if allowed, or JSONResponse if rate limited."""
    try:
        ip = request.client.host if request.client else 'unknown'
    except Exception:
        ip = 'unknown'
    key = f"rl:{ip}"
    now = _now()
    with _LOCK:
        bucket = _BUCKETS.get(key)
        if not bucket:
            bucket = {'ts': now, 'count': 1}
            _BUCKETS[key] = bucket
            return None
        # window expired
        if now - bucket['ts'] >= RATE_LIMIT_WINDOW:
            bucket['ts'] = now
            bucket['count'] = 1
            return None
        if bucket['count'] >= RATE_LIMIT_REQ:
            return JSONResponse({'error': 'rate_limited'}, status_code=429)
        bucket['count'] += 1
    return None


def get_admin_key():
    return os.getenv('ADMIN_API_KEY', '')


def check_admin(request: Request) -> bool:
    """Return True if admin key header matches; header: X-Admin-Key"""
    header = 'X-Admin-Key'
    try:
        v = request.headers.get(header)
        return bool(v and v == get_admin_key())
    except Exception:
        return False


def require_admin(request: Request):
    if not get_admin_key():
        # no admin key configured — deny by default
        return JSONResponse({'error': 'admin_key_not_configured'}, status_code=403)
    if not check_admin(request):
        return JSONResponse({'error': 'unauthorized'}, status_code=401)
    return None
