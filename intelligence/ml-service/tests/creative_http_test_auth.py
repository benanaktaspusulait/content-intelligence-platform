"""Sign mocked role HTTP traffic exactly as the durable backend boundary does."""
import hashlib
import hmac
import json


def post_role(client, body, monkeypatch):
    token='offline-disposable-dispatch-token-only-0001'
    monkeypatch.setenv('WORKFLOW_ADAPTIVE_DISPATCH_TOKEN',token)
    raw=json.dumps(body,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
    signature=hmac.new(token.encode(),raw,hashlib.sha256).hexdigest()
    return client.post('/api/v1/workflow/creative-role',content=raw,headers={'Content-Type':'application/json','X-Adaptive-Dispatch':signature})
