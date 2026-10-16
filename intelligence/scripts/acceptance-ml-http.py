#!/usr/bin/env python3
"""Launch the existing FastAPI fixture transport with process-local no-egress enforcement.

Only the acceptance harness invokes this helper. No provider, schema, or application route is replaced.
"""
import atexit
import json
import os
from pathlib import Path
import socket
import sys

if os.environ.get('POMPOM_ISOLATED_ACCEPTANCE') != 'true':
    raise SystemExit('Explicit disposable fixture mode is required')
port_file = Path(sys.argv[1])
audit_file = Path(sys.argv[2])
blocked = []
sdk_construction_attempts = []
loopback = {'127.0.0.1', 'localhost', '::1'}


def deny_egress(event, args):
    if event == 'socket.connect':
        sock, address = args
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            # The ML fixture has no reason to open any outgoing connection, including production localhost.
            if address != ('198.51.100.1', 443):
                blocked.append({'event': event, 'target': str(address)})
            raise PermissionError('Isolated ML acceptance denies outgoing network connections')
    elif event == 'socket.getaddrinfo' and args[0] not in loopback:
        blocked.append({'event': event, 'target': str(args[0])})
        raise PermissionError('Isolated ML acceptance denies external DNS')
    elif event == 'socket.bind':
        sock, address = args
        if sock.family in (socket.AF_INET, socket.AF_INET6) and address[0] not in loopback:
            raise PermissionError('Isolated ML acceptance may bind only loopback')


sys.addaudithook(deny_egress)
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.connect(('198.51.100.1', 443))
except PermissionError:
    negative_probe = 'DENIED_BEFORE_DISPATCH'
else:
    raise SystemExit('No-egress negative probe unexpectedly connected')


def write_audit():
    audit_file.write_text(json.dumps({'negativeProbe': negative_probe,
                                     'unexpectedEgressAttempts': blocked,
                                     'realSdkConstructors': 'DISABLED_IN_ISOLATED_LAUNCHER',
                                     'realSdkConstructionAttempts': sdk_construction_attempts,
                                     'noExternalEgress': not blocked and not sdk_construction_attempts}), encoding='utf-8')


atexit.register(write_audit)
write_audit()
# Imports occur after the guard so SDK construction/import side effects cannot send network traffic.
import uvicorn  # noqa: E402
import openai  # noqa: E402


def unavailable_real_sdk(*args, **kwargs):
    sdk_construction_attempts.append('Real SDK constructor was requested')
    raise RuntimeError('Real provider SDK clients are unavailable in isolated acceptance')


# Every existing OpenAI-compatible adapter keeps its normal class reference, but cannot
# construct an SDK client in this process. Fixture transport does not use these constructors.
openai.OpenAI.__init__ = unavailable_real_sdk
openai.AsyncOpenAI.__init__ = unavailable_real_sdk

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('127.0.0.1', 0))
sock.listen(128)
port_file.write_text(str(sock.getsockname()[1]), encoding='ascii')
# Audit and authenticate the actual role HTTP requests, using the normal client HMAC header.
# This wrapper is only in the isolated launcher; application routes/parsers remain unchanged.
from app.main import app
from fastapi.responses import JSONResponse
import hashlib
import hmac

@app.middleware('http')
async def record_role_transport(request, call_next):
    if request.url.path == '/api/v1/workflow/creative-role':
        raw = await request.body()
        token = os.environ.get('WORKFLOW_ADAPTIVE_DISPATCH_TOKEN', '')
        valid = len(token) >= 32 and hmac.compare_digest(
            request.headers.get('X-Adaptive-Dispatch', ''), hmac.new(token.encode(), raw, hashlib.sha256).hexdigest())
        # Harness bootstrap probe is also signed; no role dispatch without authentication.
        if not valid:
            return JSONResponse({'detail':'Isolated role HMAC authorization failed','providerDispatched':False}, status_code=403)
        with (audit_file.parent / 'ml-role-http.jsonl').open('a') as trace:
            trace.write(json.dumps({'request':json.loads(raw),'hmacVerified':True})+'\n')
    return await call_next(request)

config = uvicorn.Config(app, host='127.0.0.1', port=0, log_level='warning')
uvicorn.Server(config).run(sockets=[sock])
write_audit()
