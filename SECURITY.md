Production Hardening Checklist

1. Secrets & keys
- Generate a strong ADMIN_API_KEY and set in .env
- Ensure token_storage uses cryptography.Fernet (install cryptography)

2. TLS
- Obtain Let's Encrypt certs and mount into backend/certs
- Use deploy/nginx.conf and docker-compose.prod.yml for production

3. TURN
- Provision a public VM for coturn using terraform or cloud console
- Set TURN_EXTERNAL_IP in environment and open required ports

4. Agent security
- Use ADMIN API key for all admin endpoints
- Limit autonomous tasks by allowlist and require manual approval for destructive actions
- Set rate limits (RATE_LIMIT_REQ, RATE_LIMIT_WINDOW env vars)

5. Observability
- Centralize audit logs (rotate daily)
- Add Prometheus metrics and alerts for agent runner

6. CI/CD
- Add GitHub Actions to build images and run tests before deploy

7. Backup
- Regular DB backups and encrypted token backups
