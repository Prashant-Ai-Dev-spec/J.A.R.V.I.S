from fastapi import Request
import os, json, time
from backend import security
from backend.main import app, TASKS_FILE, APPROVALS_FILE
from fastapi.responses import JSONResponse

# Admin-only endpoints: require X-Admin-Key header to match ADMIN_API_KEY

@app.get('/admin/approvals')
def admin_list_approvals(request: Request):
    r = security.require_admin(request)
    if r: return r
    try:
        with open(APPROVALS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

@app.post('/admin/approvals/{task_id}/approve')
def admin_approve(task_id: str, request: Request):
    r = security.require_admin(request)
    if r: return r
    a = {}
    try:
        with open(APPROVALS_FILE, 'r', encoding='utf-8') as f:
            a = json.load(f)
    except Exception:
        a = {}
    a[task_id] = True
    with open(APPROVALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(a, f, indent=2)
    return {'status': 'approved', 'task_id': task_id}

@app.post('/admin/approvals/{task_id}/deny')
def admin_deny(task_id: str, request: Request):
    r = security.require_admin(request)
    if r: return r
    a = {}
    try:
        with open(APPROVALS_FILE, 'r', encoding='utf-8') as f:
            a = json.load(f)
    except Exception:
        a = {}
    a[task_id] = False
    with open(APPROVALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(a, f, indent=2)
    return {'status': 'denied', 'task_id': task_id}

@app.post('/admin/agent/kill')
def admin_kill(payload: dict, request: Request):
    r = security.require_admin(request)
    if r: return r
    AGENT_KILL_FILE = os.path.join(os.path.dirname(__file__), 'agent_kill_switch.json')
    try:
        with open(AGENT_KILL_FILE, 'w', encoding='utf-8') as f:
            json.dump({'kill': bool(payload.get('kill', False)), 'ts': time.time()}, f)
        return {'status': 'ok', 'kill': bool(payload.get('kill', False))}
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get('/admin/agent/audit')
def admin_audit(request: Request, limit: int = 200):
    r = security.require_admin(request)
    if r: return r
    AGENT_AUDIT_FILE = os.path.join(os.path.dirname(__file__), 'agent_actions.log')
    try:
        if not os.path.exists(AGENT_AUDIT_FILE):
            return []
        with open(AGENT_AUDIT_FILE, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        out = []
        for l in lines[-limit:]:
            try:
                out.append(json.loads(l))
            except Exception:
                out.append({'raw': l})
        return out
    except Exception:
        return JSONResponse({'error': 'failed to read audit'}, status_code=500)

@app.post('/admin/tasks')
def admin_create_task(payload: dict, request: Request):
    r = security.require_admin(request)
    if r: return r
    # simple passthrough to TASKS_FILE
    tasks = []
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
    except Exception:
        tasks = []
    task = {"id": payload.get('id') or str(time.time()), "payload": payload, "status": "pending", "created_at": time.time()}
    tasks.append(task)
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2)
    return {"id": task['id']}
