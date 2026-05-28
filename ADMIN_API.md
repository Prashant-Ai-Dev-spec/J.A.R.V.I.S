# ADMIN API DOCUMENTATION

## Overview

The Admin API provides operational control and monitoring of J.A.R.V.I.S.
All endpoints require the `X-Admin-Key` header.

## Authentication

All admin endpoints require:

```
Header: X-Admin-Key: <ADMIN_API_KEY>
```

The `ADMIN_API_KEY` is set in `.env`:

```bash
ADMIN_API_KEY=IypQ0dM3r9msgnEHCF5D4VXz7kWuLhAP  # Generated securely
```

**Security Notes:**
- Rotate the API key every 90 days
- Never commit `.env` to git
- Use HTTPS in production
- Log all admin requests
- Restrict by IP/VPN in production

## Endpoints

### 1. Admin Health Check

**Endpoint:** `GET /admin/health`

**Authentication:** X-Admin-Key header

**Response:**
```json
{
  "status": "admin api operational",
  "timestamp": 1779234000.123,
  "admin_key_configured": true
}
```

**Example:**
```bash
curl -H "X-Admin-Key: IypQ0dM3r9msgnEHCF5D4VXz7kWuLhAP" \
  http://127.0.0.1:8000/admin/health
```

---

### 2. Get Task Statistics

**Endpoint:** `GET /admin/tasks/stats`

**Authentication:** X-Admin-Key header

**Response:**
```json
{
  "total": 47,
  "by_status": {
    "pending": 3,
    "approved": 1,
    "running": 2,
    "done": 41
  },
  "by_cmd": {
    "demo": 45,
    "test_autonomous_123": 2
  },
  "oldest": {
    "id": "first-task-id",
    "payload": {"cmd": "demo"},
    "status": "done",
    "created_at": 1779230000.0
  },
  "newest": {
    "id": "last-task-id",
    "payload": {"cmd": "demo"},
    "status": "pending",
    "created_at": 1779233844.0
  }
}
```

**Example:**
```bash
curl -H "X-Admin-Key: IypQ0dM3r9msgnEHCF5D4VXz7kWuLhAP" \
  http://127.0.0.1:8000/admin/tasks/stats
```

---

### 3. Clean Up Old Tasks

**Endpoint:** `POST /admin/tasks/cleanup`

**Authentication:** X-Admin-Key header

**Query Parameters:**
- `status_filter` (default: "done") - Task status to delete
- `max_age_days` (default: 7) - Keep tasks newer than this

**Response:**
```json
{
  "status": "cleaned",
  "kept": 40,
  "removed": 7,
  "removed_ids": ["task-1", "task-2", ...],
  "filter": "done",
  "max_age_days": 7
}
```

**Example:**
```bash
# Delete 'done' tasks older than 30 days
curl -X POST \
  -H "X-Admin-Key: IypQ0dM3r9msgnEHCF5D4VXz7kWuLhAP" \
  -H "Content-Type: application/json" \
  -d '{"status_filter":"done","max_age_days":30}' \
  http://127.0.0.1:8000/admin/tasks/cleanup
```

---

### 4. Get Recent Audit Entries

**Endpoint:** `GET /admin/audit/recent`

**Authentication:** X-Admin-Key header

**Query Parameters:**
- `limit` (default: 100) - Number of entries to return

**Response:**
```json
{
  "entries": [
    {
      "timestamp": 1779233844.0,
      "action": "task_created",
      "task_id": "a2b5ae2c-3ad7-4c72-aa6f-2d0533330bab",
      "details": {...}
    },
    ...
  ],
  "count": 47
}
```

**Example:**
```bash
curl -H "X-Admin-Key: IypQ0dM3r9msgnEHCF5D4VXz7kWuLhAP" \
  'http://127.0.0.1:8000/admin/audit/recent?limit=50'
```

---

### 5. Rotate Audit Logs

**Endpoint:** `POST /admin/audit/rotate`

**Authentication:** X-Admin-Key header

**Query Parameters:**
- `days` (default: 30) - Keep entries from last N days

**Response:**
```json
{
  "status": "rotated",
  "kept": 150,
  "archived": 245,
  "archive_file": "agent_actions_archive_1779233900.log",
  "cutoff_date": "2026-04-20T05:25:00"
}
```

**Example:**
```bash
# Keep audit from last 30 days, archive older
curl -X POST \
  -H "X-Admin-Key: IypQ0dM3r9msgnEHCF5D4VXz7kWuLhAP" \
  -H "Content-Type: application/json" \
  -d '{"days":30}' \
  http://127.0.0.1:8000/admin/audit/rotate
```

---

### 6. Get Configuration (Sanitized)

**Endpoint:** `GET /admin/config`

**Authentication:** X-Admin-Key header

**Response:**
```json
{
  "admin_key_set": true,
  "audit_file": "/app/backend/agent_actions.log",
  "tasks_file": "/app/backend/agent_tasks.json",
  "base_url": "http://127.0.0.1:8000",
  "redis_url": "redis://redis:6379/0",
  "database_url": "postgresql://jarvis:jarvis@db:5432/jarvis",
  "timestamp": 1779233900.0
}
```

**Note:** API key is NOT exposed in this response.

**Example:**
```bash
curl -H "X-Admin-Key: IypQ0dM3r9msgnEHCF5D4VXz7kWuLhAP" \
  http://127.0.0.1:8000/admin/config
```

---

## Error Responses

### Missing/Invalid API Key

**Status Code:** 403 Forbidden

**Response:**
```json
{
  "detail": "Invalid admin API key"
}
```

### API Key Not Configured

**Status Code:** 503 Service Unavailable

**Response:**
```json
{
  "detail": "Admin API key not configured"
}
```

---

## Usage Examples

### Python

```python
import requests

ADMIN_KEY = "IypQ0dM3r9msgnEHCF5D4VXz7kWuLhAP"
BASE_URL = "http://127.0.0.1:8000"
headers = {"X-Admin-Key": ADMIN_KEY}

# Get stats
resp = requests.get(f"{BASE_URL}/admin/tasks/stats", headers=headers)
print(resp.json())

# Rotate audit
resp = requests.post(
    f"{BASE_URL}/admin/audit/rotate",
    json={"days": 30},
    headers=headers
)
print(resp.json())

# Cleanup
resp = requests.post(
    f"{BASE_URL}/admin/tasks/cleanup",
    json={"status_filter": "done", "max_age_days": 7},
    headers=headers
)
print(resp.json())
```

### cURL

```bash
# Set as env var
export ADMIN_KEY="IypQ0dM3r9msgnEHCF5D4VXz7kWuLhAP"

# Get stats
curl -H "X-Admin-Key: $ADMIN_KEY" \
  http://127.0.0.1:8000/admin/tasks/stats

# Rotate audit
curl -X POST \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"days":30}' \
  http://127.0.0.1:8000/admin/audit/rotate

# Cleanup tasks
curl -X POST \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status_filter":"done","max_age_days":7}' \
  http://127.0.0.1:8000/admin/tasks/cleanup
```

---

## Automated Maintenance

### Crontab (Linux/macOS)

```bash
# Rotate audit daily
0 2 * * * curl -X POST \
  -H "X-Admin-Key: IypQ0dM3r9msgnEHCF5D4VXz7kWuLhAP" \
  -H "Content-Type: application/json" \
  -d '{"days":30}' \
  http://127.0.0.1:8000/admin/audit/rotate >> /var/log/jarvis_admin.log 2>&1

# Cleanup weekly
0 3 * * 0 curl -X POST \
  -H "X-Admin-Key: IypQ0dM3r9msgnEHCF5D4VXz7kWuLhAP" \
  -H "Content-Type: application/json" \
  -d '{"status_filter":"done","max_age_days":7}' \
  http://127.0.0.1:8000/admin/tasks/cleanup >> /var/log/jarvis_admin.log 2>&1
```

See `scripts/CRONTAB.md` for more details.

---

## Security Best Practices

1. **Rotate Keys:** Change ADMIN_API_KEY every 90 days
   ```bash
   # Generate new key
   openssl rand -hex 16
   # Update .env
   # Restart: docker-compose up -d
   ```

2. **Use HTTPS:** In production, always use https://
   - Generate cert: `./scripts/get_cert.sh yourdomain.com`
   - Enable in nginx.conf

3. **Restrict Access:** Use firewall/VPN to limit IPs
   - Kubernetes: NetworkPolicy
   - Docker: Ingress firewall rules
   - Cloud: Security groups

4. **Audit Logging:** Admin API requests are logged
   - Check `/agent/audit` endpoint
   - Archive audit logs regularly

5. **Monitor Usage:**
   - Set alerts on GET /admin/config
   - Track cleanup/rotation success rates

---

## Troubleshooting

### Admin API returns 404

**Cause:** Admin endpoints not mounted in web container

**Solution:**
1. Verify admin.py exists: `ls backend/admin.py`
2. Check main.py imports admin: `grep "from backend.admin" backend/main.py`
3. Restart web: `docker-compose restart web`
4. Wait 10s and retry

### API Key not working

**Cause:** Key mismatch or not in .env

**Solution:**
1. Check .env: `grep ADMIN_API_KEY .env`
2. Verify header matches exactly
3. Check for leading/trailing whitespace
4. Regenerate: Generate new key and update .env

### Audit rotation fails

**Cause:** File permissions or format issue

**Solution:**
1. Check logs: `docker logs jarvis-web-1 | grep admin`
2. Verify audit file exists: `docker exec jarvis-web-1 ls -la backend/agent_actions.log`
3. Check file format: `docker exec jarvis-web-1 head -5 backend/agent_actions.log`

---

## Next Steps

1. ✅ Set ADMIN_API_KEY in .env
2. ✅ Restart web container: `docker-compose restart web`
3. ⏳ Test admin endpoints with X-Admin-Key header
4. ⏳ Schedule audit rotation via cron
5. ⏳ Set up monitoring/alerts for admin operations
