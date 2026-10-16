#!/usr/bin/env python3
"""Explicit future-execution launcher for the disposable two-provider experiment.

Preparation never invokes this file. It has no fixture path and denies every
outbound socket except the two checked-in provider origins.
"""
import atexit
import json
import os
from pathlib import Path
import socket
import sys
from urllib.parse import urlparse

if os.getenv('POMPOM_DISPOSABLE_REAL_PROVIDER') != 'true':
    raise SystemExit('Dedicated disposable real-provider mode is required')
if os.getenv('CPQ_PILOT_REAL_ENABLED') != 'true':
    raise SystemExit('A fresh authorization must explicitly enable real dispatch')
if os.getenv('POMPOM_ISOLATED_FIXTURE_DIR') or os.getenv('POMPOM_ISOLATED_FIXTURE_TOKEN'):
    raise SystemExit('Fixture transport is forbidden in real-provider mode')
if not os.getenv('OPENAI_API_KEY') or not os.getenv('DEEPSEEK_API_KEY'):
    raise SystemExit('Both experiment-scoped provider credentials are required')
if len(os.getenv('WORKFLOW_ADAPTIVE_DISPATCH_TOKEN', '')) < 32:
    raise SystemExit('Signed backend-to-ML dispatch is required')

root=Path(os.getenv('POMPOM_DATA_ROOT','data'))
catalog=json.loads((root/'workflow/creative-provider-profiles-v3.json').read_text())
hosts={urlparse(v['baseUrl']).hostname for v in catalog['profiles'].values()}
if hosts != {'api.deepseek.com','api.openai.com'}:
    raise SystemExit('Provider endpoint allowlist differs from the reviewed catalog')

# Resolve only the reviewed provider names before socket enforcement. Provider
# IP rotation is handled by starting a fresh, newly authorized process.
allowed_ips=set()
for host in sorted(hosts):
    for row in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM): allowed_ips.add(row[4][0])
blocked=[]
loopback={'127.0.0.1','::1','localhost'}
def audit(event,args):
    if event=='socket.getaddrinfo' and args[0] not in hosts|loopback:
        blocked.append({'event':event,'target':str(args[0])});raise PermissionError('External DNS denied')
    if event=='socket.connect':
        sock,address=args
        if sock.family in (socket.AF_INET,socket.AF_INET6):
            host,port=address[0],address[1]
            if port==443 and host in allowed_ips:return
            blocked.append({'event':event,'target':f'{host}:{port}'});raise PermissionError('Outbound destination denied')
    if event=='socket.bind' and args[0].family in (socket.AF_INET,socket.AF_INET6) and args[1][0] not in loopback:
        raise PermissionError('Disposable ML may bind only loopback')
sys.addaudithook(audit)

audit_path=Path(os.environ['POMPOM_DISPOSABLE_NETWORK_AUDIT'])
def write_audit():
    audit_path.write_text(json.dumps({'policy':'EXACT_PROVIDER_ORIGINS_ONLY','allowedHosts':sorted(hosts),'blockedAttempts':blocked,'fixtureFallbackAllowed':False},indent=2)+'\n')
atexit.register(write_audit);write_audit()

import uvicorn  # noqa: E402
from app.main import app  # noqa: E402
uvicorn.run(app,host='127.0.0.1',port=int(os.getenv('POMPOM_DISPOSABLE_ML_PORT','18000')),log_level='warning')
