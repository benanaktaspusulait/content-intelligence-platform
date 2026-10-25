"""Fixed stored experiment replay through two independent evidence sources."""

import json
from collections import Counter
from statistics import mean, median
from typing import Literal

from pydantic import BaseModel, ConfigDict

from . import concept_ranking as ranking
from . import semantic_concept_generation as generation
from . import shape_generation as shape_generation
from .semantic_evidence_adapter import project_candidate
from .semantic_evidence_replay import human_review_reasons, read_experiment
from .semantic_live_experiment import StoredResponseGenerator
from .short_concept_generation import ranking_input
from .short_form_evidence import StructuredCanonicalInput


class StructuredReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    experimentId: Literal["semantic-live-v1-seed-42-count-40"] = "semantic-live-v1-seed-42-count-40"
    shortFormEvidenceSourceVersion: Literal["timed-text-v1", "structured-canonical-v1"] = "timed-text-v1"
    dualEvidenceAudit: bool = False
    allowExternalGeneration: Literal[False] = False


def structured_input(raw, candidate):
    c = project_candidate(raw, candidate)
    return StructuredCanonicalInput(
        projection=c["canonicalCreativeEvidence"],
        semanticFields=c["normalizedSemanticFields"],
        protagonist=c["protagonist"],
        timing=[
            dict(startSeconds=b["startSeconds"], endSeconds=b["endSeconds"], description=b["description"])
            for b in c["beats"]
        ],
    ).model_dump()


def contexts(raw, candidate):
    return dict(
        shortFormEvidenceSourceVersion="structured-canonical-v1",
        structuredCanonicalInput=structured_input(raw, candidate),
    )


def recognition(report, projection, legacy_trigger=None):
    if report.get("canonicalEvidence"):
        d = report["canonicalEvidence"]["dimensions"]
        return dict(
            goalDeclared=d["goal"]["declared"],
            openingVisibleGoal=d["goal"]["openingVisible"],
            openingAnomaly=d["opening"]["anomalySupported"],
            coreRulePresent=d["coreRule"]["presence"] != "MISSING",
            ruleSupported=d["coreRule"]["supported"],
            triggerPresent=d["trigger"]["presence"] != "MISSING",
            causalBeats=report["majorCausalBeatCount"],
            describedBeats=report["describedBlockCount"],
            payoffPresent=d["payoff"]["presence"] != "MISSING",
            payoffRuleLinked=d["payoff"]["ruleLinked"],
            loopSupported=d["loop"]["supported"] and report["rewatchType"] == "INTENTIONAL_REWATCH",
        )
    return dict(
        goalDeclared=report["goalScore"] > 0,
        openingVisibleGoal=bool(report["beats"] and report["beats"][0]["goal"]),
        openingAnomaly=bool(report["beats"] and report["beats"][0]["rules"]),
        coreRulePresent=bool(report["rules"]),
        ruleSupported=bool(report["rules"]),
        triggerPresent=(legacy_trigger not in ("UNSPECIFIED", "UNKNOWN", None))
        if legacy_trigger is not None
        else projection["fields"]["triggerEvidence"]["classification"] != "UNCLASSIFIED_TRIGGER",
        causalBeats=report["majorCausalBeatCount"],
        describedBeats=report["describedBlockCount"],
        payoffPresent=report["payoffScore"] >= 70,
        payoffRuleLinked=report["payoffScore"] >= 70,
        loopSupported=report["rewatchType"] == "INTENTIONAL_REWATCH",
    )


def dual_audit(legacy, structured, projection, legacy_trigger=None):
    a = recognition(legacy, projection, legacy_trigger)
    b = recognition(structured, projection)
    old = {f["code"] for f in legacy["findings"]}
    new = {f["code"] for f in structured["findings"]}
    return dict(
        mode="DUAL_EVIDENCE_AUDIT",
        evidenceDifferences={k: dict(timedText=a[k], structured=b[k]) for k in a if a[k] != b[k]},
        scoreDifference=structured["shortFormScore"] - legacy["shortFormScore"],
        findingsAdded=sorted(new - old),
        findingsRemoved=sorted(old - new),
        scoresCombined=False,
    )


def change_reason(legacy, structured):
    names = (
        "hookScore",
        "goalScore",
        "ruleClarityScore",
        "beatDensityScore",
        "progressDensityScore",
        "escalationScore",
        "payoffScore",
        "silentLegibilityScore",
    )
    changes = [
        f"{key}: {legacy[key]} -> {structured[key]}" for key in names if legacy[key] != structured[key]
    ]
    return (
        ("Evidence acquisition changed: " + "; ".join(changes))
        if changes
        else "Recognized scoring dimensions unchanged; same evaluator and thresholds."
    )


def stats(rows, key):
    reports = [r[key] for r in rows]
    scores = [r["shortFormScore"] for r in reports]
    return dict(
        count=len(scores),
        min=min(scores),
        max=max(scores),
        mean=mean(scores),
        median=median(scores),
        statuses=dict(Counter(r["status"] for r in reports)),
        scores=dict(sorted(Counter(scores).items())),
    )


def selected_run(candidates, rows, config, evidence_by_id=None):
    # Reuse accepted full-stack quality/diversity/production logic, without generation.
    ready = []
    suppressed = []
    for c in candidates:
        if c["premiseNaturalness"]["instantCausalLegibility"] < 60:
            suppressed.append(
                dict(
                    candidate=c,
                    suppressionReasons=[
                        "OPENING_EVIDENCE_INSUFFICIENT",
                        *shape_generation.quality_reasons(c, rows[c["candidateId"]], config),
                    ],
                )
            )
        else:
            ready.append(c)
    selected, other, decisions = shape_generation.curate(ready, rows, config)
    suppressed.extend(other)
    ranked = (
        ranking.rank_concepts([ranking_input(c) for c in selected], short_form_evidence_by_id=evidence_by_id)
        if selected
        else None
    )
    selection = (
        shape_generation.production_selection(
            ranked["rankedEligibleCandidates"],
            selected,
            config.minimumStoryShapeDistance,
            config.minimumShapeShortFormScore,
            config.minimumShapeRankingScore,
        )
        if ranked
        else dict(productionSlate=[], firstRenderCandidate=None)
    )
    return dict(
        canonicalRanking=ranked,
        productionSelection=selection,
        selectionDecisions=decisions,
        suppressed=[
            dict(candidateId=s["candidate"]["candidateId"], reasons=s["suppressionReasons"])
            for s in suppressed
        ],
    )


def analyze(data, request):
    cfg = data["config"]
    if cfg.generatorMode != "semantic":
        raise ValueError("Stored semantic response only")
    before = generation.generate_and_rank(cfg, StoredResponseGenerator(data["raw"], data["prompt"]))
    if before != data["stored"]["storedResponseValidation"]:
        raise ValueError("Legacy replay drift against immutable stored evidence")
    raw = {i["ideaId"]: i for i in json.loads(data["raw"])["ideas"] if isinstance(i, dict)}
    candidates = []
    rows = []
    legacy_rows = {}
    structured_rows = {}
    evidence_map = {}
    review_before = []
    review_after = []
    for attempt in before["attempts"]:
        c = attempt["candidate"]
        id = c["candidateId"]
        idea = raw[c["providerData"]["ideaId"]]
        projected = project_candidate(idea, c)
        projection = projected["canonicalCreativeEvidence"]
        context = contexts(idea, c)
        evidence_map[id] = context
        after = ranking.validate_concept(ranking_input(c), short_form_evidence=context)
        old = attempt["validation"]
        a = old["shortFormEngine"]
        b = after["shortFormEngine"]
        legacy_rows[id] = old
        structured_rows[id] = after
        candidates.append(c)
        before_reasons = human_review_reasons({**attempt, "candidate": projected}, projection)
        changed_attempt = {**attempt, "candidate": projected, "validation": after}
        after_reasons = human_review_reasons(changed_attempt, projection)
        if before_reasons:
            review_before.append(id)
        if after_reasons:
            review_after.append(id)
        facts = b["canonicalEvidence"]["dimensions"]
        failures = []
        remaining = []
        codes = {f["code"] for f in b["findings"] if f["severity"] == "REVISION_REQUIRED"}
        if not facts["coreRule"]["supported"]:
            remaining.append("RULE_SUPPORT_NOT_ESTABLISHED_BY_STRUCTURAL_LINKAGE_CHECKS")
        if not facts["goal"]["openingVisible"]:
            remaining.append("OPENING_GOAL_RELATION_UNRESOLVED_BY_TOKEN_OVERLAP")
        if b["shortFormScore"] < 60 and not remaining:
            failures = sorted(codes)
        deltas = b["shortFormScore"] - a["shortFormScore"]
        rows.append(
            dict(
                ideaId=idea["ideaId"],
                candidateId=id,
                title=c["title"],
                goal=idea["everydayGoal"],
                rule=idea["impossibleRule"],
                payoff=idea["finalPayoff"],
                rawProviderIdea=idea,
                projection=projection,
                legacy=a,
                structured=b,
                legacyRecognition=recognition(a, projection, c["composition"]["trigger"]),
                structuredRecognition=recognition(b, projection),
                delta=deltas,
                dualAudit=dual_audit(a, b, projection, c["composition"]["trigger"])
                if request.dualEvidenceAudit
                else None,
                legacyValidation=old,
                structuredValidation=after,
                primaryReason=change_reason(a, b),
                canonicalStatusTransition=f"{a['status']} -> {b['status']}",
                humanReviewBefore=before_reasons,
                humanReviewAfter=after_reasons,
                completeDeclaredEvidence=all(
                    f["presence"] == "PRESENT" for f in projection["fields"].values()
                ),
                likelyContentFailureFindings=failures,
                remainingEvidenceSourceFailures=remaining,
                rankingBoundaryReasons=[
                    r for r in after["eligibilityReasons"] if r["source"] != "SHORT_FORM_ENGINE"
                ],
            )
        )
    old_selection = selected_run(candidates, legacy_rows, cfg)
    new_selection = selected_run(candidates, structured_rows, cfg, evidence_map)
    old_ids = {s["candidateId"] for s in old_selection["productionSelection"]["productionSlate"]}
    new_ids = {s["candidateId"] for s in new_selection["productionSelection"]["productionSlate"]}
    recognition_counts = {
        source: {k: sum(r[source + "Recognition"][k] for r in rows) for k in rows[0][source + "Recognition"]}
        for source in ("legacy", "structured")
    }
    taxonomy = {}
    for name, field in [("engine", "coreRule"), ("trigger", "trigger"), ("payoff", "payoff")]:
        taxonomy[name] = dict(
            Counter(r["structured"]["canonicalEvidence"]["dimensions"][field]["presence"] for r in rows)
        )
    return dict(
        workflow="STRUCTURED_SFE_OFFLINE_REPLAY",
        shortFormEvidenceSourceVersion=request.shortFormEvidenceSourceVersion,
        dualEvidenceAudit=request.dualEvidenceAudit,
        baselineExact=True,
        legacy=stats(rows, "legacy"),
        structured=stats(rows, "structured"),
        recognitionCounts=recognition_counts,
        taxonomyCoverage=taxonomy,
        legacyTaxonomyCoverage=dict(
            engine=dict(
                CLASSIFIED=sum(bool(r["legacy"]["rules"]) for r in rows),
                NOT_DETECTED=sum(not r["legacy"]["rules"] for r in rows),
            ),
            payoff=dict(
                CLASSIFIED=sum(r["legacy"]["payoffScore"] >= 70 for r in rows),
                NOT_DETECTED=sum(r["legacy"]["payoffScore"] < 70 for r in rows),
            ),
        ),
        recognitionMetricNotes=(
            "Legacy trigger recognition is the existing normalized composition trigger (13/33); "
            "SFE timed text had no independent trigger report. Structured trigger presence is "
            "explicit-field evidence, with classification reported separately."
        ),
        scoreDeltaDistribution=dict(sorted(Counter(r["delta"] for r in rows).items())),
        candidates=rows,
        increaseAtLeast10=[r["ideaId"] for r in rows if r["delta"] >= 10],
        increaseAtLeast20=[r["ideaId"] for r in rows if r["delta"] >= 20],
        materialChanges=[r["ideaId"] for r in rows if abs(r["delta"]) >= 10],
        statusTransitions=[
            dict(ideaId=r["ideaId"], transition=r["canonicalStatusTransition"])
            for r in rows
            if r["legacy"]["status"] != r["structured"]["status"]
        ],
        newlyEligible=[
            r["ideaId"]
            for r in rows
            if r["legacyValidation"]["eligibility"] != "ELIGIBLE"
            and r["structuredValidation"]["eligibility"] == "ELIGIBLE"
        ],
        newProductionCandidates=sorted(new_ids - old_ids),
        legacySelection=old_selection,
        structuredSelection=new_selection,
        HUMAN_REVIEW_SET=[
            dict(
                ideaId=r["ideaId"],
                candidateId=r["candidateId"],
                title=r["title"],
                reasons=r["humanReviewAfter"],
            )
            for r in rows
            if r["humanReviewAfter"]
        ],
        humanReviewEntering=[
            r["ideaId"] for r in rows if r["candidateId"] in set(review_after) - set(review_before)
        ],
        humanReviewLeaving=[
            r["ideaId"] for r in rows if r["candidateId"] in set(review_before) - set(review_after)
        ],
        stillBelow60CompleteDeclaredEvidence=[
            r["ideaId"]
            for r in rows
            if r["completeDeclaredEvidence"] and r["structured"]["shortFormScore"] < 60
        ],
        presentUnclassifiedEngines=[
            r["ideaId"]
            for r in rows
            if r["structured"]["canonicalEvidence"]["dimensions"]["coreRule"]["presence"]
            == "PRESENT_UNCLASSIFIED"
        ],
        presentUnclassifiedPayoffs=[
            r["ideaId"]
            for r in rows
            if r["structured"]["canonicalEvidence"]["dimensions"]["payoff"]["presence"]
            == "PRESENT_UNCLASSIFIED"
        ],
        likelyContentFailures=[r["ideaId"] for r in rows if r["likelyContentFailureFindings"]],
        remainingEvidenceSourceFailures=[r["ideaId"] for r in rows if r["remainingEvidenceSourceFailures"]],
        providerCalls=0,
        externalProviderCalls=0,
        newConceptsGenerated=0,
        renders=0,
        scoresBlended=False,
        limitations=[
            (
                "Scoring weights/thresholds/findings are unchanged; acquisition verification is a"
                " versioned deterministic heuristic, not semantic truth."
            ),
            (
                "Declared presence is not automatic visible goal, coherent rule, causal beat, "
                "strong payoff or intentional loop."
            ),
            (
                "Remaining ranking goal/rule consistency checks and downstream "
                "naturalness/BG/shape gates retain their accepted behavior."
            ),
            (
                "Unknown source support must not be reported as proof an idea is bad. Human "
                "creative review remains final."
            ),
        ],
    )


def replay_experiment(request):
    request = StructuredReplayRequest.model_validate(request)
    return analyze(read_experiment(), request)
