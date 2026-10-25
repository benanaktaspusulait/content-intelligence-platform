"""Offline stored-response evidence replay; no live transport or generation path."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from statistics import mean, median
from typing import Literal

from pydantic import BaseModel, ConfigDict

from . import concept_ranking as ranking
from . import semantic_concept_generation as generation
from . import short_form_engine as short
from . import semantic_live_diagnostics as prior_diagnostics
from .concept_fingerprint import digest
from .semantic_evidence_adapter import FIELD_MAP, VERSION, project_candidate
from .semantic_live_experiment import StoredResponseGenerator

EXPERIMENT_ID = "semantic-live-v1-seed-42-count-40"
ROOT = Path(__file__).resolve().parents[3]


class EvidenceReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    experimentId: Literal["semantic-live-v1-seed-42-count-40"] = EXPERIMENT_ID
    semanticEvidenceAdapterVersion: Literal["v1"] | None = None
    allowExternalGeneration: Literal[False] = False


class EvidenceReplayGenerator(StoredResponseGenerator):
    def generate(self, config, cast):
        candidates = super().generate(config, cast)
        raw = {i["ideaId"]: i for i in json.loads(self.raw)["ideas"] if isinstance(i, dict)}
        values = [project_candidate(raw[c["providerData"]["ideaId"]], c) for c in candidates]
        self.evidence["semanticEvidenceAdapterVersion"] = VERSION
        return values


def read_experiment():
    """Fixed repository evidence only; no arbitrary API filesystem access."""
    path = ROOT / "docs" / EXPERIMENT_ID / "live-attempt"
    return dict(
        raw=(path / "response.txt").read_text(),
        config=generation.GenerationRequest.model_validate(
            json.loads((path / "configuration.json").read_text())["generation"]
        ),
        prompt=json.loads((path / "prompt.json").read_text()),
        stored=json.loads((path / "analysis.json").read_text()),
    )


def recognized(record):
    c, v = record["candidate"], record["validation"]
    s = v["shortFormEngine"]
    return dict(
        goal=s["goalScore"] >= 60,
        frameZero=s["alreadyInTrouble"],
        coreRule=bool(s["rules"]),
        trigger=c["composition"]["trigger"] != "UNSPECIFIED",
        causalBeats=s["majorCausalBeatCount"],
        describedBeats=s["describedBlockCount"],
        payoff=s["payoffScore"] >= 60,
        payoffClassification=c["storyShapeFingerprint"]["payoffFamily"] != "UNKNOWN",
        loop=s["rewatchType"] == "INTENTIONAL_REWATCH",
    )


def _legacy_value(c, path, index=None):
    if index is not None:
        if path == "strategy":
            return c.get("beats", [])[index]["description"]
        key = "objectResponse" if path == "visibleConsequence" else "characterConsequence"
        return c.get("structuredBeatPlan", [])[index].get(key, "")
    direct = dict(everydayGoal="everydayGoal", primaryObject="primaryObject", impossibleRule="impossibleRule")
    provider = dict(
        normalExpectation="normalExpectation",
        frameZeroDescription="rawFrameZeroDescription",
        finalPayoff="rawFinalPayoff",
        whyThisObject="whyThisObject",
    )
    if path in direct:
        return c.get(direct[path], "")
    if path in provider:
        return c.get("providerData", {}).get(provider[path], "")
    if path == "goalRuleRelationship":
        return c.get("goalRuleRelationship", "")
    if path == "visibleTrigger":
        return c.get("composition", {}).get("trigger", "")
    if path == "loopPotential":
        return c.get("loopPotential", {}).get("description", "")
    return ""


def field_loss(raw, before, after):
    """Do not call classification failure a disappearance of the source field."""
    c = before["candidate"]
    projected = after["candidate"]["canonicalCreativeEvidence"]
    normalized = after["candidate"]["normalizedSemanticFields"]
    rec = recognized(after)
    mapping = dict(
        everydayGoal="goal",
        primaryObject=None,
        normalExpectation=None,
        impossibleRule="coreRule",
        visibleTrigger="trigger",
        frameZeroDescription="frameZero",
        finalPayoff="payoff",
        loopPotential="loop",
        whyThisObject=None,
        goalRuleRelationship=None,
    )
    output = []

    def row(path, raw_text, normalized_text, evidence, old, supported):
        present = isinstance(raw_text, str) and bool(raw_text.strip())
        old_preserved = present and isinstance(old, str) and raw_text.strip() in old
        evidence_texts = [e["sourceText"] for e in evidence["evidence"]]
        projection_preserved = bool(normalized_text) and normalized_text in evidence_texts
        status = (
            "SOURCE_MISSING"
            if not present
            else "NORMALIZATION_LOSS"
            if normalized_text != raw_text.strip()
            else "PROJECTION_LOSS"
            if not projection_preserved
            else "AMBIGUOUS_SOURCE"
            if supported is None
            else "VALIDATOR_EXTRACTION_LOSS"
            if not supported
            else "PRESERVED"
        )
        output.append(
            dict(
                sourceField=path,
                rawText=raw_text,
                legacyNormalizedText=old,
                legacyNormalizationStatus="PRESERVED"
                if old_preserved
                else "NORMALIZATION_LOSS"
                if present
                else "SOURCE_MISSING",
                normalizedText=normalized_text,
                projectedEvidence=evidence,
                validatorRecognition="UNSUPPORTED_STRUCTURED_INTERFACE"
                if supported is None
                else "RECOGNIZED"
                if supported
                else "NOT_RECOGNIZED",
                status=status,
                recoveredFromStoredSource=present and not old_preserved,
                limitation=(
                    "Presence and classification/creative quality are separate. Unverified declared "
                    "loops/affordances are not established facts."
                ),
            )
        )

    for name, path in FIELD_MAP.items():
        key = mapping[path]
        support = rec[key] if key is not None else None
        # Rank normalization accepts object presence, but does not verify visual meaning.
        if path == "primaryObject":
            support = after["validation"]["normalizedConcept"]["objectOrPrimaryInteraction"] == raw.get(path)
        if path in ("normalExpectation", "whyThisObject"):
            support = after["premiseNaturalness"]["admitted"]
        if path == "loopPotential":
            support = True if rec["loop"] else None
        row(path, raw.get(path), normalized[path], projected["fields"][name], _legacy_value(c, path), support)
    sfe_beats = after["validation"]["shortFormEngine"]["beats"]
    for index, beat in enumerate(normalized["beats"]):
        for key, evidence_name in [
            ("strategy", "beatStrategyEvidence"),
            ("visibleConsequence", "consequenceEvidence"),
            ("newInformation", "progressionEvidence"),
        ]:
            recognized_value = (
                bool(sfe_beats[index]["strategies"])
                if key == "strategy"
                else bool(sfe_beats[index]["result"])
                if key == "visibleConsequence"
                else bool(sfe_beats[index]["materialProgress"])
            )
            row(
                f"beats[{index}].{key}",
                raw["beats"][index].get(key),
                beat[key],
                projected["beats"][index][evidence_name],
                _legacy_value(c, key, index),
                recognized_value,
            )
    return output


def rediagnose(raw, before, after, projection):
    old = prior_diagnostics.diagnose(raw, before, prior_diagnostics.audit(raw, before))
    new = prior_diagnostics.diagnose(raw, after, prior_diagnostics.audit(raw, after))
    if new is None:
        return dict(before=old, after=None, classificationChanges=[])
    new = deepcopy(new)
    for dimension in new["failedDimensions"]:
        kind = dimension["dimension"]
        if kind == "payoffStrength" and projection["payoffPresence"] == "PRESENT":
            dimension.update(
                classification="EVIDENCE_EXTRACTION_FAILURE",
                diagnosticReason=(
                    "Terminal event is explicit and matches last consequence; SFE did not recognize "
                    "it as a qualifying payoff. Presence does not verify rule-linked payoff quality."
                ),
            )
        if (
            kind == "goalClarity"
            and projection["fields"]["visibleGoalEvidence"]["presence"] == "PRESENT"
            and any(
                r["code"] == "DECLARED_GOAL_UNSUPPORTED" for r in after["validation"]["eligibilityReasons"]
            )
        ):
            dimension.update(
                classification="EVIDENCE_EXTRACTION_FAILURE",
                diagnosticReason=(
                    "Declared goal is supplied, but accepted goal patterns reject that phrase. Goal "
                    "visibility at frame zero is still unverified."
                ),
            )
    changes = []
    old_dimensions = {d["dimension"]: d for d in (old or {}).get("failedDimensions", [])}
    for d in new["failedDimensions"]:
        prior = old_dimensions.get(d["dimension"])
        if prior and prior["classification"] != d["classification"]:
            changes.append(
                dict(dimension=d["dimension"], before=prior["classification"], after=d["classification"])
            )
    return dict(before=old, after=new, classificationChanges=changes)


def human_review_reasons(record, projection):
    reasons = []
    if prior_diagnostics.human_review(record):
        reasons.append("EXISTING_REVIEW_POLICY")
    bg = record["beatGrammar"]
    c = record["candidate"]
    normalized = c["normalizedSemanticFields"]
    complete = (
        all(f["presence"] == "PRESENT" for f in projection["fields"].values())
        and projection["fullySpecifiedBeatCount"] == projection["describedBeatCount"]
    )
    unknown = (
        projection["payoffStatus"] == "PAYOFF_PRESENT_UNCLASSIFIED"
        or projection["engineClassification"] == "UNCLASSIFIED_CAUSAL_ENGINE"
    )
    # Independent accepted BG diversity/information signals, not presence alone.
    # This is a diagnostic review policy, never admission or production selection.
    strong = (
        complete
        and 4 <= projection["describedBeatCount"] <= 5
        and bg["strategyDiversityScore"] >= 75
        and bg["informationGainScore"] >= 60
        and len({b["visibleConsequence"] for b in normalized["beats"]}) >= 4
    )
    if unknown and strong:
        reasons.append("UNCLASSIFIED_WITH_COMPLETE_SOURCE_AND_EXISTING_BG_DIVERSITY_INFORMATION")
    return reasons


def metrics(run):
    records = run["attempts"]
    scores = [r["validation"]["shortFormScore"] for r in records]
    recognized_rows = [recognized(r) for r in records]
    n = len(records)
    counts = {
        key: sum(bool(x[key]) for x in recognized_rows)
        for key in ("goal", "frameZero", "coreRule", "trigger", "payoff", "payoffClassification", "loop")
    }
    counts["causalBeats"] = sum(x["causalBeats"] for x in recognized_rows)
    counts["describedBeats"] = sum(x["describedBeats"] for x in recognized_rows)
    return dict(
        normalizedCount=n,
        validatorRecognitionCounts=counts,
        validatorRecognitionRates={
            k: v / n if n else None for k, v in counts.items() if k not in ("causalBeats", "describedBeats")
        },
        causalBeatRecognitionRate=counts["causalBeats"] / counts["describedBeats"]
        if counts["describedBeats"]
        else None,
        score=dict(
            min=min(scores) if scores else None,
            max=max(scores) if scores else None,
            mean=mean(scores) if scores else None,
            median=median(scores) if scores else None,
        ),
        dispositionCounts=dict(Counter(r["validation"]["shortFormEngine"]["status"] for r in records)),
        existingHumanReviewSetCount=sum(prior_diagnostics.human_review(r) for r in records),
        productionCandidateCount=len(run["top3ProductionCandidates"]),
    )


def analyze(raw, config, prompt, stored, *, adapter_version="v1"):
    # Replay CONTROL first. This cannot generate deterministic candidates: mode is semantic,
    # and the injected generator only parses the supplied stored response.
    if config.generatorMode != "semantic":
        raise ValueError("Stored semantic replay only; no hybrid/deterministic generation")
    before = generation.generate_and_rank(config, StoredResponseGenerator(raw, prompt))
    if before != stored["storedResponseValidation"]:
        raise ValueError("Stored baseline replay does not match immutable evidence")
    if adapter_version is None:
        return dict(
            workflow="SEMANTIC_EVIDENCE_REPLAY",
            semanticEvidenceAdapterVersion=None,
            baseline=metrics(before),
            baselineExact=True,
            providerCalls=0,
        )
    if adapter_version != "v1":
        raise ValueError("Unsupported semantic evidence adapter version")
    after = generation.generate_and_rank(config, EvidenceReplayGenerator(raw, prompt))
    old = {r["candidateId"]: r for r in before["attempts"]}
    by_idea = {i["ideaId"]: i for i in json.loads(raw)["ideas"] if isinstance(i, dict)}
    baseline_raw = {r["ideaId"]: r for r in stored["diagnostics"]["allRawConcepts"]}
    rows = []
    for record in after["attempts"]:
        c = record["candidate"]
        idea_id = c["providerData"]["ideaId"]
        source = by_idea[idea_id]
        projection = c["canonicalCreativeEvidence"]
        # Re-run the exact canonical input independently; no sidecar-score authority.
        authoritative = ranking.validate_concept({k: v for k, v in generation.ranking_input(c).items()})
        if authoritative != record["validation"]:
            raise ValueError("Non-authoritative canonical validation result")
        diagnosis = rediagnose(source, old[c["candidateId"]], record, projection)
        rows.append(
            dict(
                ideaId=idea_id,
                candidateId=c["candidateId"],
                title=c["title"],
                rawProviderIdea=source,
                openingExtractionAudit=dict(
                    rawFrame=source["frameZeroDescription"],
                    rawFrameFeatures=short._features(source["frameZeroDescription"]),
                    declaredGoalPresence=projection["fields"]["visibleGoalEvidence"]["presence"],
                    goalProblemRelationshipPresence=projection["fields"]["goalRuleRelationshipEvidence"][
                        "presence"
                    ],
                    acceptedRawOpeningNaturalness=c["premiseNaturalness"],
                    actualVisualEvidenceInspected=False,
                    limitation="Lexical recognition and declared fields are separate; no semantic/visual verification is claimed.",
                ),
                payoffExtractionAudit=dict(
                    finalPayoff=source.get("finalPayoff"),
                    lastVisibleConsequence=source["beats"][-1]["visibleConsequence"],
                    lastNewInformation=source["beats"][-1]["newInformation"],
                    untrustedSuggestedPayoffFamily=source.get("suggestedPayoffFamily"),
                    suggestedLabelUsedAsEvidence=False,
                    presenceConclusion=projection["payoffStatus"],
                    classificationBasis="UNCHANGED_EXISTING_CREATIVE_SHAPE_OUTPUT",
                ),
                normalizedSemanticStructure=dict(
                    semanticFields=c["normalizedSemanticFields"],
                    legacyCandidate=old[c["candidateId"]]["candidate"],
                ),
                projectedCanonicalEvidence=projection,
                fieldLossAudit=field_loss(source, old[c["candidateId"]], record),
                beforeValidation=old[c["candidateId"]]["validation"],
                afterValidation=record["validation"],
                beforeRecognition=recognized(old[c["candidateId"]]),
                afterRecognition=recognized(record),
                supportedCausalBeatCount=record["validation"]["shortFormEngine"]["majorCausalBeatCount"],
                providerDeclaredLoop=projection["providerDeclaredLoop"],
                validatorSupportedLoop=recognized(record)["loop"],
                beforeLowScoreDiagnosis=diagnosis["before"],
                afterLowScoreDiagnosis=diagnosis["after"],
                diagnosisChanges=diagnosis["classificationChanges"],
                humanReviewReasons=human_review_reasons(record, projection),
                canonicalDisposition=record["validation"]["shortFormEngine"]["status"],
                originalRawRecordDisposition=baseline_raw[idea_id]["finalDisposition"],
                selectionBlockReasons=record["selectionBlockReasons"],
            )
        )
    changed = [
        dict(
            ideaId=r["ideaId"],
            before=r["beforeValidation"]["shortFormScore"],
            after=r["afterValidation"]["shortFormScore"],
        )
        for r in rows
        if r["beforeValidation"] != r["afterValidation"]
    ]
    complete = [
        r["ideaId"]
        for r in rows
        if all(f["presence"] == "PRESENT" for f in r["projectedCanonicalEvidence"]["fields"].values())
        and r["projectedCanonicalEvidence"]["fullySpecifiedBeatCount"]
        == r["projectedCanonicalEvidence"]["describedBeatCount"]
    ]
    missing = [i for i in stored["diagnostics"]["allRawConcepts"] if not i.get("normalizedInterpretation")]
    return dict(
        workflow="SEMANTIC_EVIDENCE_REPLAY",
        semanticEvidenceAdapterVersion=VERSION,
        experimentId=EXPERIMENT_ID,
        sourceResponseSha256=digest(raw),
        rootCauseEvidence=dict(
            legacyTerminalRelationshipCounts=dict(
                Counter(
                    r["candidate"]["structuredBeatPlan"][-1]["relationshipAfter"] for r in before["attempts"]
                )
            ),
            legacyPayoffShapeCounts=dict(
                Counter(r["candidate"]["storyShapeFingerprint"]["payoffFamily"] for r in before["attempts"])
            ),
            explanation="Legacy semantic adapter maps terminal relations through narrow growth/transfer/environment patterns; Creative Shape returns UNKNOWN for unsupported terminal relations. SFE independently reads timed prose with fixed goal/rule/payoff patterns. Neither UNKNOWN nor an unsupported phrase proves the source field is absent.",
        ),
        baselineExact=True,
        before=metrics(before),
        after=metrics(after),
        projectedRecognitionCounts={
            name: sum(r["projectedCanonicalEvidence"]["fields"][name]["presence"] == "PRESENT" for r in rows)
            for name in FIELD_MAP
        },
        payoffBreakdown={
            status: sum(r["projectedCanonicalEvidence"]["payoffStatus"] == status for r in rows)
            for status in (
                "PAYOFF_MISSING",
                "PAYOFF_PRESENT_CLASSIFIED",
                "PAYOFF_PRESENT_UNCLASSIFIED",
                "PAYOFF_AMBIGUOUS",
            )
        },
        unknownEngineIdeaIds=[
            r["ideaId"]
            for r in rows
            if r["projectedCanonicalEvidence"]["engineClassification"] == "UNCLASSIFIED_CAUSAL_ENGINE"
        ],
        unclassifiedPayoffIdeaIds=[
            r["ideaId"]
            for r in rows
            if r["projectedCanonicalEvidence"]["payoffStatus"] == "PAYOFF_PRESENT_UNCLASSIFIED"
        ],
        completeSourceProjectionIdeaIds=complete,
        below60DespiteCompleteProjection=[
            r["ideaId"]
            for r in rows
            if r["ideaId"] in complete and r["afterValidation"]["shortFormScore"] < 60
        ],
        completeValidatorRecognitionIdeaIds=[
            r["ideaId"]
            for r in rows
            if all(r["afterRecognition"][k] for k in ("goal", "frameZero", "coreRule", "trigger", "payoff"))
            and r["afterRecognition"]["causalBeats"] == r["afterRecognition"]["describedBeats"]
        ],
        changedCanonicalOutcomes=changed,
        materialScoreChanges=[r for r in changed if abs(r["after"] - r["before"]) >= 5],
        HUMAN_REVIEW_SET=[
            dict(
                ideaId=r["ideaId"],
                candidateId=r["candidateId"],
                title=r["title"],
                reasons=r["humanReviewReasons"],
            )
            for r in rows
            if r["humanReviewReasons"]
        ],
        candidates=rows,
        excludedRawEntries=missing,
        fieldLossStatusCounts=dict(Counter(x["status"] for r in rows for x in r["fieldLossAudit"])),
        legacyNormalizationStatusCounts=dict(
            Counter(x["legacyNormalizationStatus"] for r in rows for x in r["fieldLossAudit"])
        ),
        diagnosisTransitions=dict(
            Counter(f"{x['before']} -> {x['after']}" for r in rows for x in r["diagnosisChanges"])
        ),
        canonicalRankingUnchanged=before["rankingResult"] == after["rankingResult"],
        baselineProductionSlate=before["top3ProductionCandidates"],
        adapterProductionSlate=after["top3ProductionCandidates"],
        pipelineEvidence=dict(before=before["generationEvidence"], after=after["generationEvidence"]),
        providerCalls=0,
        externalProviderCalls=0,
        newConceptsGenerated=0,
        renders=0,
        scoreOverrides=False,
        limitations=[
            "Projection presence is not proof of coherent causality, visible staging or a strong idea.",
            (
                "Accepted SFE/ranking consume timed prose and do not accept typed evidence "
                "overrides. Canonical input remains unchanged; no keyword injection or "
                "monkeypatching."
            ),
            (
                "Typed projection is complete where declared source fields are supplied; scoring-"
                "validator recognition can still be incomplete. These are separately counted."
            ),
            "Existing shape taxonomy is reused; suggested provider payoff labels and rationale are excluded.",
            "The expanded review set is diagnostic only; it never changes ranking or production admission.",
        ],
    )


def replay_experiment(request):
    request = EvidenceReplayRequest.model_validate(request)
    data = read_experiment()
    return analyze(**data, adapter_version=request.semanticEvidenceAdapterVersion)
