"""Conservative semantic text-to-plan adapter; accepted analyzers and scores are reused."""

import json
import re
from copy import deepcopy
from pathlib import Path

from . import beat_grammar as bg
from . import creative_shape as shape
from . import premise_naturalness as natural
from .concept_fingerprint import digest, fingerprint

VERSION = "semantic-plan-adapter-v1"


def strategy(text, index):
    t = text.lower()
    for pattern, value in [
        (r"fold|different (side|corner)|other (side|edge|corner)", "SWITCH_CONTACT_POINT"),
        (r"turn|angle|sideways|rotate", "CHANGE_ANGLE"),
        (r"guide|along|surface", "USE_ENVIRONMENT_SURFACE"),
        (r"wedge|pin|anchor", "ANCHOR_TO_ENVIRONMENT"),
        (r"brace|harder|both hands", "BRACE_BODY"),
        (r"light|gently|slow", "REDUCE_FORCE"),
        (r"stop|pause", "TEMPORARILY_STOP_TRIGGER"),
    ]:
        if re.search(pattern, t):
            return value
    return "DIRECT_USE"


def normalize_idea(idea, config, cast, prompt):
    raw = idea.model_dump()
    actor = next(
        (
            c
            for c in cast
            if idea.protagonistSuggestion.casefold() in (c["name"].casefold(), c["id"].casefold())
        ),
        None,
    )
    if actor is None:
        raise ValueError("NON_CANONICAL_PROTAGONIST: use one supplied canonical character")
    scene_text = " ".join(
        [idea.frameZeroDescription, idea.finalPayoff, *[b.model_dump_json() for b in idea.beats]]
    )
    if any(
        person["id"] != actor["id"] and re.search(r"\b" + re.escape(person["name"]) + r"\b", scene_text, re.I)
        for person in cast
    ):
        raise ValueError("MULTIPLE_OR_CONFLICTING_CANONICAL_CHARACTERS")
    rule = idea.impossibleRule
    trigger = natural._trigger({"impossibleRule": rule + " " + idea.visibleTrigger})
    response = natural.infer_response({"impossibleRule": rule})
    extension = json.loads(Path(__file__).with_name("semantic_concept_analysis_v1.json").read_text())
    transfer_data = extension["waterPatchTransfer"]
    water_transfer = all(re.search(pattern, rule, re.I) for pattern in transfer_data["requiredRulePatterns"])
    if water_transfer:
        response = "WATER_PATCH_TRANSFER"
    c = dict(
        candidateId="sem1-" + digest([idea.ideaId, rule, idea.beats[0].visibleConsequence])[:16],
        title=idea.title,
        protagonist=actor["name"],
        protagonistCharacterId=actor["id"],
        everydayGoal=idea.everydayGoal,
        primaryObject=idea.primaryObject,
        engineFamily=response if response != "UNSUPPORTED_RESPONSE" else "UNCLASSIFIED_SEMANTIC_ENGINE",
        impossibleRule=rule,
        goalRuleRelationship=idea.goalRuleRelationship,
        frameZeroDescription=idea.frameZeroDescription,
        finalPayoff=idea.finalPayoff,
        intendedDurationSeconds=idea.durationSeconds,
        environment=idea.environment,
        dialogueRequirement=idea.dialogueNeed,
        loopPotential={"type": "PROVIDER_SUGGESTION_UNVERIFIED", "description": idea.loopPotential},
        generationSource="SEMANTIC_V1",
        generationRunId=config.run_id(),
        providerName=config.semanticProvider.provider,
        providerModel=config.semanticProvider.model,
        providerPromptVersion=prompt["version"],
        providerData={
            "ideaId": idea.ideaId,
            "normalExpectation": idea.normalExpectation,
            "whyThisObject": idea.whyThisObject,
            "providerRationale": idea.providerRationale,
            "suggestedPayoffFamily": idea.suggestedPayoffFamily,
        },
        provenance={
            "generationSource": "SEMANTIC_V1",
            "adapterVersion": VERSION,
            "providerPromptSha256": prompt["sha256"],
            "rawIdeaSha256": digest(raw),
            "rationaleScored": False,
        },
        productionNotes=[
            "Semantic provider data is untrusted; deterministic analysis and human review required."
        ],
        composition={
            "trigger": trigger,
            "stateTransition": response,
            "objectCategory": natural.load_model()["objects"]
            .get(idea.primaryObject.casefold(), {})
            .get("archetype", "UNCLASSIFIED"),
            "goalFamily": "SEMANTIC_GOAL",
            "engineFamily": response,
            "escalationTopology": "SEMANTIC_SEQUENCE",
            "payoffTopology": "UNCLASSIFIED",
        },
        structuralPlan={
            "interactionType": trigger,
            "trigger": trigger,
            "transformationDirection": response,
            "escalationTopology": "SEMANTIC_SEQUENCE",
            "resolutionTopology": "UNCLASSIFIED",
            "finalSilhouetteTopology": "UNKNOWN",
            "loopTopology": "UNVERIFIED",
        },
    )
    # Exact provider phrasing is retained; no canonical keyword injection or prose rewrite.
    c["beats"] = [
        dict(
            startSeconds=round(i * idea.durationSeconds / len(idea.beats), 2),
            endSeconds=round((i + 1) * idea.durationSeconds / len(idea.beats), 2),
            description=f"{actor['name']} {b.strategy}. {b.visibleConsequence} {b.newInformation}",
        )
        for i, b in enumerate(idea.beats)
    ]
    c["providerData"].update(
        rawFrameZeroDescription=idea.frameZeroDescription, rawFinalPayoff=idea.finalPayoff
    )
    c["beats"][0]["description"] = idea.frameZeroDescription + " " + c["beats"][0]["description"]
    c["frameZeroDescription"] = c["beats"][0]["description"]
    c["finalPayoff"] = c["beats"][-1]["description"]
    c["structuralFingerprint"] = fingerprint(c)
    baseline = natural.assess({**c, "frameZeroDescription": idea.frameZeroDescription})
    c["premiseNaturalness"] = baseline
    if water_transfer:
        # Data-driven extension is isolated from the accepted default model. Faithful lexical
        # normalization calls the same assessor/formula; original rule and baseline remain visible.
        model = natural.load_model()
        model["version"] = "semantic-affordance-extension-v1"
        model["contradictionPolicies"].append(deepcopy(transfer_data["policy"]))
        interpreted = {
            **c,
            "impossibleRule": transfer_data["lexicalAssessmentInput"],
            "frameZeroDescription": idea.frameZeroDescription,
        }
        annotated = natural.assess(interpreted, model)
        annotated.update(
            actualImpossibleResponse=rule,
            baselineAssessment=baseline,
            adapterEvidence={
                "version": VERSION,
                "recognizedRelation": "WATER_PATCH_TRANSFER",
                "lexicalAssessmentInput": interpreted["impossibleRule"],
                "scope": "NEW_NON_CANONICAL_COVERAGE_USING_ACCEPTED_ASSESSOR_WITH_ISOLATED_MODEL_COPY",
            },
        )
        # Opening support is not repaired by the rule normalization.
        c["premiseNaturalness"] = annotated
    transfer = response in ("WATER_PATCH_TRANSFER", "MARK_TRANSFER")
    data = deepcopy(bg.load_data())
    for value in [
        "BODY_SURFACE_MARKED",
        "SURFACE_PATTERN_SPREADS",
        "ENVIRONMENT_MARKED",
        "GOAL_ACHIEVED_NEW_PROBLEM",
    ]:
        if value not in data["consequences"]:
            data["consequences"].append(value)
    plan = []
    state = {"kind": "USABLE_START", "applicationCount": 0}
    body = "NORMAL_CONTROL"
    for i, b in enumerate(idea.beats):
        text = b.visibleConsequence + " " + b.newInformation
        tactic = strategy(b.strategy, i)
        paused = tactic == "TEMPORARILY_STOP_TRIGGER"
        final = i == len(idea.beats) - 1
        grows = bool(re.search(r"grow|larger|giant|enormous", text, re.I))
        environment = bool(re.search(r"fills? the room|room becomes", text, re.I))
        path_blocked = bool(re.search(r"blocks? the (route|door)", text, re.I))
        space_reduced = bool(re.search(r"usable space|squeez", text, re.I))
        achieved = bool(
            re.search(
                r"(paper|table|surface).{0,20}(clean|dry)|goal.{0,15}(reached|achieved)|finally.{0,20}closed",
                text,
                re.I,
            )
        )
        target = (
            "BODY_SURFACE_MARKED"
            if re.search(r"sleeve|shirt|clothes|cheek", text, re.I)
            else "ENVIRONMENT_MARKED"
            if re.search(r"wall|floor", text, re.I)
            else "SURFACE_PATTERN_SPREADS"
        )
        consequence = (
            "GOAL_ACHIEVED_NEW_PROBLEM"
            if transfer and final and achieved
            else target
            if transfer
            else "ENVIRONMENT_BECOMES_BLOCKED"
            if environment
            else "PATH_BLOCKED"
            if path_blocked
            else "SPACE_REDUCES"
            if space_reduced or grows and i
            else "OBJECT_GROWS"
            if grows
            else "CHARACTER_MOVES"
        )
        after = (
            "PATTERNED_BODY"
            if transfer and final
            else "WET_SLEEVE"
            if transfer and re.search(r"sleeve", text, re.I)
            else "MARKED_CLOTHES"
            if transfer
            else "SPACE_CONSTRAINED"
            if environment
            else "CROUCHED"
            if space_reduced
            else "BRACED"
            if path_blocked
            else "OFF_BALANCE"
            if i
            else "LEANING"
        )
        relation = (
            "OBJECT_PROPERTY_TRANSFERRED"
            if transfer and final
            else "ENVIRONMENT_BECOMES_OBSTACLE"
            if environment
            else "OBJECT_DISPLACES_BODY"
            if i and grows
            else "CHARACTER_ATTEMPTS_CONTROL"
        )
        nxt = (
            deepcopy(state)
            if paused
            else {"kind": response, "applicationCount": state["applicationCount"] + 1}
        )
        facts = ["INITIAL_CONTRADICTION"] if not i else []
        if transfer:
            facts += [target]
        if environment:
            facts += ["WORKING_SPACE_LOST"]
        if achieved:
            facts += ["EVERYDAY_GOAL_REACHED_WITH_NEW_PROBLEM"]
        if tactic not in [p["characterStrategy"] for p in plan]:
            facts += ["TACTIC:" + tactic]
        plan.append(
            dict(
                beatNumber=i + 1,
                beatRole="HOOK_PROBLEM" if not i else "PAYOFF" if final else "TACTIC_CHANGE",
                characterStrategy=tactic,
                trigger="NONE" if paused else trigger,
                impossibleRule=rule,
                objectResponse=b.visibleConsequence,
                characterConsequence=b.newInformation,
                bodyStateBefore=body,
                bodyStateAfter=after,
                objectStateBefore=deepcopy(state),
                objectStateAfter=nxt,
                spatialChange={
                    "distanceToGoal": "AT_GOAL" if achieved else "FARTHER",
                    "environmentUse": "BOUNDARY_CONTACT" if environment else "UNCHANGED",
                    "availableFreeSpace": "REDUCED" if environment else "UNCHANGED",
                },
                goalProgress="SUCCESS" if achieved else "FARTHER",
                newInformation=facts,
                contactPattern="ALTERNATE_CONTACT" if tactic == "SWITCH_CONTACT_POINT" else "WORKING_CONTACT",
                consequenceType=consequence,
                relationshipAfter=relation,
                payoffContribution="FINAL_RELATIONSHIP_CHANGE" if final else "CAUSAL_CONSEQUENCE",
                payoffStateChange=relation if final else "NONE",
            )
        )
        state = nxt
        body = after
    c["structuredBeatPlan"] = plan
    c["beatGrammar"] = bg.assess(plan, data=data)
    c["beatGrammar"]["adapterVersion"] = VERSION
    c["storyShapeFingerprint"] = shape.annotate(c)
    if transfer:
        f = c["storyShapeFingerprint"]
        d = f["dimensions"]
        d.update(
            payoffMechanism="PROPERTY_TRANSFER",
            finalCharacterObjectRelation="OBJECT_PROPERTY_TRANSFERRED",
            loopMechanism="NONE",
        )
        d["controlStateSequence"][-1] = "OBJECT_DOMINATES"
        f.update(
            shapeHash=digest(d),
            macroShapeHash=digest(
                {
                    k: d[k]
                    for k in [
                        "goalStateSequence",
                        "controlStateSequence",
                        "strategyRoleSequence",
                        "payoffMechanism",
                        "finalCharacterObjectRelation",
                        "loopMechanism",
                    ]
                }
            ),
            payoffFamily="PROPERTY_TRANSFER",
            finalRelationship="OBJECT_PROPERTY_TRANSFERRED",
            adapterVersion=VERSION,
        )
    c["structuralPlan"].update(
        resolutionTopology=c["storyShapeFingerprint"]["payoffFamily"], finalSilhouetteTopology=body
    )
    c["visualFingerprint"] = dict(
        characterPoseFamily=body,
        objectRelativePosition="WORKING_CONTACT",
        dominantDirection=response,
        objectScaleRelation="INCREASING" if response == "SCALE_UP" else "STABLE",
        characterObjectContact=plan[-1]["contactPattern"],
        finalFrameComposition=c["storyShapeFingerprint"]["finalRelationship"],
        movementAxis="PLANNED_SEQUENCE",
        environmentInteraction="ROOM_BLOCKED"
        if any(p["consequenceType"] == "ENVIRONMENT_BECOMES_BLOCKED" for p in plan)
        else "LOCAL_WORK_AREA",
    )
    c["escalationCurve"] = [
        dict(
            beatIndex=p["beatNumber"],
            sourceRule=rule,
            stateTransition=response,
            transitionApplication=p["objectStateAfter"]["applicationCount"],
        )
        for p in plan
    ]
    c["structuralFingerprint"] = fingerprint(c)
    c["historicalCreativeTerritory"] = shape.territory(c)
    return c
