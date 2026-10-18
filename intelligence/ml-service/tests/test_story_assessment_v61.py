"""Offline gpt-6.1-sol compatibility: actual installed SDK, mocked HTTP only."""

import json
import uuid
from unittest.mock import patch

import httpx
import openai
import pytest
from story_assessment_cases import case_response
from story_experiment_fixture import assessment_inputs

from app.workflow import story_assessment as assessment


def configure(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKFLOW_STORY_REVIEW_MODEL", "gpt-6.1-sol")
    monkeypatch.setenv("WORKFLOW_STORY_REVIEW_INPUT_USD_PER_MILLION", "2")
    monkeypatch.setenv("WORKFLOW_STORY_REVIEW_OUTPUT_USD_PER_MILLION", "10")
    monkeypatch.setenv("WORKFLOW_CREATIVE_ROLES_ENABLED", "true")
    monkeypatch.setenv("CPQ_PILOT_REAL_ENABLED", "true")
    monkeypatch.setenv("POMPOM_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "offline-not-a-credential")
    for key in ("POMPOM_ISOLATED_ACCEPTANCE", "POMPOM_ISOLATED_FIXTURE_DIR", "POMPOM_ISOLATED_FIXTURE_TOKEN"):
        monkeypatch.delenv(key, raising=False)


def test_v61_preview_exact_model_params_scope_and_cost(monkeypatch):
    monkeypatch.setenv("WORKFLOW_STORY_REVIEW_MODEL", "gpt-6.1-sol")
    monkeypatch.setenv("WORKFLOW_STORY_REVIEW_INPUT_USD_PER_MILLION", "2")
    monkeypatch.setenv("WORKFLOW_STORY_REVIEW_OUTPUT_USD_PER_MILLION", "10")
    text, context = assessment_inputs()
    body = assessment.request_body(text, context)
    preview = assessment.preview(text, context)
    assert body["model"] == "gpt-6.1-sol"
    assert body["reasoning_effort"] == "medium"
    assert body["max_completion_tokens"] == 12000
    assert "temperature" not in body and "max_tokens" not in body
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert preview["serializedRequestBytes"] == len(assessment.encoded(body).encode()) <= 24064
    assert preview["maximumInputBytes"] == 24064
    assert preview["maximumCalculatedUsd"] == pytest.approx(
        ((preview["serializedRequestBytes"] + 1000) * 2 + 12000 * 10) / 1_000_000
    )
    assert (
        preview["reasoningEffort"] == "medium"
        and preview["completionTokenParameter"] == "max_completion_tokens"
    )
    assert preview["fullOperationBindingSha256"]
    assert preview["sourceAssessmentScopeSha256"] == preview["scopeSha256"]
    assert preview["timeoutPolicy"] == assessment.TIMEOUT_POLICY


def test_v61_execute_uses_installed_sdk_mock_transport_and_accounts_reasoning(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    text, context = assessment_inputs()
    preview = assessment.preview(text, context)
    preview["maxCostUsd"] = preview["maximumCalculatedUsd"]
    context.update(
        assessmentDispatch=preview, assessmentSpendingAuthorized=True, storyRequestId=str(uuid.uuid4())
    )
    captured = []

    def transport(request):
        body = json.loads(request.content)
        captured.append(body)
        assert request.url == "https://api.openai.com/v1/chat/completions"
        assert request.extensions["timeout"] == {"connect": 5, "pool": 5, "write": 10, "read": 60}
        assert body["model"] == "gpt-6.1-sol"
        assert body["reasoning_effort"] == "medium" and body["max_completion_tokens"] == 12000
        assert "temperature" not in body and "max_tokens" not in body
        assert body["response_format"]["type"] == "json_schema"
        assert body["response_format"]["json_schema"]["strict"] is True
        payload = json.loads(body["messages"][1]["content"])
        content = case_response(payload, "positive")
        return httpx.Response(
            200,
            headers={"x-request-id": "offline-mock-request"},
            json={
                "id": "MOCK_ONLY_v61",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-6.1-sol",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 12000,
                    "completion_tokens": 1800,
                    "total_tokens": 13800,
                    "completion_tokens_details": {"reasoning_tokens": 900},
                },
            },
        )

    def client(**kwargs):
        assert kwargs["max_retries"] == 0
        return openai.OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(transport)))

    with patch("app.llm.openai_provider.OpenAI", side_effect=client):
        receipt = assessment.execute(text, context, preview["maximumCalculatedUsd"])
    assert len(captured) == 1
    assert receipt["processingStatus"] == "INDEPENDENT_REVIEW_COMPLETED"
    assert receipt["modelIdentity"]["verified"] is True
    assert receipt["usage"]["completion_tokens_details"]["reasoning_tokens"] == 900
    assert receipt["actualCostUsd"] == pytest.approx((12000 * 2 + 1800 * 10) / 1_000_000)
    assert receipt["retrySafe"] is False and receipt["assessmentOnly"] is True
    assert receipt["buildPromptAuthorized"] if "buildPromptAuthorized" in receipt else True


def test_v61_incomplete_response_is_rejected_but_usage_is_accounted(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    text, context = assessment_inputs()
    preview = assessment.preview(text, context)
    preview["maxCostUsd"] = preview["maximumCalculatedUsd"]
    context.update(
        assessmentDispatch=preview, assessmentSpendingAuthorized=True, storyRequestId=str(uuid.uuid4())
    )

    def transport(request):
        json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "MOCK_ONLY_length",
                "model": "gpt-6.1-sol",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "{}"}, "finish_reason": "length"}
                ],
                "usage": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 12000,
                    "total_tokens": 13000,
                    "completion_tokens_details": {"reasoning_tokens": 9000},
                },
            },
        )

    def client(**kwargs):
        return openai.OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(transport)))

    with patch("app.llm.openai_provider.OpenAI", side_effect=client):
        receipt = assessment.execute(text, context, preview["maximumCalculatedUsd"])
    assert receipt["processingStatus"] == "LOCALLY_REJECTED"
    assert receipt["modelIdentity"]["verified"] is True
    assert receipt["actualCostUsd"] == pytest.approx((1000 * 2 + 12000 * 10) / 1_000_000)
    assert receipt["retrySafe"] is False
