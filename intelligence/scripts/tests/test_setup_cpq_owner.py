"""Isolated PTY tests: synthetic secrets, stub deployment, no real owner setup."""
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'setup-cpq-owner.sh'
FAKE = 'SYNTHETIC_TEST_ONLY_' + 'x' * 48


class OwnerSetupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cpq-owner-script-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        scripts = self.root / 'repo/intelligence/scripts'
        scripts.mkdir(parents=True)
        self.script = scripts / SCRIPT.name
        shutil.copy2(SCRIPT, self.script)
        deploy = scripts / 'deploy.sh'
        deploy.write_text('#!/bin/sh\n[ "$CPQ_PILOT_REAL_ENABLED" = false ] || exit 99\nprintf "%s" "$CPQ_OWNER_ID" > "$TEST_DEPLOY_MARKER"\nexit "${TEST_DEPLOY_EXIT:-0}"\n')
        deploy.chmod(0o700)
        modules = self.root / 'modules'
        modules.mkdir()
        (modules / 'secrets.py').write_text('def token_urlsafe(n):\n    return ' + repr(FAKE) + '\n')
        # --check has no network access and must still leave the disk unchanged.
        (modules / 'sitecustomize.py').write_text('import urllib.request\ndef offline(*a, **k):\n    raise OSError("offline test")\nurllib.request.urlopen = offline\n')
        self.private = self.root / 'private'
        self.marker = self.root / 'stub-deploy-marker'
        self.env = dict(os.environ, CPQ_OWNER_CONFIG_DIR=str(self.private),
                        PYTHONPATH=str(modules), TEST_DEPLOY_MARKER=str(self.marker))

    def seed(self, profile=True, credential=True):
        self.private.mkdir(mode=0o700)
        if profile:
            (self.private / 'owner.json').write_text('{"ownerId":"test-owner"}\n')
            (self.private / 'owner.json').chmod(0o600)
        if credential:
            (self.private / 'credential').write_text(FAKE + '\n')
            (self.private / 'credential').chmod(0o600)

    def snapshot(self):
        return {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
                for p in self.private.rglob('*') if p.is_file()} if self.private.exists() else {}

    def interactive(self, answer=b'test-owner\n', interrupt=False, env=None):
        pid, master = pty.fork()
        if pid == 0:
            os.execve(str(self.script), [str(self.script)], env or self.env)
        output = b''
        status = None
        answered = False
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if select.select([master], [], [], .05)[0]:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    output += chunk
                    if b'Choose your own' in output and not answered:
                        answered = True
                        if interrupt:
                            os.killpg(pid, signal.SIGINT)
                        else:
                            os.write(master, answer)
                done, current = os.waitpid(pid, os.WNOHANG)
                if done:
                    status = current
                    break
            else:
                os.kill(pid, signal.SIGKILL)
                self.fail('Interactive setup timed out')
        finally:
            os.close(master)
            if status is None:
                _, status = os.waitpid(pid, 0)
        text = output.decode(errors='replace')
        self.assertNotIn(FAKE, text, 'Synthetic credential leaked to terminal')
        return os.waitstatus_to_exitcode(status), text

    def test_interactive_mac_compatible_terminal_and_permissions(self):
        code, output = self.interactive()
        self.assertEqual(code, 0, output)
        self.assertEqual(json.loads((self.private / 'owner.json').read_text()), {'ownerId': 'test-owner'})
        self.assertEqual((self.private / 'credential').read_text(), FAKE + '\n')
        self.assertEqual((self.private / 'credential').stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.private.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.marker.read_text(), 'test-owner')

    def test_existing_identity_and_credential_are_preserved(self):
        self.seed()
        before = self.snapshot()
        code, output = self.interactive()
        self.assertEqual(code, 0, output)
        self.assertEqual(before, self.snapshot())
        self.assertNotIn('Choose your own', output)

    def test_noninteractive_creates_nothing(self):
        result = subprocess.run([str(self.script)], env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.private.exists())
        self.assertFalse(self.marker.exists())

    def test_check_read_only_with_and_without_configuration(self):
        for configured in (False, True):
            if configured:
                self.seed()
            before = self.snapshot()
            result = subprocess.run([str(self.script), '--check'], env=self.env, capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(before, self.snapshot())
            self.assertEqual(self.private.exists(), configured)
            self.assertFalse(self.marker.exists())
            self.assertNotIn(FAKE.encode(), result.stdout + result.stderr)

    def test_interruption_before_identity_creates_nothing(self):
        code, output = self.interactive(interrupt=True)
        self.assertNotEqual(code, 0, output)
        self.assertFalse(self.private.exists())
        self.assertFalse(self.marker.exists())

    def test_profile_only_partial_setup_resumes_same_identity(self):
        self.seed(credential=False)
        before = (self.private / 'owner.json').read_bytes()
        code, output = self.interactive()
        self.assertEqual(code, 0, output)
        self.assertEqual(before, (self.private / 'owner.json').read_bytes())
        self.assertEqual(self.marker.read_text(), 'test-owner')

    def test_orphan_credential_refuses_identity_assignment(self):
        self.seed(profile=False)
        before = self.snapshot()
        code, output = self.interactive()
        self.assertNotEqual(code, 0, output)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.marker.exists())

    def test_incomplete_profile_and_credential_are_preserved(self):
        for filename in ('owner.json', 'credential'):
            with self.subTest(filename=filename):
                if self.private.exists():
                    shutil.rmtree(self.private)
                self.seed()
                (self.private / filename).write_text('')
                before = self.snapshot()
                code, output = self.interactive()
                self.assertNotEqual(code, 0, output)
                self.assertEqual(before, self.snapshot())
                self.assertFalse(self.marker.exists())

    def test_failed_deployment_can_resume_without_rotation(self):
        code, output = self.interactive(env=dict(self.env, TEST_DEPLOY_EXIT='7'))
        self.assertNotEqual(code, 0, output)
        before = self.snapshot()
        code, output = self.interactive()
        self.assertEqual(code, 0, output)
        self.assertEqual(before, self.snapshot())

    def test_invalid_identity_creates_nothing(self):
        code, output = self.interactive(answer=b'bad identity\n')
        self.assertNotEqual(code, 0, output)
        self.assertFalse(self.private.exists())

    def test_symbolic_link_configuration_rejected(self):
        actual = self.root / 'actual'
        actual.mkdir()
        self.private.symlink_to(actual, target_is_directory=True)
        code, output = self.interactive()
        self.assertNotEqual(code, 0, output)
        self.assertEqual(list(actual.iterdir()), [])
        self.assertFalse(self.marker.exists())


if __name__ == '__main__':
    unittest.main()
