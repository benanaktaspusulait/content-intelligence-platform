"""Propagation approvals cannot broaden historical protection or accept unknown bytes."""
import json
from pathlib import Path
import hashlib
import pytest
import protected_integrity as integrity
from test_protected_integrity_policy import workspace


def repin(data,tmp_path,monkeypatch):
    p=tmp_path/'policy-propagation.json';p.write_text(json.dumps(data))
    monkeypatch.setattr(integrity,'PROPAGATION_PATH',p)
    monkeypatch.setattr(integrity,'PROPAGATION_SHA256',hashlib.sha256(p.read_bytes()).hexdigest())


@pytest.mark.parametrize('path',sorted(integrity.PROPAGATION_IMPLEMENTATIONS))
def test_each_propagation_source_remains_strict(workspace,path):
    root,_=workspace
    policy=json.loads(integrity.PROPAGATION_PATH.read_text())
    old=policy['files'][path]['previousSha256']
    integrity.assert_manifest_integrity(root,{path:old})
    (root/path).write_text('unreviewed code change')
    with pytest.raises(AssertionError,match='active implementation changed'):
        integrity.assert_manifest_integrity(root,{path:old})


def test_propagation_scope_cannot_expand_to_history(workspace,tmp_path,monkeypatch):
    root,_=workspace;p=json.loads(integrity.PROPAGATION_PATH.read_text())
    p['files']['intelligence/docs/frozen.json']={};p['scope'].append('intelligence/docs/frozen.json')
    repin(p,tmp_path,monkeypatch)
    with pytest.raises(AssertionError,match='Unreviewed propagation scope'):integrity.load_policy(root)


def test_propagation_hash_must_match_approval_record(workspace,tmp_path,monkeypatch):
    root,_=workspace;p=json.loads(integrity.PROPAGATION_PATH.read_text())
    p['files'][next(iter(p['files']))]['approvedSha256']='0'*64
    repin(p,tmp_path,monkeypatch)
    with pytest.raises(AssertionError,match='reviewed record'):integrity.load_policy(root)


def test_propagation_evidence_cannot_change(workspace):
    root,_=workspace;p=json.loads(integrity.PROPAGATION_PATH.read_text())
    (root/p['evidence'][0]['path']).write_text('{}')
    with pytest.raises(AssertionError,match='approval evidence changed'):integrity.load_policy(root)
