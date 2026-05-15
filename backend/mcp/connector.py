"""Reference MCP-compatible local connector (FastAPI).
Provides /invoke, /status, /info endpoints and a minimal async task queue.
"""
import base64
import uuid
import threading
import time
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import os
from backend.connectors import chrome_devtools

# Import desktop automation implementation
try:
    from backend.desktop_automation.core import DesktopAutomation
except Exception:
    DesktopAutomation = None

from .custom_actions_api import router as custom_router
app = FastAPI(title="JARVIS MCP Connector")
app.include_router(custom_router, prefix="/custom")

# Simple in-memory task store
_tasks: Dict[str, Dict[str, Any]] = {}
_da = DesktopAutomation() if DesktopAutomation else None


class InvokeRequest(BaseModel):
    action: str
    params: Dict[str, Any] = {}
    request_id: str | None = None


@app.post('/invoke')
def invoke(req: InvokeRequest, request: Request):
    # Optional bearer token auth: set JARVIS_MCP_TOKEN to require it
    token = os.environ.get('JARVIS_MCP_TOKEN')
    if token:
        auth = request.headers.get('authorization', '')
        if not auth.lower().startswith('bearer ') or auth.split()[1] != token:
            raise HTTPException(status_code=401, detail='Unauthorized')
    rid = req.request_id or str(uuid.uuid4())
    if rid in _tasks:
        raise HTTPException(status_code=400, detail="request_id already exists")

    _tasks[rid] = {"status": "queued", "result": None, "error": None}

    def run_action():
        _tasks[rid]["status"] = "running"
        try:
            action = req.action
            params = req.params or {}
            if action == 'screenshot':
                if _da is None:
                    raise RuntimeError('DesktopAutomation not available')
                img_bytes = _da.screenshot()
                b64 = base64.b64encode(img_bytes).decode('ascii') if img_bytes else ''
                _tasks[rid]['result'] = {'type': 'screenshot', 'content_b64': b64}
            elif action == 'click':
                x = int(params.get('x', 0))
                y = int(params.get('y', 0))
                clicks = int(params.get('clicks', 1))
                right = bool(params.get('right', False))
                if _da is None:
                    raise RuntimeError('DesktopAutomation not available')
                _da.click(x, y, clicks=clicks, right=right)
                _tasks[rid]['result'] = {'type': 'click', 'ok': True}
            elif action == 'type':
                text = str(params.get('text', ''))
                use_clip = bool(params.get('use_clipboard', True))
                if _da is None:
                    raise RuntimeError('DesktopAutomation not available')
                _da.type_text(text, use_clipboard_paste=use_clip)
                _tasks[rid]['result'] = {'type': 'type', 'ok': True}
            elif action == 'open_url':
                url = str(params.get('url', ''))
                ok = False
                try:
                    chrome_devtools.start_browser(headless=True)
                    ok = chrome_devtools.open_url(url)
                except Exception:
                    ok = False
                _tasks[rid]['result'] = {'type': 'open_url', 'ok': bool(ok)}
            elif action == 'cd_click':
                selector = str(params.get('selector', ''))
                ok = False
                try:
                    chrome_devtools.start_browser(headless=True)
                    ok = chrome_devtools.click_selector(selector)
                except Exception:
                    ok = False
                _tasks[rid]['result'] = {'type': 'cd_click', 'ok': bool(ok)}
            elif action == 'cd_scroll':
                pixels = int(params.get('pixels', 500))
                ok = False
                try:
                    chrome_devtools.start_browser(headless=True)
                    ok = chrome_devtools.scroll(pixels)
                except Exception:
                    ok = False
                _tasks[rid]['result'] = {'type': 'cd_scroll', 'ok': bool(ok)}
            else:
                _tasks[rid]['error'] = {'code': 'unsupported_action', 'message': f'Action {action} not supported'}
                _tasks[rid]['status'] = 'failed'
                return
            _tasks[rid]['status'] = 'done'
        except Exception as e:
            _tasks[rid]['status'] = 'failed'
            _tasks[rid]['error'] = {'code': 'internal_error', 'message': str(e)}

    t = threading.Thread(target=run_action, daemon=True)
    t.start()

    return {"request_id": rid, "status": "queued"}


@app.get('/status')
def status(request_id: str):
    if request_id not in _tasks:
        raise HTTPException(status_code=404, detail='request_id not found')
    return {"request_id": request_id, "status": _tasks[request_id]['status'], "result": _tasks[request_id]['result'], "error": _tasks[request_id]['error']}


@app.get('/info')
def info():
    return {"actions": ["screenshot", "click", "type", "open_url", "cd_click", "cd_scroll"], "name": "jv-mcp-connector", "version": "0.2.0"}
