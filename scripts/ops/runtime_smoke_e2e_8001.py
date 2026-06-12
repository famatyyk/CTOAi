import json
import os
import urllib.request

base = os.getenv('CTOA_RUNTIME_SMOKE_BASE', 'http://127.0.0.1:8001')

def req(path, method='GET', token=None, payload=None):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, json.loads(response.read().decode('utf-8'))

status, data = req('/api/auth/login', 'POST', payload={'username': 'famatyyk', 'password': 'ctoa-owner'})
assert status == 200, data
token = data['token']

status, data = req('/api/auth/me', token=token)
assert status == 200 and data['user']['role'] == 'owner', data

status, data = req('/api/community/invites', token=token)
assert status == 200, data

print('RUNTIME_SMOKE_E2E_OK')
