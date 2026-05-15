"""Example plugin that uses the local MCP connector to open a URL and run a typed-mouse flow."""
import requests
import time

BASE = 'http://127.0.0.1:8000'

def run_example():
    # open GitHub
    r = requests.post(f'{BASE}/invoke', json={'action':'open_url','params':{'url':'https://github.com'}})
    rid = r.json().get('request_id')
    # poll status
    for _ in range(20):
        s = requests.get(f'{BASE}/status', params={'request_id': rid}).json()
        if s.get('status') == 'done':
            break
        time.sleep(0.5)
    # run a typed_mouse flow to open run dialog (if desktop available)
    flow = [
        {'op':'hotkey','keys':['win','r']},
        {'op':'type','text':'notepad'},
        {'op':'press','key':'enter'}
    ]
    r2 = requests.post(f'{BASE}/custom/invoke', json={'action':'typed_mouse','params':{'steps': flow}})
    return r2.json()
