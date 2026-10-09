"""Source-grounded local workflow. No media generation or provider calls here."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any

from app.assessment.family8_projection import project_family8
from app.quality.general_producibility import general_producibility_evidence

VERSION = "post-family-v1"
DECISION_POLICY_VERSION = "impact-review-v1"
EXTRACTION_VERSION = "source-span-production-evidence-v1"
PROFILES = ("ABSURD_PHYSICS", "CURIOSITY_ADVENTURE", "EDUCATIONAL", "MIXED", "UNKNOWN")
GENERATORS = ("SEEDANCE_2_0_MINI", "SEEDANCE_2_0", "SEEDANCE_2_5")
MODEL_IDS = dict(
    zip(
        GENERATORS,
        ("byte-plus-seedance-2-mini", "byte-plus-seedance-2", "byte-plus-seedance-2-5"),
        strict=True,
    )
)
TIMES = re.compile(
    r"(?im)^[ \t]*(?:[-*]\s*)?(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)"
    r"\s*(?:s(?:ec(?:onds?)?)?\b|:)"
)
# Each detector describes a different required dependency. Matches are retained
# as claims, never used as proof that the remaining dimensions are absent.
DEPENDENCIES = (
    (
        "fineMotorRequirement",
        r"[^.\n]*(?:thread(?:ing)? (?:a |the )?(?:tiny )?needle|"
        r"exact finger placement|two.finger|pinch(?:es|ing)? (?:a |the )?tiny)[^.\n]*",
        "HIGH",
    ),
    (
        "contactPhysicsRequirement",
        r"[^.\n]*(?:catch(?:es|ing)?|between (?:his |her |the )?hands|"
        r"sticks? (?:there|to|onto)|precise collision|balanc(?:e|es|ing)|stack(?:s|ing))[^.\n]*",
        "HIGH",
    ),
    (
        "objectContinuity",
        r"[^.\n]*(?:same (?:journal|object|ball|box)|must (?:remain|return) (?:unchanged|identical))[^.\n]*",
        "HIGH",
    ),
    (
        "characterContinuity",
        r"[^.\n]*(?:same character|identity (?:must|across)|large pose changes)[^.\n]*",
        "MODERATE",
    ),
    (
        "occlusionRequirement",
        r"[^.\n]*(?:disappears? behind|fully occluded|out of frame|hidden under)[^.\n]*",
        "MODERATE",
    ),
    (
        "exactCountDependency",
        r"[^.\n]*(?:exactly \d+|exact(?: visual)? count|(?:three|six|twelve|3|6|"
        r"12) (?:balls|objects|copies))[^.\n]*",
        "HIGH",
    ),
    (
        "transformationRequirement",
        r"[^.\n]*(?:morph(?:s|ing)?|split(?:s|ting)? into|merg(?:es|ing)|"
        r"stretches? (?:toward|like)|flexes? (?:slightly|toward)|"
        r"return(?:s)? to (?:its|their) original shape)[^.\n]*",
        "MODERATE",
    ),
    (
        "simulationRequirement",
        r"[^.\n]*(?:precise (?:liquid|cloth|particles)|liquid (?:must|spills)|"
        r"fabric (?:must|folds)|individual particles)[^.\n]*",
        "MODERATE",
    ),
    (
        "spatialRequirement",
        r"[^.\n]*(?:mirror|reflection|narrow gap|exact (?:left|right|position|target)|same spot)[^.\n]*",
        "HIGH",
    ),
    (
        "sceneContinuityRequirement",
        r"[^.\n]*(?:same .+ across (?:scenes|locations)|state .+ next scene)[^.\n]*",
        "HIGH",
    ),
    (
        "textRequirement",
        r"[^.\n]*(?:exact readable text|letters must match|lip.sync|synchroni[sz]ed (?:mouth|speech))[^.\n]*",
        "HIGH",
    ),
    (
        "segmentContinuityRequirement",
        r"[^.\n]*(?:same .+ (?:clips|segments)|identical .+ (?:clips|segments)|"
        r"match .+ (?:handoff|segment))[^.\n]*",
        "HIGH",
    ),
)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def binding_fingerprint(request: dict[str, Any]) -> str:
    keys = (
        "prompt",
        "sourceId",
        "sourceVersion",
        "profile",
        "references",
        "generator",
        "desiredDuration",
        "settings",
        "segments",
        "contentProfile",
        "openingStrategy",
        "protectedIntent",
        "qualityJustification",
        "structuredPlan",
        "viewerQuestion",
        "plannedEditedDuration",
        "intentRequirements",
        "creativeEvidence",
        "intentChangeReason",
    )
    return sha256(
        json.dumps(
            {**{key: request.get(key) for key in keys}, "decisionPolicyVersion": DECISION_POLICY_VERSION, **({"retrievedLessons": request["retrievedLessons"]} if request.get("retrievedLessons") else {})},
            sort_keys=True,
            ensure_ascii=False,
        )
    )


def source_claim(
    request: dict[str, Any], field: str, match: re.Match[str], state: str = "INFERRED"
) -> dict[str, Any]:
    return {
        "field": field,
        "state": state,
        "quote": match.group(),
        "span": list(match.span()),
        "sourceId": request.get("sourceId"),
        "sourceVersion": request.get("sourceVersion"),
        "sourceHash": sha256(request["prompt"]),
        "method": "LOCAL_SOURCE_PATTERN",
        "methodVersion": EXTRACTION_VERSION,
        "provider": None,
        "confidence": "MEDIUM" if state == "INFERRED" else "HIGH",
    }


def enrich_production_evidence(request: dict[str, Any]) -> dict[str, Any]:
    text = request["prompt"]
    source = {
        "artifact": request.get("sourceId"),
        "version": request.get("sourceVersion"),
        "sha256": sha256(text),
    }
    claims: list[dict[str, Any]] = []
    ir: dict[str, Any] = {
        "metadata": {
            "generalProducibilityEvidence": {
                "source": "POST_FAMILY_SOURCE_ENRICHMENT",
                "sourceHash": source["sha256"],
                "sourceVersion": source["version"],
                "extractionVersion": EXTRACTION_VERSION,
            }
        }
    }
    beats: list[dict[str, Any]] = []
    intervals = list(TIMES.finditer(text))
    for index, match in enumerate(intervals):
        start, end = map(float, match.groups())
        if end <= start:
            continue
        action_end = intervals[index + 1].start() if index + 1 < len(intervals) else len(text)
        action = text[match.end() : action_end].strip()
        # A text section is not an exhaustive object/actor inventory. Keep it
        # incomplete until a separately grounded tracked plan supplies one.
        beats.append(
            {
                "id": f"source_{index}",
                "startTime": start,
                "endTime": end,
                "action": action,
                "sourceSpan": [match.start(), action_end],
            }
        )
        claims.append(source_claim(request, "beats", match, "OBSERVED"))
    ir["beats"] = beats
    declared = re.search(r"(?i)(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*second", text)
    single = re.search(r"(?i)(\d+(?:\.\d+)?)\s*(?:-| )?second\b", text)
    duration = float(declared.group(2)) if declared else float(single.group(1)) if single else None
    if duration is None and beats:
        duration = max(beat["endTime"] for beat in beats)
    if duration is None:
        duration = request.get("desiredDuration")
    if duration is not None and duration > 0:
        ir["metadata"]["duration"] = duration
    for field, pattern, precision in DEPENDENCIES:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        negative = [
            match
            for match in matches
            if re.search(
                r"(?i)\b(?:no|without|avoid|do not|never)\s+(?:any\s+)?"
                r"(?:lip.sync|morph|transformation|simulation|exact readable text)",
                match.group(),
            )
        ]
        matches = [match for match in matches if match not in negative]
        for match in negative:
            claim = source_claim(request, field, match, "OBSERVED_NOT_REQUIRED")
            claim["required"] = False
            claims.append(claim)
        if negative and not matches:
            ir[field] = {
                "required": False,
                "evidenceReferences": [
                    f"{source['artifact']}#chars={match.start()}-{match.end()}" for match in negative
                ],
                "reason": "Explicit source exclusion; not inferred from omission.",
            }
            continue
        if matches:
            observed = (
                "OBSERVED"
                if any(re.search(r"(?i)must|required|exact|lip.sync", m.group()) for m in matches)
                else "INFERRED"
            )
            new_claims = [source_claim(request, field, match, observed) for match in matches]
            claims.extend(new_claims)
            refs = [f"{source['artifact']}#chars={c['span'][0]}-{c['span'][1]}" for c in new_claims]
            ir[field] = {
                "required": True,
                "precision": precision,
                "evidenceReferences": refs,
                "reason": "; ".join(c["quote"].strip() for c in new_claims[:2]),
            }
            if field == "exactCountDependency":
                ir[field]["acrossStages"] = len(matches) > 1
        else:
            claims.append(
                {
                    "field": field,
                    "state": "MISSING",
                    "quote": None,
                    "span": None,
                    "sourceId": source["artifact"],
                    "sourceVersion": source["version"],
                    "sourceHash": source["sha256"],
                    "methodVersion": EXTRACTION_VERSION,
                    "confidence": None,
                    "reason": "Omission does not confirm absence.",
                }
            )
    supplied = request.get("structuredPlan")
    if isinstance(supplied, dict):
        # Source-bound tracked plan: every beat must quote a real source span.
        tracked = supplied.get("beats") or []
        valid = bool(tracked) and all(
            valid_span(text, b.get("sourceSpan"), b.get("sourceQuote"))
            and isinstance(b.get("action"), str)
            and b["action"] in b["sourceQuote"]
            and all(
                isinstance(name, str) and name.lower() in b["sourceQuote"].lower()
                for field in ("actors", "objects", "heldObjects")
                for name in b.get(field, [])
            )
            for b in tracked
        )
        if valid:
            ir["beats"] = deepcopy(tracked)
            claims.append(
                {
                    "field": "trackedPlan",
                    "state": "OBSERVED",
                    "sourceHash": source["sha256"],
                    "methodVersion": "OPERATOR_SOURCE_BOUND_PLAN_V1",
                    "confidence": "HUMAN_REVIEWED",
                }
            )
            # To avoid treating unscreened omissions as LOW, retain incomplete
            # tracking until all production dependency fields were reviewed.
            if any(c["state"] == "MISSING" for c in claims):
                for beat in ir["beats"]:
                    beat.pop("objects", None)
                    beat.pop("heldObjects", None)
                    beat.pop("targetObject", None)
        else:
            claims.append(
                {
                    "field": "trackedPlan",
                    "state": "CONTRADICTORY",
                    "sourceHash": source["sha256"],
                    "methodVersion": EXTRACTION_VERSION,
                    "reason": "Plan spans do not match the source.",
                }
            )
    projection = general_producibility_evidence(ir)
    return {
        "source": source,
        "claims": claims,
        "videoPlanIR": ir,
        "generalProducibility": projection,
        "remainingUncertainty": [c["field"] for c in claims if c["state"] in {"MISSING", "CONTRADICTORY"}],
    }


def valid_span(text: str, span: Any, quote: Any) -> bool:
    return (
        isinstance(span, list)
        and len(span) == 2
        and all(isinstance(x, int) for x in span)
        and 0 <= span[0] < span[1] <= len(text)
        and isinstance(quote, str)
        and text[span[0] : span[1]] == quote
    )


def route_content(request: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    selected = request.get("contentProfile", "AUTO")
    text = request["prompt"]
    if selected in PROFILES:
        return {
            "contentProfile": selected,
            "basis": "OPERATOR_SELECTED",
            "confidence": "HUMAN_REVIEWED",
            "viewerQuestion": request.get("viewerQuestion") or None,
            "alternatives": [],
        }
    # Central progression across source clauses, not names, isolated nouns or labels.
    discovery = re.search(
        r"(?i)discover|reveals?|explor|earth tour|emotional turn|found you|hidden path", text
    )
    learning = re.search(
        r"(?i)learning objective|teach[^.\n]*(?:shape|color|number)|"
        r"(?:demonstrat|explain|compare)[^.\n]*(?:shape|color|number)",
        text,
    )
    physics = bool(
        re.search(
            r"(?i)sticks?[^.\n]{0,80}instead of bouncing|defies? gravity|"
            r"gravity revers|grows? gigantic|impossible[^.\n]*(?:physics|motion|shape)",
            text,
        )
    ) and any(
        c["field"] in {"transformationRequirement", "contactPhysicsRequirement"} and c["state"] != "MISSING"
        for c in evidence["claims"]
    )
    candidates = []
    if discovery and len(evidence["videoPlanIR"]["beats"]) >= 2:
        candidates.append("CURIOSITY_ADVENTURE")
    if learning:
        candidates.append("EDUCATIONAL")
    if physics:
        candidates.append("ABSURD_PHYSICS")
    profile = candidates[0] if len(candidates) == 1 else "MIXED" if candidates else "UNKNOWN"
    return {
        "contentProfile": profile,
        "basis": "SOURCE_PROGRESSION_HYPOTHESIS",
        "confidence": "LOW",
        "viewerQuestion": request.get("viewerQuestion"),
        "alternatives": candidates,
        "reason": "Kaynak mekanizması bir öneri üretir; operatör seçimi ile doğrulayın.",
    }


def generation_plan(
    request: dict[str, Any], evidence: dict[str, Any], capabilities: dict[str, Any]
) -> dict[str, Any]:
    duration = request.get("desiredDuration") or evidence["videoPlanIR"]["metadata"].get("duration")
    preferred = (
        "SEEDANCE_2_5"
        if duration and duration > 15
        else "SEEDANCE_2_0"
        if request.get("qualityJustification")
        else "SEEDANCE_2_0_MINI"
    )
    selected = request.get("generator")
    selected = str(preferred if selected in {None, "AUTO"} else selected)
    capability = capabilities.get(selected) or {}
    settings = request.get("settings") or {}
    mode = settings.get("mode", "image2video")
    schema = (capability.get("modes") or {}).get(mode)
    status = "UNKNOWN"
    reasons: list[str] = []
    missing_inputs: list[str] = []
    if schema:
        missing_inputs = [key for key in schema.get("required", []) if key not in settings]
        props = schema.get("properties") or {}
        spec = props.get("duration") or {}
        supported = (
            duration is not None
            and isinstance(duration, (int, float))
            and duration == int(duration)
            and spec.get("minimum", float("inf")) <= duration <= spec.get("maximum", -1)
        )
        for key, value in settings.items():
            if key == "mode":
                continue
            option = props.get(key)
            if not option or ("enum" in option and value not in option["enum"]):
                supported = False
                reasons.append(f"Unsupported setting: {key}={value}")
            elif option.get("type") == "object":
                if not isinstance(value, dict) or any(
                    not value.get(field) for field in option.get("required", [])
                ):
                    supported = False
                    reasons.append(f"Incomplete structured setting: {key}")
                elif any(field not in option.get("properties", {}) for field in value):
                    supported = False
                    reasons.append(f"Unsupported structured setting: {key}")
        status = "SUPPORTED" if supported else "UNSUPPORTED"
        if not supported:
            reasons.append("İstenen süre/ayar sözleşmede yok; başka modele veya süreye otomatik geçilmedi.")
    else:
        reasons.append("Seçilen model/mod için doğrulanmış bağlı sağlayıcı sözleşmesi yok.")
    return {
        "recommendedGenerator": preferred,
        "selectedGenerator": selected,
        "apiModelId": capability.get("apiModelId"),
        "desiredDuration": duration,
        "supportedRenderDuration": duration if status == "SUPPORTED" else None,
        "plannedEditedDuration": request.get("plannedEditedDuration") or duration,
        "capabilityStatus": status,
        "missingExecutionInputs": missing_inputs,
        "capabilityProvenance": capability.get("provenance"),
        "profileVersion": capability.get("version"),
        "mode": mode,
        "settings": settings,
        "segments": request.get("segments") or [],
        "reasons": reasons,
        "selectionReason": request.get("qualityJustification")
        or "Konsept süresine göre kullanıcı üretim tercihi.",
    }


def supported_source(request: dict[str, Any], item: dict[str, Any]) -> bool:
    span, quote = item.get("sourceSpan"), item.get("sourceQuote")
    return bool(isinstance(quote, str) and quote and valid_span(request["prompt"], span, quote))


def intent_requirements(request: dict[str, Any], evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Only explicit source-bound intent; no retrospective render-side reclassification."""
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    ids = {b["id"] for b in evidence["videoPlanIR"]["beats"]}
    for item in request.get("intentRequirements") or []:
        if not isinstance(item, dict):
            result.append({"status": "UNKNOWN", "reason": "Invalid intent declaration"})
            continue
        supported = (
            supported_source(request, item)
            and item.get("level") in {"ESSENTIAL", "FLEXIBLE", "POLISH"}
            and isinstance(item.get("id"), str)
            and bool(item.get("id"))
            and item["id"] not in seen
            and isinstance(item.get("eventIds", []), list)
            and all(isinstance(i, str) for i in item.get("eventIds", []))
            and set(item.get("eventIds", [])) <= ids
        )
        if isinstance(item.get("id"), str):
            seen.add(item["id"])
        result.append(
            {
                **{
                    k: item.get(k)
                    for k in ("id", "level", "sourceSpan", "sourceQuote", "eventIds", "rationale")
                },
                "status": "SOURCE_SUPPORTED" if supported else "UNKNOWN",
                "sourceHash": evidence["source"]["sha256"],
                "sourceVersion": evidence["source"].get("version"),
                "basis": "EXPLICIT_PRE_RENDER_SOURCE_DECLARATION",
            }
        )
    # Existing protected anchors are explicit operator intent, not auto-invented requirements.
    for index, quote in enumerate(request.get("protectedIntent") or []):
        start = request["prompt"].find(quote)
        if start < 0 or not quote:
            result.append(
                {
                    "id": f"protected-{index + 1}",
                    "level": "ESSENTIAL",
                    "sourceQuote": quote,
                    "status": "UNKNOWN",
                }
            )
        else:
            result.append(
                {
                    "id": f"protected-{index + 1}",
                    "level": "ESSENTIAL",
                    "sourceQuote": quote,
                    "sourceSpan": [start, start + len(quote)],
                    "status": "SOURCE_SUPPORTED",
                    "eventIds": [b["id"] for b in evidence["videoPlanIR"]["beats"] if quote in b["action"]],
                    "sourceHash": evidence["source"]["sha256"],
                    "basis": "EXPLICIT_PROTECTED_SOURCE_ANCHOR",
                }
            )
    return result


def plan_quality(request: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    beats = evidence["videoPlanIR"]["beats"]
    allowed = {
        "OPENING": {
            "READABLE_EARLY_DEVELOPMENT",
            "READABLE_PROMISE",
            "UNREADABLE",
            "EXCESSIVELY_DELAYED",
            "UNKNOWN",
        },
        "PROGRESSION": {"DEVELOPING", "WEAK", "PURPOSEFUL_REPETITION", "UNKNOWN"},
        "ENDING": {"DELIVERS_PROMISE", "PURPOSEFUL_UNRESOLVED", "ARBITRARY_TRUNCATION", "WEAK", "UNKNOWN"},
        "SAFETY": {"APPROPRIATE", "CONFIRMED_FAILURE", "UNKNOWN"},
    }
    interpretations: dict[str, dict[str, Any]] = {}
    invalid: list[dict[str, str]] = []
    for item in request.get("creativeEvidence") or []:
        if (
            not isinstance(item, dict)
            or not supported_source(request, item)
            or item.get("assessment") not in allowed.get(str(item.get("dimension")), set())
            or not item.get("rationale")
        ):
            invalid.append({"status": "UNKNOWN", "reason": "Unsupported source interpretation"})
            continue
        interpretations[item["dimension"]] = {
            **{
                k: item.get(k)
                for k in (
                    "assessment",
                    "sourceSpan",
                    "sourceQuote",
                    "rationale",
                    "visualFocus",
                    "promise",
                    "causeAtFrameZero",
                    "promiseSupportedAt",
                    "mechanisms",
                    "functions",
                )
            },
            "basis": "OPERATOR_SOURCE_INTERPRETATION",
            "confidence": "HYPOTHESIS",
        }
    opening: dict[str, Any] = {
        "assessment": "UNKNOWN",
        "visualFocus": "UNKNOWN",
        "promise": "UNKNOWN",
        "causeAtFrameZero": "UNKNOWN",
        "plannedFirstBeat": beats[0]["action"] if beats else None,
        **interpretations.get("OPENING", {}),
    }
    progression: dict[str, Any] = {
        "assessment": "UNKNOWN",
        "mechanisms": [],
        **interpretations.get("PROGRESSION", {}),
    }
    progression["mechanisms"] = [
        m
        for m in progression.get("mechanisms") or []
        if m in {"PHYSICAL", "RELATIONAL", "INFORMATIONAL", "EMOTIONAL", "RHYTHMIC_VISUAL"}
    ]
    ending: dict[str, Any] = {
        "assessment": "UNKNOWN",
        "functions": [],
        "sameVideoReplay": "UNKNOWN",
        "sequelCuriosity": "UNKNOWN",
        "plannedLastBeat": beats[-1]["action"] if beats else None,
        **interpretations.get("ENDING", {}),
    }
    ending["functions"] = [
        f
        for f in ending.get("functions") or []
        if f
        in {
            "RESOLUTION",
            "REVEAL",
            "REFRAME",
            "REVERSAL",
            "EMOTIONAL_SATISFACTION",
            "VISUAL_RESET",
            "CALLBACK",
            "PURPOSEFUL_UNRESOLVED",
        }
    ]
    if ending["assessment"] == "ARBITRARY_TRUNCATION":
        ending["functions"] = [f for f in ending["functions"] if f != "PURPOSEFUL_UNRESOLVED"]
    elif set(ending["functions"]) & {"CALLBACK", "REFRAME", "VISUAL_RESET"}:
        ending["sameVideoReplay"] = "HYPOTHESIS"
    findings = []
    for dimension, item in interpretations.items():
        if item["assessment"] in {
            "UNREADABLE",
            "CONFIRMED_FAILURE",
            "EXCESSIVELY_DELAYED",
            "WEAK",
            "ARBITRARY_TRUNCATION",
        }:
            findings.append(
                {
                    "dimension": dimension,
                    "rawResult": item,
                    "applicability": "APPLICABLE",
                    "severity": "BLOCKING"
                    if item["assessment"] in {"UNREADABLE", "CONFIRMED_FAILURE"}
                    else "WARNING",
                    "impact": "COMPREHENSION_OR_SAFETY"
                    if dimension in {"OPENING", "SAFETY"}
                    else "WEAK_VIEWING_EXPERIENCE",
                    "recommendation": "MATERIAL_CONCEPT_REPAIR",
                }
            )
    recommendation = (
        "MATERIAL_CONCEPT_REPAIR"
        if findings
        else "PROCEED_NEXT_EVIDENCE_STEP"
        if beats
        else "INSUFFICIENT_EVIDENCE"
    )
    return {
        "status": "HYPOTHESIS" if beats else "UNKNOWN",
        "opening": opening,
        "progression": progression,
        "ending": ending,
        "findings": findings,
        "invalidEvidence": invalid,
        "recommendation": recommendation,
        "audienceModel": "Adult discovery; child-appropriate shared viewing",
        "objective": ["SCROLL_STOP", "ATTENTION", "COMPLETION", "REWATCH_OR_SHARE_HYPOTHESIS"],
        "limitations": [
            "Source interpretations are planned experience, never actual frame evidence or predicted views.",
            "Motion, repetition, holds and different verbs alone do not establish progression.",
        ],
    }


def execution_decision(execution: dict[str, Any]) -> dict[str, Any]:
    findings = []
    for item in execution.get("findings", []):
        basis = item.get("evidenceBasis")
        findings.append(
            {
                "rawResult": item,
                "applicability": "APPLICABLE",
                "severity": "WARNING",
                "basis": basis,
                "confidence": item.get("confidence"),
                "recommendation": "MINIMAL_PROMPT_REPAIR",
                "authorizationBlocking": False,
                "reason": "Speculative execution limitation is advisory; no confirmed essential failure.",
            }
        )
    return {
        "status": "ADVISORY_RISK" if findings else execution["status"],
        "findings": findings,
        "selectedGenerator": execution.get("targetGenerator"),
        "rawStatus": execution["status"],
        "visualInspected": False,
    }


def operator_report(
    plan: dict[str, Any], execution: dict[str, Any], actual: dict[str, Any] | None = None
) -> list[dict[str, str]]:
    actual = actual or {}
    defects = actual.get("findings") or []
    severity_labels = {"WARNING": "Uyarı", "BLOCKING": "Temel engel", "UNKNOWN": "Kanıt yetersiz"}
    decision_labels = {
        "PROCEED_NEXT_EVIDENCE_STEP": "Gerekli sonraki üretim/kanıt adımına geç",
        "MINIMAL_PROMPT_REPAIR": "Küçük prompt düzeltmesi önerilir",
        "MATERIAL_CONCEPT_REPAIR": "İzleme deneyimini koruyan kavram düzeltmesi gerekir",
        "INSUFFICIENT_EVIDENCE": "Karar için kanıt yetersiz",
        "TEST_CANDIDATE": "Kontrollü izleyici testi için editoryal aday",
        "EDIT_RECOMMENDED": "Kurgu düzenlemesi önerilir",
        "UNUSABLE_CONFIRMED_BLOCKER": "Doğrulanmış temel engel nedeniyle kullanılamaz",
        "RERENDER_MATERIALLY_JUSTIFIED": "Temel faydası gerekçelendirilmiş yeniden render önerisi",
    }
    decision = actual.get("editorialRecommendation") or plan.get("recommendation")
    progression = plan.get("progression", {})
    mechanism = (
        progression.get("rationale")
        or plan.get("opening", {}).get("plannedFirstBeat")
        or "İzleme gerekçesini değerlendirmek için kaynak kanıtı yetersiz"
    )

    experience = actual.get("experience", {})
    opening_text = plan.get("opening", {}).get("rationale") or plan.get("opening", {}).get("plannedFirstBeat")
    progression_text = plan.get("progression", {}).get("rationale")
    if actual:
        opening_fact = experience.get("opening", {})
        opening_frame = experience.get("openingFrame", {})
        if opening_fact.get("status") == "OBSERVED":
            opening_text = opening_fact.get("observed")
        else:
            opening_text = (
                str(opening_frame.get("observed") or "")
                + " Gerçek açılış hareketi için kanıt yetersiz. Planlanan vaat: "
                + str(opening_text or "UNKNOWN")
            )
        progression_fact = experience.get("progression", {})
        progression_text = (
            progression_fact.get("observed")
            if progression_fact.get("status") == "OBSERVED"
            else "Gerçek ilerleme için kanıt yetersiz. Planlanan değişim: "
            + str(progression_text or "UNKNOWN")
        )

    return [
        {"label": label, "text": str(value or "Kanıt yetersiz")}
        for label, value in (
            ("KARAR", decision_labels.get(str(decision), str(decision or "Kanıt yetersiz"))),
            ("İZLEME MEKANİZMASI", mechanism),
            ("AÇILIŞ", opening_text),
            ("İLERLEME", progression_text),
            (
                "FİNAL",
                actual.get("experience", {}).get("ending", {}).get("observed")
                if actual.get("experience", {}).get("ending", {}).get("status") == "OBSERVED"
                else "Planlanan final: "
                + str(
                    plan.get("ending", {}).get("rationale")
                    or plan.get("ending", {}).get("plannedLastBeat")
                    or "UNKNOWN"
                ),
            ),
            (
                "TEMEL OLAY/KİMLİK/ANLAŞILABİLİRLİK",
                {
                    "USABLE": "Temel deneyim okunabilir ve kullanılabilir",
                    "UNUSABLE": "Doğrulanmış temel olay/kimlik/anlaşılabilirlik engeli",
                    "READABLE_BUT_CREATIVELY_WEAK": "Okunabilir; izleme deneyiminin gelişimi zayıf",
                    "UNKNOWN": "Gerçek video deneyimi için kanıt yetersiz",
                }.get(actual.get("viewerFacingUsability", ""), "Gerçek video henüz incelenmedi"),
            ),
            (
                "TEKNİK KUSURLAR",
                "; ".join(
                    f"{d.get('start')}–{d.get('end')} s: "
                    f"{d.get('observed') or d.get('type', 'PLAN_DEVIATION')}"
                    for d in defects
                )
                or "Doğrulanmış kusur kanıtı yok",
            ),
            (
                "KUSURUN ETKİSİ",
                "; ".join(
                    f"{severity_labels.get(d.get('severity'), d.get('severity'))}: "
                    f"{d.get('inferred') or d.get('reason') or d.get('viewerImpact')}"
                    for d in defects
                )
                or "Yalnız teknik temizlik yaratıcı değer kanıtı değildir",
            ),
            (
                "EN KÜÇÜK MÜDAHALE",
                actual.get("smallestIntervention")
                or ("MINIMAL_PROMPT_REPAIR" if execution.get("findings") else plan.get("recommendation")),
            ),
            ("PERFORMANS", "Kör inceleme tamamlanana kadar sonuç verisi ayrıdır; izlenme garantisi yok"),
        )
    ]


def engagement_review(request: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    beats = evidence["videoPlanIR"]["beats"]
    opening = beats[0]["action"] if beats else None
    ending = beats[-1]["action"] if beats else None
    purposeful = bool(
        ending and re.search(r"(?i)callback|loop|return|again|reveals?|lights? up|same|remember", ending)
    )
    sequel = bool(
        ending and re.search(r"(?i)cliffhanger|continue|next episode|to explore|mystery remains", ending)
    )
    return {
        "stage": "PROMPT_REVIEW",
        "status": "HYPOTHESIS" if beats else "UNKNOWN",
        "attentionPromise": opening,
        "progression": [b["action"] for b in beats[1:-1]],
        "endingDelivery": ending,
        "rewatchMechanism": "CALLBACK_OR_LOOP_HYPOTHESIS"
        if purposeful
        else "SEQUEL_CURIOSITY"
        if sequel
        else "UNKNOWN",
        "endingKind": "OPEN_LOOP_HYPOTHESIS_REQUIRES_DELIVERY_REVIEW"
        if sequel
        else "PLANNED_ENDING"
        if ending
        else "UNKNOWN",
        "limitations": [
            "Ön değerlendirme hipotezdir; izlenme/retention yüzdesi tahmini değildir.",
            "Cevapsız soru tek başına aynı videoyu tekrar izleme kanıtı değildir.",
            "Durağanlık tek başına gereksiz ölü zaman değildir.",
        ],
    }


def opening_review(
    request: dict[str, Any], evidence: dict[str, Any], routing: dict[str, Any]
) -> dict[str, Any]:
    beats = evidence["videoPlanIR"]["beats"]
    duration = evidence["videoPlanIR"]["metadata"].get("duration")
    strategy = request.get("openingStrategy")
    if strategy in {None, "AUTO"}:
        strategy = (
            "INSTANT_IMPOSSIBLE" if routing["contentProfile"] == "ABSURD_PHYSICS" else "CURIOSITY_DISCOVERY"
        )
    canonical = request.get("authorizationEvidence") or {}
    gate = (canonical.get("visualEvidence") or {}).get("firstFrame") or {}
    frame_id = ((request.get("settings") or {}).get("startFrame") or {}).get("id")
    frame_bound = any(
        ref.get("kind") == "FIRST_FRAME"
        and ref.get("status") == "VERIFIED"
        and ref.get("relativePath") == frame_id
        and ref.get("sha256") == gate.get("assetSha256")
        for ref in request.get("references", [])
    )
    actual_frame = {"status": "UNKNOWN"}
    if (
        canonical.get("fresh") is True
        and canonical.get("promptSha256") == sha256(request["prompt"])
        and gate.get("status") == "PASS"
        and gate.get("assetSha256")
        and frame_bound
    ):
        actual_frame = {**gate, "status": "PASS", "basis": "CANONICAL_BOUND_FRAME_EVIDENCE"}
    return {
        "strategy": strategy,
        "designWindowSeconds": min(2.0, duration / 3) if duration else None,
        "plannedOpening": {
            "status": "HYPOTHESIS" if beats else "UNKNOWN",
            "sourceSpan": beats[0].get("sourceSpan") if beats else None,
            "visualPromise": beats[0]["action"] if beats else None,
        },
        "actualFirstFrame": actual_frame,
        "actualOpeningVideo": {"status": "UNKNOWN"},
        "cover": {"status": "NOT_EVIDENCE_OF_OPENING"},
        "alternatives": [
            "Nesne önce: anormalliği/öğrenme sorusunu okunur göster.",
            "Tepki + sorun: karakter ile görsel nedenini aynı kadrajda göster.",
            "Aksiyon önce: sonucu doğuran hareketle aç.",
        ]
        if not beats
        else [],
        "reason": (
            "Odak ve görsel vaat erkenden okunmalı; "
            "frame zero tam nedensellik açıklaması zorunlu değildir. "
            "Tasarım penceresi kabul eşiği değildir."
        ),
    }


def review_prompt(request: dict[str, Any], capabilities: dict[str, Any] | None = None) -> dict[str, Any]:
    from .critic import LocalExecutionCritic

    if request.get("profile") != VERSION:
        raise ValueError("Explicit post-family-v1 selection required")
    evidence = enrich_production_evidence(request)
    routing = route_content(request, evidence)
    generation = generation_plan(request, evidence, capabilities or {})
    # Approval is checked by the backend; the resolved target capability must match too.
    requested_lessons = request.get("retrievedLessons") or []
    def stable_settings(value):
        return {key: value[key] for key in value if key != "startFrame"}
    matched_lessons = [lesson for lesson in requested_lessons
        if generation.get("profileVersion")
        and lesson.get("targetModelVersion") == generation["profileVersion"]
        and lesson.get("contentProfile") == routing.get("contentProfile")
        and stable_settings(lesson.get("settings") or {}) == stable_settings(generation.get("settings") or {})]
    request = {**request, "retrievedLessons": matched_lessons}
    execution = LocalExecutionCritic().review(request, evidence, generation)
    intent = intent_requirements(request, evidence)
    quality = plan_quality(request, evidence)
    execution_risk = execution_decision(execution)
    references = request.get("references") or []
    named = set(re.findall(r"(?i)\b(Luca|Zipo|Kiko|Mimi|Pompom)\b", request["prompt"]))
    required_names = {name.lower() for name in named}
    supplied_names = {
        str(r.get("character", "")).strip().lower()
        for r in references
        if r.get("kind") in {"CHARACTER", "CHARACTER_REFERENCE"}
    }
    reference_ready = (
        bool(references)
        and required_names <= supplied_names
        and all(
            r.get("status") == "VERIFIED" and re.fullmatch("[a-f0-9]{64}", str(r.get("sha256") or ""))
            for r in references
        )
    )
    reasons: list[dict[str, Any]] = []

    def pending(message: str, source: str) -> None:
        reasons.append(
            {"code": "REQUIRED_EVIDENCE_MISSING", "source": source, "message": message, "references": []}
        )

    if not reference_ready:
        pending("Yetkili karakter/nesne referansı eksik veya doğrulanmadı.", "REFERENCE_ASSOCIATION")
    if generation["capabilityStatus"] != "SUPPORTED":
        pending("İstenen model/süre/ayar doğrulanmış sözleşmeyle desteklenmiyor.", "GENERATOR_CAPABILITY")
    if generation["missingExecutionInputs"]:
        pending(
            "Sağlayıcının zorunlu yürütme girdileri eksik: "
            + ", ".join(generation["missingExecutionInputs"]),
            "EXECUTION_INPUTS",
        )
    if execution["status"] == "UNKNOWN":
        pending(
            "Jeneratör yürütme incelemesi tamamlanmadı veya küçük düzeltme gerekiyor.", "EXECUTION_REVIEW"
        )
    if evidence["generalProducibility"]["status"] == "UNKNOWN":
        pending("Genel üretilebilirlik için kaynak kanıtı yetersiz.", "GENERAL_PRODUCIBILITY")
    if any(c["state"] == "CONTRADICTORY" for c in evidence["claims"]):
        reasons.append(
            {
                "code": "ASSESSMENT_TECHNICAL_FAILURE",
                "source": "SOURCE_INTEGRITY",
                "message": "Çelişkili kaynak kanıtı.",
                "references": [],
            }
        )
    if quality["invalidEvidence"] or any(i["status"] == "UNKNOWN" for i in intent):
        pending("Temel niyet/yaratıcı yorum gerçek kaynakla doğrulanmadı.", "INTENT_SOURCE_INTEGRITY")
    for finding in quality["findings"]:
        if finding["severity"] == "BLOCKING":
            reasons.append(
                {
                    "code": "CREATIVE_BLOCKER",
                    "source": "POST_FAMILY_IMPACT_PLAN",
                    "message": finding["impact"],
                    "references": [finding["rawResult"]["sourceQuote"]],
                }
            )
    canonical = request.get("authorizationEvidence") or {}
    integrity = (
        canonical.get("renderAuthorization") == "AUTHORIZED"
        and canonical.get("promptSha256") == sha256(request["prompt"])
        and canonical.get("finalVideoEligible") is True
        and canonical.get("independentRevalidationId") is not None
        and canonical.get("fresh") is True
        and ("+profile-admission-v1:" not in str(canonical.get("deterministicRulesetVersion", "")) or str(canonical["deterministicRulesetVersion"]).endswith(":" + binding_fingerprint(request)))
    )
    if not integrity:
        pending(
            "Son video kabulü için mevcut doğrulanmış görsel kapılar ve bağımsız revalidation gereklidir.",
            "FINAL_VIDEO_INTEGRITY",
        )
    family8 = project_family8(
        {
            "creativeQuality": {"creativeScore": None, "creativeGrade": None},
            "evidenceCompleteness": {"status": "COMPLETE" if not reasons else "INCOMPLETE"},
            "authorizationReasons": reasons,
        }
    )
    applicability = {
        key: {
            "status": "NOT_APPLICABLE",
            "reason": "Yeni profilin evrensel zorunluluğu değildir.",
            "profileVersion": VERSION,
        }
        for key in (
            "COMEDY",
            "THREE_ATTEMPTS",
            "FAKE_RESOLUTION",
            "RESOLVED_ENDING",
            "FRAME_ZERO_FULL_CAUSALITY",
            "INCREASING_PHYSICAL_INTENSITY",
            "BIGGEST_FINAL_EVENT",
            "SEAMLESS_LOOP",
            "FLAWLESS_ANIMATION",
            "UNIVERSAL_15_SECONDS",
            "ONE_CHARACTER_ONE_OBJECT",
        )
    }
    if routing["contentProfile"] == "ABSURD_PHYSICS":
        applicability["ONE_CHARACTER_ONE_OBJECT"]["status"] = "PREFERRED_TEMPLATE"
    if execution_risk["findings"] and quality["recommendation"] == "PROCEED_NEXT_EVIDENCE_STEP":
        quality["recommendation"] = "MINIMAL_PROMPT_REPAIR"
    return {
        "decisionPolicyVersion": DECISION_POLICY_VERSION,
        "planQuality": quality,
        "executionRisk": execution_risk,
        "intentRequirements": intent,
        "actualRenderQuality": {"status": "UNKNOWN", "reason": "Actual video evidence required"},
        "audienceOutcome": {"status": "NOT_JOINED"},
        "reviewDimensions": {
            "promptPlanQuality": quality,
            "generatorExecutionRisk": execution_risk,
            "actualRenderQuality": {"status": "UNKNOWN"},
            "audienceDistributionOutcome": {"status": "NOT_JOINED"},
        },
        "operatorReport": operator_report(quality, execution_risk),
        "workflowVersion": VERSION,
        "bindingHash": sha256(
            binding_fingerprint(request) + json.dumps(generation.get("capabilityProvenance"), sort_keys=True)
        ),
        "authorizationEvidence": canonical,
        "source": evidence["source"],
        "productionEvidence": evidence,
        "generalProducibility": evidence["generalProducibility"],
        "routing": routing,
        "applicability": applicability,
        "engagement": engagement_review(request, evidence),
        "generation": generation,
        "opening": opening_review(request, evidence, routing),
        "executionReview": execution,
        "family8": family8,
        "originalPrompt": request["prompt"],
        "finalPrompt": request["prompt"],
        "patch": [],
        "changedSettings": {},
        "repairPasses": 0,
        "verificationPasses": 0,
        "protectedIntent": request.get("protectedIntent") or [],
        "retrievedLessons": request.get("retrievedLessons", []),
        "manualHandoff": {
            "allowed": True,
            "authorization": family8["renderAuthorization"],
            "notice": "İnceleme paketi dışa aktarımı render yetkisi veya kredi harcama onayı değildir.",
        },
    }
