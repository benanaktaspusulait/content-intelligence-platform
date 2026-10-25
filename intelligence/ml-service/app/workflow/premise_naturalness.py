"""Versioned deterministic affordance contradiction screen; never canonical quality."""

import json
import re
from copy import deepcopy
from pathlib import Path

from .concept_fingerprint import digest, token

VERSION = "premise-naturalness-v1"
REVIEW_STATUSES = (
    "INTUITIVE_AND_STRONG",
    "INTUITIVE_BUT_WEAK",
    "STRANGE_BUT_LEGIBLE",
    "CONTRIVED",
    "ARBITRARY",
    "BROKEN",
)


def load_model():
    return json.loads(Path(__file__).with_name("affordance_expectations_v1.json").read_text())


def infer_response(candidate):
    text = str(candidate.get("impossibleRule", "")).lower()
    # Functional reversals must be identified by their actual function, not a supplied quality label.
    for pattern, response in [
        (
            r"(eras\w*|remov\w*).{0,90}mark.{0,90}(appear|transfer)|mark.{0,80}(appear|transfer).{0,80}(elsewhere|face|somewhere)",
            "MARK_TRANSFER",
        ),
        (r"(wipe|dry).{0,90}(wetter|adds? water)", "WETTER"),
        (r"slipperier|more slippery", "SLIP_INCREASE"),
        (r"(heavier|weight).{0,70}bounc|bounc.{0,70}(heavier|weight)", "WEIGHT_PER_BOUNCE"),
        (r"(attract|draw).{0,50}rain", "RAIN_ATTRACTION"),
        (r"float|levitat", "FLOAT_AWAY"),
        (r"stick|adhere|clings?", "CONTACT_RETAINS"),
        (r"shrink|smaller", "SCALE_DOWN"),
        (r"grow|bigger|larger", "SCALE_UP"),
        (r"flips?|upside.down", "INVERT_ORIENTATION"),
        (r"stretch|lengthen", "EXTEND_CONTACT"),
        (r"slides?.{0,50}away|moves? away|escapes?", "MOVE_AWAY"),
        (r"inward|slides? back|snaps? back|reset|returns? to", "RETURN_ORIGIN"),
    ]:
        if re.search(pattern, text):
            return response
    return (
        "ORDINARY_RESPONSE"
        if re.search(r"moves? (slightly|normally)|ordinary|normal movement", text)
        else "UNSUPPORTED_RESPONSE"
    )


def _policy(archetype, response, model):
    return next(
        (
            p
            for p in model["contradictionPolicies"]
            if archetype in p["archetypes"] and response in p["responses"]
        ),
        None,
    )


def _trigger(candidate):
    explicit = candidate.get("composition", {}).get("trigger") or candidate.get("trigger")
    if explicit:
        return token(str(explicit))
    text = str(candidate.get("impossibleRule", "")).lower()
    for pattern, value in [
        (r"wear|foot.*enter", "WEAR"),
        (r"bounc", "BOUNCE"),
        (r"lift", "LIFT"),
        (r"pull", "PULL"),
        (r"stroke|drawing|eras", "STROKE"),
        (r"wip", "WIPE"),
        (r"squeez|press", "PRESSURE"),
        (r"weight|sat on|sit", "WEIGHT_APPLIED"),
        (r"touch", "TOUCH"),
    ]:
        if re.search(pattern, text):
            return value
    return "UNSPECIFIED"


def assess(candidate, model=None, *, canonical_creative_evidence=None, generalized_premise_evidence=False):
    """No mutation, providers, prose rewrites or canonical assessors."""
    if generalized_premise_evidence:
        if canonical_creative_evidence is None or not canonical_creative_evidence.is_structured:
            raise ValueError('Generalized premise evidence requires explicit canonical structured context')
        from .premise_admission_evidence import assess as assess_generalized
        return assess_generalized(candidate, model or load_model(), canonical_creative_evidence)
    canonical = canonical_creative_evidence
    if canonical is not None and canonical.is_structured:
        candidate = canonical.naturalness_input(candidate)
    model = model or load_model()
    name = str(candidate.get("primaryObject", "")).strip().casefold()
    obj = model["objects"].get(name)
    archetype = obj["archetype"] if obj else "GENERIC"
    expected = model["archetypes"][archetype]
    rule = str(candidate.get("impossibleRule", "")).strip()
    goal = str(candidate.get("everydayGoal", "")).strip()
    frame = str(candidate.get("frameZeroDescription", "")).strip()
    response = infer_response(candidate)
    trigger = _trigger(candidate)
    if canonical is not None and canonical.is_structured:
        # Classification remains the existing classifier; presence is exposed separately.
        trigger = _trigger({"impossibleRule": canonical.fields["visibleTrigger"]})
    policy = _policy(archetype, response, model)
    flags = []
    broken = not rule or not goal or not name or response == "UNSUPPORTED_RESPONSE"
    natural_trigger = 100 if trigger in expected["naturalTriggers"] else 40 if trigger != "UNSPECIFIED" else 0
    goal_match = any(re.search(p, goal, re.I) for p in expected["goalPatterns"]) if goal else False
    # Preserve rather than repair mismatched declared nouns in accepted grammar.
    noun_conflict = bool(name == "towel" and re.search(r"\bshirt\b", goal, re.I))
    if noun_conflict:
        flags.append(
            {
                "code": "DECLARED_GOAL_OBJECT_MISMATCH",
                "reason": "The declared goal names a shirt while the primary object is a towel.",
            }
        )
    relationship = policy["relationshipStrength"] if policy else 0
    direct = bool(policy and goal_match and not noun_conflict and natural_trigger >= 70)
    interference = policy["goalInterferenceType"] if direct else "CONTRIVED" if rule else "NONE"
    if policy and not direct and not noun_conflict:
        interference = "INDIRECT" if goal_match else "CONTRIVED"
    arbitrary = not policy and response not in ("ORDINARY_RESPONSE", "UNSUPPORTED_RESPONSE")
    if arbitrary:
        flags.append(
            {
                "code": "ARBITRARY_MAGIC_RELATIONSHIP",
                "reason": (
                    "No configured functional or material dependency connects this "
                    "response to the object affordance."
                ),
            }
        )
    ordinary = response == "ORDINARY_RESPONSE"
    distance = (
        "TOO_SMALL"
        if ordinary
        else "ARBITRARY_DISCONNECT"
        if arbitrary or not direct
        else "CLEAR_CONTRADICTION"
    )
    if ordinary:
        flags.append(
            {
                "code": "EXPECTATION_DISTANCE_TOO_SMALL",
                "reason": (
                    "The described response is ordinary movement, not a clear affordance contradiction."
                ),
            }
        )
    # Hold the violated function fixed when swapping roles. Swapping a title is not a new function.
    target = expected["primaryExpectedBehaviors"][policy["expectedBehaviorIndex"]] if policy else None
    swaps = []
    for role in sorted(model["comparisonArchetypes"]):
        other = model["archetypes"][role]
        other_policy = _policy(role, response, model)
        preserved = bool(policy and other_policy and target in other["primaryExpectedBehaviors"])
        if not policy:
            preserved = response not in ("UNSUPPORTED_RESPONSE", "ORDINARY_RESPONSE")
        swaps.append(
            {
                "replacementArchetype": role,
                "functionalLogicPreserved": preserved,
                "reason": "Same expected function supports the response."
                if preserved and policy
                else "Unbound effect remains portable."
                if preserved
                else "The original violated function is not preserved.",
            }
        )
    portable = sum(s["functionalLogicPreserved"] for s in swaps) / len(swaps)
    specificity = round(100 * (1 - portable) * min(1, relationship / 80)) if policy else 0
    if not direct:
        specificity = min(specificity, 45)
    swap_status = "OBJECT_SPECIFIC_PREMISE" if specificity >= 70 else "GENERIC_ENGINE_APPLICATION"
    if swap_status == "GENERIC_ENGINE_APPLICATION":
        flags.append(
            {
                "code": "GENERIC_ENGINE_APPLICATION",
                "reason": "The effect has insufficient supported dependence on this object function.",
            }
        )
    irony = policy["functionalIrony"] if direct else "LOW" if policy else "NONE"
    material = policy.get("materialConnection") if policy else None
    material_supported = bool(material and material in expected["materialProperties"])
    # Separate an authored rule from evidence in a proposed opening frame.
    object_visible = bool(frame and re.search(r"\b" + re.escape(name) + r"\b", frame, re.I))
    action_visible = bool(frame and any(re.search(p, frame, re.I) for p in expected["goalPatterns"]))
    anomaly_visible = bool(
        frame
        and infer_response({"impossibleRule": frame}) == response
        and response not in ("UNSUPPORTED_RESPONSE", "ORDINARY_RESPONSE")
    )
    if canonical is not None and canonical.is_structured:
        opening = canonical.facts["opening"]
        action_visible = opening["goalPresent"]
        anomaly_visible = opening["anomalyPresent"]
        source_supported = opening["causalRelationshipVisible"]
    else:
        source_supported = object_visible and action_visible and anomaly_visible
    full_causal = (
        90 if direct and source_supported else 60 if direct and not frame else 35 if source_supported else 15
    )
    if frame and (not direct or not source_supported):
        flags.append(
            {
                "code": "CAUSE_NOT_VISIBLE_AT_FRAME_ZERO",
                "reason": (
                    "The supplied opening does not support a clear use-to-functional-contradiction link."
                ),
            }
        )
    static = (
        85
        if source_supported
        and direct
        and response
        in ("SCALE_UP", "INVERT_ORIENTATION", "EXTEND_CONTACT", "WETTER", "MARK_TRANSFER", "CONTACT_RETAINS")
        else 65
        if source_supported and direct
        else 25
        if source_supported
        else 15
        if frame
        else None
    )
    payoff = (
        round(0.45 * relationship + 0.25 * specificity + 0.20 * natural_trigger + (10 if direct else 0))
        if policy
        else 25
        if natural_trigger >= 70
        else 10
    )
    if not direct:
        payoff = min(payoff, 45)
    payoff = min(payoff, 100)
    naturalness = (
        "BROKEN"
        if broken
        else "CONTRIVED"
        if arbitrary or not direct or ordinary
        else "STRONG"
        if relationship >= 80 and natural_trigger >= 70
        else "ACCEPTABLE"
    )
    review = (
        "BROKEN"
        if broken
        else "ARBITRARY"
        if arbitrary
        else "CONTRIVED"
        if not direct
        else "INTUITIVE_BUT_WEAK"
        if ordinary or relationship < 70
        else "STRANGE_BUT_LEGIBLE"
        if policy and policy["strangeButIntuitive"]
        else "INTUITIVE_AND_STRONG"
    )
    energy = (
        "HIGH_ENERGY"
        if direct and payoff >= 80
        else "MEDIUM_ENERGY"
        if direct and payoff >= 60
        else "LOW_ENERGY"
    )
    admitted = (
        naturalness in ("STRONG", "ACCEPTABLE")
        and interference == "DIRECT"
        and distance == "CLEAR_CONTRADICTION"
    )
    if canonical is not None and canonical.is_structured:
        for flag in flags:
            if flag["code"] == "CAUSE_NOT_VISIBLE_AT_FRAME_ZERO":
                flag["qualityScope"] = "CONFIGURED_USE_TO_AFFORDANCE_CONTRADICTION"
                flag["canonicalCausalRelationshipVisible"] = canonical.facts["opening"]["causalRelationshipVisible"]
                flag["evidenceClassification"] = "TAXONOMY_COVERAGE_LIMIT" if not policy else "LEGITIMATE_QUALITY_DIFFERENCE"
                flag["reason"] = (
                    "Canonical opening facts are attached. The configured direct object-response "
                    "contradiction is not established; this legacy-named quality flag does not "
                    "assert that a declared goal, anomaly, rule or trigger is absent."
                )
    return {
        "gateVersion": VERSION,
        **({"canonicalCreativeEvidence": canonical.receipt(),
            "sourceExpectations": {k:canonical.fields[k] for k in ("normalExpectation","whyThisObject","visibleTrigger")},
            "responseDiagnosis": {
                "responsePresent": canonical.facts["rule"]["present"],
                "category": "B" if response == "UNSUPPORTED_RESPONSE" and canonical.facts["rule"]["present"] else "C" if policy is None and response != "UNSUPPORTED_RESPONSE" else "CLASSIFIED",
                "classification": "TAXONOMY_COVERAGE_LIMIT" if response == "UNSUPPORTED_RESPONSE" or policy is None else "LEGITIMATE_QUALITY_DIFFERENCE",
                "meaning": "responseType classifies the impossible object response, not the existence of a rule",
            }} if canonical is not None and canonical.is_structured else {}),
        "modelVersion": model["version"],
        "modelSha256": digest(model),
        "primaryExpectedBehaviors": deepcopy(expected["primaryExpectedBehaviors"]),
        "expectedResponse": target or deepcopy(expected["primaryExpectedBehaviors"]),
        "actualImpossibleResponse": rule,
        "responseType": response,
        "contradictionType": policy["contradictionType"] if policy else None,
        "expectationDistance": distance,
        "premiseNaturalness": naturalness,
        "premiseReviewStatus": review,
        "goalInterferenceType": interference,
        "triggerNaturalness": natural_trigger,
        "objectSpecificityScore": specificity,
        "objectSpecificity": "HIGH" if specificity >= 75 else "MEDIUM" if specificity >= 50 else "LOW",
        "functionalIrony": irony,
        "physicalPayoffPotential": payoff,
        "instantCausalLegibility": full_causal,
        "staticFrameLegibility": static,
        "materialPropertyConnection": {"property": material, "supportedInObjectData": material_supported},
        "whyThisObject": f"The contradiction violates '{target}', a configured expectation of {name}."
        if direct
        else "No supported object-function dependency; a natural trigger alone is insufficient.",
        "objectSwapTest": {
            "classification": swap_status,
            "portableArchetypeFraction": round(portable, 6),
            "comparisons": swaps,
            "scope": (
                "Configured archetype substitutions with the violated function "
                "held fixed; not semantic counterfactual proof."
            ),
        },
        "premiseEnergy": energy,
        "admitted": admitted,
        "flags": flags,
        "scoreUse": "NON_CANONICAL_PRE_RENDER_HEURISTICS_NOT_RETENTION",
        "limitations": [
            (
                "Curated expectation/response coverage; absence of a policy is a "
                "review/filter decision, not proof that an idea is bad."
            ),
            (
                "Static-frame and causal legibility are text-plan estimates, not "
                "observed pixels. Object specificity is function-family dependence, "
                "not unique-object originality."
            ),
        ],
    }
