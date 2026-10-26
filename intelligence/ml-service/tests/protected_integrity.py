"""Strict frozen-evidence hashes plus exact reviewed active-code migrations.

Historical manifests are never rewritten. Only the explicitly reviewed source
paths/from/to hashes below can resolve to an approved current implementation.
No directories, globs, skipped checks or synthetic historical digests are used.
"""

import hashlib
import json
from pathlib import Path

POLICY_PATH = Path(__file__).parent / "fixtures/approved_active_integrity_v1.json"
POLICY_SHA256 = "6d8389e5cc567d8408e404c3e11294337200fb64970ed30403d92e751661ff57"
ACTIVE_IMPLEMENTATIONS = frozenset(
    {
        "intelligence/ml-service/app/workflow/short_form_engine.py",
        "intelligence/ml-service/app/workflow/concept_ranking.py",
    }
)
INTEGRITY_TEST_ADAPTERS = frozenset(
    "intelligence/ml-service/tests/" + name
    for name in (
        "test_beat_generation.py",
        "test_concept_ranking.py",
        "test_premise_generation.py",
        "test_semantic_concept_generation.py",
        "test_semantic_evidence_adapter.py",
        "test_shape_generation.py",
        "test_short_concept_generation.py",
        "test_short_concept_v2.py",
        "test_structured_short_form.py",
    )
)


PROPAGATION_PATH = Path(__file__).parent / "fixtures/canonical_evidence_integrity_v1.json"
PROPAGATION_SHA256 = "7f897aec7c40f3a7bc759867abb075e02db96f79637fb013adf6c8c190a8cbff"
PROPAGATION_IMPLEMENTATIONS = frozenset({'intelligence/ml-service/app/workflow/concept_ranking.py','intelligence/ml-service/app/workflow/premise_naturalness.py','intelligence/ml-service/app/workflow/beat_grammar.py','intelligence/ml-service/app/workflow/creative_shape.py'})


def load_propagation(root):
    assert sha256(PROPAGATION_PATH) == PROPAGATION_SHA256, "Propagation policy differs from reviewed pin"
    policy = json.loads(PROPAGATION_PATH.read_text())
    assert set(policy) == {"version", "scope", "files", "evidence"}, "Unexpected propagation sections"
    assert policy["version"] == "canonical-evidence-propagation-integrity-v1"
    assert set(policy["scope"]) == set(policy["files"]) == PROPAGATION_IMPLEMENTATIONS, "Unreviewed propagation scope"
    bound = {}
    for ref in policy["evidence"]:
        path = (root / ref["path"]).resolve()
        assert path.is_relative_to(root.resolve()), "Propagation evidence outside repository"
        assert sha256(path) == ref["sha256"], "Propagation approval evidence changed"
        if ref["role"] in {"historical", "approved"}:
            bound[ref["role"]] = json.loads(path.read_text())
    for role, key in [("historical", "previousSha256"), ("approved", "approvedSha256")]:
        assert bound[role] == {p:v[key] for p,v in policy["files"].items()}, "Propagation differs from reviewed record"
    for entry in policy["files"].values():
        assert set(entry) == {"previousSha256", "approvedSha256"}, "Invalid propagation digest fields"
        assert all(len(v)==64 and set(v)<=set("0123456789abcdef") for v in entry.values())
    return policy["files"]


BEAT_EVIDENCE_PATH = Path(__file__).parent / "fixtures/beat_evidence_integrity_v1.json"
BEAT_EVIDENCE_SHA256 = "5c8dd761bbd6a0638696139918c4d38248b93064f7e65c98364e301a8483eb92"
BEAT_EVIDENCE_IMPLEMENTATIONS = frozenset({'intelligence/ml-service/app/workflow/beat_grammar.py','intelligence/ml-service/app/workflow/canonical_creative_evidence.py'})


def load_beat_evidence(root):
    assert sha256(BEAT_EVIDENCE_PATH) == BEAT_EVIDENCE_SHA256, "Beat evidence policy differs from reviewed pin"
    policy = json.loads(BEAT_EVIDENCE_PATH.read_text())
    assert set(policy) == {"version", "files", "evidence"}, "Unexpected beat evidence sections"
    assert policy["version"] == "beat-evidence-integrity-v1"
    assert set(policy["files"]) == BEAT_EVIDENCE_IMPLEMENTATIONS, "Unreviewed beat evidence scope"
    bound = {}
    for ref in policy["evidence"]:
        path = (root / ref["path"]).resolve()
        assert path.is_relative_to(root.resolve()), "Beat evidence approval outside repository"
        assert sha256(path) == ref["sha256"], "Beat evidence approval changed"
        if ref["role"] in {"historical", "approved"}:
            bound[ref["role"]] = json.loads(path.read_text())
    for role,key in [("historical","previousSha256"),("approved","approvedSha256")]:
        assert bound[role] == {p:v[key] for p,v in policy["files"].items()}, "Beat evidence differs from reviewed record"
    for entry in policy["files"].values():
        assert set(entry) == {"previousSha256", "approvedSha256"}
        assert all(len(v)==64 and set(v)<=set("0123456789abcdef") for v in entry.values())
    return policy["files"]


PREMISE_EVIDENCE_PATH = Path(__file__).parent / "fixtures/premise_evidence_integrity_v1.json"
PREMISE_EVIDENCE_SHA256 = "e510ecb33cb294a22ddb0b30e2ba0baa50f2de5ca85d2cf51c80640801c70b9c"
PREMISE_EVIDENCE_IMPLEMENTATIONS = frozenset({'intelligence/ml-service/app/workflow/premise_naturalness.py'})


def load_premise_evidence(root):
    assert sha256(PREMISE_EVIDENCE_PATH) == PREMISE_EVIDENCE_SHA256, "Premise evidence policy differs from reviewed pin"
    policy=json.loads(PREMISE_EVIDENCE_PATH.read_text())
    assert set(policy) == {"version", "files", "evidence"}, "Unexpected premise evidence sections"
    assert policy["version"] == "premise-evidence-integrity-v1"
    assert set(policy["files"]) == PREMISE_EVIDENCE_IMPLEMENTATIONS, "Unreviewed premise evidence scope"
    bound={}
    for ref in policy["evidence"]:
        path=(root/ref["path"]).resolve()
        assert path.is_relative_to(root.resolve()), "Premise evidence approval outside repository"
        assert sha256(path)==ref["sha256"], "Premise evidence approval changed"
        if ref["role"] in {"historical","approved"}:bound[ref["role"]]=json.loads(path.read_text())
    for role,key in [("historical","previousSha256"),("approved","approvedSha256")]:
        assert bound[role]=={p:v[key] for p,v in policy["files"].items()}, "Premise evidence differs from reviewed record"
    for entry in policy["files"].values():
        assert set(entry)=={"previousSha256","approvedSha256"}
        assert all(len(v)==64 and set(v)<=set("0123456789abcdef") for v in entry.values())
    return policy["files"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_policy(root):
    data = POLICY_PATH.read_bytes()
    assert hashlib.sha256(data).hexdigest() == POLICY_SHA256, (
        "Active integrity policy differs from its reviewed pin"
    )
    policy = json.loads(data)
    assert set(policy) == {"version", "architectureApproval", "integrityRepairApproval"}, (
        "Unexpected policy sections"
    )
    assert policy["version"] == "approved-active-integrity-v1", "Unknown integrity policy version"
    approvals = {}
    for section, paths in [
        ("architectureApproval", ACTIVE_IMPLEMENTATIONS),
        ("integrityRepairApproval", INTEGRITY_TEST_ADAPTERS),
    ]:
        approval = policy[section]
        assert set(approval) == {"id", "evidence", "files"}, "Unexpected approval fields"
        assert set(approval["files"]) == paths, "Unreviewed active integrity scope"
        bound = {}
        for ref in approval["evidence"]:
            p = (root / ref["path"]).resolve()
            assert p.is_relative_to(root.resolve()), "Approval evidence path outside repository"
            assert sha256(p) == ref["sha256"], f"Approval evidence changed: {ref['path']}"
            bound[ref["role"]] = json.loads(p.read_text())
        for role, key in [("historical", "historicalSha256"), ("approved", "approvedSha256")]:
            assert bound.get(role) == {name: value[key] for name, value in approval["files"].items()}, (
                "Migration differs from reviewed record"
            )
        for name, hashes in approval["files"].items():
            assert set(hashes) == {"historicalSha256", "approvedSha256"}, "Invalid migration hash fields"
            assert all(len(h) == 64 and set(h) <= set("0123456789abcdef") for h in hashes.values()), (
                "Invalid migration digest"
            )
            approvals[name] = hashes
    for name, entry in load_propagation(root).items():
        previous = approvals.get(name)
        if previous:
            assert previous["approvedSha256"] == entry["previousSha256"], "Propagation chain is not contiguous"
        approvals[name] = {"historicalSha256": previous["historicalSha256"] if previous else entry["previousSha256"], "approvedSha256": entry["approvedSha256"]}
    for name,entry in load_beat_evidence(root).items():
        previous=approvals.get(name)
        if previous:
            assert previous["approvedSha256"] == entry["previousSha256"], "Beat evidence chain is not contiguous"
        approvals[name]={"historicalSha256":previous["historicalSha256"] if previous else entry["previousSha256"],"approvedSha256":entry["approvedSha256"]}
    for name,entry in load_premise_evidence(root).items():
        previous=approvals.get(name)
        assert previous and previous["approvedSha256"]==entry["previousSha256"], "Premise evidence chain is not contiguous"
        approvals[name]={"historicalSha256":previous["historicalSha256"],"approvedSha256":entry["approvedSha256"]}
    return approvals


def assert_manifest_integrity(root, manifest):
    """Verify every manifest entry, retaining strict evidence protection.

    An active path must match its exact CURRENT approval, including when its
    historical bytes would otherwise pass. Unknown historical revisions fail.
    Unlisted paths must match their historical digest exactly.
    """
    root = Path(root).resolve()
    approvals = load_policy(root)
    assert isinstance(manifest, dict), "Expected historical path-to-hash mapping"
    for name, historical in manifest.items():
        lexical = Path(name)
        relative = (lexical.relative_to(root) if lexical.is_absolute() else lexical).as_posix()
        assert ".." not in Path(relative).parts, "Non-canonical protected path"
        path = (root / relative).resolve()
        assert path.is_relative_to(root), f"Protected path outside repository: {name}"
        actual = sha256(path)
        migration = approvals.get(relative)
        if migration:
            revisions = {migration["historicalSha256"], migration["approvedSha256"]}
            propagation = load_propagation(root).get(relative)
            if propagation:
                revisions.update(propagation.values())
            beat_evidence = load_beat_evidence(root).get(relative)
            if beat_evidence:
                revisions.add(beat_evidence["previousSha256"])
            premise_evidence=load_premise_evidence(root).get(relative)
            if premise_evidence:
                revisions.add(premise_evidence["previousSha256"])
            assert historical in revisions, (
                f"Unapproved historical active revision: {relative}"
            )
            assert actual == migration["approvedSha256"], (
                f"Approved active implementation changed: {relative}"
            )
        else:
            assert actual == historical, f"Frozen evidence/unapproved code changed: {relative}"
