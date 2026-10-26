"""One reviewed Naturalness transition; no new scope or historical exceptions."""
import hashlib,json
import pytest
import protected_integrity as integrity
from test_protected_integrity_policy import workspace


def test_premise_active_source_is_exact(workspace):
    root,_=workspace;policy=json.loads(integrity.PREMISE_EVIDENCE_PATH.read_text());path=next(iter(policy['files']));previous=policy['files'][path]['previousSha256']
    integrity.assert_manifest_integrity(root,{path:previous})
    (root/path).write_text('unreviewed edit')
    with pytest.raises(AssertionError,match='active implementation changed'):integrity.assert_manifest_integrity(root,{path:previous})


def test_premise_scope_cannot_expand(workspace,tmp_path,monkeypatch):
    root,_=workspace;policy=json.loads(integrity.PREMISE_EVIDENCE_PATH.read_text());policy['files']['intelligence/docs/frozen.json']={}
    p=tmp_path/'bad.json';p.write_text(json.dumps(policy));monkeypatch.setattr(integrity,'PREMISE_EVIDENCE_PATH',p);monkeypatch.setattr(integrity,'PREMISE_EVIDENCE_SHA256',hashlib.sha256(p.read_bytes()).hexdigest())
    with pytest.raises(AssertionError,match='Unreviewed premise evidence scope'):integrity.load_policy(root)


def test_premise_approval_record_cannot_change(workspace):
    root,_=workspace;policy=json.loads(integrity.PREMISE_EVIDENCE_PATH.read_text());(root/policy['evidence'][0]['path']).write_text('{}')
    with pytest.raises(AssertionError,match='Premise evidence approval changed'):integrity.load_policy(root)


def test_premise_hash_must_match_reviewed_record(workspace,tmp_path,monkeypatch):
    root,_=workspace;policy=json.loads(integrity.PREMISE_EVIDENCE_PATH.read_text());policy['files'][next(iter(policy['files']))]['approvedSha256']='0'*64
    p=tmp_path/'bad.json';p.write_text(json.dumps(policy));monkeypatch.setattr(integrity,'PREMISE_EVIDENCE_PATH',p);monkeypatch.setattr(integrity,'PREMISE_EVIDENCE_SHA256',hashlib.sha256(p.read_bytes()).hexdigest())
    with pytest.raises(AssertionError,match='reviewed record'):integrity.load_policy(root)
