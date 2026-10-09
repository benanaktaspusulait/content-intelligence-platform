from app.workflow.api import CreativeRoleRequest


def test_story_review_role_is_accepted_by_api_contract():
    request = CreativeRoleRequest(
        role="STORY_REVIEW",
        text="Compare these stories.",
        maxCostUsd=0.25,
        context={"candidates": []},
    )
    assert request.role == "STORY_REVIEW"
