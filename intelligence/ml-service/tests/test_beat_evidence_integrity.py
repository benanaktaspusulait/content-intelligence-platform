"""The new approval admits only the two reviewed source transitions."""
import hashlib
import json
import pytest
import protected_integrity as integrity
from test_protected_integrity_policy import workspace


@pytest.mark.parametrize('path',sorted(integrity.BEAT_EVIDENCE_IMPLEMENTATIONS))
def test_reviewed_beat_evidence_source_cannot_drift(workspace,path):
    root,_=workspace;policy=json.loads(integrity.BEAT_EVIDENCE_PATH.read_text())
    previous=policy['files'][path]['previousSha256']
    integrity.assert_manifest_integrity(root,{path:previous})
    (root/path).write_text('unreviewed source')
    with pytest.raises(AssertionError,match='active implementation changed'):
        integrity.assert_manifest_integrity(root,{path:previous})


def test_beat_scope_cannot_expand(workspace,tmp_path,monkeypatch):
    root,_=workspace;policy=json.loads(integrity.BEAT_EVIDENCE_PATH.read_text())
    policy['files']['intelligence/docs/history.json']={}
    p=tmp_path/'invalid-policy.json';p.write_text(json.dumps(policy))
    monkeypatch.setattr(integrity,'BEAT_EVIDENCE_PATH',p)
    monkeypatch.setattr(integrity,'BEAT_EVIDENCE_SHA256',hashlib.sha256(p.read_bytes()).hexdigest())
    with pytest.raises(AssertionError,match='Unreviewed beat evidence scope'):integrity.load_policy(root)


def test_beat_approval_record_cannot_change(workspace):
    root,_=workspace;policy=json.loads(integrity.BEAT_EVIDENCE_PATH.read_text())
    (root/policy['evidence'][0]['path']).write_text('{}')
    with pytest.raises(AssertionError,match='Beat evidence approval changed'):integrity.load_policy(root)


def test_no_beat_policy_tampering_even_without_scope_change(workspace,tmp_path,monkeypatch):
    root,_=workspace;policy=json.loads(integrity.BEAT_EVIDENCE_PATH.read_text())
    policy['files'][next(iter(policy['files']))]['approvedSha256']='0'*64
    p=tmp_path/'invalid-policy.json';p.write_text(json.dumps(policy))
    monkeypatch.setattr(integrity,'BEAT_EVIDENCE_PATH',p)
    monkeypatch.setattr(integrity,'BEAT_EVIDENCE_SHA256',hashlib.sha256(p.read_bytes()).hexdigest())
    with pytest.raises(AssertionError,match='reviewed record'):integrity.load_policy(root)
