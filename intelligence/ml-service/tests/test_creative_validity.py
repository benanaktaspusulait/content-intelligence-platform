"""Adversarial creative-validity checks; these never alter Ruleset 1.11."""
import json
from pathlib import Path

from app.workflow.creative_validity import assess, normalize_origin, provenance_contract

ROOT = Path(__file__).parents[2]


def canonical(*rows, score=93.427, grade="A"):
    buckets={"passedRules":[],"failedRules":[],"unknownRules":[],"notApplicableRules":[]}
    for rule_id,outcome,severity,message in rows:
        key={"PASS":"passedRules","FAIL":"failedRules","UNKNOWN":"unknownRules","NOT_APPLICABLE":"notApplicableRules"}[outcome]
        buckets[key].append({"ruleId":rule_id,"outcome":outcome,"severity":severity,"message":message,"details":{}})
    return {"status":"EVALUATED","rulesetVersion":"1.11","score":score,"grade":grade,**buckets}


FIXTURE={"origin":"DETERMINISTIC_FIXTURE","provider":"ISOLATED_FIXTURE","model":"fixture-p2-v1",
         "requestFingerprint":"a"*64,"responseFingerprint":"b"*64,"reviewerOrigin":"DETERMINISTIC_FIXTURE","reviewerIndependent":False}


def test_a_numeric_a_and_hook_pass_do_not_verify_first_frame_excellence():
    value=assess("0-2s: Already mid-action, Pip reaches toward a note.",canonical(
        ("HOOK_002","PASS","PASS","Textual first-frame intent establishes an immediate anomaly; visual verification remains separate.")),FIXTURE)
    assert value["canonicalScore"]==93.427 and value["canonicalGrade"]=="A"
    assert not value["creativelyStrongVerified"]
    assert any(r["code"]=="TEXTUAL_HOOK_NOT_VISUAL_PROOF" for r in value["risks"])
    assert value["dimensions"][0]["state"]=="TEXTUALLY_STRUCTURED_VISUALLY_UNVERIFIED"


def test_b_distinct_verbs_with_same_count_consequence_surface_repetition_risk():
    prompt="\n".join(("0-3s: Pip peels one note -> one becomes two.","3-6s: Pip presses two notes -> two become four.","6-9s: Pip pushes four notes -> four become eight."))
    value=assess(prompt,canonical(),FIXTURE)
    assert value["dimensions"][1]["state"]=="REPETITION_RISK"
    assert any(r["code"]=="REPETITIVE_VIEWER_VISIBLE_CONSEQUENCE" for r in value["risks"])


def test_c_overloaded_final_window_is_visible():
    prompt="0-11s: Pip struggles.\n11-15s: Pip sees, realizes, stops, turns, remains covered, sneezes, scatters notes, and is relieved."
    value=assess(prompt,canonical(),FIXTURE)
    risk=next(r for r in value["risks"] if r["code"]=="ENDING_TIMING_OVERLOAD")
    assert risk["evidence"]["window"]=="11.0-15.0s"


def test_d_high_score_never_hides_critical_production_risk():
    value=assess("0-2s: A note folds around a finger.",canonical(
        ("PRODUCIBILITY_003","FAIL","CRITICAL","Thin-object interaction is fragile.")),FIXTURE)
    assert value["canonicalGrade"]=="A"
    assert value["dimensions"][3]["state"]=="RISK_DETECTED"
    assert any(r["code"]=="CRITICAL_PRODUCIBILITY_RISK" for r in value["risks"])


def test_e_curiosity_opening_is_not_rejected_for_lacking_immediate_impossible_event():
    value=assess("0-3s: Pip notices a faint tapping behind a tiny closed door and leans closer.",canonical(score=88,grade="B"),
                 {**FIXTURE,"origin":"HUMAN_AUTHORED"})
    assert value["dimensions"][0]["state"]=="TEXTUALLY_STRUCTURED_VISUALLY_UNVERIFIED"
    assert not any(r["code"]=="MISSING_IMMEDIATE_IMPOSSIBLE_EVENT" for r in value["risks"])


def test_f_unresolved_or_replay_ending_does_not_require_conventional_resolution():
    value=assess("0-12s: Pip follows the sound.\n12-15s: The tiny door taps again just after Pip turns away.",canonical(score=88,grade="B"),FIXTURE)
    assert value["dimensions"][4]["state"]=="REPLAY_UNKNOWN"
    assert not any("resolution" in r["finding"].lower() for r in value["risks"])


def test_g_prompt_quality_claims_are_unsupported_evidence():
    value=assess("0-2s: VIRAL scroll-stop excellent hook. Pip enters.",canonical(),FIXTURE)
    assert any(r["code"]=="UNSUPPORTED_SELF_ASSERTED_QUALITY" for r in value["risks"])


def test_h_fixture_creatively_strong_label_remains_provisional_and_excluded():
    value=assess("0-2s: Pip enters.",canonical(),FIXTURE,{"candidateAssessments":[{"status":"CREATIVELY_STRONG"}]})
    assert value["creativeQualityStatus"]=="CREATIVE_RISK_DETECTED"
    assert value["finalQualification"]=="PROVISIONAL_CREATIVE_VALIDITY_REQUIRED"
    assert not value["provenance"]["realCapabilityStatisticsEligible"]
    assert not value["realProviderCapabilityClaimAllowed"]
    assert value["officialAPlus"]=="INACTIVE"


def test_p2_actual_prompt_is_numeric_a_but_creative_risk_detected():
    prompt=(ROOT/"docs/p2-canonical-aware-story-evidence/generated-prompt.txt").read_text()
    actual=json.loads((ROOT/"docs/p2-canonical-aware-story-evidence/canonical-evaluation.json").read_text())
    value=assess(prompt,actual,FIXTURE,{"candidateAssessments":[{"status":"CREATIVELY_STRONG"}]})
    assert value["canonicalScore"]==93.42708333333334 and value["canonicalGrade"]=="A"
    codes={r["code"] for r in value["risks"]}
    assert {"TEXTUAL_HOOK_NOT_VISUAL_PROOF","REPETITIVE_VIEWER_VISIBLE_CONSEQUENCE","ENDING_TIMING_OVERLOAD","CRITICAL_PRODUCIBILITY_RISK","SELF_CONFIRMING_REVIEW"} <= codes
    assert value["creativeQualityStatus"]=="CREATIVE_RISK_DETECTED"


def test_origin_normalization_is_closed_and_unknown_fails_closed():
    assert normalize_origin("DETERMINISTIC_MOCK_PROVIDER_PLUS_ACTUAL_APPLICATION_EVALUATOR")=="DETERMINISTIC_FIXTURE"
    assert normalize_origin("REAL_PROVIDER")=="REAL_AI_PROVIDER"
    assert normalize_origin("surprise") == "UNKNOWN_ORIGIN"
    assert not provenance_contract({"origin":"UNKNOWN_ORIGIN"})["realCapabilityStatisticsEligible"]
