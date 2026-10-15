#!/usr/bin/env bash
# Run interactively by the actual owner. Never prints or transmits the credential.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 - "$script_dir/../.." "$@" <<'PY'
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import stat
import subprocess
import sys
import urllib.request

project = Path(sys.argv[1]).resolve()
args = sys.argv[2:]
private_dir = Path(os.environ.get('CPQ_OWNER_CONFIG_DIR', str(Path.home() / '.config/pompom-owner'))).expanduser().absolute()
credential = private_dir / 'credential'
profile = private_dir / 'owner.json'

if args == ['--check']:
    try:
        with urllib.request.urlopen('http://localhost:4200/api/v1/intelligence/workflow/owner-auth', timeout=10) as response:
            state = json.load(response)
        print('Owner authentication configured:', bool(state.get('configured')))
    except Exception:
        print('Application owner status unavailable; start the existing local stack first.')
    private = credential.is_file() and not credential.is_symlink()
    permissions = private and stat.S_IMODE(credential.stat().st_mode) & 0o077 == 0
    print('Private local credential exists:', private)
    print('Credential has owner-only permissions:', bool(permissions))
    print('No setup, login, deployment or inference performed.')
    sys.exit(0)
if args:
    sys.exit('Usage: ./intelligence/scripts/setup-cpq-owner.sh [--check]')
if not sys.stdout.isatty():
    sys.exit('Run this setup yourself in a local interactive terminal. No identity or credential was created.')
if private_dir.is_symlink() or credential.is_symlink() or profile.is_symlink():
    sys.exit('Refusing symbolic links for private owner configuration.')
if private_dir.is_relative_to(project):
    sys.exit('Owner credentials must live outside the repository.')

saved = json.loads(profile.read_text()) if profile.exists() else {}
owner_id = saved.get('ownerId', '')
if not owner_id:
    with open('/dev/tty', 'r+') as terminal:
        terminal.write('Choose your own local owner identifier (3–80 letters, digits, . _ @ -): ')
        terminal.flush()
        owner_id = terminal.readline().strip()
if not isinstance(owner_id, str) or not re.fullmatch(r'[A-Za-z0-9._@-]{3,80}', owner_id):
    sys.exit('Invalid owner identifier; no credential was created.')
private_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
os.chmod(private_dir, 0o700)
if credential.exists():
    if not credential.is_file() or stat.S_IMODE(credential.stat().st_mode) & 0o077 or not 32 <= credential.stat().st_size <= 1025:
        sys.exit('Existing credential is not a valid private file. Resolve it locally; it was not overwritten.')
else:
    fd = os.open(credential, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(secrets.token_urlsafe(48) + '\n')
if not profile.exists():
    fd = os.open(profile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        json.dump({'ownerId': owner_id}, handle)
        handle.write('\n')

env = dict(os.environ, CPQ_OWNER_ID=owner_id, CPQ_OWNER_CONFIG_DIR=str(private_dir), CPQ_PILOT_REAL_ENABLED='false')
print('Private owner configuration prepared. Credential contents are not displayed.')
print('Deploying backend with real AI dispatch disabled; no production review is created.')
subprocess.run([str(project / 'intelligence/scripts/deploy.sh'), 'backend'], cwd=project, env=env, check=True)
print('Open Step 6 → Creative Optimization → Inspect owner pilot → Owner login.')
print('On macOS, copy the credential privately in your terminal if needed:')
print('pbcopy < ' + shlex.quote(str(credential)))
print('Paste only into the local owner login, then clear your clipboard. Never send it to an AI chat.')
print('For later deployments preserving owner configuration, rerun this script; it reuses the private identity/credential.')
print('Paid dispatch remains disabled. Any real model run needs separate explicit authorization.')
PY
