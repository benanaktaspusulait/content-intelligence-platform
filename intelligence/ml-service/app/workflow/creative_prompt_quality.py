"""CPQ V1 text-only assessment previews and calibration validation.

The preview is intentionally non-numeric until a governed, held-out calibrated
corpus and activation record exist. It does not call providers or trust model
self-evaluations, canonical grades, or render outcomes.
"""
from __future__ import annotations

import re
from hashlib import sha256
from typing import Any

VERSION = "creative-prompt-quality-v1"
CORPUS_VERSION = None
DIMENSIONS = (
    "SCROLL_STOP_VISUAL_PROMISE", "CAUSAL_PROGRESSION", "VISUAL_STORYTELLING",
    "PRODUCTION_EXECUTABILITY", "ENDING_REPLAY", "DISTINCTIVE_CREATIVE_VALUE",
)


def fingerprint(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _dimension(dim: str, prompt: str, profile: str, generator: str, duration: float | None,
              diagnosis: dict[str, Any], critic: dict[str, Any]) -> dict[str, Any]:
    text = prompt.lower()
    plan = diagnosis.get("opportunities", [])
    relevant = [p for p in plan if p.get("dimension") == dim]
    canonical = diagnosis.get("canonicalFindings", [])
    risk_rows = [r for r in critic.get("findings", []) if r.get("dimension") == dim or r.get("dimension") == "PRODUCTION_EXECUTABILITY"]
    evidence: list[dict[str, str]] = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []
    def has(pattern: str) -> bool:
        return bool(re.search(pattern, text, re.I))
    if dim == "SCROLL_STOP_VISUAL_PROMISE":
        patterns = [r"\b(?:first frame|opening|at 0(?:\.\d+)?s|0[-–]2 seconds)\b", r"\b(?:visible|in frame|foreground|close-up|wide shot)\b", r"\b(?:but|suddenly|instead|impossible|floats|sticks|duplicates|moves)\b"]
        labels = ["opening window", "viewer-facing composition", "visual anomaly or contrast"]
    elif dim == "CAUSAL_PROGRESSION":
        patterns = [r"\b(?:because|when|as soon as|causing|so that|therefore|then)\b", r"\b(?:increases|doubles|multiplies|spreads|changes|becomes|until|finally)\b", r"\b(?:first|next|then|after|finally|ending)\b"]
        labels = ["explicit cause/consequence relation", "state change or escalation", "ordered progression"]
    elif dim == "VISUAL_STORYTELLING":
        patterns = [r"\b(?:left|right|behind|beside|above|below|between|over|under|next to)\b", r"\b(?:hand|finger|touch|contact|surface|edge|sticks|detaches|covers)\b", r"\b(?:camera|frame|shot|foreground|background|visible|occluded)\b"]
        labels = ["spatial relation", "physical interaction", "composition or visibility instruction"]
    elif dim == "PRODUCTION_EXECUTABILITY":
        patterns = [r"\b(?:seconds?|s)\b", r"\b(?:locked|static|pan|track|camera|single shot|cut)\b", r"\b(?:one at a time|continuously|without cutting|remains visible|in sequence)\b"]
        labels = ["timing budget", "camera/shot plan", "continuity or action-complexity control"]
    elif dim == "ENDING_REPLAY":
        patterns = [r"\b(?:finally|ending|ends with|last frame|final image|payoff)\b", r"\b(?:returns to|matches the opening|loops?|seamlessly)\b", r"\b(?:reveals|realizes|decides|surprise|curiosity|open question)\b"]
        labels = ["defined final image/consequence", "opening relation or loop option", "payoff or intentional curiosity"]
    else:
        patterns = [r"\b(?:mechanic|rule|each time|every time|doubles|multiplies|copies|reverses|imitates)\b", r"\b(?:distinct|unexpected|surprising|visual pattern|contrast|transforms)\b", r"\b(?:specific|exactly|one at a time|in a clear sequence)\b"]
        labels = ["specific visual mechanism", "non-generic variation or contrast", "concrete execution choice"]
    found = [label for pattern, label in zip(patterns, labels, strict=True) if has(pattern)]
    for label in found:
        strengths.append(f"Text explicitly specifies {label}.")
        evidence.append({"kind": "PROMPT_TEXT_SIGNAL", "label": label})
    missing = [label for label in labels if label not in found]
    for label in missing:
        weaknesses.append(f"The prompt does not explicitly establish {label}.")
        recommendations.append(f"Add a source-faithful, observable instruction for {label} only if diagnosis supports it.")
    for item in relevant:
        evidence.append({"kind": "DIAGNOSIS_REFERENCE", "label": str(item.get("opportunityId", "unbound"))})
    for item in risk_rows:
        evidence.append({"kind": "EXECUTION_CRITIC_REFERENCE", "label": str(item.get("id", item.get("ruleId", "unbound")))} )
        weaknesses.append(str(item.get("message", "Execution risk requires review.")))
    # Canonical findings are traceable context only, never a CPQ score input.
    canonical_refs = [str(r.get("ruleId")) for r in canonical if r.get("ruleId")]
    return {
        "dimension": dim, "status": "TEXT_EVIDENCE_PREVIEW", "calibratedScore": None,
        "strengths": strengths, "weaknesses": weaknesses, "recommendations": recommendations,
        "evidenceReferences": evidence, "confidence": "NOT_CALIBRATED",
        "explicitUnknowns": ["Actual rendered visual adherence is unverified.", "Audience effect is unmeasured."],
        "profileConstraints": {"contentProfile": profile, "generator": generator, "durationSeconds": duration},
        "canonicalContextReferences": canonical_refs,
    }


def assess(payload: dict[str, Any]) -> dict[str, Any]:
    original = payload["originalPrompt"]
    candidate = payload["candidatePrompt"]
    if not original.strip() or not candidate.strip():
        raise ValueError("Complete original and candidate prompts are required")
    if len(original) > 50000 or len(candidate) > 50000:
        raise ValueError("Prompt exceeds the 50000-character assessment limit")
    profile = str(payload.get("contentProfile", "UNKNOWN"))
    generator = str(payload.get("generator", "UNKNOWN"))
    duration = payload.get("durationSeconds")
    diagnosis = payload.get("diagnosis") or {}
    critic = payload.get("executionCritic") or {}
    dims = [_dimension(d, candidate, profile, generator, duration, diagnosis, critic) for d in DIMENSIONS]
    orig_tokens = set(re.findall(r"[\w'-]+", original.casefold()))
    cand_tokens = set(re.findall(r"[\w'-]+", candidate.casefold()))
    added = sorted(cand_tokens - orig_tokens)
    removed = sorted(orig_tokens - cand_tokens)
    changed = fingerprint(original) != fingerprint(candidate)
    materiality_refs = diagnosis.get("validatedMaterialChanges", [])
    # Requests cannot self-assert independent evidence. The trusted backend
    # may attach a validated immutable review after this assessment is made.
    fidelity_state = "UNKNOWN"
    return {
        "contractVersion": VERSION, "rubricVersion": VERSION, "calibrationCorpusVersion": CORPUS_VERSION,
        "gradingStatus": "CALIBRATION_INCOMPLETE", "absoluteQuality": {
            "status": "NOT_QUALIFIED", "grade": None, "aggregateScore": None,
            "reason": "No approved, independently reviewed calibration corpus and activated thresholds are available.",
        },
        "relativeImprovement": {
            "status": "REVIEW_REQUIRED" if changed else "NO_CHANGE",
            "promptFingerprintChanged": changed,
            "addedTokenCount": len(added), "removedTokenCount": len(removed),
            "materialityEvidence": materiality_refs,
            "classification": "UNVERIFIED" if changed else "EQUIVALENT",
            "note": "Token difference and verbosity do not establish material improvement.",
        },
        "dimensions": dims,
        "sourceFidelity": {"decision": fidelity_state, "requiredForQualifiedGrade": True,
                           "evidenceId": None},
        "canonicalValidation": payload.get("canonicalFindings") or {"rulesetVersion": "1.11", "status": "NOT_PROVIDED"},
        "productionRisks": critic.get("findings", []),
        "missingEvidence": ["Approved calibration corpus", "Calibrated dimension thresholds and aggregation", "Held-out error analysis", "Independent reviewer agreement"],
        "qualityConfidence": {"status": "NOT_CALIBRATED", "reviewerAgreement": None},
        "visualAdherence": "UNVERIFIED", "audienceEffect": "UNMEASURED", "renderReadiness": "SEPARATE_F8_POLICY",
        "renderAuthorized": False, "automaticApproval": False,
        "fingerprints": {"originalPromptSha256": fingerprint(original), "candidatePromptSha256": fingerprint(candidate)},
    }


def validate_calibration(records: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [r.get("exampleId") for r in records]
    duplicates = sorted({str(x) for x in ids if ids.count(x) > 1})
    problems: list[str] = []
    if not records:
        problems.append("No independently reviewed examples have been imported.")
    if duplicates:
        problems.append("Duplicate example IDs are present.")
    missing = []
    for index, record in enumerate(records):
        required = ("promptSha256", "promptVersion", "sourceStoryId", "sourceRevision", "contentProfile", "generator", "durationSeconds", "promptText", "reviewerJudgments", "sourceFidelityEvidence", "reviewerProvenance", "split")
        absent = [field for field in required if record.get(field) is None]
        if absent:
            missing.append({"index": index, "exampleId": record.get("exampleId"), "fields": absent})
        if record.get("promptText") and fingerprint(str(record["promptText"])) != record.get("promptSha256"):
            problems.append(f"Prompt fingerprint mismatch for example {record.get('exampleId')}.")
        if record.get("split") not in {"CALIBRATION", "HELD_OUT"}:
            problems.append(f"Invalid corpus split for example {record.get('exampleId')}.")
        if record.get("sourceFidelityEvidence", {}).get("decision") not in {"PASS", "FAIL"}:
            problems.append(f"Independent source-fidelity decision unavailable for example {record.get('exampleId')}.")
        judgments = record.get("reviewerJudgments") or []
        if len({j.get("reviewerId") for j in judgments if j.get("reviewerId")}) < 2:
            problems.append(f"Fewer than two distinct reviewers for example {record.get('exampleId')}.")
        if any(j.get("reviewerId") == record.get("sourceFidelityEvidence", {}).get("reviewerId") for j in judgments):
            problems.append(f"Fidelity verifier overlaps a quality reviewer for example {record.get('exampleId')}.")
        for judgment in judgments:
            dimensions = judgment.get("dimensions") or {}
            if set(dimensions) != set(DIMENSIONS) or judgment.get("overallQualityAnchor") not in {"A+", "A", "B", "C", "F", "UNKNOWN"}:
                problems.append(f"Incomplete dimension judgment or invalid quality anchor for example {record.get('exampleId')}.")
            if not judgment.get("reviewMethodVersion") or not judgment.get("reviewedAt") or not judgment.get("evidenceCitations"):
                problems.append(f"Reviewer provenance or citations incomplete for example {record.get('exampleId')}.")
    return {"corpusVersion": None, "state": "CALIBRATION_INCOMPLETE" if problems or missing else "READY_FOR_CALIBRATION_ANALYSIS",
            "exampleCount": len(records), "heldOutCount": sum(r.get("split") == "HELD_OUT" for r in records),
            "missingFields": missing, "problems": problems,
            "gradeThresholdsJustified": False, "activated": False,
            "note": "Structural readiness does not approve examples, calibrate thresholds, or activate grading."}


def calibration_preview(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Fit inspectable provisional boundaries to blinded reviewer anchors.

    This is a research output only. It cannot activate or emit product grades.
    Each corpus example must have multiple independent reviewer records.
    """
    structural = validate_calibration(records)
    levels = {"WEAK": 1.0, "ADEQUATE": 2.0, "STRONG": 3.0, "EXCELLENT": 4.0}
    anchors = {"F": 0, "C": 1, "B": 2, "A": 3, "A+": 4}
    prepared: list[dict[str, Any]] = []
    disagreements: list[str] = []
    agreement_values: list[bool] = []
    for record in records:
        judgments = record.get("reviewerJudgments") or []
        if len({j.get("reviewerId") for j in judgments}) < 2:
            continue
        labels = [j.get("overallQualityAnchor") for j in judgments]
        if len(set(labels)) != 1 or labels[0] not in anchors:
            disagreements.append(str(record.get("exampleId")))
            continue
        vectors = []
        for judgment in judgments:
            dim = judgment.get("dimensions") or {}
            values = [levels.get(str((dim.get(key) or {}).get("level"))) for key in DIMENSIONS]
            vectors.append(values)
        if any(any(v is None for v in row) for row in vectors):
            continue
        for i in range(len(judgments)):
            for j in range(i + 1, len(judgments)):
                a, b = judgments[i].get("dimensions") or {}, judgments[j].get("dimensions") or {}
                agreement_values.extend((a.get(key) or {}).get("level") == (b.get(key) or {}).get("level") for key in DIMENSIONS)
        means = [sum(row[index] for row in vectors) / len(vectors) for index in range(len(DIMENSIONS))]
        prepared.append({"id": record.get("exampleId"), "split": record.get("split"), "anchor": anchors[labels[0]], "score": sum(means) / len(means)})

    train = [r for r in prepared if r["split"] == "CALIBRATION"]
    held = [r for r in prepared if r["split"] == "HELD_OUT"]
    missing_anchors = [label for label, value in anchors.items() if not any(r["anchor"] == value for r in train)]
    threshold_labels = ["A+", "A", "B", "C"]
    thresholds: dict[str, float] = {}
    for label in threshold_labels:
        target = anchors[label]
        positives = [r for r in train if r["anchor"] >= target]
        negatives = [r for r in train if r["anchor"] < target]
        if not positives or not negatives:
            continue
        values = sorted({r["score"] for r in train})
        candidates = [values[0] - 1e-9] + [(a + b) / 2 for a, b in zip(values, values[1:])] + [values[-1] + 1e-9]
        def balanced(threshold: float) -> float:
            tpr = sum(r["score"] >= threshold for r in positives) / len(positives)
            tnr = sum(r["score"] < threshold for r in negatives) / len(negatives)
            return (tpr + tnr) / 2
        thresholds[label] = max(candidates, key=lambda value: (balanced(value), -value))
    # Keep grade boundaries ordered: an A threshold cannot be harder to meet
    # than A+, and lower bands cannot accidentally outrank higher bands.
    for higher, lower in zip(("A+", "A", "B"), ("A", "B", "C")):
        if higher in thresholds and lower in thresholds and thresholds[lower] > thresholds[higher]:
            thresholds[lower] = thresholds[higher]

    def predicted(score: float) -> str:
        for label in ("A+", "A", "B", "C"):
            if label in thresholds and score >= thresholds[label]:
                return label
        return "F"
    matrix = {actual: {label: 0 for label in anchors} for actual in anchors}
    for row in held:
        actual = next(label for label, value in anchors.items() if value == row["anchor"])
        matrix[actual][predicted(row["score"])] += 1
    false_a_plus = sum(matrix[actual]["A+"] for actual in ("F", "C", "B", "A"))
    false_a = sum(matrix[actual][prediction] for actual in ("F", "C", "B") for prediction in ("A", "A+"))
    false_negative_a = sum(matrix[actual][prediction] for actual in ("A", "A+") for prediction in ("F", "C", "B"))
    issues = list(structural["problems"])
    if missing_anchors:
        issues.append("Calibration split lacks reviewer anchors for: " + ", ".join(missing_anchors))
    if disagreements:
        issues.append("Reviewer anchor disagreement requires independent adjudication for: " + ", ".join(disagreements))
    if len(held) == 0:
        issues.append("No eligible held-out judgments are available for error analysis.")
    if not thresholds:
        issues.append("No class boundary can be estimated from the reviewed calibration examples.")
    return {
        "rubricVersion": VERSION, "state": "CALIBRATION_PREVIEW_ONLY", "exampleCount": len(prepared),
        "calibrationCount": len(train), "heldOutCount": len(held), "provisionalThresholds": thresholds,
        "thresholdMethod": "PER_CUMULATIVE_CLASS_MAXIMUM_BALANCED_ACCURACY_ON_CALIBRATION_SPLIT",
        "heldOutConfusionMatrix": matrix, "heldOutFalsePositiveAPlus": false_a_plus,
        "heldOutFalsePositiveA": false_a, "heldOutFalseNegativeA": false_negative_a,
        "reviewerDimensionExactAgreement": sum(agreement_values) / len(agreement_values) if agreement_values else None,
        "reviewerAnchorDisagreementExampleIds": disagreements, "missingAnchorClasses": missing_anchors,
        "issues": issues, "aggregateGradesJustified": False, "activated": False,
        "warning": "Provisional empirical cutoffs are diagnostic only; sample size, uncertainty, reviewer agreement and formal approval still determine whether any boundary is defensible.",
    }
