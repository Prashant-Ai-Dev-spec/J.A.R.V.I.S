JARVIS Deployment Quickstart

1. Populate .env from .env.example with your credentials and public IP.
2. Update docker-compose.prod.yml or docker-compose.yml as needed (NGINX cert mounts, TURN external IP).
3. Provision TURN server (coturn) and set TURN_EXTERNAL_IP.
4. Obtain TLS certs (certbot) or provide certs in backend/certs.
5. Build and run:
   docker-compose up --build -d
6. Register OAuth apps:
   - Slack: create app, set redirect to https://YOUR_HOST/integrations/slack/oauth_callback
   - GitHub / Google: set redirect URIs similarly
7. Call install endpoints to start auth flow:
   curl "http://localhost:8000/integrations/slack/install"
8. Test WebRTC meeting at: https://YOUR_HOST/meeting (frontend required)
9. Review backend/safety/policy.md and configure RUNNER approval flows before enabling agentic autonomy.

Notes:
- I cannot create external OAuth apps or obtain certs on your behalf; follow the provider consoles.
- For browsing-capable agents, integrate Playwright/Chromium or remote browsing APIs and add to backend/browsing_adapter.py
