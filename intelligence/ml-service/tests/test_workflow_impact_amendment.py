"""Synthetic behavior contracts A–T, never labels for the real corpus."""

import pytest

from app.workflow.feedback import review_render
from app.workflow.review import binding_fingerprint, review_prompt


def prompt(text=None, **options):
    return dict(
        prompt=text
        or (
            "0-2 SEC\nLuca searches the box.\n2-4 SEC\nA clue narrows the search.\n"
            "4-6 SEC\nThe missing shoe is revealed under the cap. CUT."
        ),
        profile="post-family-v1",
        sourceId="synthetic",
        sourceVersion="1",
        desiredDuration=6,
        contentProfile="CURIOSITY_ADVENTURE",
        **options,
    )


def evidence(p, dimension, assessment, **extra):
    q = p["prompt"].splitlines()[-1]
    s = p["prompt"].index(q)
    return dict(
        dimension=dimension,
        assessment=assessment,
        sourceSpan=[s, s + len(q)],
        sourceQuote=q,
        rationale="Synthetic source interpretation",
        **extra,
    )


def qa(level="FLEXIBLE", state="PRESENT", impact=None, progression="DEVELOPING", basis="HUMAN_REVIEWED_CLIP"):
    p = {
        "bindingHash": "bound",
        "decisionPolicyVersion": "impact-review-v1",
        "intentRequirements": [
            {"id": "main", "level": "ESSENTIAL", "eventIds": ["main"], "sourceQuote": "Reveal"}
        ],
        "events": [
            {"id": "main", "start": 0, "end": 3, "intentLevel": "ESSENTIAL", "requiresMotion": True},
            {"id": "turn", "start": 3, "end": 6, "intentLevel": level, "requiresMotion": True},
        ],
    }

    def obs(**fields):
        return dict(
            start=0,
            end=6,
            evidenceBasis=basis,
            reference="synthetic:clip:0-6",
            observed="Visible synthetic experience",
            inferred="",
            uncertainty="Synthetic only",
            confidence="HIGH",
            **fields,
        )

    o = {
        "bindingHash": "bound",
        "assetHash": "a" * 64,
        "duration": 6,
        "coverage": [0, 6],
        "events": [obs(id="main", state="PRESENT"), obs(id="turn", state=state)],
        "experience": {
            k: obs(value=v)
            for k, v in {
                "coreEventReadability": "ADEQUATE",
                "identity": "RECOGNIZABLE",
                "safety": "APPROPRIATE",
                "coherence": "ADEQUATE",
                "progression": progression,
            }.items()
        },
        "defects": [],
    }
    if impact:
        o["defects"] = [
            obs(
                type="CONTACT",
                impact=impact,
                eventId="main",
                durationSeconds=0.2,
                recurrence=1,
                affectedEntity="hand",
                rawSeverity="BLOCKING",
            )
        ]
    return p, o


def test_A_non_comedic_curiosity():
    r = review_prompt(prompt())
    assert r["planQuality"]["status"] != "FAIL"
    assert r["applicability"]["COMEDY"]["status"] == "NOT_APPLICABLE"


@pytest.mark.parametrize("function", ["REVEAL", "RESOLUTION", "VISUAL_RESET"])
def test_B_K_resolved_search_and_reset_endings(function):
    p = prompt()
    p["creativeEvidence"] = [evidence(p, "ENDING", "DELIVERS_PROMISE", functions=[function])]
    r = review_prompt(p)["planQuality"]
    assert function in r["ending"]["functions"]
    assert r["ending"]["assessment"] == "DELIVERS_PROMISE"


def test_C_D_purposeful_unresolved_and_arbitrary_cut_distinct():
    p = prompt()
    p["creativeEvidence"] = [
        evidence(p, "ENDING", "PURPOSEFUL_UNRESOLVED", functions=["PURPOSEFUL_UNRESOLVED"])
    ]
    assert review_prompt(p)["planQuality"]["ending"]["assessment"] == "PURPOSEFUL_UNRESOLVED"
    p["creativeEvidence"] = [
        evidence(p, "ENDING", "ARBITRARY_TRUNCATION", functions=["PURPOSEFUL_UNRESOLVED"])
    ]
    r = review_prompt(p)["planQuality"]
    assert r["ending"]["sameVideoReplay"] == "UNKNOWN"
    assert r["recommendation"] == "MATERIAL_CONCEPT_REPAIR"


def test_E_F_early_readable_reveal_and_unreadable_problem():
    p = prompt()
    p["creativeEvidence"] = [
        evidence(
            p,
            "OPENING",
            "READABLE_EARLY_DEVELOPMENT",
            visualFocus="READABLE",
            promise="CONCRETE",
            causeAtFrameZero="UNEXPLAINED",
            promiseSupportedAt=0.7,
        )
    ]
    r = review_prompt(p)["planQuality"]["opening"]
    assert r["assessment"] == "READABLE_EARLY_DEVELOPMENT"
    assert r["causeAtFrameZero"] == "UNEXPLAINED"
    p["creativeEvidence"] = [evidence(p, "OPENING", "UNREADABLE", visualFocus="UNREADABLE")]
    assert review_prompt(p)["planQuality"]["recommendation"] == "MATERIAL_CONCEPT_REPAIR"


@pytest.mark.parametrize("mechanism", ["INFORMATIONAL", "RELATIONAL", "RHYTHMIC_VISUAL", "EMOTIONAL"])
def test_G_nonphysical_progression(mechanism):
    p = prompt()
    p["creativeEvidence"] = [evidence(p, "PROGRESSION", "DEVELOPING", mechanisms=[mechanism])]
    assert review_prompt(p)["planQuality"]["progression"]["mechanisms"] == [mechanism]


def test_H_M_high_fidelity_busy_but_weak():
    p, o = qa(progression="WEAK")
    r = review_render(p, o)
    assert r["planFidelity"] == "HIGH"
    assert r["viewerFacingUsability"] == "READABLE_BUT_CREATIVELY_WEAK"
    assert r["editorialRecommendation"] == "EDIT_RECOMMENDED"


@pytest.mark.parametrize("kind", ["CONTACT", "DISAPPEARANCE", "IDENTITY_DRIFT"])
def test_I_J_same_type_contextual_severity(kind):
    p, o = qa(impact="LOCAL_TOLERABLE")
    o["defects"][0]["type"] = kind
    r = review_render(p, o)
    assert r["findings"][0]["severity"] == "WARNING"
    assert r["family8"]["renderAuthorization"]["status"] == "AUTHORIZED"
    o["defects"][0]["impact"] = "CORE_EVENT_LOST"
    r = review_render(p, o)
    assert r["findings"][0]["severity"] == "BLOCKING"
    assert r["family8"]["renderAuthorization"]["status"] == "BLOCKED_CREATIVE_FAILURE"


def test_L_R_partial_fidelity_usable_no_hidden_polish_block():
    p, o = qa(level="POLISH", state="ABSENT", impact="LOCAL_TOLERABLE")
    r = review_render(p, o)
    assert r["planFidelity"] == "PARTIAL"
    assert r["viewerFacingUsability"] == "USABLE"
    assert r["editorialRecommendation"] == "TEST_CANDIDATE"
    assert r["family8"]["renderAuthorization"]["reasons"] == []
    assert r["publicationAuthorized"] is False


def test_N_blind_review_unchanged_by_views():
    p = prompt()
    p["views"] = 500
    r = review_prompt(p)
    p["views"] = 100000
    assert review_prompt(p) == r
    p, o = qa(impact="LOCAL_TOLERABLE")
    o["views"] = 500
    r = review_render(p, o)
    o["views"] = 100000
    assert review_render(p, o) == r


def test_O_new_soap_no_audience_failure():
    r = review_prompt(prompt("0-6 SEC\nKiko watches the soap escape again."))
    assert r["audienceOutcome"]["status"] == "NOT_JOINED"
    assert r["planQuality"]["status"] != "FAIL"


def test_P_missing_source_video_sparse_contact_unknown():
    assert review_prompt(prompt("Unspecified idea."))["planQuality"]["status"] == "UNKNOWN"
    p, o = qa(impact="CORE_EVENT_LOST", basis="SAMPLED_STILLS")
    r = review_render(p, o)
    assert r["viewerFacingUsability"] == "UNKNOWN"
    assert r["findings"][0]["severity"] == "UNKNOWN"
    o.pop("assetHash")
    assert review_render(p, o)["editorialRecommendation"] == "INSUFFICIENT_EVIDENCE"


def test_Q_specialists_and_speculation_not_universal_blockers():
    r = review_prompt(prompt("0-6 SEC\nLuca lifts the ball while Zipo waves."))
    assert r["executionReview"]["status"] == "REWRITE"
    assert not any(x["source"] == "EXECUTION_REVIEW" for x in r["family8"]["renderAuthorization"]["reasons"])
    assert r["executionRisk"]["findings"][0]["severity"] == "WARNING"
    assert r["applicability"]["ONE_CHARACTER_ONE_OBJECT"]["status"] == "NOT_APPLICABLE"


@pytest.mark.parametrize("impact", ["SAFETY_FAILURE", "COHERENCE_DESTROYED"])
def test_S_genuine_blocker_not_neutralized_by_views(impact):
    p, o = qa(impact=impact)
    o["views"] = 100000
    assert review_render(p, o)["family8"]["renderAuthorization"]["status"] == "BLOCKED_CREATIVE_FAILURE"


@pytest.mark.parametrize(
    "key,value",
    [
        ("prompt", "Changed"),
        ("references", [{"sha256": "b" * 64}]),
        ("generator", "SEEDANCE_2_0"),
        ("settings", {"resolution": "720p"}),
        ("intentRequirements", [{"id": "different"}]),
    ],
)
def test_T_changed_binding(key, value):
    p = prompt()
    assert binding_fingerprint(p) != binding_fingerprint({**p, key: value})


def test_intent_source_bound_cannot_redefine_after_render():
    p = prompt()
    q = "The missing shoe is revealed under the cap."
    s = p["prompt"].index(q)
    p["intentRequirements"] = [
        {
            "id": "reveal",
            "level": "ESSENTIAL",
            "sourceSpan": [s, s + len(q)],
            "sourceQuote": q,
            "eventIds": ["source_2"],
        }
    ]
    assert review_prompt(p)["intentRequirements"][0]["status"] == "SOURCE_SUPPORTED"
    p["intentRequirements"][0]["sourceQuote"] = "Invented"
    assert review_prompt(p)["intentRequirements"][0]["status"] == "UNKNOWN"
    plan, o = qa()
    o["events"][0]["state"] = "ABSENT"
    o["intentRequirements"] = []
    assert review_render(plan, o)["editorialRecommendation"] == "UNUSABLE_CONFIRMED_BLOCKER"


def test_API_dimensions_and_invalid_source_fail_closed():
    from app.workflow.api import ReviewRequest

    p = prompt()
    p["creativeEvidence"] = [
        {"dimension": "PROGRESSION", "assessment": "DEVELOPING", "sourceSpan": [0, 3], "sourceQuote": "fake"}
    ]
    r = review_prompt(ReviewRequest(**p).model_dump())
    assert len(r["reviewDimensions"]) == 4
    assert r["planQuality"]["progression"]["assessment"] == "UNKNOWN"
    assert any(
        x["source"] == "INTENT_SOURCE_INTEGRITY" for x in r["family8"]["renderAuthorization"]["reasons"]
    )


def test_runtime_authorization_does_not_retain_speculative_critic_block():
    import json
    from pathlib import Path

    from app.workflow.review import sha256

    p = prompt("0-6 SEC\nLuca balances the ball while Zipo waves.")
    p.update(
        generator="SEEDANCE_2_0_MINI",
        settings={
            "mode": "image2video",
            "aspectRatio": "9:16",
            "resolution": "480p",
            "startFrame": {
                "type": "image",
                "id": "frame.png",
                "url": "https://example.test/frame.png",
                "label": "frame",
            },
        },
        references=[
            {"kind": "CHARACTER", "character": name, "status": "VERIFIED", "sha256": "a" * 64}
            for name in ["Luca", "Zipo"]
        ]
        + [{"kind": "FIRST_FRAME", "relativePath": "frame.png", "status": "VERIFIED", "sha256": "b" * 64}],
        authorizationEvidence={
            "renderAuthorization": "AUTHORIZED",
            "promptSha256": sha256(p["prompt"]),
            "finalVideoEligible": True,
            "independentRevalidationId": "independent",
            "fresh": True,
            "visualEvidence": {"firstFrame": {"status": "PASS", "assetSha256": "b" * 64}},
        },
    )
    registry = json.loads(
        (Path(__file__).parents[2] / "data/workflow/provider-capabilities.json").read_text()
    )["models"]
    r = review_prompt(p, registry)
    assert r["executionReview"]["status"] == "REWRITE"
    assert r["family8"]["renderAuthorization"] == {"status": "AUTHORIZED", "reasons": []}


def test_full_rerender_requires_grounded_essential_benefit_and_smaller_intervention_reason():
    p, o = qa(impact="CORE_EVENT_LOST")
    d = o["defects"][0]
    o["repairProposal"] = {
        **d,
        "request": "FULL_RERENDER",
        "requirementId": "main",
        "expectedEssentialBenefit": "Restore promised reveal",
        "defectAddressed": "Missing core reveal",
        "whySmallerInsufficient": "No existing clip contains the essential reveal; trim would remove it",
        "remainingUncertainty": "Future generator execution is unverified",
    }
    r = review_render(p, o)
    assert r["editorialRecommendation"] == "RERENDER_MATERIALLY_JUSTIFIED"
    assert r["family8"]["renderAuthorization"]["status"] == "BLOCKED_CREATIVE_FAILURE"
    o["repairProposal"].pop("whySmallerInsufficient")
    assert review_render(p, o)["editorialRecommendation"] == "UNUSABLE_CONFIRMED_BLOCKER"


def test_actual_event_can_render_earlier_without_becoming_absent():
    p, o = qa()
    p["events"][0].update(start=17, end=22)
    r = review_render(p, o)
    assert r["events"][0]["status"] == "PRESENT"
    assert r["planFidelity"] == "PARTIAL"
    assert r["editorialRecommendation"] == "TEST_CANDIDATE"


def test_local_repair_cannot_silently_remove_essential_intent():
    from app.workflow.repair import repair_prompt

    p = prompt()
    q = "shoe"
    start = p["prompt"].index(q)
    p["protectedIntent"] = ["Luca"]
    p["intentRequirements"] = [{"id": "shoe", "level": "ESSENTIAL", "sourceQuote": q}]
    with pytest.raises(ValueError, match="essential intent"):
        repair_prompt(p, [{"start": start, "end": start + len(q), "replacement": "hat"}])


def test_dense_static_frames_support_readable_pose_variation_not_motion_claim():
    p, o = qa(impact="LOCAL_TOLERABLE", basis="SAMPLED_STILLS")
    o["defects"][0].update(evidenceBasis="DENSE_LOCAL_FRAMES", requiresMotion=False)
    r = review_render(p, o)
    assert r["findings"][0]["severity"] == "WARNING"
    assert r["editorialRecommendation"] == "INSUFFICIENT_EVIDENCE"
    o["defects"][0]["requiresMotion"] = True
    assert review_render(p, o)["findings"][0]["severity"] == "UNKNOWN"


def test_exact_first_frame_readability_is_not_motion_or_authorization_proof():
    p, o = qa(basis="SAMPLED_STILLS")
    o["experience"]["openingFrame"] = {
        "value": "READABLE",
        "start": 0,
        "end": 0,
        "evidenceBasis": "DENSE_LOCAL_FRAMES",
        "requiresMotion": False,
        "observed": "Readable exact first frame",
        "reference": "synthetic:clip:0",
        "confidence": "MEDIUM",
    }
    r = review_render(p, o)
    assert r["actualFirstFrame"]["status"] == "OBSERVED"
    assert r["actualFirstFrame"]["canonicalAuthorizationGate"] is False
    assert r["actualOpeningVideo"]["status"] == "UNKNOWN"
    assert r["editorialRecommendation"] == "INSUFFICIENT_EVIDENCE"
