"""Provisional creative-validity evidence, separate from canonical scoring.

This module never changes a Ruleset result.  It prevents transport fixtures,
unverified reviewer labels, and prompt self-description from becoming claims of
real creative effectiveness.
"""
from __future__ import annotations

import re
from hashlib import sha256
from typing import Any

VERSION = "creative-validity-v1"
ORIGINS = {"DETERMINISTIC_FIXTURE", "REAL_AI_PROVIDER", "HUMAN_AUTHORED", "UNKNOWN_ORIGIN"}
DIMENSIONS = (
    "SCROLL_STOP_VISUAL_PROMISE", "CAUSAL_PROGRESSION", "VISUAL_STORYTELLING",
    "PRODUCTION_EXECUTABILITY", "ENDING_REPLAY", "DISTINCTIVE_CREATIVE_VALUE",
)


def _hash(value: Any) -> str | None:
    if value in (None, ""): return None
    return sha256(str(value).encode()).hexdigest()


def normalize_origin(value: Any) -> str:
    raw = str(value or "").upper()
    if raw in ORIGINS: return raw
    if any(token in raw for token in ("FIXTURE", "MOCK", "ISOLATED")): return "DETERMINISTIC_FIXTURE"
    if any(token in raw for token in ("REAL_PROVIDER", "OPENAI", "DEEPSEEK")): return "REAL_AI_PROVIDER"
    if "HUMAN" in raw: return "HUMAN_AUTHORED"
    return "UNKNOWN_ORIGIN"


def provenance_contract(value: dict[str, Any] | None = None) -> dict[str, Any]:
    value = value or {}
    origin = normalize_origin(value.get("origin") or value.get("evidenceOrigin") or value.get("provider"))
    request_fp = value.get("requestFingerprint") or value.get("requestSha256")
    response_fp = value.get("responseFingerprint") or value.get("responseSha256")
    return {
        "version": "creative-evidence-provenance-v1", "origin": origin,
        "provider": value.get("provider"), "model": value.get("model"),
        "storySourceId": value.get("storySourceId"), "promptSourceId": value.get("promptSourceId"),
        "generatorProfile": value.get("generatorProfile"),
        "requestFingerprint": request_fp, "responseFingerprint": response_fp,
        "generationTimestamp": value.get("generationTimestamp") or value.get("timestamp"),
        "evaluatorVersion": value.get("evaluatorVersion"),
        "reviewerOrigin": normalize_origin(value.get("reviewerOrigin")),
        "reviewerIndependent": value.get("reviewerIndependent") is True,
        "realCapabilityStatisticsEligible": origin == "REAL_AI_PROVIDER",
        "officialCalibrationEligible": False,
        "fingerprintsComplete": bool(request_fp and response_fp),
    }


def _rows(canonical: dict[str, Any]) -> list[dict[str, Any]]:
    return sum((canonical.get(k, []) or [] for k in ("passedRules", "failedRules", "unknownRules", "notApplicableRules")), [])


def _timed_beats(prompt: str) -> list[tuple[float, float, str]]:
    result = []
    for m in re.finditer(r"(?mi)^\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)s\s*:\s*(.+)$", prompt):
        result.append((float(m.group(1)), float(m.group(2)), m.group(3).strip()))
    return result


def assess(prompt: str, canonical: dict[str, Any], provenance: dict[str, Any] | None = None,
           reviewer: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return bounded textual evidence; never a creative grade or canonical override."""
    prov = provenance_contract(provenance)
    reviewer = reviewer or {}
    rows = _rows(canonical)
    by_id = {r.get("ruleId"): r for r in rows}
    beats = _timed_beats(prompt)
    opening = beats[0][2] if beats else prompt[:500]
    ending = beats[-1][2] if beats else prompt[-700:]
    ending_actions = re.findall(r"\b(?:sees?|realizes?|stops?|turns?|remains?|sneezes?|scatters?|relieved|cuts?|loops?|reveals?)\b", ending.lower())
    consequences = []
    for _, _, beat in beats:
        tail = beat.split("->", 1)[-1].lower()
        consequences.append(re.sub(r"\b(?:one|two|three|four|eight|\d+)\b", "#", tail))
    repeated_consequence = len(consequences) >= 3 and len(set(consequences[1:-1])) <= max(1, len(consequences[1:-1]) // 2)
    count_progression = len(re.findall(r"\b(?:one|two|four|eight|1|2|4|8)\b", prompt.lower())) >= 4
    production_risks = [r for r in rows if r.get("outcome") in ("FAIL", "UNKNOWN") and r.get("severity") in ("BLOCKER", "CRITICAL")]
    producibility = by_id.get("PRODUCIBILITY_003", {})
    hook = by_id.get("HOOK_002", {})
    reviewer_claim = any(x.get("status") == "CREATIVELY_STRONG" for x in reviewer.get("candidateAssessments", [])) or reviewer.get("status") == "CREATIVELY_STRONG"
    self_claims = re.findall(r"\b(?:scroll[- ]stop|viral|high retention|irresistible|excellent hook|creatively strong)\b", prompt.lower())

    risks: list[dict[str, Any]] = []
    if hook.get("outcome") == "PASS":
        risks.append({"code":"TEXTUAL_HOOK_NOT_VISUAL_PROOF","severity":"MATERIAL","evidence":hook.get("message"),
                      "finding":"HOOK_002 proves a parsed textual opening condition, not scroll-stop or frame-zero excellence."})
    if opening.lower().startswith("already mid-action"):
        risks.append({"code":"FRAME_ZERO_STATE_UNVERIFIED","severity":"MATERIAL","evidence":opening,
                      "finding":"The phrase 'already mid-action' does not specify what is already visible at frame zero."})
    if repeated_consequence or count_progression:
        risks.append({"code":"REPETITIVE_VIEWER_VISIBLE_CONSEQUENCE","severity":"MATERIAL","evidence":consequences,
                      "finding":"Different verbs may still present the same count-multiplication consequence; strategy diversity is provisional."})
    if beats and beats[-1][1] - beats[-1][0] <= 4.1 and len(ending_actions) >= 5:
        risks.append({"code":"ENDING_TIMING_OVERLOAD","severity":"MATERIAL","evidence":{"window":f"{beats[-1][0]}-{beats[-1][1]}s","actions":ending_actions},
                      "finding":"The final window carries too many distinct state/action changes for text-only feasibility confidence."})
    if producibility.get("outcome") == "FAIL":
        risks.append({"code":"CRITICAL_PRODUCIBILITY_RISK","severity":producibility.get("severity"),"evidence":producibility.get("message"),
                      "finding":"Canonical producibility risk remains visible and unresolved."})
    if self_claims:
        risks.append({"code":"UNSUPPORTED_SELF_ASSERTED_QUALITY","severity":"MATERIAL","evidence":sorted(set(self_claims)),
                      "finding":"Prompt quality labels are instructions, not audience or visual evidence."})
    if reviewer_claim and (prov["origin"] == "DETERMINISTIC_FIXTURE" or not prov["reviewerIndependent"]):
        risks.append({"code":"SELF_CONFIRMING_REVIEW","severity":"MATERIAL","evidence":"CREATIVELY_STRONG",
                      "finding":"A fixture or non-independent reviewer label cannot establish real creative strength."})

    def dimension(name: str, outcome: str, state: str, evidence: Any, limitation: str) -> dict[str, Any]:
        return {"dimension":name,"outcome":outcome,"state":state,"evidence":evidence,"limitation":limitation,
                "visualEvidenceVerified":False,"audienceEvidenceVerified":False}
    dims = [
        dimension(DIMENSIONS[0], "UNKNOWN", "TEXTUALLY_STRUCTURED_VISUALLY_UNVERIFIED" if beats else "UNKNOWN", opening,
                  "Curiosity and immediate-problem openings remain valid patterns; rendered frame-zero salience is unobserved."),
        dimension(DIMENSIONS[1], "UNKNOWN" if repeated_consequence or count_progression else "PASS", "REPETITION_RISK" if repeated_consequence or count_progression else "PLAUSIBLE_TEXTUAL_SUPPORT", consequences,
                  "Distinct verbs do not by themselves establish viewer-visible strategy diversity."),
        dimension(DIMENSIONS[2], "UNKNOWN", "UNKNOWN", [b[2] for b in beats], "No rendered visual evidence."),
        dimension(DIMENSIONS[3], "FAIL" if production_risks else "UNKNOWN", "RISK_DETECTED" if production_risks else "PLAUSIBLE_TEXTUAL_SUPPORT", production_risks,
                  "Text parsing cannot prove generator execution."),
        dimension(DIMENSIONS[4], "UNKNOWN", "TIMING_RISK_REPLAY_UNKNOWN" if any(r["code"]=="ENDING_TIMING_OVERLOAD" for r in risks) else "REPLAY_UNKNOWN", ending,
                  "A coherent or unresolved ending is allowed; replay value requires independent evidence."),
        dimension(DIMENSIONS[5], "UNKNOWN", "UNSUPPORTED" if prov["origin"]=="DETERMINISTIC_FIXTURE" else "UNKNOWN", reviewer.get("strengths", []),
                  "Fixture labels and numeric canonical grades do not establish distinctive creative value."),
    ]
    material_risk = any(r["severity"] in ("MATERIAL", "CRITICAL", "BLOCKER") for r in risks)
    return {
        "version": VERSION, "scope": "PROVISIONAL_TEXT_AND_EVIDENCE_VALIDITY",
        "canonicalRulesetUnchanged": True,
        "canonicalScore": canonical.get("score", canonical.get("overallScore")),
        "canonicalGrade": canonical.get("grade"),
        "structuralQualification": "STRUCTURALLY_COMPLIANT" if canonical.get("status") == "EVALUATED" else "STRUCTURAL_STATUS_UNKNOWN",
        "creativeQualityStatus": "CREATIVE_RISK_DETECTED" if material_risk else "CREATIVE_VALIDITY_UNVERIFIED",
        "finalQualification": "PROVISIONAL_CREATIVE_VALIDITY_REQUIRED",
        "creativelyStrongVerified": False, "officialAPlus": "INACTIVE",
        "provenance": {**prov,"evaluatorVersion":prov.get("evaluatorVersion") or canonical.get("rulesetVersion"),
                       "numericCanonicalScore":canonical.get("score",canonical.get("overallScore")),
                       "finalQualification":"PROVISIONAL_CREATIVE_VALIDITY_REQUIRED",
                       "evidenceCompleteness":"INCOMPLETE"},
        "dimensions": dims, "risks": risks,
        "creativeStrengths": [{"claim":"Text supplies a parseable causal sequence.","evidence":"Timed beats and explicit consequences"}] if beats else [],
        "creativeWeaknesses": [{"code":r["code"],"finding":r["finding"],"evidence":r["evidence"]} for r in risks],
        "artificialOptimizationIndicators": [r for r in risks if r["code"] in {"REPETITIVE_VIEWER_VISIBLE_CONSEQUENCE","ENDING_TIMING_OVERLOAD","UNSUPPORTED_SELF_ASSERTED_QUALITY","SELF_CONFIRMING_REVIEW"}],
        "evidenceLimitations": ["No rendered first-frame evidence", "No audience outcome evidence", "No official A+ calibration"],
        "realProviderCapabilityClaimAllowed": prov["realCapabilityStatisticsEligible"] and prov["reviewerIndependent"] and not material_risk,
        "renderAuthorized": False,
    }
