JARVIS MCP-compatible Connector Protocol (Draft)

Overview
- Purpose: define a minimal Model Context Protocol (MCP)-compatible connector surface so JARVIS can call local connectors (desktop automation, Chrome, Office) and receive structured results.
- Transport: HTTP (localhost) for local connectors; JSON over POST requests. Authentication via bearer token for non-local deployments.

Endpoints (minimal)
- POST /invoke
  - Description: invoke a named action on the connector.
  - Request JSON: {"action":"screenshot", "params": {...}, "request_id":"uuid"}
  - Response: 202 Accepted with {"request_id":"uuid", "status":"queued"} or 200 with immediate result {"request_id":"uuid","status":"done","result":{...}}

- GET /status?request_id=uuid
  - Description: poll for status and result.
  - Response JSON: {"request_id":"uuid","status":"queued|running|done|failed","result":{...},"error":{...}}

- POST /cancel
  - Description: cancel a long-running job.
  - Request: {"request_id":"uuid"}

Message formats
- Standardize result envelopes:
  {"request_id":"uuid","status":"done","result": {"type":"screenshot","content_b64":"..."}}
- Errors:
  {"request_id":"uuid","status":"failed","error":{"code":"internal_error","message":"..."}}

Connector capabilities discovery
- GET /info -> returns supported actions and parameters
  Example: {"actions": ["screenshot", "click", "type", "open_app"], "name":"jv-desktop-connector","version":"0.1.0"}

Action examples
- screenshot -> params: {"format":"png","region":null}
- click -> params: {"x": 123, "y": 456, "button":"left","clicks":1}
- type -> params: {"text":"Hello","use_clipboard":true}
- find_image -> params: {"image_b64":"...","confidence":0.8}

Security
- Local: optional bearer token, allowlist of origins for ui/open-link.
- Remote: enforce TLS, per-connector tokens, audit logging.

Notes
- Keep the protocol small to start. Implement the connector as a small FastAPI/Flask app for local development.
- This draft maps closely to Claude's MCP ideas but is intentionally minimal for iteration.

Next steps
- Implement a reference Python connector (FastAPI) that implements /invoke and /status and supports screenshot, click, type, and find_image.
- Add tests that exercise the connector locally and from the main JARVIS process.
