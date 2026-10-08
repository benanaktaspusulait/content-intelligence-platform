import json

import pytest

from app.workflow.critic import ProviderExecutionCritic
from app.workflow.repair import repair_prompt
from app.workflow.review import review_prompt


class Critic:
    def __init__(self, output):
        self.output = output

    def complete(self, *args, **kwargs):
        if isinstance(self.output, Exception):
            raise self.output
        return json.dumps(self.output)


def value():
    return {
        "prompt": "0-6 SEC\nLuca pushes the box. CUT.",
        "sourceId": "prompt",
        "sourceVersion": "1",
        "profile": "post-family-v1",
        "settings": {},
        "protectedIntent": ["Luca pushes the box"],
        "references": [],
        "generator": "AUTO",
        "desiredDuration": 6,
        "segments": [],
    }


@pytest.mark.parametrize(
    "output",
    [
        TimeoutError(),
        {"status": "PASS", "visualInspected": True, "findings": []},
        {"status": "REWRITE", "findings": [{"sourceSpan": [0, 2], "sourceQuote": "wrong"}]},
        {"status": "PASS"},
    ],
)
def test_failed_ungrounded_and_false_visual_critics_stay_unknown(output):
    v = value()
    reviewed = review_prompt(v)
    result = ProviderExecutionCritic(Critic(output), "mock-text", "fixture").review(
        v, reviewed["productionEvidence"], reviewed["generation"]
    )
    assert result["status"] == "UNKNOWN"
    assert result["calls"] == 1
    assert result["visualInspected"] is False


def test_general_heuristic_is_not_a_hard_blocker():
    v = value()
    r = review_prompt(v)
    output = {
        "status": "BLOCK",
        "findings": [
            {
                "sourceSpan": [8, 28],
                "sourceQuote": v["prompt"][8:28],
                "riskCategory": "CONTACT",
                "plausibleFailure": "May miss contact",
                "evidenceBasis": "GENERAL_HEURISTIC",
                "confidence": "LOW",
                "smallestChange": "Name the box",
                "altersCreativeIntent": False,
            }
        ],
    }
    assert (
        ProviderExecutionCritic(Critic(output), "mock", "fixture").review(
            v, r["productionEvidence"], r["generation"]
        )["status"]
        == "REWRITE"
    )


def test_minimal_patch_preserves_protected_intent_and_revalidates_final_prompt():
    v = value()
    original = v["prompt"]
    start = original.index("CUT.")
    result = repair_prompt(
        v, [{"start": start, "end": len(original), "replacement": "Hold the resulting pose."}]
    )
    assert result["originalPrompt"] == original
    assert result["finalPrompt"].startswith("0-6 SEC\nLuca pushes the box.")
    assert result["repairPasses"] == 1 and result["verificationPasses"] == 1
    assert result["bindingHash"] != review_prompt(v)["bindingHash"]


def test_core_intent_changes_are_rejected_and_repair_passes_are_bounded():
    v = value()
    with pytest.raises(ValueError, match="protected"):
        repair_prompt(v, [{"start": 8, "end": 28, "replacement": "Kiko runs away."}])
    with pytest.raises(ValueError, match="one repair"):
        repair_prompt({**v, "repairPasses": 1}, [])


def test_unsupported_settings_never_get_substituted():
    v = value()
    v["settings"] = {"mode": "image2video", "resolution": "4K", "aspectRatio": "9:16"}
    caps = {
        "SEEDANCE_2_0_MINI": {
            "apiModelId": "verified-mini",
            "modes": {
                "image2video": {
                    "properties": {
                        "duration": {"minimum": 4, "maximum": 15},
                        "resolution": {"enum": ["720p"]},
                        "aspectRatio": {"enum": ["9:16"]},
                    }
                }
            },
        }
    }
    result = review_prompt(v, caps)
    assert result["generation"]["capabilityStatus"] == "UNSUPPORTED"
    assert result["generation"]["selectedGenerator"] == "SEEDANCE_2_0_MINI"
    assert result["generation"]["supportedRenderDuration"] is None


def test_capability_change_invalidates_binding_even_with_identical_prompt():
    v = value()
    schema = {"properties": {"duration": {"minimum": 4, "maximum": 15}}}
    a = {"SEEDANCE_2_0_MINI": {"modes": {"image2video": schema}, "provenance": {"schemaSha256": "a"}}}
    b = {"SEEDANCE_2_0_MINI": {"modes": {"image2video": schema}, "provenance": {"schemaSha256": "b"}}}
    assert review_prompt(v, a)["bindingHash"] != review_prompt(v, b)["bindingHash"]


def test_default_api_cannot_spend_critic_credits(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.delenv("WORKFLOW_PAID_CRITIC_ENABLED", raising=False)
    assert (
        TestClient(app)
        .post(
            "/api/v1/workflow/critic",
            json={"request": value(), "provider": "deepseek", "model": "configured"},
        )
        .status_code
        == 403
    )


def test_repair_without_reviewed_intent_cannot_rewrite_concept():
    with pytest.raises(ValueError, match="protected"):
        repair_prompt(
            {**value(), "protectedIntent": []}, [{"start": 0, "end": 31, "replacement": "A different story"}]
        )


def test_ordinary_contact_does_not_imply_absurd_physics():
    request = {**value(), "prompt": "0-6 SEC\nLuca catches the ball and places it on the floor."}
    assert review_prompt(request)["routing"]["contentProfile"] == "UNKNOWN"


def test_named_character_reference_cannot_be_replaced_by_unrelated_asset():
    request = {
        **value(),
        "prompt": "CHARACTERS: LUCA and ZIPO.\n0-6 SEC\nLuca meets Zipo.",
        "references": [{"character": "Kiko", "kind": "CHARACTER", "status": "VERIFIED", "sha256": "a" * 64}],
    }
    reasons = review_prompt(request)["family8"]["renderAuthorization"]["reasons"]
    assert any(r["source"] == "REFERENCE_ASSOCIATION" for r in reasons)
