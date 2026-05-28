Integrations Setup

- Slack: set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET in env. Visit /integrations/slack/install to get install URL.
- GitHub: set GITHUB_CLIENT_ID / SECRET.
- Drive: set GOOGLE_CLIENT_ID / SECRET and follow OAuth flow.

Token storage uses backend/integrations/token_storage.py which encrypts tokens if cryptography is available.
