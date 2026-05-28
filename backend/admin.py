"""
Admin API endpoints - protected by X-Admin-Key header
"""
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
import os, json, time
from datetime import datetime, timedelta

app_admin = FastAPI(title="JARVIS Admin API")

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
AGENT_AUDIT_FILE = os.path.join(os.path.dirname(__file__), 'agent_actions.log')
TASKS_FILE = os.path.join(os.path.dirname(__file__), "agent_tasks.json")

def verify_admin_key(x_admin_key: str = Header(None)):
    """Verify admin API key from header"""
    if not ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key not configured"
        )
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key"
        )
    return x_admin_key

@app_admin.get("/admin/health")
def admin_health(x_admin_key: str = Header(None)):
    """Admin health check"""
    verify_admin_key(x_admin_key)
    return {
        "status": "admin api operational",
        "timestamp": time.time(),
        "admin_key_configured": bool(ADMIN_API_KEY)
    }

@app_admin.get("/admin/audit/recent")
def get_recent_audit(limit: int = 100, x_admin_key: str = Header(None)):
    """Get recent audit entries"""
    verify_admin_key(x_admin_key)
    try:
        if not os.path.exists(AGENT_AUDIT_FILE):
            return {"entries": [], "count": 0}
        with open(AGENT_AUDIT_FILE, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        entries = []
        for line in lines[-limit:]:
            try:
                entries.append(json.loads(line))
            except:
                entries.append({"raw": line, "type": "parse_error"})
        return {"entries": entries, "count": len(entries)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app_admin.post("/admin/audit/rotate")
def rotate_audit(days: int = 30, x_admin_key: str = Header(None)):
    """Rotate audit log - keep last N days, archive older entries"""
    verify_admin_key(x_admin_key)
    try:
        if not os.path.exists(AGENT_AUDIT_FILE):
            return {"status": "no audit file", "archived": 0}
        
        with open(AGENT_AUDIT_FILE, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        
        cutoff_time = time.time() - (days * 86400)
        kept = []
        archived = []
        
        for line in lines:
            try:
                entry = json.loads(line)
                entry_time = entry.get("timestamp", entry.get("ts", 0))
                if entry_time > cutoff_time:
                    kept.append(line)
                else:
                    archived.append(line)
            except:
                kept.append(line)  # Keep unparseable entries
        
        # Write back kept entries
        with open(AGENT_AUDIT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(kept))
        
        # Archive old entries
        archive_file = AGENT_AUDIT_FILE.replace('.log', f'_archive_{int(time.time())}.log')
        if archived:
            with open(archive_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(archived))
        
        return {
            "status": "rotated",
            "kept": len(kept),
            "archived": len(archived),
            "archive_file": archive_file if archived else None,
            "cutoff_date": datetime.fromtimestamp(cutoff_time).isoformat()
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app_admin.get("/admin/tasks/stats")
def get_task_stats(x_admin_key: str = Header(None)):
    """Get task statistics"""
    verify_admin_key(x_admin_key)
    try:
        tasks = []
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
        
        stats = {
            "total": len(tasks),
            "by_status": {},
            "by_cmd": {},
            "oldest": None,
            "newest": None
        }
        
        for task in tasks:
            status = task.get("status", "unknown")
            cmd = task.get("payload", {}).get("cmd", "unknown")
            
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            stats["by_cmd"][cmd] = stats["by_cmd"].get(cmd, 0) + 1
            
            if not stats["oldest"] or task.get("created_at", 0) < stats["oldest"]["created_at"]:
                stats["oldest"] = task
            if not stats["newest"] or task.get("created_at", 0) > stats["newest"]["created_at"]:
                stats["newest"] = task
        
        return stats
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app_admin.post("/admin/tasks/cleanup")
def cleanup_tasks(status_filter: str = "done", max_age_days: int = 7, x_admin_key: str = Header(None)):
    """Clean up old tasks (default: delete 'done' tasks older than 7 days)"""
    verify_admin_key(x_admin_key)
    try:
        tasks = []
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
        
        cutoff_time = time.time() - (max_age_days * 86400)
        kept = []
        removed = []
        
        for task in tasks:
            task_time = task.get("created_at", 0)
            task_status = task.get("status", "")
            
            if task_status == status_filter and task_time < cutoff_time:
                removed.append(task["id"])
            else:
                kept.append(task)
        
        # Write back
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(kept, f, indent=2)
        
        return {
            "status": "cleaned",
            "kept": len(kept),
            "removed": len(removed),
            "removed_ids": removed,
            "filter": status_filter,
            "max_age_days": max_age_days
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app_admin.get("/admin/config")
def get_config(x_admin_key: str = Header(None)):
    """Get sanitized configuration (admin key not exposed)"""
    verify_admin_key(x_admin_key)
    return {
        "admin_key_set": bool(ADMIN_API_KEY),
        "audit_file": AGENT_AUDIT_FILE,
        "tasks_file": TASKS_FILE,
        "base_url": os.getenv("BASE_URL", "http://127.0.0.1:8000"),
        "redis_url": os.getenv("REDIS_URL", "redis://redis:6379/0"),
        "database_url": os.getenv("DATABASE_URL", "postgresql://jarvis:jarvis@db:5432/jarvis"),
        "timestamp": time.time()
    }
