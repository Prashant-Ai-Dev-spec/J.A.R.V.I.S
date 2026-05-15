"""Small test client for the MCP connector."""
import requests
import time

BASE = 'http://127.0.0.1:8000'

if __name__ == '__main__':
    r = requests.get(f'{BASE}/info')
    print('INFO', r.json())
    inv = requests.post(f'{BASE}/invoke', json={'action': 'screenshot'})
    print('INVOKE', inv.json())
    rid = inv.json()['request_id']
    for _ in range(10):
        s = requests.get(f'{BASE}/status', params={'request_id': rid})
        print('STATUS', s.json())
        if s.json().get('status') in ('done','failed'):
            break
        time.sleep(0.5)
