"""SQLite-backed durable queue for dispatch manager.

Stores tasks in a local SQLite DB so queued tasks survive process restarts.
This is intentionally simple: functions are stored by name (func_name) and the
manager must register callables in its function registry for execution.

API:
- init_db(db_path)
- enqueue(id, func_name, args, kwargs, retries, backoff)
- claim_next_task() -> dict or None
- mark_done(id, result)
- mark_failed(id, error)
- requeue(id)
- list_tasks()
"""
from __future__ import annotations
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

_conn: Optional[sqlite3.Connection] = None
_db_path: Optional[str] = None


def _now_str():
    return datetime.utcnow().isoformat() + 'Z'


def init_db(db_path: str):
    global _conn, _db_path
    _db_path = db_path
    # ensure directory
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    _conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
    _conn.execute('PRAGMA journal_mode=WAL;')
    _conn.execute('PRAGMA synchronous=NORMAL;')
    _conn.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        func_name TEXT,
        args TEXT,
        kwargs TEXT,
        status TEXT,
        attempts INTEGER DEFAULT 0,
        retries INTEGER DEFAULT 0,
        backoff REAL DEFAULT 0.5,
        result TEXT,
        error TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    ''')


def enqueue(task_id: str, func_name: str, args: list, kwargs: dict, retries: int = 0, backoff: float = 0.5):
    global _conn
    if _conn is None:
        raise RuntimeError('DB not initialized')
    now = _now_str()
    _conn.execute(
        'INSERT OR REPLACE INTO tasks (id, func_name, args, kwargs, status, attempts, retries, backoff, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (task_id, func_name, json.dumps(args or []), json.dumps(kwargs or {}), 'queued', 0, retries, backoff, now, now)
    )


def claim_next_task() -> Optional[Dict[str, Any]]:
    global _conn
    if _conn is None:
        return None
    cur = _conn.cursor()
    try:
        cur.execute('BEGIN IMMEDIATE')
        row = cur.execute("SELECT id, func_name, args, kwargs, attempts, retries, backoff FROM tasks WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
        if not row:
            cur.execute('COMMIT')
            return None
        task_id, func_name, args_json, kwargs_json, attempts, retries, backoff = row
        now = _now_str()
        # mark running and increment attempts
        cur.execute('UPDATE tasks SET status=?, attempts=attempts+1, updated_at=? WHERE id=?', ('running', now, task_id))
        cur.execute('COMMIT')
        return {
            'id': task_id,
            'func_name': func_name,
            'args': json.loads(args_json or '[]'),
            'kwargs': json.loads(kwargs_json or '{}'),
            'attempts': attempts + 1,
            'retries': retries,
            'backoff': backoff,
        }
    except Exception:
        try:
            cur.execute('ROLLBACK')
        except Exception:
            pass
        return None


def mark_done(task_id: str, result: Any):
    global _conn
    if _conn is None:
        return
    try:
        _conn.execute('UPDATE tasks SET status=?, result=?, updated_at=? WHERE id=?', ('done', json.dumps(result), _now_str(), task_id))
    except Exception:
        pass


def mark_failed(task_id: str, error: str):
    global _conn
    if _conn is None:
        return
    try:
        _conn.execute('UPDATE tasks SET status=?, error=?, updated_at=? WHERE id=?', ('failed', error, _now_str(), task_id))
    except Exception:
        pass


def requeue(task_id: str):
    global _conn
    if _conn is None:
        return
    try:
        _conn.execute('UPDATE tasks SET status=?, updated_at=? WHERE id=?', ('queued', _now_str(), task_id))
    except Exception:
        pass


def list_tasks() -> Dict[str, Dict[str, Any]]:
    global _conn
    if _conn is None:
        return {}
    out = {}
    cur = _conn.cursor()
    for row in cur.execute('SELECT id, func_name, args, kwargs, status, attempts, retries, backoff, result, error, created_at, updated_at FROM tasks'):
        tid, func_name, args_json, kwargs_json, status, attempts, retries, backoff, result_json, error, created_at, updated_at = row
        try:
            result = json.loads(result_json) if result_json else None
        except Exception:
            result = result_json
        out[tid] = {
            'func_name': func_name,
            'args': json.loads(args_json or '[]'),
            'kwargs': json.loads(kwargs_json or '{}'),
            'status': status,
            'attempts': attempts,
            'retries': retries,
            'backoff': backoff,
            'result': result,
            'error': error,
            'created_at': created_at,
            'updated_at': updated_at,
        }
    return out
