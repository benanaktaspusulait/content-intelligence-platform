"""Actual-render observations and audience data never enter prompt validation."""

from __future__ import annotations

import math
from typing import Any


def review_render(plan: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    import re

    from app.assessment.family8_projection import project_family8

    from .review import DECISION_POLICY_VERSION, operator_report

    if not plan.get("bindingHash") or plan.get("bindingHash") != observation.get("bindingHash"):
        raise ValueError("stale or mismatched final-plan binding")
    coverage = observation.get("coverage") or []
    asset = observation.get("assetHash")
    asset_known = bool(re.fullmatch(r"[a-f0-9]{64}", str(asset or "")))
    duration = observation.get("duration")

    def grounded(item: dict[str, Any], motion: bool = True) -> bool:
        start, end = item.get("start"), item.get("end")
        return bool(
            asset_known
            and isinstance(start, (int, float))
            and not isinstance(start, bool)
            and isinstance(end, (int, float))
            and not isinstance(end, bool)
            and math.isfinite(start)
            and math.isfinite(end)
            and 0 <= start <= end
            and (start < end or not motion)
            and (duration is None or end <= duration)
            and len(coverage) == 2
            and all(isinstance(v, (int, float)) and math.isfinite(v) for v in coverage)
            and coverage[0] <= start
            and coverage[1] >= end
            and item.get("reference")
            and item.get("observed")
            and item.get("confidence") in {"HIGH", "MEDIUM"}
            and (
                item.get("evidenceBasis") in {"HUMAN_REVIEWED_CLIP", "DENSE_LOCAL_CLIP", "VERIFIED_VLM_CLIP"}
                or not motion
                and item.get("evidenceBasis") in {"SAMPLED_STILLS", "DENSE_LOCAL_FRAMES"}
            )
        )

    def raw(item: dict[str, Any]) -> dict[str, Any]:
        # Blind review has an allowlist: reach/views/history labels never enter stored review facts.
        return {
            k: item.get(k)
            for k in (
                "type",
                "start",
                "end",
                "evidenceBasis",
                "reference",
                "observed",
                "inferred",
                "uncertainty",
                "confidence",
                "durationSeconds",
                "recurrence",
                "affectedEntity",
                "eventId",
                "requirementId",
                "rawSeverity",
                "state",
                "requiresMotion",
                "impact",
                "value",
            )
        }

    reasons, findings, events = [], [], []
    essentials = {
        i["id"]: i
        for i in plan.get("intentRequirements", [])
        if i.get("level") == "ESSENTIAL" and i.get("status", "SOURCE_SUPPORTED") == "SOURCE_SUPPORTED"
    }

    def finding(item: dict[str, Any], impact: str, sufficient: bool, essential: bool = False) -> None:
        severe = (
            impact
            in {
                "CORE_EVENT_LOST",
                "IDENTITY_LOST",
                "SAFETY_FAILURE",
                "FACTUAL_FAILURE",
                "COHERENCE_DESTROYED",
            }
            or impact == "ESSENTIAL_CONSTRAINT_VIOLATED"
            and essential
        )
        severity = (
            "BLOCKING"
            if sufficient and severe
            else "WARNING"
            if sufficient and impact == "LOCAL_TOLERABLE"
            else "UNKNOWN"
        )
        findings.append(
            {
                **raw(item),
                "rawResult": raw(item),
                "applicability": "APPLICABLE",
                "severity": severity,
                "viewerImpact": impact if sufficient else "UNKNOWN",
                "essentialRequirementAffected": essential,
                "reason": item.get("observed") or "Gözlem eksik",
                "repairLevel": "MATERIAL_REPAIR_REVIEW"
                if severity == "BLOCKING"
                else "KEEP_OR_EDIT"
                if severity == "WARNING"
                else "MORE_EVIDENCE",
                "action": (
                    "Temel olayı koruyarak önce mevcut segment/kurgu olanağını kontrol et; "
                    "otomatik rerender yok."
                ),
            }
        )
        if severity != "WARNING":
            reasons.append(
                {
                    "code": "CREATIVE_BLOCKER" if severity == "BLOCKING" else "REQUIRED_EVIDENCE_MISSING",
                    "source": "POST_FAMILY_RENDER_IMPACT",
                    "message": impact if sufficient else "Actual interval evidence insufficient",
                    "references": [str(item.get("reference") or "UNKNOWN")],
                }
            )

    for defect in observation.get("defects") or []:
        if not isinstance(defect, dict):
            continue
        finding(
            defect,
            str(defect.get("impact") or "UNKNOWN"),
            grounded(defect, defect.get("requiresMotion", True)),
            defect.get("requirementId") in essentials,
        )
    for event in plan.get("events") or []:
        observed: dict[str, Any] = next(
            (i for i in observation.get("events", []) if i.get("id") == event["id"]), {}
        )
        sufficient = grounded(observed, event.get("requiresMotion", True) or event.get("requiresLoop", False))
        # Planned timestamps are expectations, not proof of actual event location.
        # A positive clip observation may place a readable event earlier/later.
        if observed.get("state") == "ABSENT" and event.get("intentLevel") == "ESSENTIAL":
            sufficient = (
                sufficient
                and duration is not None
                and observed.get("start") == 0
                and observed.get("end", -1) >= duration
            )
        state = (
            observed.get("state")
            if sufficient and observed.get("state") in {"PRESENT", "ABSENT"}
            else "UNKNOWN"
        )
        level = event.get("intentLevel", "UNCLASSIFIED")
        events.append(
            {
                "eventId": event["id"],
                "status": state,
                "intentLevel": level,
                "start": event["start"],
                "end": event["end"],
                "evidenceBasis": observed.get("evidenceBasis"),
                "reference": observed.get("reference"),
                "observed": observed.get("observed"),
                "inferred": observed.get("inferred"),
                "uncertainty": observed.get("uncertainty"),
                "observedStart": observed.get("start"),
                "observedEnd": observed.get("end"),
            }
        )
        if state == "ABSENT":
            missing = {
                **observed,
                "eventId": event["id"],
                "type": "PLAN_DEVIATION",
                "start": event["start"],
                "end": event["end"],
            }
            finding(
                missing,
                "CORE_EVENT_LOST"
                if level == "ESSENTIAL"
                else "LOCAL_TOLERABLE"
                if level in {"FLEXIBLE", "POLISH"}
                else "UNKNOWN",
                sufficient,
                level == "ESSENTIAL",
            )
    experience = {}
    values = {
        "coreEventReadability": {"ADEQUATE", "UNREADABLE"},
        "identity": {"RECOGNIZABLE", "UNRECOGNIZABLE"},
        "safety": {"APPROPRIATE", "UNSAFE"},
        "coherence": {"ADEQUATE", "DESTROYED"},
        "progression": {"DEVELOPING", "PURPOSEFUL_REPETITION", "WEAK"},
        "opening": {"READABLE_EARLY_DEVELOPMENT", "READABLE_PROMISE", "UNREADABLE", "EXCESSIVELY_DELAYED"},
        "ending": {"DELIVERS_PROMISE", "PURPOSEFUL_UNRESOLVED", "ARBITRARY_TRUNCATION", "WEAK"},
        "openingFrame": {"READABLE", "UNREADABLE"},
    }
    failures = {
        "UNREADABLE": "CORE_EVENT_LOST",
        "UNRECOGNIZABLE": "IDENTITY_LOST",
        "UNSAFE": "SAFETY_FAILURE",
        "DESTROYED": "COHERENCE_DESTROYED",
    }
    for key, allowed in values.items():
        item = (observation.get("experience") or {}).get(key) or {}
        valid = (
            grounded(item, item.get("requiresMotion", True) if key in {"identity", "openingFrame"} else True)
            and item.get("value") in allowed
        )
        if key in {"safety", "coherence", "progression"} and duration is not None:
            valid = valid and item.get("start", 1) == 0 and item.get("end", -1) >= duration
        experience[key] = {
            **raw(item),
            "value": item.get("value") if valid else "UNKNOWN",
            "status": "OBSERVED" if valid else "UNKNOWN",
        }
        if valid and key != "openingFrame" and item["value"] in failures:
            finding({**item, "type": key}, failures[item["value"]], True, True)
    planned_duration = max((i["end"] for i in events), default=0)
    timing_deviation = bool(
        asset_known
        and isinstance(duration, (int, float))
        and math.isfinite(duration)
        and planned_duration > 0
        and abs(duration - planned_duration) > 0.1
    )
    fidelity = (
        "PARTIAL"
        if timing_deviation or any(i["status"] == "ABSENT" for i in events)
        else "HIGH"
        if events and all(i["status"] == "PRESENT" for i in events)
        else "UNKNOWN"
    )
    required = ("coreEventReadability", "identity", "safety", "coherence", "progression")
    # Unclassified missing events cannot be retroactively declared harmless.
    unknown = (
        not asset_known
        or not events
        or any(i["status"] == "UNKNOWN" for i in events)
        or any(experience[k]["value"] == "UNKNOWN" for k in required)
        or any(i["severity"] == "UNKNOWN" for i in findings)
    )
    blocked = any(i["severity"] == "BLOCKING" for i in findings)
    weak = (
        experience["progression"]["value"] == "WEAK"
        or experience["ending"]["value"] in {"WEAK", "ARBITRARY_TRUNCATION"}
        or experience["opening"]["value"] == "EXCESSIVELY_DELAYED"
    )
    usability = (
        "UNUSABLE"
        if blocked
        else "UNKNOWN"
        if unknown
        else "READABLE_BUT_CREATIVELY_WEAK"
        if weak
        else "USABLE"
    )
    recommendation = (
        "UNUSABLE_CONFIRMED_BLOCKER"
        if blocked
        else "INSUFFICIENT_EVIDENCE"
        if unknown
        else "EDIT_RECOMMENDED"
        if weak
        else "TEST_CANDIDATE"
    )
    proposal = observation.get("repairProposal") or {}
    justified = (
        blocked
        and grounded(proposal)
        and proposal.get("request") == "FULL_RERENDER"
        and proposal.get("requirementId") in essentials
        and all(
            isinstance(proposal.get(k), str) and proposal[k].strip()
            for k in (
                "expectedEssentialBenefit",
                "defectAddressed",
                "whySmallerInsufficient",
                "remainingUncertainty",
            )
        )
    )
    repair_economics = {
        "order": [
            "KEEP_USABLE",
            "EDIT_TRIM",
            "INTERVAL_PROMPT_REPAIR",
            "SUPPORTED_NECESSARY_SEGMENT",
            "JUSTIFIED_FULL_RERENDER",
        ],
        "fullRerenderJustified": bool(justified),
        "automaticExecution": False,
        "essentialBenefit": proposal.get("expectedEssentialBenefit") if justified else None,
        "defectAddressed": proposal.get("defectAddressed") if justified else None,
        "whySmallerInsufficient": proposal.get("whySmallerInsufficient") if justified else None,
        "remainingUncertainty": proposal.get("remainingUncertainty")
        if justified
        else "No verified repair execution outcome",
        "successProbability": None,
    }
    if justified:
        recommendation = "RERENDER_MATERIALLY_JUSTIFIED"
    if unknown:
        reasons.append(
            {
                "code": "REQUIRED_EVIDENCE_MISSING",
                "source": "ACTUAL_VIEWING_EXPERIENCE",
                "message": "Actual-video/source-supported experience incomplete",
                "references": [],
            }
        )
    family8 = project_family8(
        {
            "creativeQuality": {"creativeScore": None, "creativeGrade": None},
            "evidenceCompleteness": {"status": "INCOMPLETE" if unknown else "COMPLETE"},
            "authorizationReasons": reasons,
        }
    )
    actual = {
        "status": "FAIL" if blocked else "UNKNOWN" if unknown else "REPAIR" if weak else "PASS",
        "planFidelity": fidelity,
        "viewerFacingUsability": usability,
        "editorialRecommendation": recommendation,
        "findings": findings,
        "experience": experience,
        "repairEconomics": repair_economics,
        "smallestIntervention": "Gerekli temel olayı koruyan en küçük kurgu/segment müdahalesini değerlendir"
        if blocked or weak
        else "Kanıt aralığını tamamla"
        if unknown
        else "Mevcut kullanılabilir çıktıyı koru; kontrollü test için editoryal aday",
    }
    return {
        **actual,
        "stage": "ACTUAL_RENDER_QA",
        "decisionPolicyVersion": DECISION_POLICY_VERSION,
        "bindingHash": plan["bindingHash"],
        "assetHash": asset,
        "events": events,
        "family8": family8,
        "fidelityEvidence": {
            "plannedDuration": planned_duration or None,
            "actualDuration": duration,
            "timingAlignment": "DEVIATES"
            if timing_deviation
            else "UNKNOWN"
            if not asset_known
            else "ALIGNED",
            "reason": "Duration mismatch proves timing deviation, not loss of core event",
            "eventCoverage": events,
        },
        "authorizationScope": "EDITORIAL_ASSESSMENT_ONLY",
        "publicationAuthorized": False,
        "automaticRerender": False,
        "renderAuthorizationUnchanged": True,
        "actualFirstFrame": {**experience.get("openingFrame", {}), "canonicalAuthorizationGate": False},
        "actualOpeningVideo": {"status": experience["opening"]["value"], "evidence": experience["opening"]},
        "audioReview": {
            "mode": "SOUND_OFF",
            "status": "UNKNOWN",
            "reason": "No verified actual audio/transcript evidence supplied",
        },
        "technicalAnalysis": observation.get("technicalAnalysis"),
        "reviewDimensions": {
            "promptPlanQuality": plan.get("planQuality", {"status": "UNKNOWN"}),
            "generatorExecutionRisk": plan.get("executionRisk", {"status": "UNKNOWN"}),
            "actualRenderQuality": actual,
            "audienceDistributionOutcome": {"status": "NOT_JOINED"},
        },
        "operatorReport": operator_report(plan.get("planQuality", {}), plan.get("executionRisk", {}), actual),
        "limitations": [
            "Seyrek kareler sürekli hareket, hassas temas veya kusursuz loop kanıtı değildir.",
            (
                "TEST_CANDIDATE yayın veya üretim izni değildir; "
                "kanonik operasyon kontrolleri ayrıca gereklidir."
            ),
        ],
    }


def match_publication(
    platform: str, publication_id: str, associations: list[dict[str, Any]]
) -> dict[str, Any]:
    if not isinstance(publication_id, str) or not publication_id.strip():
        raise ValueError("Platform identifier must be a non-empty lossless string")
    matches = [
        r
        for r in associations
        if r.get("platform") == platform and r.get("platformContentId") == publication_id
    ]
    identities = {r.get("videoId") for r in matches}
    return {
        "platform": platform,
        "platformContentId": publication_id,
        "status": "MATCHED" if len(identities) == 1 else "AMBIGUOUS" if identities else "UNMATCHED",
        "videoId": next(iter(identities)) if len(identities) == 1 else None,
        "candidates": matches,
        "method": "EXACT_STORED_PLATFORM_ID",
    }


def numeric(value: Any) -> float | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        return None
    return float(value)


def measure_observation(raw: dict[str, Any], near_organic_threshold: float = 0.05) -> dict[str, Any]:
    if not 0 <= near_organic_threshold <= 1:
        raise ValueError("Invalid configurable cohort threshold")
    duration, watch = numeric(raw.get("durationSeconds")), numeric(raw.get("averageWatchSeconds"))
    reach, views, paid_reach = (
        numeric(raw.get("reach")),
        numeric(raw.get("views")),
        numeric(raw.get("paidReach")),
    )
    source = {
        "sourceHash": raw.get("sourceHash"),
        "sourceId": raw.get("sourceId"),
        "observedAt": raw.get("observedAt"),
        "window": raw.get("window", "UNKNOWN"),
        "publicationAgeSeconds": raw.get("publicationAgeSeconds"),
    }

    def metric(value: Any, definition: str, unit: str, denominator: str | None = None) -> dict[str, Any]:
        return {
            "value": value,
            "definition": definition,
            "unit": unit,
            "denominator": denominator,
            "window": source["window"],
            "provenance": source,
        }

    ratio = watch / duration if watch is not None and duration is not None and duration > 0 else None
    paid_share = paid_reach / reach if paid_reach is not None and reach and paid_reach <= reach else None
    shares = numeric(raw.get("shares"))
    share_rate = shares / reach if shares is not None and reach else None
    return {
        "source": source,
        "raw": raw,
        "durationSeconds": duration,
        "horizon": source["window"],
        "fixedHorizonSnapshot": source if source["window"] in {"1H", "3H", "24H", "72H"} else None,
        "audience": {
            "averageWatchSeconds": metric(watch, "Platform reported average watch duration", "seconds"),
            "averageWatchDurationRatio": metric(
                ratio,
                "Average watch duration / actual video duration; replay proxy only",
                "ratio",
                "durationSeconds",
            ),
            "initialSwipeAwayRate": metric(
                None, "Not derivable from three-second unique viewers / Reach", "ratio"
            ),
            "shareRatePerReach": metric(share_rate, "Shares / Reach", "ratio", "reach"),
            "retentionCurve": metric(
                raw.get("retentionCurve"),
                raw.get("retentionDefinition") or "Platform-defined retention; denominator unverified",
                "platform_defined",
                raw.get("retentionDenominator"),
            ),
            "intentionalReplayRate": metric(
                None, "Intentional replay is not established by average watch duration", "ratio"
            ),
        },
        "distribution": {
            "paidReachShare": metric(paid_share, "Paid Reach / total Reach", "ratio", "reach"),
            "paidWatchTimeShare": metric(
                numeric(raw.get("paidWatchTimeShare")),
                "Paid watch time / total watch time; not paid Reach share",
                "ratio",
                "totalWatchTime",
            ),
            "recommendationShare": metric(
                numeric(raw.get("recommendationShare")),
                "Reported recommendation source share",
                "ratio",
                raw.get("recommendationDenominator"),
            ),
            "cohort": "UNKNOWN"
            if paid_share is None
            else "NEAR_ORGANIC"
            if paid_share <= near_organic_threshold
            else "PAID",
            "nearOrganicDefinition": {"maxPaidReachShare": near_organic_threshold},
        },
        "outcome": {
            "reach": metric(reach, "Platform reported Reach", "accounts"),
            "views": metric(views, "Platform reported plays/views", "plays"),
            "totalWatchTime": metric(
                numeric(raw.get("totalWatchSeconds")), "Platform reported total watch time", "seconds"
            ),
        },
        "limitations": [
            "Lifetime değerlerden geçmiş 1h/3h/24h/72h snapshot türetilmedi.",
            "Audience response, distribution ve sonuç ayrı tutulur; korelasyon nedensellik değildir.",
        ],
    }


def compare_cohort(
    records: list[dict[str, Any]], horizon: str, near_organic_threshold: float = 0.05
) -> dict[str, Any]:
    eligible = [
        record
        for record in records
        if horizon in {"1H", "3H", "24H", "72H"} and record.get("window") == horizon
    ]
    metrics = [measure_observation(record, near_organic_threshold) for record in eligible]
    return {
        "horizon": horizon,
        "included": len(eligible),
        "excluded": len(records) - len(eligible),
        "groups": {
            name: [m for m in metrics if m["distribution"]["cohort"] == name]
            for name in ("PAID", "NEAR_ORGANIC", "UNKNOWN")
        },
        "causalConclusion": None,
        "notice": "Yalnızca aynı gerçek observation window karşılaştırılır; süre ayrıca korunur.",
    }
