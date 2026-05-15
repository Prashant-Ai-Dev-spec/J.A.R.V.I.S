import os
import requests
import time
import unittest

BASE = 'http://127.0.0.1:8000'

class MCPAuthTests(unittest.TestCase):
    def test_unauth_and_auth(self):
        # Server must be started with JARVIS_MCP_TOKEN=secrettoken for this test to be meaningful
        token = os.environ.get('JARVIS_MCP_TOKEN')
        # If token is not set on server, skip
        if not token:
            self.skipTest('Server not configured with JARVIS_MCP_TOKEN')
        # call without auth -> expect 401
        r = requests.post(f'{BASE}/invoke', json={'action': 'screenshot'})
        self.assertEqual(r.status_code, 401)
        # call with auth -> expect 202 or 200
        headers = {'Authorization': f'Bearer {token}'}
        r2 = requests.post(f'{BASE}/invoke', json={'action': 'screenshot'}, headers=headers)
        self.assertIn(r2.status_code, (200,202))


if __name__ == '__main__':
    unittest.main()
