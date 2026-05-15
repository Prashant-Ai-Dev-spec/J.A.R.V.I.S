import os, json
from backend.integrations import token_storage

BASEDIR = os.path.dirname(__file__)
FILES = ['drive_tokens.json', 'github_tokens.json', 'slack_tokens.json']

for fname in FILES:
    path = os.path.join(BASEDIR, fname)
    if not os.path.isfile(path):
        continue
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        continue
    changed = False
    for k, v in list(data.items()):
        if isinstance(v, dict):
            # access_token
            at = v.get('access_token')
            if at and isinstance(at, str) and not at.startswith('gAAAA'):
                try:
                    data[k]['access_token'] = token_storage.encrypt_token(at)
                    changed = True
                except Exception:
                    pass
            # refresh_token
            rt = v.get('refresh_token')
            if rt and isinstance(rt, str) and not rt.startswith('gAAAA'):
                try:
                    data[k]['refresh_token'] = token_storage.encrypt_token(rt)
                    changed = True
                except Exception:
                    pass
        elif isinstance(v, str):
            # Github older format: string token
            if v and isinstance(v, str) and not v.startswith('gAAAA'):
                try:
                    data[k] = {'access_token': token_storage.encrypt_token(v)}
                    changed = True
                except Exception:
                    pass
    if changed:
        with open(path, 'w') as f:
            json.dump(data, f)
        print(f'Updated {path}')
    else:
        print(f'No changes for {path}')
print('Migration complete')
