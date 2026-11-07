#!/usr/bin/env python3
"""One bounded Phase A and one separately authorized, conditional Phase B."""
import argparse
from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "intelligence/ml-service"
DOCS = ROOT / "intelligence/docs/net-new-generation-v1"
RUNS = DOCS / "runs"
RECOVERY_RUN_ID = "net-new-v1-20261102-v2-e0a93c0f3e56612cd051b434f001dd9b"
RECOVERY_CANDIDATE_ID = RECOVERY_RUN_ID + "-opening-a-kiko-watering-can-return-loop"
# Exact immutable inputs and replay approved in the Kiko opening-gate recovery.
# Pinning the replay digest prevents an arbitrary newer sidecar from becoming authoritative.
RECOVERY_BINDING = {
    "candidateCreationRecordSha256": "8c05f0a221191456afa225cd060f82de7a819eee588db88e0b87ee2ce5dbce07",
    "seedFileSha256": "2e73dfe253257f8880918bc79c145d70442b2da35f0d155447ea4e04efbc2044",
    "seedSha256": "effa6b432502f2d5a903f5b49860f85e942d7869d8d5127973debad55d8eebd6",
    "originalGateSha256": "ce17ab53aff5e77d735e4164aa2c366f36c85e5fb7c4cb0d7de95db07916355f",
    "replaySha256": "6f9f83d55d511e4f0f979da81c55d91748a876bb146ddb78828a5f2259fc633a",
    "noveltySha256": "c1a5b0a4fad48f574b9cd71bd66e2b302711200fc531d54087d75faa9bcbf737",
    "openingEvaluatorSha256": "b8d47e8fa744a81d93b253d1a33eb96121c840f7b59ba5bd390ac95db249fab1",
}
REPLAY_NAME = "opening-gate-replay-after-object-token-fix.json"
NOVELTY_CLEARANCE_TEXT = "CLEAR controlled experiment"
PREPARED_PHASE_A_RUN_ID = "net-new-v1-20261102-post-kiko-rejection-001"
PREPARED_PHASE_A_REQUEST = DOCS / "prepared-next-phase-a/request-preview.json"
PREPARED_PHASE_A_REQUEST_SHA256 = "e8dcb88df8ea79a062ec559ec3d12e34b9727a0ea70471377deceb7aa184ad2b"
PREPARED_PHASE_A_CONTEXT_SHA256 = "485c7bdc961b129a1e292ed43d303aea9dd14e0cbbac80d403cd76407b192b7e"
sys.path.insert(0, str(SERVICE))
os.environ.setdefault("POMPOM_DATA_ROOT", str(ROOT / "intelligence/data"))


def write_new(path, value, *, raw=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(value if raw else json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_effective_phase_a(run_id, run_dir, novelty_clearance):
    """Resolve only the exact recovered Kiko decision; never rewrite Phase A history."""
    from app.workflow import semantic_two_stage_v1 as stage

    if run_id != RECOVERY_RUN_ID:
        raise RuntimeError("NO_PINNED_PHASE_A_REPLAY_FOR_RUN")
    if novelty_clearance != NOVELTY_CLEARANCE_TEXT:
        raise RuntimeError("HUMAN_NOVELTY_CLEARANCE_REQUIRED")

    phase_a = Path(run_dir) / "phase-a"
    creation_path = Path(run_dir) / "candidate-creation-record.json"
    seed_path = phase_a / "seed.json"
    original_gate_path = phase_a / "opening-gate.json"
    replay_path = phase_a / REPLAY_NAME
    novelty_path = Path(run_dir) / "seed-stage-novelty.json"
    for path, expected, code in (
        (creation_path, RECOVERY_BINDING["candidateCreationRecordSha256"], "PHASE_A_RECORD_HASH_MISMATCH"),
        (seed_path, RECOVERY_BINDING["seedFileSha256"], "PHASE_A_SEED_FILE_HASH_MISMATCH"),
        (original_gate_path, RECOVERY_BINDING["originalGateSha256"], "ORIGINAL_GATE_HASH_MISMATCH"),
        (novelty_path, RECOVERY_BINDING["noveltySha256"], "PHASE_A_NOVELTY_HASH_MISMATCH"),
    ):
        if not path.is_file():
            raise RuntimeError("ACCEPTED_REPLAY_OR_BOUND_EVIDENCE_MISSING")
        if file_sha256(path) != expected:
            raise RuntimeError(code)
    if not replay_path.is_file():
        raise RuntimeError("ACCEPTED_REPLAY_OR_BOUND_EVIDENCE_MISSING")
    evaluator_path = SERVICE / "app/workflow/premise_admission_evidence.py"
    if file_sha256(evaluator_path) != RECOVERY_BINDING["openingEvaluatorSha256"]:
        raise RuntimeError("ACCEPTED_OPENING_EVALUATOR_HASH_MISMATCH")

    record = json.loads(creation_path.read_text())
    if (record.get("generationRunId") != run_id or record.get("phaseBEligible") is not False
            or record.get("phaseAStatus") != "COMPLETED"):
        raise RuntimeError("ORIGINAL_PHASE_A_DECISION_NOT_PRESERVED")
    original_gate = json.loads(original_gate_path.read_text())
    if (original_gate.get("openingScore") != 35
            or original_gate.get("disposition") != "OPENING_TOO_WEAK"
            or original_gate.get("acceptedForExpansion") is not False):
        raise RuntimeError("ORIGINAL_REJECTED_GATE_NOT_PRESERVED")
    candidate_id = (record.get("candidate") or {}).get("candidateId")
    if candidate_id != RECOVERY_CANDIDATE_ID:
        raise RuntimeError("PHASE_A_CANDIDATE_ID_MISMATCH")
    seed = stage.OpeningSeed.model_validate(json.loads(seed_path.read_text()))
    if stage.digest(seed.model_dump()) != RECOVERY_BINDING["seedSha256"]:
        raise RuntimeError("PHASE_A_SEED_HASH_MISMATCH")
    if record.get("seedSha256") != RECOVERY_BINDING["seedSha256"] or record.get("seed") != seed.model_dump():
        raise RuntimeError("PHASE_A_RECORD_SEED_BINDING_MISMATCH")

    novelty = json.loads(novelty_path.read_text())
    if novelty.get("disposition") != "NO_KNOWN_EQUIVALENT":
        raise RuntimeError("PHASE_A_NOVELTY_NOT_CLEARED_NO_PHASE_B_REQUEST")
    replay = json.loads(replay_path.read_text())
    if replay.get("candidateId") != candidate_id:
        raise RuntimeError("ACCEPTED_REPLAY_CANDIDATE_MISMATCH")
    if file_sha256(replay_path) != RECOVERY_BINDING["replaySha256"]:
        raise RuntimeError("ACCEPTED_REPLAY_HASH_MISMATCH")
    if replay.get("seedSha256") != RECOVERY_BINDING["seedFileSha256"]:
        raise RuntimeError("ACCEPTED_REPLAY_SOURCE_FILE_MISMATCH")
    gate = replay.get("replayedGate") or {}
    if (gate.get("seedSha256") != RECOVERY_BINDING["seedSha256"]
            or gate.get("openingSeedId") != candidate_id):
        raise RuntimeError("ACCEPTED_REPLAY_SEED_BINDING_MISMATCH")
    if (gate.get("openingScore") != 90 or gate.get("acceptedFloor") != 60
            or gate.get("disposition") != "OPENING_SEED_ACCEPTED"
            or gate.get("acceptedForExpansion") is not True or gate.get("blockers") != []):
        raise RuntimeError("ACCEPTED_REPLAY_GATE_NOT_ACCEPTED")
    if (replay.get("providerCalls") != 0 or replay.get("phaseBCalls") != 0
            or replay.get("renders") != 0 or replay.get("imageGenerations") != 0):
        raise RuntimeError("REPLAY_HAS_UNEXPECTED_EXTERNAL_ACTIVITY")
    effective = deepcopy(record)
    effective.update(openingGate=gate, phaseBEligible=True,
                     effectiveEligibilitySource=dict(path=str(replay_path),
                         sha256=RECOVERY_BINDING["replaySha256"],
                         originalRecordPreserved=True))
    return effective, seed, gate, novelty


def request_context():
    from app.workflow import semantic_two_stage_v1 as stage
    from app.workflow import semantic_low_reasoning_probe_v1 as low
    from app.workflow.creative_provider_profiles import profile
    from app.workflow.short_concept_generation import resolve_cast

    prior = json.loads((ROOT / "intelligence/docs/semantic-compact-full-contract-probe-1-run-001/request-before-sdk.json").read_text())
    accepted = json.loads((ROOT / "intelligence/docs/semantic-low-reasoning-full-contract-probe-1-run-001/request-before-sdk.json").read_text())
    inherited = low.plan(profile("openai-escalation"), prior)
    if inherited.get("newRequest") != accepted or inherited.get("selectedReasoningEffort") != "low":
        raise RuntimeError("ACCEPTED_LOW_REASONING_PROFILE_CHANGED")
    selected = inherited["profile"]
    config = stage.TwoStageRequest.model_validate({
        **inherited["spec"]["configuration"], "semanticConceptPromptVersion": "two-stage-v1"
    })
    cast, _ = resolve_cast(config)
    return stage, config, cast, selected


def load_prepared_phase_a(spec, run_id, prepared_request_file):
    """Load the pinned prepared Phase A request; fail closed on any drift."""
    from app.workflow.concept_fingerprint import digest
    from app.workflow.net_new_novelty import context_record, request_message

    if run_id != PREPARED_PHASE_A_RUN_ID:
        raise RuntimeError("PREPARED_PHASE_A_RUN_ID_MISMATCH")
    if not prepared_request_file:
        raise RuntimeError("PREPARED_PHASE_A_REQUEST_REQUIRED")
    request_path = Path(prepared_request_file)
    if not request_path.is_file():
        raise RuntimeError("PREPARED_PHASE_A_REQUEST_MISSING")
    try:
        preview = json.loads(request_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("PREPARED_PHASE_A_REQUEST_INVALID") from error
    if (preview.get("runId") != run_id or preview.get("phase") != "A"
            or preview.get("generationArchitecture") != "TWO_STAGE_V1"
            or preview.get("provider") != "openai" or preview.get("model") != "gpt-6.1-sol"
            or preview.get("reasoningEffort") != "low" or preview.get("candidateCount") != 1
            or preview.get("phaseBEnabled") is not False or preview.get("renderEnabled") is not False
            or preview.get("providerCalls") != 0 or preview.get("renderCalls") != 0):
        raise RuntimeError("PREPARED_PHASE_A_REQUEST_BINDING_MISMATCH")
    arguments = preview.get("requestArguments")
    if not isinstance(arguments, dict) or digest(arguments) != PREPARED_PHASE_A_REQUEST_SHA256:
        raise RuntimeError("PREPARED_PHASE_A_REQUEST_HASH_MISMATCH")
    if preview.get("requestSha256") != PREPARED_PHASE_A_REQUEST_SHA256:
        raise RuntimeError("PREPARED_PHASE_A_REQUEST_HASH_MISMATCH")
    if preview.get("promptSha256") != spec["prompt"]["sha256"]:
        raise RuntimeError("PREPARED_PHASE_A_PROMPT_MISMATCH")
    if preview.get("schemaValidation") != spec["FINAL_PROVIDER_SCHEMA_VALIDATION"]:
        raise RuntimeError("PREPARED_PHASE_A_SCHEMA_MISMATCH")

    context_path = request_path.with_name("historical-exclusion-context.json")
    if not context_path.is_file():
        raise RuntimeError("PREPARED_PHASE_A_CONTEXT_MISSING")
    try:
        context = json.loads(context_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("PREPARED_PHASE_A_CONTEXT_INVALID") from error
    body = {"version": context.get("version"), "exclusions": context.get("exclusions")}
    if (context.get("version") != "net-new-opening-exclusions-v1"
            or digest(body) != PREPARED_PHASE_A_CONTEXT_SHA256
            or context.get("contextSha256") != PREPARED_PHASE_A_CONTEXT_SHA256
            or preview.get("historicalExclusionContextSha256") != PREPARED_PHASE_A_CONTEXT_SHA256
            or preview.get("historicalExclusionContext") != context):
        raise RuntimeError("PREPARED_PHASE_A_CONTEXT_HASH_OR_BINDING_MISMATCH")
    exclusions = context.get("exclusions") or []
    if [row.get("conceptId") for row in exclusions] != [
        "mimi-rolling-pin-dough-wall", "kiko-watering-can-return-loop"
    ]:
        raise RuntimeError("PREPARED_PHASE_A_EXCLUSIONS_MISSING_OR_REORDERED")

    # Preserve and verify the original rolling-pin record byte-for-byte against
    # the accepted versioned context builder.
    legacy_context = context_record()
    if exclusions[0] != legacy_context["exclusions"][0]:
        raise RuntimeError("PREPARED_PHASE_A_ROLLING_PIN_PROVENANCE_MISMATCH")
    water = exclusions[1]
    source_path = Path(water.get("sourceRecord", ""))
    related_story_path = Path(water.get("relatedRejectedStoryRecord", ""))
    if (not source_path.is_file() or file_sha256(source_path) != water.get("sourceSha256")
            or not related_story_path.is_file()
            or file_sha256(related_story_path) != water.get("relatedRejectedStorySha256")):
        raise RuntimeError("PREPARED_PHASE_A_KIKO_SOURCE_PROVENANCE_MISMATCH")
    source_data = json.loads(source_path.read_text())
    source_seed = source_data.get("seed")
    decision_path = related_story_path.with_name("human-creative-decision.json")
    if not isinstance(source_seed, dict) or not decision_path.is_file():
        raise RuntimeError("PREPARED_PHASE_A_KIKO_DECISION_EVIDENCE_MISSING")
    decision = json.loads(decision_path.read_text())
    if (decision.get("decision") != "REJECTED_FOR_PRODUCTION"
            or decision.get("reason") != "INSUFFICIENT_STORY_PROGRESSION"
            or decision.get("publicationStatus") != "NOT_PUBLISHED_CONFIRMED_BY_THIS_DECISION_RECORD"
            or decision.get("immutableEvidenceSha256", {}).get("phaseBResponse")
                != water.get("relatedRejectedStorySha256")
            or water.get("experimentDisposition") != "UNSUCCESSFUL_CREATIVE_EXPERIMENT_NOT_PUBLISHED"
            or water.get("publicationStatus") != "NOT_PUBLISHED"
            or water.get("linkedPublishedVideo") is not False
            or water.get("sourceFields") != {key: source_seed[key] for key in water["sourceFields"]}):
        raise RuntimeError("PREPARED_PHASE_A_KIKO_REJECTION_OR_SOURCE_BINDING_MISMATCH")

    expected_message = request_message(context)
    expected_arguments = deepcopy(spec["arguments"])
    expected_arguments["messages"].append(expected_message)
    if arguments != expected_arguments:
        raise RuntimeError("PREPARED_PHASE_A_ARGUMENTS_DIFFER_FROM_ACCEPTED_REQUEST")
    # Use the same verified context and exact prepared payload for the SDK guard.
    spec["arguments"] = deepcopy(arguments)
    spec["noveltyExclusionContext"] = context
    return context


def verify_authorization(path, expected):
    path = Path(path)
    if not path.is_file() or path.read_text().strip() != expected:
        raise RuntimeError("EXACT_ONE_REQUEST_OPERATOR_AUTHORIZATION_REQUIRED")
    if os.getenv("POMPOM_OFFLINE_MODE", "true").lower() != "false":
        raise RuntimeError("OFFLINE_MODE_ENABLED_NO_REQUEST_SENT")
    if os.getenv("POMPOM_EXTERNAL_AI_AUTHORIZED", "false").lower() != "true":
        raise RuntimeError("EXTERNAL_AI_NOT_AUTHORIZED_NO_REQUEST_SENT")
    if not os.getenv("OPENAI_API_KEY"):
        from dotenv import load_dotenv
        load_dotenv(ROOT / "intelligence/ml-service/.env", override=False)
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_CREDENTIAL_UNAVAILABLE_NO_REQUEST_SENT")
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def run_once(path, run_id, phase, spec, selected, authorization):
    from app.workflow.semantic_compact_1_probe_v1 import bounded
    from app.workflow.semantic_live_experiment import write_new as write_artifact
    from app.workflow.semantic_transport_isolation_v1 import TIMEOUT
    from app.workflow.concept_fingerprint import digest
    from app.workflow.semantic_schema_integrity_probe_v1 import timing_record
    import time

    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    plan = dict(
        generationArchitecture="TWO_STAGE_V1", generationRunId=run_id, phase=phase,
        provider="openai", model="gpt-6.1-sol", reasoningEffort="low",
        maximumPhaseARequests=1, maximumPhaseBRequests=1, maximumTotalProviderRequests=2,
        phaseBConditionalOnAcceptedPhaseA=True, retries=0, sdkRetries=0, replacements=0,
        fallbacks=0, DeepSeekCalls=0, renders=0, maxCompletionTokens=8192,
        timeoutSeconds=90, streaming="NON_STREAMING", authorization=authorization)
    write_artifact(path / "plan.json", plan)
    write_artifact(path / "prompt.json", spec["prompt"])
    write_artifact(path / "request-before-sdk.json", dict(
        provider="openai", baseUrl=selected["baseUrl"], phase=phase,
        arguments=spec["arguments"], requestCountMaximum=1, sdkRetries=0, timeout=TIMEOUT))
    write_artifact(path / "offline-schema-validation.json", spec["FINAL_PROVIDER_SCHEMA_VALIDATION"])
    start = datetime.now(UTC); start_ns = time.monotonic_ns()
    write_artifact(path / "request-started.json", dict(logicalRequestCount=1, maximumLiveRequests=1,
        phase=phase, requestSha256=digest(spec["arguments"]), startedAt=start.isoformat()))
    # The worker and exact-request guard are frozen. Carry their one canonical
    # authorized SDK payload through the existing provider configuration boundary
    # so CreativeCapabilityProvider forwards the complete sequence unchanged.
    provider_profile = deepcopy(selected)
    provider_profile["_authorizedRequestArguments"] = deepcopy(spec["arguments"])
    try:
        result = bounded(path, provider_profile, spec)
    except Exception as error:
        result = dict(status="FAILED", errorClass=type(error).__name__, usage=None,
                      safeMessage="Single request failed; no retry, fallback, or replacement.")
    end = datetime.now(UTC)
    response = path / "response.txt"
    if not response.exists(): write_artifact(response, "", raw=True)
    result.update(phase=phase, generationRunId=run_id, requestCount=1,
        maximumLiveRequests=1, retries=0, sdkRetries=0, replacements=0, fallbacks=0,
        DeepSeekCalls=0, renders=0, promptSha256=spec["prompt"]["sha256"],
        timing=timing_record(start, end, start_ns, time.monotonic_ns()),
        responseBytes=len(response.read_bytes()))
    write_artifact(path / "result.json", result)
    return result, response.read_text()


def existing_candidate_ids():
    path = ROOT / "intelligence/data/workflow/production-lifecycle-registry.json"
    if not path.is_file(): return set()
    data = json.loads(path.read_text())
    return {str(row.get("candidateId")) for row in data.get("entries", []) if row.get("candidateId")}


def phase_a(run_id, run_dir, authorization_file, prepared_request_file=None):
    stage, config, cast, selected = request_context()
    expected = f"AUTHORIZE_PHASE_A:{run_id}:MAX_PROVIDER_REQUESTS=1"
    auth = verify_authorization(authorization_file, expected)
    if run_dir.exists(): raise RuntimeError("RUN_ID_ALREADY_CLAIMED_NO_RETRY_OR_REPLACEMENT")
    spec = stage.request_spec(config, cast, selected, "A")
    from app.workflow.net_new_novelty import context_record, request_message
    if prepared_request_file:
        exclusion_context = load_prepared_phase_a(spec, run_id, prepared_request_file)
    else:
        if run_id == PREPARED_PHASE_A_RUN_ID:
            raise RuntimeError("PREPARED_PHASE_A_REQUEST_REQUIRED_NO_LEGACY_FALLBACK")
        exclusion_context = context_record()
        # Historical exclusions are a separate, versioned request message; the
        # accepted system prompt and user payload remain byte-for-byte unchanged.
        spec["arguments"]["messages"].append(request_message(exclusion_context))
        spec["noveltyExclusionContext"] = exclusion_context
    phase_dir = run_dir / "phase-a"
    write_new(run_dir / "historical-exclusion-context.json", exclusion_context)
    result, raw = run_once(phase_dir, run_id, "A", spec, selected, auth)
    record = dict(generationRunId=run_id, generationArchitecture="TWO_STAGE_V1",
        createdAt=datetime.now(UTC).isoformat(), requestCount=1, providerCalls=1,
        phaseAStatus=result["status"], phaseBEligible=False, candidate=None)
    if result.get("status") == "COMPLETED" and raw:
        try:
            seed = stage.parse_seed(raw)
            candidate_id = f"{run_id}-opening-a-{seed.seedId}"
            if candidate_id in existing_candidate_ids(): raise ValueError("CANDIDATE_ID_COLLISION")
            gate = stage.gate_seed(seed, cast, candidate_id)
            from app.workflow.net_new_novelty import compare_opening
            novelty = compare_opening(seed.model_dump(), exclusion_context["exclusions"])
            write_new(run_dir / "seed-stage-novelty.json", novelty)
            duplicate = novelty["disposition"] == "DUPLICATE_CREATIVE_TERRITORY"
            record.update(seed=seed.model_dump(), seedSha256=stage.digest(seed.model_dump()),
                openingGate=gate, noveltyDisposition=novelty["disposition"],
                phaseBEligible=bool(gate["acceptedForExpansion"] and not duplicate and novelty["disposition"] == "NO_KNOWN_EQUIVALENT"),
                candidate=dict(candidateId=candidate_id,
                    candidateOrigin="NEW_CONCEPT", lifecycleStatus="NEW_CONCEPT", creationProvenance=dict(
                        generationArchitecture="TWO_STAGE_V1", generationRunId=run_id,
                        phaseARequestId="opening-a", createdAt=record["createdAt"],
                        provider="openai", model="gpt-6.1-sol", reasoningEffort="low",
                        sourceSeedSha256=stage.digest(seed.model_dump()))))
            write_new(phase_dir / "seed.json", seed.model_dump())
            write_new(phase_dir / "opening-gate.json", gate)
        except Exception as error:
            record["rejection"] = dict(code="SEED_PARSE_GATE_OR_ID_FAILURE",
                errorClass=type(error).__name__, safeMessage=str(error)[:500])
    write_new(run_dir / "candidate-creation-record.json", record)
    print(json.dumps(dict(generationRunId=run_id, phaseAStatus=record["phaseAStatus"],
        candidateId=(record.get("candidate") or {}).get("candidateId"),
        openingScore=(record.get("openingGate") or {}).get("openingScore"),
        phaseBEligible=record["phaseBEligible"], providerCalls=1, renders=0), indent=2))


def phase_b(run_id, run_dir, authorization_file, novelty_clearance=None):
    stage, config, cast, selected = request_context()
    creation_path = run_dir / "candidate-creation-record.json"
    if not creation_path.is_file(): raise RuntimeError("PHASE_A_RECORD_REQUIRED")
    if run_id == RECOVERY_RUN_ID:
        record, seed, gate, _novelty = resolve_effective_phase_a(run_id, run_dir, novelty_clearance)
    else:
        # Preserve the accepted original path for ordinary Phase A records.
        # Only the specifically pinned recovery run may resolve beyond its
        # immutable stored decision via a separately hash-bound replay.
        record = json.loads(creation_path.read_text())
        if record.get("generationRunId") != run_id or not record.get("phaseBEligible"):
            raise RuntimeError("PHASE_A_OPENING_DID_NOT_PASS_NO_PHASE_B_REQUEST")
        novelty_path = run_dir / "seed-stage-novelty.json"
        if (not novelty_path.is_file()
                or json.loads(novelty_path.read_text()).get("disposition") != "NO_KNOWN_EQUIVALENT"):
            raise RuntimeError("PHASE_A_NOVELTY_NOT_CLEARED_NO_PHASE_B_REQUEST")
        seed = stage.OpeningSeed.model_validate(record["seed"])
        gate = record["openingGate"]
        if stage.digest(seed.model_dump()) != record.get("seedSha256"):
            raise RuntimeError("PHASE_A_SEED_HASH_MISMATCH")
    candidate_id = record["candidate"]["candidateId"]
    expected = f"AUTHORIZE_PHASE_B:{run_id}:CANDIDATE_ID={candidate_id}:MAX_PROVIDER_REQUESTS=1"
    phase_dir = run_dir / "phase-b"
    consumed_path = run_dir / "phase-b-authorization-consumed.json"
    if phase_dir.exists() or consumed_path.exists():
        raise RuntimeError("PHASE_B_AUTHORIZATION_ALREADY_CONSUMED_NO_RETRY_OR_REPLACEMENT")
    auth = verify_authorization(authorization_file, expected)
    provenance = stage.SeedProvenance(openingSeedId=gate["openingSeedId"],
        openingSeedRunId=f"{run_id}/opening-a", storyExpansionRunId=f"{run_id}/expansion-1")
    frozen = stage.freeze_seed(seed, gate, provenance)
    spec = stage.request_spec(config, cast, selected, "B", frozen)
    # The accepted request spec is fully constructed and schema-validated before
    # the one-use authorization is consumed. The unchanged bounded worker then
    # enforces this exact argument object at both SDK and HTTP boundaries.
    if (spec["phase"] != "B" or spec["arguments"].get("model") != "gpt-6.1-sol"
            or spec["arguments"].get("reasoning_effort") != "low"
            or spec["arguments"].get("max_completion_tokens") != 8192
            or spec["FINAL_PROVIDER_SCHEMA_VALIDATION"].get("syntax") != "VALID_DRAFT202012"
            or spec["FINAL_PROVIDER_SCHEMA_VALIDATION"].get("unresolvedReferences") != 0
            or spec["FINAL_PROVIDER_SCHEMA_VALIDATION"].get("unsupportedReferences") != 0):
        raise RuntimeError("PHASE_B_EXACT_REQUEST_PREFLIGHT_FAILED")
    write_new(consumed_path, dict(runId=run_id, candidateId=candidate_id,
        authorizationSha256=auth["sha256"], requestSha256=stage.digest(spec["arguments"]),
        consumedBeforeProviderDispatch=True, maximumProviderRequests=1))
    write_new(run_dir / "frozen-opening-seed.json", frozen)
    result, raw = run_once(phase_dir, run_id, "B", spec, selected, auth)
    analysis = None
    if result.get("status") == "COMPLETED" and raw:
        try: analysis = stage.analyze_expansion(raw, frozen, config, spec["prompt"])
        except Exception as error:
            analysis = dict(status="EXPANSION_REJECTED", errorClass=type(error).__name__,
                            safeMessage=str(error)[:1000], pipelineRan=False)
        write_new(run_dir / "phase-b-candidate-provenance.json", dict(
            candidateId=candidate_id, phaseBResponseSha256=hashlib.sha256(raw.encode()).hexdigest(),
            phaseBPromptVersion=spec["prompt"]["version"], phaseBPromptSha256=spec["prompt"]["sha256"],
            generationRunId=run_id, provider="openai", model="gpt-6.1-sol", reasoningEffort="low"))
    write_new(run_dir / "phase-b-analysis.json", analysis or dict(status="NO_VALID_RESPONSE", pipelineRan=False))
    print(json.dumps(dict(generationRunId=run_id, candidateId=candidate_id,
        phaseBStatus=result["status"], analysisStatus=(analysis or {}).get("status"),
        providerCalls=1, renders=0), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("A", "B"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--authorization-file", required=True)
    parser.add_argument("--prepared-request")
    parser.add_argument("--novelty-clearance")
    args = parser.parse_args()
    if not re.fullmatch(r"net-new-v1-[A-Za-z0-9][A-Za-z0-9._-]{0,50}", args.run_id):
        parser.error("run-id must use the net-new-v1- prefix and a unique run suffix")
    run_dir = RUNS / args.run_id
    try:
        if args.phase == "A": phase_a(args.run_id, run_dir, args.authorization_file, args.prepared_request)
        else: phase_b(args.run_id, run_dir, args.authorization_file, args.novelty_clearance)
    except Exception as error:
        parser.error(f"{type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
