import threading, time, json, os

TASKS_FILE = os.path.join(os.path.dirname(__file__), 'agent_tasks.json')
APPROVALS_FILE = os.path.join(os.path.dirname(__file__), 'agent_approvals.json')
RUNNER_STARTED = False


def _load_tasks():
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save_tasks(tasks):
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2)


def _load_approvals():
    try:
        with open(APPROVALS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_approvals(d):
    with open(APPROVALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2)


def _execute_task(task):
    # Minimal executor: log and simulate execution
    print(f"[AGENT] Executing task {task.get('id')}: {task.get('payload')}")
    # Simulated action: you would integrate the real tool execution here
    time.sleep(2)
    print(f"[AGENT] Completed {task.get('id')}")
    return True


def runner_loop():
    while True:
        tasks = _load_tasks()
        approvals = _load_approvals()
        changed = False
        for t in tasks:
            if t.get('status') == 'pending':
                # If task requests autonomous action, require explicit approval unless already approved
                requires_approval = bool(t.get('payload', {}).get('autonomous', False))
                if requires_approval and approvals.get(t.get('id')) != True:
                    t['status'] = 'awaiting_approval'
                    continue
                t['status'] = 'running'
                _save_tasks(tasks)
                success = _execute_task(t)
                t['status'] = 'done' if success else 'failed'
                t['completed_at'] = time.time()
                changed = True
        if changed:
            _save_tasks(tasks)
        time.sleep(3)


def start_background_runner():
    global RUNNER_STARTED
    if RUNNER_STARTED:
        return
    RUNNER_STARTED = True
    th = threading.Thread(target=runner_loop, daemon=True)
    th.start()
    print('[AGENT] background runner started')
