"""The evaluator migration approves one exact active source transition."""
import hashlib
import json

import pytest
import protected_integrity as integrity
from test_protected_integrity_policy import workspace

def test_opening_evidence_source_is_exactly_approved(workspace):
    root,_=workspace
    migrations=integrity.load_opening_evidence(root)
    path='intelligence/ml-service/app/workflow/premise_admission_evidence.py';migration=migrations[path]
    assert integrity.sha256(root/path)==migration['approvedSha256']
    previous=migration['previousSha256']
    for old in previous if isinstance(previous,list) else [previous]: integrity.assert_manifest_integrity(root,{path:old})
    integrity.assert_manifest_integrity(root,{path:migration['approvedSha256']})
    (root/path).write_text('unreviewed opening evaluator edit')
    with pytest.raises(AssertionError,match='active implementation changed'):
        integrity.assert_manifest_integrity(root,{path:(previous[0] if isinstance(previous,list) else previous)})


def test_opening_evidence_scope_cannot_expand_even_when_repinned(workspace,tmp_path,monkeypatch):
    root,_=workspace;policy=json.loads(integrity.OPENING_EVIDENCE_PATH.read_text())
    policy['files']['intelligence/ml-service/app/unrelated.py']={}
    target=tmp_path/'expanded.json';target.write_text(json.dumps(policy))
    monkeypatch.setattr(integrity,'OPENING_EVIDENCE_PATH',target)
    monkeypatch.setattr(integrity,'OPENING_EVIDENCE_SHA256',hashlib.sha256(target.read_bytes()).hexdigest())
    with pytest.raises(AssertionError,match='Unreviewed opening evidence scope'):
        integrity.load_opening_evidence(root)


def test_opening_evidence_approval_records_are_immutable(workspace):
    root,_=workspace;policy=json.loads(integrity.OPENING_EVIDENCE_PATH.read_text())
    (root/policy['evidence'][0]['path']).write_text('{}')
    with pytest.raises(AssertionError,match='Opening evidence approval changed'):
        integrity.load_opening_evidence(root)


def test_opening_evidence_hashes_must_match_reviewed_before_after_records(workspace,tmp_path,monkeypatch):
    root,_=workspace;policy=json.loads(integrity.OPENING_EVIDENCE_PATH.read_text())
    path=next(iter(policy['files']));policy['files'][path]['approvedSha256']='0'*64
    target=tmp_path/'wrong-transition.json';target.write_text(json.dumps(policy))
    monkeypatch.setattr(integrity,'OPENING_EVIDENCE_PATH',target)
    monkeypatch.setattr(integrity,'OPENING_EVIDENCE_SHA256',hashlib.sha256(target.read_bytes()).hexdigest())
    with pytest.raises(AssertionError,match='Opening evidence hash differs'):
        integrity.load_opening_evidence(root)
