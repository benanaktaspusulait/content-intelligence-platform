#!/usr/bin/env python3
"""Run text-validation tests with outbound sockets and media processes denied.

Usage (from ml-service): .venv/bin/python ../scripts/test-story-premise-offline.py
Pass pytest arguments to select a smaller suite. Media QA tests are excluded by
default because they synthesize video/image fixtures. Frozen data/docs are read-only.
"""

import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT / "ml-service")
sys.path.insert(0, str(ROOT / "ml-service"))
for key in tuple(os.environ):
    if key.endswith("_API_KEY") or key.endswith("_API_TOKEN"):
        os.environ.pop(key)
os.environ["WORKFLOW_CREATIVE_ROLES_ENABLED"] = "false"
os.environ["CPQ_PILOT_REAL_ENABLED"] = "false"
# Use a disposable copy of configuration so inherited test data roots cannot
# omit provider-contract fixtures and no test can rewrite production history.
workspace = tempfile.TemporaryDirectory(prefix="pompom-premise-tests-")
for folder in ("rules", "workflow", "golden", "test_cases", "model-artifacts"):
    source = ROOT / "data" / folder
    if source.is_dir():
        shutil.copytree(source, Path(workspace.name) / folder)
os.environ["POMPOM_DATA_ROOT"] = workspace.name
frozen = (ROOT / "data", ROOT / "docs")


def guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo"}:
        raise RuntimeError("Offline verification forbids outbound network access")
    if event == "subprocess.Popen":
        if args[1] != ["git", "rev-parse", "HEAD"]:
            raise RuntimeError(
                "Offline text verification permits only read-only git provenance, no media execution"
            )
    if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).resolve()
        flags = args[2] or 0
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            if any(path.is_relative_to(root) for root in frozen):
                raise RuntimeError("Frozen validation data and historical docs are read-only")
    if event in {"os.remove", "os.rmdir", "os.rename"}:
        for value in args[:2] if event == "os.rename" else args[:1]:
            if isinstance(value, (str, bytes, os.PathLike)):
                path = Path(os.fsdecode(value)).resolve()
                if any(path.is_relative_to(root) for root in frozen):
                    raise RuntimeError("Frozen validation data and historical docs are read-only")


sys.addaudithook(guard)
import pytest

arguments = sys.argv[1:] or ["tests", "--ignore=tests/qa", "--ignore=tests/test_video_qc.py", "-q"]
raise SystemExit(pytest.main(arguments))
