Operator deployment & security

This document describes how to deploy the JARVIS MCP connector securely and rotate credentials.

1. TLS and Reverse Proxy
- Run the MCP connector behind a TLS-terminating reverse proxy (nginx, envoy).
- Bind the FastAPI app to localhost and expose only the proxy port.

2. Authentication
- Set JARVIS_MCP_TOKEN on the server to a strong token.
- Validate Authorization: Bearer <token> on every incoming /invoke request.
- Store tokens in a secrets manager (AWS Secrets Manager, HashiCorp Vault) rather than environment vars in production.
- Rotate tokens regularly by updating the secret and restarting the connector with the new token.

3. Network Controls
- Restrict inbound access using firewall rules to permitted IPs or internal networks.
- Disable direct internet access from the connector host if unnecessary.

4. Telemetry & Audit
- Telemetry is logged locally by default. For enterprise, forward logs to a secure logging endpoint and enable audit trails.

5. Runtime hardening
- Run the connector as an unprivileged user.
- Use OS-level sandboxing and process supervisors (systemd) for restarts and monitoring.

6. CI & secrets
- Use CI secrets to inject JARVIS_MCP_TOKEN during integration tests.
- Do not print secrets in logs and use short-lived tokens when possible.
