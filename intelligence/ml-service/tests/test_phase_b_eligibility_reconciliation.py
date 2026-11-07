"""Offline runner coverage for the pinned Kiko opening-gate recovery."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
RUN_ID = "net-new-v1-20261102-v2-e0a93c0f3e56612cd051b434f001dd9b"
CANDIDATE_ID = RUN_ID + "-opening-a-kiko-watering-can-return-loop"
SOURCE_RUN = ROOT / "intelligence/docs/net-new-generation-v1/runs" / RUN_ID
SCRIPT = ROOT / "intelligence/scripts/run-net-new-two-stage-v1.py"
CLEARANCE = "CLEAR controlled experiment"
AUTH_TEXT = f"AUTHORIZE_PHASE_B:{RUN_ID}:CANDIDATE_ID={CANDIDATE_ID}:MAX_PROVIDER_REQUESTS=1"


def runner_module():
    spec = importlib.util.spec_from_file_location("net_new_phase_b_runner_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copied_run(tmp_path):
    target = tmp_path / RUN_ID
    import shutil
    shutil.copytree(SOURCE_RUN, target)
    return target


def test_original_rejection_stays_preserved_while_pinned_replay_resolves_effective_eligibility(tmp_path):
    module = runner_module()
    run_dir = copied_run(tmp_path)
    creation_path = run_dir / "candidate-creation-record.json"
    original_bytes = creation_path.read_bytes()
    original_gate_bytes = (run_dir / "phase-a/opening-gate.json").read_bytes()

    effective, seed, gate, novelty = module.resolve_effective_phase_a(RUN_ID, run_dir, CLEARANCE)

    assert effective["phaseBEligible"] is True
    assert effective["candidate"]["candidateId"] == CANDIDATE_ID
    assert gate["disposition"] == "OPENING_SEED_ACCEPTED"
    assert gate["openingScore"] == 90 and gate["blockers"] == []
    assert seed.seedId == "kiko-watering-can-return-loop"
    assert novelty["disposition"] == "NO_KNOWN_EQUIVALENT"
    assert json.loads(creation_path.read_text())["phaseBEligible"] is False
    assert creation_path.read_bytes() == original_bytes
    assert (run_dir / "phase-a/opening-gate.json").read_bytes() == original_gate_bytes


def test_replay_for_another_candidate_is_rejected(tmp_path):
    module = runner_module()
    run_dir = copied_run(tmp_path)
    path = run_dir / "phase-a" / module.REPLAY_NAME
    replay = json.loads(path.read_text())
    replay["candidateId"] = "different-candidate"
    path.write_text(json.dumps(replay, indent=2, ensure_ascii=False) + "\n")
    with pytest.raises(RuntimeError, match="ACCEPTED_REPLAY_CANDIDATE_MISMATCH"):
        module.resolve_effective_phase_a(RUN_ID, run_dir, CLEARANCE)


def test_replay_cannot_be_rebound_to_another_run_id(tmp_path):
    module = runner_module()
    run_dir = copied_run(tmp_path)
    with pytest.raises(RuntimeError, match="NO_PINNED_PHASE_A_REPLAY_FOR_RUN"):
        module.resolve_effective_phase_a("net-new-v1-different-run", run_dir, CLEARANCE)


def test_mutated_replay_is_rejected_by_pinned_integrity_hash(tmp_path):
    module = runner_module()
    run_dir = copied_run(tmp_path)
    path = run_dir / "phase-a" / module.REPLAY_NAME
    replay = json.loads(path.read_text())
    replay["replayedGate"]["openingScore"] = 91
    path.write_text(json.dumps(replay, indent=2, ensure_ascii=False) + "\n")
    with pytest.raises(RuntimeError, match="ACCEPTED_REPLAY_HASH_MISMATCH"):
        module.resolve_effective_phase_a(RUN_ID, run_dir, CLEARANCE)


def test_missing_replay_and_missing_human_clearance_fail_closed(tmp_path):
    module = runner_module()
    run_dir = copied_run(tmp_path)
    (run_dir / "phase-a" / module.REPLAY_NAME).unlink()
    with pytest.raises(RuntimeError, match="HUMAN_NOVELTY_CLEARANCE_REQUIRED"):
        module.resolve_effective_phase_a(RUN_ID, run_dir, "")
    with pytest.raises(RuntimeError, match="ACCEPTED_REPLAY_OR_BOUND_EVIDENCE_MISSING"):
        module.resolve_effective_phase_a(RUN_ID, run_dir, CLEARANCE)


def test_missing_authorization_rejects_before_creating_phase_b_files(monkeypatch, tmp_path):
    module = runner_module()
    run_dir = copied_run(tmp_path)
    monkeypatch.setattr(module, "request_context", module.request_context)
    with pytest.raises(RuntimeError, match="EXACT_ONE_REQUEST_OPERATOR_AUTHORIZATION_REQUIRED"):
        module.phase_b(RUN_ID, run_dir, tmp_path / "missing-phase-b.txt", CLEARANCE)
    assert not (run_dir / "phase-b").exists()
    assert not (run_dir / "phase-b-authorization-consumed.json").exists()


def test_offline_runner_constructs_exact_single_phase_b_payload_and_rejects_reuse(monkeypatch, tmp_path):
    module = runner_module()
    run_dir = copied_run(tmp_path)
    auth_path = tmp_path / "operator-created-test-auth.txt"
    auth_path.write_text(AUTH_TEXT + "\n")
    monkeypatch.setenv("POMPOM_OFFLINE_MODE", "false")
    monkeypatch.setenv("POMPOM_EXTERNAL_AI_AUTHORIZED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-key")

    from app.workflow import semantic_compact_1_probe_v1 as compact_worker
    seen = {}

    def fake_bounded(path, profile, spec):
        seen["profile"] = profile
        seen["spec"] = spec
        assert profile["_authorizedRequestArguments"] == spec["arguments"]
        assert spec["phase"] == "B"
        assert spec["prompt"]["version"] == "semantic-two-stage-expansion-v1"
        payload = json.loads(spec["arguments"]["messages"][1]["content"])
        assert payload["requestedCount"] == 1
        assert payload["frozenOpeningSeed"]["seedId"] == "kiko-watering-can-return-loop"
        assert spec["arguments"]["model"] == "gpt-6.1-sol"
        assert spec["arguments"]["reasoning_effort"] == "low"
        assert spec["arguments"]["max_completion_tokens"] == 8192
        assert spec["FINAL_PROVIDER_SCHEMA_VALIDATION"]["unresolvedReferences"] == 0
        return {"status": "FAILED", "errorClass": "OfflineFakeTransport", "usage": None,
                "safeMessage": "Offline integration test; no provider call."}

    monkeypatch.setattr(compact_worker, "bounded", fake_bounded)
    module.phase_b(RUN_ID, run_dir, auth_path, CLEARANCE)

    assert seen["spec"]["arguments"]["response_format"]["type"] == "json_schema"
    plan = json.loads((run_dir / "phase-b" / "plan.json").read_text())
    assert plan["maximumPhaseBRequests"] == 1
    assert plan["retries"] == plan["sdkRetries"] == plan["replacements"] == plan["fallbacks"] == 0
    assert plan["renders"] == 0
    consumed = json.loads((run_dir / "phase-b-authorization-consumed.json").read_text())
    assert consumed["maximumProviderRequests"] == 1
    assert consumed["consumedBeforeProviderDispatch"] is True
    with pytest.raises(RuntimeError, match="PHASE_B_AUTHORIZATION_ALREADY_CONSUMED"):
        module.phase_b(RUN_ID, run_dir, auth_path, CLEARANCE)


def test_existing_last_mile_exact_request_guard_rejects_mutated_phase_b_payload(tmp_path):
    module = runner_module()
    run_dir = SOURCE_RUN
    effective, seed, gate, _ = module.resolve_effective_phase_a(RUN_ID, run_dir, CLEARANCE)
    stage, config, cast, selected = module.request_context()
    provenance = stage.SeedProvenance(openingSeedId=gate["openingSeedId"],
        openingSeedRunId=f"{RUN_ID}/opening-a", storyExpansionRunId=f"{RUN_ID}/expansion-1")
    frozen = stage.freeze_seed(seed, gate, provenance)
    phase_b_spec = stage.request_spec(config, cast, selected, "B", frozen)

    class FakeProvider:
        def __init__(self, profile, _tokens, _timeout):
            self.arguments = dict(profile["_authorizedRequestArguments"])
            self.arguments["temperature"] = 0.1  # prohibited extra request field
            self.client = SimpleNamespace(
                max_retries=0, timeout=None, _client=SimpleNamespace(event_hooks={"request": [], "response": []}),
                chat=SimpleNamespace(completions=SimpleNamespace(create=self.create)),
                close=lambda: None)
            self.last_usage = None
            self.last_response_metadata = None
            self.last_raw_response = ""

        def create(self, **_kwargs):
            raise AssertionError("mutated request must be stopped before transport")

        def complete(self, _prompt, system="", temperature=0.7):
            return self.client.chat.completions.create(**self.arguments)

        def close(self):
            pass

    from app.workflow.semantic_compact_1_probe_v1 import worker
    selected = {**selected, "_authorizedRequestArguments": phase_b_spec["arguments"]}
    worker_dir = tmp_path / "exact-guard"
    worker_dir.mkdir()
    worker(worker_dir, selected, phase_b_spec, provider_factory=FakeProvider)
    result = json.loads((worker_dir / "worker-result.json").read_text())
    assert result["status"] == "FAILED"
    assert result["SDKRequestsForwarded"] == 0
    assert result["HTTPRequestsObserved"] == 0
    assert result["safeMessage"] == "Single compact probe failed; no retry, fallback or replacement."

