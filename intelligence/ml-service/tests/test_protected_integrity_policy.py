"""No skipped protection: exact approved active transitions and strict evidence."""

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import protected_integrity as integrity
import pytest

ROOT = Path(__file__).parents[3]
CORE = "intelligence/ml-service/app/workflow/short_form_engine.py"


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def workspace(tmp_path):
    policy = json.loads(integrity.POLICY_PATH.read_text())
    for section in ["architectureApproval", "integrityRepairApproval"]:
        for ref in policy[section]["evidence"]:
            p = tmp_path / ref["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / ref["path"], p)
        for name in policy[section]["files"]:
            p = tmp_path / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, p)
    propagation = json.loads(integrity.PROPAGATION_PATH.read_text())
    for ref in propagation["evidence"]:
        p = tmp_path / ref["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / ref["path"], p)
    for name in propagation["files"]:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, p)
    beat_evidence = json.loads(integrity.BEAT_EVIDENCE_PATH.read_text())
    for ref in beat_evidence["evidence"]:
        p = tmp_path / ref["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / ref["path"], p)
    for name in beat_evidence["files"]:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, p)
    premise_evidence=json.loads(integrity.PREMISE_EVIDENCE_PATH.read_text())
    for ref in premise_evidence["evidence"]:
        p=tmp_path/ref["path"]
        p.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/ref["path"],p)
    for name in premise_evidence["files"]:
        p=tmp_path/name
        p.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,p)
    return tmp_path, policy


def test_reviewed_policy_scopes_are_exact_and_all_current_sources_pinned():
    approvals = integrity.load_policy(ROOT)
    assert set(approvals) == integrity.ACTIVE_IMPLEMENTATIONS | integrity.INTEGRITY_TEST_ADAPTERS | integrity.PROPAGATION_IMPLEMENTATIONS | integrity.BEAT_EVIDENCE_IMPLEMENTATIONS
    assert len(integrity.ACTIVE_IMPLEMENTATIONS) == 2
    for path, entry in approvals.items():
        assert digest(ROOT / path) == entry["approvedSha256"]


def test_historical_and_current_active_references_validate_without_manifest_rewrite(workspace):
    root, policy = workspace
    entry = policy["architectureApproval"]["files"][CORE]
    for value in entry.values():
        manifest = {CORE: value}
        original = deepcopy(manifest)
        integrity.assert_manifest_integrity(root, manifest)
        assert manifest == original


def test_unreviewed_active_edit_is_rejected(workspace):
    root, policy = workspace
    entry = policy["architectureApproval"]["files"][CORE]
    (root / CORE).write_text("Unreviewed change")
    with pytest.raises(AssertionError, match="active implementation changed"):
        integrity.assert_manifest_integrity(root, {CORE: entry["historicalSha256"]})


def test_rollback_to_historical_source_is_rejected(workspace):
    root, policy = workspace
    source = (
        ROOT
        / "intelligence/docs/semantic-live-v1-seed-42-count-40-structured-sfe-v1"
        / "legacy-short-form-engine.py.txt"
    )
    shutil.copyfile(source, root / CORE)
    expected = policy["architectureApproval"]["files"][CORE]["historicalSha256"]
    assert digest(root / CORE) == expected
    with pytest.raises(AssertionError, match="active implementation changed"):
        integrity.assert_manifest_integrity(root, {CORE: expected})


def test_unknown_historical_revision_is_not_allowed(workspace):
    root, _ = workspace
    with pytest.raises(AssertionError, match="Unapproved historical"):
        integrity.assert_manifest_integrity(root, {CORE: "0" * 64})


@pytest.mark.parametrize(
    "path",
    [
        "intelligence/docs/frozen.json",
        "intelligence/data/frozen.json",
        "intelligence/ml-service/app/unrelated.py",
        "intelligence/ml-service/tests/fixtures/other.json",
    ],
)
def test_every_unlisted_path_remains_strictly_protected(workspace, path):
    root, _ = workspace
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("original")
    manifest = {path: digest(p)}
    integrity.assert_manifest_integrity(root, manifest)
    p.write_text("changed")
    with pytest.raises(AssertionError, match="Frozen evidence/unapproved code changed"):
        integrity.assert_manifest_integrity(root, manifest)


def test_approval_evidence_is_immutable(workspace):
    root, policy = workspace
    ref = policy["architectureApproval"]["evidence"][0]
    (root / ref["path"]).write_text("{}")
    with pytest.raises(AssertionError, match="Approval evidence changed"):
        integrity.load_policy(root)


def test_policy_tampering_is_rejected_by_pin(workspace, tmp_path, monkeypatch):
    root, policy = workspace
    policy["architectureApproval"]["files"][CORE]["approvedSha256"] = "0" * 64
    path = tmp_path / "tampered-policy.json"
    path.write_text(json.dumps(policy))
    monkeypatch.setattr(integrity, "POLICY_PATH", path)
    with pytest.raises(AssertionError, match="reviewed pin"):
        integrity.load_policy(root)


def test_policy_scope_cannot_approve_frozen_evidence_even_if_repinned(workspace, tmp_path, monkeypatch):
    root, policy = workspace
    policy["architectureApproval"]["files"]["intelligence/docs/frozen.json"] = {}
    path = tmp_path / "invalid-scope.json"
    path.write_text(json.dumps(policy))
    monkeypatch.setattr(integrity, "POLICY_PATH", path)
    monkeypatch.setattr(integrity, "POLICY_SHA256", digest(path))
    with pytest.raises(AssertionError, match="Unreviewed active integrity scope"):
        integrity.load_policy(root)


def test_reviewed_hashes_must_match_architecture_record_even_if_repinned(workspace, tmp_path, monkeypatch):
    root, policy = workspace
    policy["architectureApproval"]["files"][CORE]["approvedSha256"] = "0" * 64
    path = tmp_path / "invalid-record.json"
    path.write_text(json.dumps(policy))
    monkeypatch.setattr(integrity, "POLICY_PATH", path)
    monkeypatch.setattr(integrity, "POLICY_SHA256", digest(path))
    with pytest.raises(AssertionError, match="differs from reviewed record"):
        integrity.load_policy(root)


def test_symlink_cannot_bypass_active_rollback_check(workspace):
    root, policy = workspace
    source = (
        ROOT
        / "intelligence/docs/semantic-live-v1-seed-42-count-40-structured-sfe-v1"
        / "legacy-short-form-engine.py.txt"
    )
    alias = root / "old-source.txt"
    shutil.copyfile(source, alias)
    (root / CORE).unlink()
    (root / CORE).symlink_to(alias)
    with pytest.raises(AssertionError, match="active implementation changed"):
        integrity.assert_manifest_integrity(
            root, {CORE: policy["architectureApproval"]["files"][CORE]["historicalSha256"]}
        )


def test_path_escape_rejected(workspace):
    root, _ = workspace
    with pytest.raises(AssertionError, match="Non-canonical protected path"):
        integrity.assert_manifest_integrity(root, {"../outside": "0" * 64})
