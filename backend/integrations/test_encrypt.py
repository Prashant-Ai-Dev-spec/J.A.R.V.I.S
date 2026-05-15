from backend.integrations import token_storage
s = token_storage.encrypt_token('test-secret-123')
print('encrypted:', s)
print('decrypted:', token_storage.decrypt_token(s))
