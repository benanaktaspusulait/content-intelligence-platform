"""Run-level entry point for the existing Pompom production workflow.

This module only performs deterministic selection and preflight work. Paid
provider work remains behind the existing image, validation, and Render
Service authorization gates.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import beat_grammar, concept_ranking, creative_shape, premise_naturalness

VERSION = "autonomous-production-entry-v1"
DEFAULT_SOURCE = (
    Path(__file__).resolve().parents[3] / "docs/creative-shape-v1/experiment-seed-42-count-20.json"
)
PAYOFF_PREFERENCE = {
    "CONTROL_REVERSAL": 0,
    "CONTACT_ENTANGLEMENT": 1,
    "HIDDEN_CAUSE_REVEAL": 2,
    "CHAIN_REACTION": 3,
}


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_json(value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _source_path() -> Path:
    configured = os.getenv("AUTONOMOUS_CANDIDATE_SOURCE", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    mounted = (
        Path(os.getenv("POMPOM_DATA_ROOT", "/tmp/pompom-data"))
        / "accepted-candidates"
        / "experiment-seed-42-count-20.json"
    )
    return mounted if mounted.is_file() else DEFAULT_SOURCE


def _data_root() -> Path:
    return Path(os.getenv("POMPOM_DATA_ROOT", "/tmp/pompom-data")).expanduser().resolve()


def _candidate_input(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": candidate["candidateId"],
        "title": candidate["title"],
        "protagonist": candidate["protagonist"],
        "protagonistGoal": candidate["everydayGoal"],
        "objectOrPrimaryInteraction": candidate["primaryObject"],
        "impossibleRuleOrCoreContradiction": candidate["impossibleRule"],
        "frameZeroDescription": candidate["frameZeroDescription"],
        "escalationPlan": candidate["beats"],
        "finalPayoff": candidate["finalPayoff"],
        "intendedDurationSeconds": candidate["intendedDurationSeconds"],
    }


def _ranked_candidates(source: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = [
        row
        for row in source.get("candidates", [])
        if row.get("candidate") and row.get("disposition") == "ELIGIBLE"
    ]
    if not records:
        raise ValueError("Accepted creative-shape source has no eligible structured candidates")
    inputs = [_candidate_input(row["candidate"]) for row in records]
    ranking = concept_ranking.rank_concepts(inputs)
    ranked = {
        row["candidateId"]: row
        for row in [*ranking.get("rankedEligibleCandidates", []), *ranking.get("revisionCandidates", [])]
    }
    validations: list[dict[str, Any]] = []
    for stored in records:
        candidate = stored["candidate"]
        candidate_id = candidate["candidateId"]
        rank = ranked.get(candidate_id)
        if rank is None:
            raise ValueError(f"Existing ranking pipeline omitted candidate {candidate_id}")
        grammar = beat_grammar.assess(candidate["structuredBeatPlan"], candidate.get("composition"))
        naturalness = premise_naturalness.assess(candidate)
        shape = creative_shape.annotate(candidate)
        territory = creative_shape.territory(candidate)
        blockers: list[str] = []
        if rank.get("eligibility") != "ELIGIBLE":
            blockers.extend(rank.get("eligibilityReasons") or ["RANKING_NOT_ELIGIBLE"])
        if grammar.get("beatGrammarQuality") != "STRONG":
            blockers.append("BEAT_GRAMMAR_NOT_STRONG")
        if not naturalness.get("admitted"):
            blockers.append("PREMISE_NATURALNESS_NOT_ADMITTED")
        if len(candidate.get("structuredBeatPlan", [])) not in (4, 5):
            blockers.append("BEAT_COUNT_OUTSIDE_4_TO_5")
        if float(candidate.get("intendedDurationSeconds", 0)) > 15:
            blockers.append("DURATION_EXCEEDS_15_SECONDS")
        if shape.get("finalRelationship") == "OPENING_STATE_RECREATED":
            blockers.append("PAYOFF_RECREATES_OPENING_STATE")
        if grammar.get("nearDuplicateAttemptRate", 1) > 0.25:
            blockers.append("BEAT_GRAMMAR_NEAR_DUPLICATE_ATTEMPTS")
        validations.append(
            {
                "candidateId": candidate_id,
                "title": candidate["title"],
                "protagonist": candidate["protagonist"],
                "protagonistCharacterId": candidate.get("protagonistCharacterId"),
                "ranking": rank,
                "beatGrammar": grammar,
                "premiseNaturalness": naturalness,
                "creativeShape": shape,
                "historicalTerritory": territory,
                "sourceDisposition": stored.get("disposition"),
                "templateShapeRisk": stored.get("templateShapeRisk"),
                "sourceHumanDecision": "NO_CANDIDATE_SPECIFIC_DECISION_FOUND_IN_SOURCE_ARTIFACT",
                "selectionBlockers": blockers,
                "candidate": candidate,
            }
        )
    return validations, ranking


def _selection_key(record: dict[str, Any]) -> tuple[Any, ...]:
    score = record["ranking"].get("rankingScore")
    return (
        PAYOFF_PREFERENCE.get(record["creativeShape"].get("payoffFamily"), 10),
        -(float(score) if score is not None else -1),
        record["candidateId"],
    )


def _resolve_character_reference(candidate: dict[str, Any], root: Path) -> dict[str, Any]:
    library_root = Path(os.getenv("POMPOM_LIBRARY_ROOT", str(root / "library"))).expanduser().resolve()
    library = library_root / "01-CHARACTERS" / "drawings"
    name = str(candidate.get("protagonist", "")).strip().lower()
    if not name or not library.is_dir():
        return {"status": "MISSING", "reason": "Mounted canonical character drawing directory is unavailable"}
    matches = [
        path
        for path in library.iterdir()
        if path.is_file()
        and path.stem.lower() == name
        and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]
    if len(matches) != 1:
        return {"status": "MISSING" if not matches else "AMBIGUOUS", "matches": [str(p) for p in matches]}
    path = matches[0]
    content = path.read_bytes()
    return {
        "status": "DISCOVERED_UNREVIEWED",
        "path": str(path),
        "relativePath": path.relative_to(library_root).as_posix(),
        "sha256": _sha_bytes(content),
        "approvalStatus": "UNREVIEWED",
        "assetId": None,
        "approvalBlocker": "Existing Character Lab review/approval record is required before reference use",
    }


def _capability_preflight() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / "data/workflow/provider-capabilities.json"
    if not path.is_file():
        path = _data_root() / "workflow/provider-capabilities.json"
    if not path.is_file():
        return {"status": "NOT_VERIFIED", "reason": "Versioned provider capability schema is missing"}
    data = json.loads(path.read_text(encoding="utf-8"))
    model = data.get("models", {}).get("SEEDANCE_2_0_MINI", {})
    schema = model.get("modes", {}).get("image2video", {})
    props = schema.get("properties", {})
    duration = props.get("duration", {})
    aspect = props.get("aspectRatio", {})
    supports = duration.get("maximum", 0) >= 15 and "9:16" in aspect.get("enum", [])
    live_verified = bool(model.get("provenance", {}).get("liveGenerationVerified"))
    return {
        "status": "SUPPORTED_CACHED_SCHEMA_LIVE_UNVERIFIED"
        if supports and not live_verified
        else "SUPPORTED"
        if supports
        else "UNSUPPORTED",
        "model": model.get("apiModelId"),
        "durationMaximumSeconds": duration.get("maximum"),
        "durationMinimumSeconds": duration.get("minimum"),
        "aspectRatios": aspect.get("enum", []),
        "provenance": model.get("provenance", {}),
        "reason": "Cached CLI schema supports 9:16 and up to 15s; provenance explicitly says live generation is unverified"
        if supports and not live_verified
        else "",
    }


def _write_run(root: Path, run: dict[str, Any]) -> None:
    directory = root / "autonomous-production" / "runs"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{run['runId']}.json"
    fd, temp = tempfile.mkstemp(prefix=f".{run['runId']}.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(run, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_run(run_id: str, *, root: Path | None = None) -> dict[str, Any]:
    if not run_id or any(ch not in "0123456789abcdef-" for ch in run_id.lower()):
        raise ValueError("Invalid production run id")
    path = (root or _data_root()) / "autonomous-production" / "runs" / f"{run_id}.json"
    if not path.is_file():
        raise FileNotFoundError(run_id)
    return json.loads(path.read_text(encoding="utf-8"))


def start_run(
    *, idempotency_key: str, root: Path | None = None, source_path: Path | None = None
) -> dict[str, Any]:
    if not idempotency_key or len(idempotency_key) > 200:
        raise ValueError("A 1–200 character Idempotency-Key is required")
    root = (root or _data_root()).resolve()
    source = (source_path or _source_path()).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Accepted structured candidate source not found: {source}")
    source_bytes = source.read_bytes()
    source_data = json.loads(source_bytes)
    validations, ranking_result = _ranked_candidates(source_data)
    available = [row for row in validations if not row["selectionBlockers"]]
    selected = sorted(available, key=_selection_key)[0] if available else None
    run_id = str(uuid.uuid4())
    created = datetime.now(UTC).isoformat()
    blockers: list[dict[str, str]] = []
    selection = selected
    if selection is None:
        blockers.append(
            {
                "code": "NO_EXISTING_CANDIDATE_MEETS_CREATIVE_GATES",
                "detail": "Existing source candidates are ranked but fail one or more current creative suitability gates; an authorized existing generator run is needed.",
            }
        )
    character_reference = (
        _resolve_character_reference(selection["candidate"], root)
        if selection
        else {"status": "NOT_APPLICABLE"}
    )
    if selected and character_reference.get("status") != "DISCOVERED_UNREVIEWED":
        blockers.append(
            {
                "code": "CANONICAL_CHARACTER_REFERENCE_UNAVAILABLE",
                "detail": str(character_reference.get("reason") or character_reference.get("status")),
            }
        )
    elif selected:
        blockers.append(
            {
                "code": "CANONICAL_CHARACTER_REFERENCE_REVIEW_REQUIRED",
                "detail": "The archive drawing is discoverable and hash-bound, but no approved Character Lab reference record exists for it.",
            }
        )
    template_risk = (selected or {}).get("templateShapeRisk", {}) if selected else {}
    if selected and template_risk.get("risk") == "HIGH":
        blockers.append(
            {
                "code": "CREATIVE_REVIEW_RECOMMENDED_HIGH_TEMPLATE_SHAPE_RISK",
                "detail": "The existing batch diagnostic marks this story shape HIGH risk; it remains a review signal, not a changed ranking or scoring gate.",
            }
        )
    capability = _capability_preflight()
    if capability.get("status") != "SUPPORTED":
        blockers.append(
            {
                "code": "LIVE_MODEL_CAPABILITY_UNVERIFIED",
                "detail": capability.get("reason") or capability.get("status", "unsupported"),
            }
        )
    if (
        os.getenv("OPENART_ENABLED", "false").lower() != "true"
        or os.getenv("OPENART_MOCK_ENABLED", "true").lower() == "true"
    ):
        blockers.append(
            {
                "code": "OPENART_LIVE_DISPATCH_DISABLED",
                "detail": "OpenArt is disabled or mock mode is enabled in the current configuration.",
            }
        )
    if not os.getenv("OPENART_TOKEN", "").strip():
        blockers.append(
            {
                "code": "OPENART_CREDENTIAL_MISSING",
                "detail": "No OpenArt live provider token is configured in the current application environment.",
            }
        )
    if os.getenv("POMPOM_EXTERNAL_AI_AUTHORIZED", "false").lower() != "true":
        blockers.append(
            {
                "code": "RUN_LEVEL_SPENDING_AUTHORIZATION_MISSING",
                "detail": "No bounded production-run authorization is active; image or video provider requests are blocked.",
            }
        )
    if os.getenv("AUTONOMOUS_MAX_SPEND_USD", "").strip() == "":
        blockers.append(
            {
                "code": "RUN_LEVEL_SPENDING_LIMIT_MISSING",
                "detail": "Set an explicit maximum USD spend in the application approval boundary before any paid request.",
            }
        )

    blockers.append(
        {
            "code": "PRODUCTION_HISTORY_AUTOMATED_LOOKUP_NOT_CONNECTED",
            "detail": "This run has not queried the production archive, publication records, or human rejection registry; novelty status is not established automatically.",
        }
    )

    evidence = {
        "version": VERSION,
        "createdAt": created,
        "source": {
            "path": str(source),
            "sha256": _sha_bytes(source_bytes),
            "candidateCount": len(validations),
        },
        "ranking": {
            "version": ranking_result.get("version"),
            "inputFingerprint": ranking_result.get("inputFingerprint"),
            "providerCalls": ranking_result.get("providerCalls", 0),
        },
        "candidateEvaluations": validations,
        "selectedCandidateId": selected.get("candidateId") if selected else None,
        "productionHistory": {
            "status": "NOT_EVALUATED",
            "reason": "Production, publication, and human rejection records are not connected to this selector.",
        },
        "characterReference": character_reference,
        "firstFrame": {"status": "MISSING" if selected else "NOT_APPLICABLE", "candidateId": None},
        "productionPrompt": {
            "status": "NOT_CREATED",
            "reason": "No approved first-frame/character binding or run-level authorization; prompt generation has not been invoked.",
        },
        "modelConfiguration": {
            "model": "SEEDANCE_2_0_MINI",
            "mode": "image2video",
            "aspectRatio": "9:16",
            "targetDurationSeconds": 14,
            "hardMaximumSeconds": 15,
            "capabilityPreflight": capability,
        },
        "validationEvidence": {
            "storyPremise": "NOT_EVALUATED: this source is a structured short-concept candidate, not a persisted STORY artifact accepted by the Story Premise/Admission workflow.",
            "premiseAdmission": "NOT_EVALUATED: no canonical story-review record or source-bound production prompt exists.",
            "promptValidation": "NOT_EVALUATED: derived production prompt has not been created.",
            "firstFrameValidation": "NOT_EVALUATED: no matching first-frame asset exists.",
            "productionAdmission": "BLOCKED: existing render admission requires prompt/visual bindings and authorization.",
        },
        "blockers": blockers,
        "providerRequests": 0,
        "imageGenerationRequests": 0,
        "renderRequests": 0,
        "status": "AWAITING_HUMAN_REVIEW"
        if selected and template_risk.get("risk") == "HIGH"
        else "AWAITING_BUDGET_AUTHORIZATION"
        if selected
        else "BLOCKED",
        "nextApplicationAction": "The story-shape and canonical character decisions must be resolved in the application. Then one run-scoped approval with an explicit USD ceiling must authorize the bounded image/prompt/render work. That approval/resume action is not yet connected; no provider action is available from this run.",
    }
    run = {"runId": run_id, "idempotencyKeySha256": _sha_bytes(idempotency_key.encode("utf-8")), **evidence}
    _write_run(root, run)
    return run


def start_idempotent(
    idempotency_key: str, *, root: Path | None = None, source_path: Path | None = None
) -> dict[str, Any]:
    root = (root or _data_root()).resolve()
    store = root / "autonomous-production"
    store.mkdir(parents=True, exist_ok=True)
    key_path = store / f"idempotency-{_sha_bytes(idempotency_key.encode('utf-8'))}.json"
    lock_path = store / "idempotency.lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if key_path.is_file():
            run_id = json.loads(key_path.read_text(encoding="utf-8"))["runId"]
            return read_run(run_id, root=root)
        run = start_run(idempotency_key=idempotency_key, root=root, source_path=source_path)
        temp = key_path.with_suffix(".tmp")
        temp.write_text(json.dumps({"runId": run["runId"]}), encoding="utf-8")
        os.replace(temp, key_path)
        return run
