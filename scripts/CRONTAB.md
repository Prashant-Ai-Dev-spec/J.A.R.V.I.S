# Crontab entries for J.A.R.V.I.S maintenance tasks
# 
# For Linux/macOS:
# 1. Edit crontab: crontab -e
# 2. Add these lines:

# Rotate audit logs daily at 2 AM (keep last 30 days)
0 2 * * * /path/to/jarvis/scripts/rotate_audit.sh "YOUR_ADMIN_API_KEY" 30 >> /var/log/jarvis_audit_rotation.log 2>&1

# Clean up completed tasks older than 7 days, daily at 3 AM
0 3 * * * curl -s -X POST http://127.0.0.1:8000/admin/tasks/cleanup -H "X-Admin-Key: YOUR_ADMIN_API_KEY" -H "Content-Type: application/json" -d '{"status_filter":"done","max_age_days":7}' >> /var/log/jarvis_tasks_cleanup.log 2>&1

# Get admin stats weekly (Sundays at 4 AM)
0 4 * * 0 curl -s http://127.0.0.1:8000/admin/tasks/stats -H "X-Admin-Key: YOUR_ADMIN_API_KEY" >> /var/log/jarvis_stats.log 2>&1

# For Docker/Kubernetes:
# Add to docker-compose.yml or use a separate cron container:

# Example: Add to docker-compose.yml under services:
# cron:
#   image: mcuadros/ofelia:latest
#   volumes:
#     - /var/run/docker.sock:/var/run/docker.sock
#   command: daemon --docker
#   labels:
#     ofelia.enabled: "true"
#     ofelia.job-exec.audit-rotate.schedule: "@daily"
#     ofelia.job-exec.audit-rotate.command: "/bin/sh -c 'curl -X POST http://web:8000/admin/audit/rotate -H \"X-Admin-Key: ${ADMIN_API_KEY}\" -H \"Content-Type: application/json\" -d \"{\\\"days\\\":30}\"'"

# Or use a simple Python script with APScheduler in the container:
# See: backend/maintenance.py for example

# Admin API Key Rotation:
# - Change ADMIN_API_KEY in .env every 90 days
# - Update all cron jobs with new key
# - Restart containers: docker-compose up -d
