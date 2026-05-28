Security README

Quick steps to enable production security:

1. Set ADMIN_API_KEY in .env (long random string).
2. Install cryptography in your environment and rebuild images so token encryption uses Fernet.
3. Configure rate limit env vars if needed: RATE_LIMIT_REQ, RATE_LIMIT_WINDOW.
4. Use admin endpoints under /admin/* for sensitive operations.
5. Ensure audit logs are collected and rotated by external log agent (fluentd/filebeat).
