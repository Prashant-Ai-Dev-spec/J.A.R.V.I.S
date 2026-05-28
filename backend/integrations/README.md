Integration helpers README

- Implement provider-specific exchange flows in each module (slack/github/drive).
- Use token_storage.encrypt_token(provider, payload) to persist tokens.
- Use token_storage.decrypt_token(provider) to retrieve tokens.
