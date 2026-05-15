"""Dispatch manager: lightweight sub-agent dispatcher for background tasks.

Provides an in-process task queue with simple status tracking and the ability to run
callables in background worker threads. This version adds a worker pool, retry
logic, backoff, and safer persistence.
"""
import threading
import uuid
import time
import os
from typing import Any, Callable, Dict, Optional
import queue
import math
import random

from . import persistence
from backend import telemetry

# Load persisted tasks on import (best-effort)
try:
    _tasks: Dict[str, Dict[str, Any]] = persistence.load_tasks() or {}
except Exception:
    _tasks: Dict[str, Dict[str, Any]] = {}

_lock = threading.Lock()
_task_queue: "queue.Queue" = queue.Queue()
_workers: list = []
_shutdown = threading.Event()

# Worker pool size (bounded)
_WORKER_COUNT = max(2, min(4, (os.cpu_count() or 2)))

# Optional SQLite-backed durable queue. If available, tasks will be persisted
# in a local SQLite DB so queued work survives process restarts. Functions are
# stored by name in the DB and must be registered in _func_registry to execute.
_use_sql = False
_sql_queue = None
_func_registry: Dict[str, Callable[..., Any]] = {}

try:
    from . import sql_queue as sql_queue_mod
    db_path = os.path.join(os.path.dirname(__file__), 'dispatch.db')
    sql_queue_mod.init_db(db_path)
    _use_sql = True
    _sql_queue = sql_queue_mod
except Exception:
    _use_sql = False
    _sql_queue = None


def _worker_loop(worker_id: int):
    """Worker loop that supports either the in-memory queue or the optional
    SQLite-backed durable queue. When using SQLite the task's func is looked up
    from _func_registry by name; if not found the task is marked failed.
    """
    while not _shutdown.is_set():
        item = None
        # Prefer SQL-backed queue if available
        if _use_sql and _sql_queue is not None:
            try:
                item = _sql_queue.claim_next_task()
                if item is None:
                    time.sleep(0.2)
                    continue
            except Exception:
                # fallback to in-memory queue on error
                item = None
        else:
            try:
                item = _task_queue.get(timeout=0.5)
            except queue.Empty:
                continue

        if item is None:
            continue

        rid = item['id']
        attempts = item.get('attempts', 0)
        max_retries = item.get('retries', 0)
        backoff = item.get('backoff', 0.5)

        # Resolve callable
        func = None
        if _use_sql and 'func_name' in item:
            func_name = item.get('func_name')
            func = _func_registry.get(func_name)
            if func is None:
                # cannot execute unknown function
                try:
                    _sql_queue.mark_failed(rid, f'unknown function: {func_name}')
                except Exception:
                    pass
                continue
        else:
            func = item.get('func')

        args = item.get('args', ())
        kwargs = item.get('kwargs', {})

        with _lock:
            _tasks.setdefault(rid, {})
            _tasks[rid]['status'] = 'running'
            _tasks[rid]['error'] = None
            try:
                persistence.save_tasks(_tasks)
            except Exception:
                pass
        try:
            telemetry.log_event('dispatch.task_running', {'id': rid, 'worker': worker_id})
        except Exception:
            pass

        try:
            res = func(*args, **kwargs)
            with _lock:
                _tasks[rid]['status'] = 'done'
                _tasks[rid]['result'] = res
                try:
                    persistence.save_tasks(_tasks)
                except Exception:
                    pass
            if _use_sql and _sql_queue is not None:
                try:
                    _sql_queue.mark_done(rid, res)
                except Exception:
                    pass
            try:
                telemetry.log_event('dispatch.task_done', {'id': rid, 'result': res})
            except Exception:
                pass
        except Exception as e:
            attempts += 1
            with _lock:
                _tasks[rid]['status'] = 'failed'
                _tasks[rid]['error'] = str(e)
                try:
                    persistence.save_tasks(_tasks)
                except Exception:
                    pass
            try:
                telemetry.log_event('dispatch.task_failed', {'id': rid, 'error': str(e), 'attempts': attempts})
            except Exception:
                pass
            # retry logic
            if attempts <= max_retries and not _shutdown.is_set():
                # exponential backoff with jitter
                base = backoff * (2 ** (attempts - 1)) if attempts > 0 else backoff
                cap = 30
                delay = min(base, cap)
                try:
                    jitter = random.uniform(0, 0.5 * delay) if delay > 0 else 0
                except Exception:
                    jitter = 0
                delay = delay + jitter
                try:
                    telemetry.log_event('dispatch.retry', {'id': rid, 'attempts': attempts, 'delay': delay})
                    telemetry.log_event('dispatch.retry_scheduled', {'id': rid, 'attempts': attempts, 'delay': delay})
                except Exception:
                    pass
                # requeue through SQL or in-memory queue
                if _use_sql and _sql_queue is not None:
                    try:
                        # mark queued again; DB claim increments attempts on claim
                        _sql_queue.requeue(rid)
                    except Exception:
                        pass
                else:
                    # update attempts on item and put back with delay
                    item['attempts'] = attempts
                    try:
                        time.sleep(delay)
                        _task_queue.put(item)
                    except Exception:
                        pass
        finally:
            # if this task originated from in-memory queue, mark done on queue
            if not _use_sql:
                try:
                    _task_queue.task_done()
                except Exception:
                    pass


# Start worker threads
for i in range(_WORKER_COUNT):
    t = threading.Thread(target=_worker_loop, args=(i,), daemon=True)
    t.start()
    _workers.append(t)


def start_task(func: Callable[..., Any], args: Optional[tuple] = None, kwargs: Optional[dict] = None, retries: int = 0, backoff: float = 0.5) -> str:
    """Schedule a callable to run in background. Returns request_id.

    Parameters:
    - retries: number of times to retry on failure (default 0)
    - backoff: base backoff in seconds for retries (default 0.5)
    """
    rid = str(uuid.uuid4())
    args = args or ()
    kwargs = kwargs or {}
    func_name = getattr(func, '__name__', None)

    # Register task in in-memory status map for compatibility and persistence snapshot
    with _lock:
        _tasks[rid] = {"status": "queued", "result": None, "error": None}
        try:
            persistence.save_tasks(_tasks)
        except Exception:
            pass

    # If SQLite-backed queue is available and function has a name, use it
    if _use_sql and _sql_queue is not None and func_name:
        # register callable so workers can resolve it by name
        _func_registry[func_name] = func
        try:
            telemetry.log_event('dispatch.task_queued', {'id': rid, 'func': func_name})
        except Exception:
            pass
        try:
            # Ensure args are JSON-serializable lists
            arg_list = list(args) if isinstance(args, (list, tuple)) else [args]
            _sql_queue.enqueue(rid, func_name, arg_list, kwargs or {}, retries=retries, backoff=backoff)
            return rid
        except Exception:
            # fallback to in-memory queue
            pass

    # Default in-memory queue path
    try:
        telemetry.log_event('dispatch.task_queued', {'id': rid, 'func': getattr(func, '__name__', str(func))})
    except Exception:
        pass

    item = {'id': rid, 'func': func, 'args': args, 'kwargs': kwargs, 'retries': retries, 'backoff': backoff, 'attempts': 0}
    _task_queue.put(item)
    return rid


def get_status(request_id: str) -> Dict[str, Any]:
    with _lock:
        if request_id not in _tasks:
            raise KeyError('request_id not found')
        return dict(_tasks[request_id])


def list_tasks() -> Dict[str, Dict[str, Any]]:
    with _lock:
        return {k: dict(v) for k, v in _tasks.items()}


def shutdown(wait: bool = False, timeout: Optional[float] = None):
    """Signal workers to shut down. Optionally wait for termination."""
    _shutdown.set()
    if wait:
        start = time.time()
        for w in _workers:
            remaining = None
            if timeout is not None:
                elapsed = time.time() - start
                remaining = max(0, timeout - elapsed)
            w.join(remaining)


# Simple example worker function
def example_job(duration: int = 1):
    time.sleep(duration)
    return {'slept': duration}
