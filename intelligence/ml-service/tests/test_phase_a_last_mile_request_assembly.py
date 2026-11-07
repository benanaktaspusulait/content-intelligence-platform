"""Offline request-path checks for legacy and diversity-aware Phase A."""
from copy import deepcopy
import importlib.util
import json
import pathlib

import httpx
import pytest
from openai import OpenAI as RealOpenAI

from app.workflow import creative_provider_profiles as provider_module
from app.workflow import semantic_compact_1_probe_v1 as bounded_module
from app.workflow.concept_fingerprint import digest
from app.workflow.net_new_novelty import context_record, request_message

ROOT = pathlib.Path(__file__).resolve().parents[3]
OLD_RESPONSE = ROOT / "intelligence/docs/net-new-generation-v1/runs/net-new-v1-20261102-001/phase-a/response.txt"
PREPARED_REQUEST = ROOT / "intelligence/docs/net-new-generation-v1/prepared-next-phase-a/request-preview.json"
PREPARED_RUN_ID = "net-new-v1-20261102-post-kiko-rejection-001"


def load_runner():
    path = ROOT / "intelligence/scripts/run-net-new-two-stage-v1.py"
    spec = importlib.util.spec_from_file_location("phase_a_assembly_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_openai(monkeypatch, request_bodies):
    def transport(request):
        request_bodies.append(json.loads(request.content))
        body = {
            "id": "chatcmpl-offline-assembly-test", "object": "chat.completion",
            "created": 1793650000, "model": "gpt-6.1-sol",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": OLD_RESPONSE.read_text()}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
        }
        return httpx.Response(200, json=body, request=request)

    def local_client(**kwargs):
        # MockTransport services every request locally; no socket/network is used.
        local_http = httpx.Client(timeout=kwargs["timeout"], transport=httpx.MockTransport(transport))
        return RealOpenAI(api_key=kwargs["api_key"], base_url=kwargs["base_url"],
                          timeout=kwargs["timeout"], max_retries=kwargs["max_retries"],
                          http_client=local_http)

    monkeypatch.setattr(provider_module, "OpenAI", local_client)


def make_spec():
    runner = load_runner()
    stage, config, cast, profile = runner.request_context()
    spec = stage.request_spec(config, cast, profile, "A")
    ctx = context_record()
    spec["arguments"]["messages"].append(request_message(ctx))
    spec["noveltyExclusionContext"] = ctx
    return runner, profile, spec, ctx


def test_runner_authorization_to_fake_http_transport_preserves_three_messages(tmp_path, monkeypatch):
    runner, profile, expected, ctx = make_spec()
    calls = []
    fake_openai(monkeypatch, calls)
    monkeypatch.setenv("POMPOM_OFFLINE_MODE", "false")
    monkeypatch.setenv("POMPOM_EXTERNAL_AI_AUTHORIZED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fake-key")
    monkeypatch.setattr(runner, "RUNS", tmp_path / "runs")

    def local_bounded(path, selected, spec):
        bounded_module.worker(path, selected, spec)
        return json.loads((pathlib.Path(path) / "worker-result.json").read_text())

    monkeypatch.setattr(bounded_module, "bounded", local_bounded)
    run_id = "net-new-v1-offline-three-message"
    auth_dir = tmp_path / "auth"
    auth_dir.mkdir()
    auth = auth_dir / "phase-a.txt"
    auth.write_text(f"AUTHORIZE_PHASE_A:{run_id}:MAX_PROVIDER_REQUESTS=1\n")
    runner.phase_a(run_id, runner.RUNS / run_id, auth)

    run = runner.RUNS / run_id
    saved = json.loads((run / "phase-a/request-before-sdk.json").read_text())["arguments"]
    last = json.loads((run / "phase-a/last-mile-sdk-request.json").read_text())
    assert len(saved["messages"]) == 3
    assert last == saved == expected["arguments"]
    assert digest(last) == digest(saved)
    sdk_receipt = json.loads((run / "phase-a/sdk-request-forwarded.json").read_text())
    http_receipt = json.loads((run / "phase-a/http-request-started.json").read_text())
    assert sdk_receipt["requestSha256"] == http_receipt["bodySha256"] == digest(saved)
    assert calls == [saved]
    assert calls[0]["messages"][2] == request_message(ctx)
    assert json.loads(calls[0]["messages"][2]["content"])["historicalExclusions"][0]["conceptId"] == "mimi-rolling-pin-dough-wall"
    result = json.loads((run / "phase-a/result.json").read_text())
    assert result["status"] == "COMPLETED"
    assert result["SDKRequestsForwarded"] == result["HTTPRequestsObserved"] == 1
    assert result["retries"] == result["sdkRetries"] == result["fallbacks"] == 0
    assert result["renders"] == 0
    assert not (run / "phase-b").exists()


def test_prepared_two_exclusion_context_is_hash_pinned_and_bound_to_request():
    runner, _, spec, _ = make_spec()
    spec["arguments"]["messages"].pop()  # Prepared path starts from the existing two-message accepted request.
    context = runner.load_prepared_phase_a(spec, PREPARED_RUN_ID, PREPARED_REQUEST)
    preview = json.loads(PREPARED_REQUEST.read_text())
    exclusion_message = preview["requestArguments"]["messages"][-1]
    envelope = json.loads(exclusion_message["content"])
    assert [row["conceptId"] for row in context["exclusions"]] == [
        "mimi-rolling-pin-dough-wall", "kiko-watering-can-return-loop"
    ]
    assert [row["conceptId"] for row in envelope["historicalExclusions"]] == [
        "mimi-rolling-pin-dough-wall", "kiko-watering-can-return-loop"
    ]
    assert envelope["contextSha256"] == context["contextSha256"]
    assert spec["arguments"] == preview["requestArguments"]


@pytest.mark.parametrize("mutation", ["missing_exclusion", "modified_exclusion", "wrong_context_hash"])
def test_prepared_exclusion_context_tampering_fails_closed(tmp_path, mutation):
    runner, _, spec, _ = make_spec()
    preview = json.loads(PREPARED_REQUEST.read_text())
    context = json.loads((PREPARED_REQUEST.parent / "historical-exclusion-context.json").read_text())
    if mutation == "missing_exclusion":
        context["exclusions"].pop()
        preview["historicalExclusionContext"] = context
    elif mutation == "modified_exclusion":
        context["exclusions"][1]["mechanic"] += " altered"
        preview["historicalExclusionContext"] = context
    else:
        context["contextSha256"] = "0" * 64
        preview["historicalExclusionContext"] = context
    path = tmp_path / "request-preview.json"
    path.write_text(json.dumps(preview))
    (tmp_path / "historical-exclusion-context.json").write_text(json.dumps(context))
    with pytest.raises(RuntimeError):
        runner.load_prepared_phase_a(spec, PREPARED_RUN_ID, path)


def test_prepared_request_reaches_fake_sdk_exactly_with_both_exclusions(tmp_path, monkeypatch):
    runner, _, _, _ = make_spec()
    expected = json.loads(PREPARED_REQUEST.read_text())
    calls = []
    fake_openai(monkeypatch, calls)
    monkeypatch.setenv("POMPOM_OFFLINE_MODE", "false")
    monkeypatch.setenv("POMPOM_EXTERNAL_AI_AUTHORIZED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fake-key")
    monkeypatch.setattr(runner, "RUNS", tmp_path / "runs")

    def local_bounded(path, selected, spec):
        bounded_module.worker(path, selected, spec)
        return json.loads((pathlib.Path(path) / "worker-result.json").read_text())

    monkeypatch.setattr(bounded_module, "bounded", local_bounded)
    auth = tmp_path / "phase-a.txt"
    auth.write_text(f"AUTHORIZE_PHASE_A:{PREPARED_RUN_ID}:MAX_PROVIDER_REQUESTS=1\n")
    runner.phase_a(PREPARED_RUN_ID, runner.RUNS / PREPARED_RUN_ID, auth, PREPARED_REQUEST)

    run = runner.RUNS / PREPARED_RUN_ID
    saved = json.loads((run / "phase-a/request-before-sdk.json").read_text())["arguments"]
    last = json.loads((run / "phase-a/last-mile-sdk-request.json").read_text())
    assert saved == last == expected["requestArguments"]
    assert calls == [expected["requestArguments"]]
    envelope = json.loads(calls[0]["messages"][-1]["content"])
    assert [row["conceptId"] for row in envelope["historicalExclusions"]] == [
        "mimi-rolling-pin-dough-wall", "kiko-watering-can-return-loop"
    ]
    assert digest(calls[0]) == digest(saved)
    result = json.loads((run / "phase-a/result.json").read_text())
    assert result["retries"] == result["sdkRetries"] == result["fallbacks"] == 0
    assert result["SDKRequestsForwarded"] == result["HTTPRequestsObserved"] == 1
    assert not (run / "phase-b").exists()


def test_prepared_run_without_authorization_never_dispatches(tmp_path, monkeypatch):
    runner, _, _, _ = make_spec()
    monkeypatch.setattr(runner, "RUNS", tmp_path / "runs")
    monkeypatch.setenv("POMPOM_OFFLINE_MODE", "false")
    monkeypatch.setenv("POMPOM_EXTERNAL_AI_AUTHORIZED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fake-key")
    monkeypatch.setattr(runner, "run_once", lambda *a, **k: pytest.fail("dispatch must not occur"))
    with pytest.raises(RuntimeError, match="EXACT_ONE_REQUEST_OPERATOR_AUTHORIZATION_REQUIRED"):
        runner.phase_a(PREPARED_RUN_ID, runner.RUNS / PREPARED_RUN_ID,
                       tmp_path / "missing-auth.txt", PREPARED_REQUEST)
    assert not (runner.RUNS / PREPARED_RUN_ID).exists()


def test_prepared_run_cannot_fall_back_to_legacy_context(tmp_path, monkeypatch):
    runner, _, _, _ = make_spec()
    monkeypatch.setattr(runner, "RUNS", tmp_path / "runs")
    monkeypatch.setenv("POMPOM_OFFLINE_MODE", "false")
    monkeypatch.setenv("POMPOM_EXTERNAL_AI_AUTHORIZED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fake-key")
    run_id = PREPARED_RUN_ID
    auth = tmp_path / "phase-a.txt"
    auth.write_text(f"AUTHORIZE_PHASE_A:{run_id}:MAX_PROVIDER_REQUESTS=1\n")
    with pytest.raises(RuntimeError, match="PREPARED_PHASE_A_REQUEST_REQUIRED_NO_LEGACY_FALLBACK"):
        runner.phase_a(run_id, runner.RUNS / run_id, auth)
    assert not (runner.RUNS / run_id).exists()


@pytest.mark.parametrize("mutation", ["omitted", "modified", "reordered", "duplicated", "wrong_hash", "extra"])
def test_exact_guard_blocks_changed_or_unexpected_messages_before_transport(tmp_path, monkeypatch, mutation):
    runner, profile, spec, _ = make_spec()
    profile["_authorizedRequestArguments"] = deepcopy(spec["arguments"])
    sent = []
    fake_openai(monkeypatch, sent)
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fake-key")
    path = tmp_path / mutation
    path.mkdir()
    original_complete = provider_module.CreativeCapabilityProvider.complete

    def tampered_complete(self, *args, **kwargs):
        body = deepcopy(self.configuration["_authorizedRequestArguments"])
        messages = body["messages"]
        if mutation == "omitted":
            messages.pop()
        elif mutation == "modified":
            messages[2]["content"] += " altered"
        elif mutation == "reordered":
            messages[1], messages[2] = messages[2], messages[1]
        elif mutation == "duplicated":
            messages.append(deepcopy(messages[2]))
        elif mutation == "wrong_hash":
            envelope = json.loads(messages[2]["content"])
            envelope["contextSha256"] = "0" * 64
            messages[2]["content"] = json.dumps(envelope, sort_keys=True, ensure_ascii=False)
        elif mutation == "extra":
            messages.append({"role": "user", "content": "unexpected extra"})
        self.configuration["_authorizedRequestArguments"] = body
        return original_complete(self, *args, **kwargs)

    monkeypatch.setattr(provider_module.CreativeCapabilityProvider, "complete", tampered_complete)
    bounded_module.worker(path, profile, spec)
    result = json.loads((path / "worker-result.json").read_text())
    assert result["status"] == "FAILED"
    assert result["errorClass"] == "ValueError"
    assert any(row["function"] == "exact_guard" for row in result["safeTrace"])
    assert result["SDKRequestsForwarded"] == 0
    assert result["HTTPRequestsObserved"] == 0
    assert sent == []


def test_legacy_two_message_adapter_remains_compatible(monkeypatch):
    captured = []

    def transport(request):
        captured.append(json.loads(request.content))
        body = {"id": "legacy", "object": "chat.completion", "created": 1, "model": "gpt-6.1-sol",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
        return httpx.Response(200, json=body, request=request)

    local_http = httpx.Client(transport=httpx.MockTransport(transport))
    monkeypatch.setattr(provider_module, "OpenAI", lambda **kw: RealOpenAI(
        api_key=kw["api_key"], base_url=kw["base_url"], timeout=kw["timeout"],
        max_retries=kw["max_retries"], http_client=local_http))
    profile = {"provider": "openai", "model": "gpt-6.1-sol", "baseUrl": "https://api.openai.com/v1",
               "responseMode": "json_schema", "tokenParameter": "max_completion_tokens",
               "reasoningEffort": "low", "temperatureSupported": False}
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fake-key")
    provider = provider_module.CreativeCapabilityProvider(profile, 8192, 90)
    provider.response_format = {"type": "json_schema", "json_schema": {"schema": {"type": "object"}}}
    assert provider.complete("legacy payload", system="legacy system") == "ok"
    assert captured[0]["messages"] == [
        {"role": "system", "content": "legacy system"},
        {"role": "user", "content": "legacy payload"},
    ]


@pytest.mark.parametrize("case", ["missing", "wrong_run_id", "provider_disabled", "consumed_run_id"])
def test_runner_authorization_and_consumption_blocks_before_transport(tmp_path, monkeypatch, case):
    runner, _, _, _ = make_spec()
    monkeypatch.setattr(runner, "RUNS", tmp_path / "runs")
    monkeypatch.setenv("POMPOM_OFFLINE_MODE", "false")
    monkeypatch.setenv("POMPOM_EXTERNAL_AI_AUTHORIZED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fake-key")
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("transport must not be reached")

    monkeypatch.setattr(runner, "run_once", forbidden)
    run_id = f"net-new-v1-block-{case}"
    auth = tmp_path / "auth.txt"
    if case != "missing":
        content_run = "net-new-v1-wrong" if case == "wrong_run_id" else run_id
        auth.write_text(f"AUTHORIZE_PHASE_A:{content_run}:MAX_PROVIDER_REQUESTS=1\n")
    if case == "provider_disabled":
        monkeypatch.setenv("POMPOM_EXTERNAL_AI_AUTHORIZED", "false")
    if case == "consumed_run_id":
        (runner.RUNS / run_id).mkdir(parents=True)
    with pytest.raises((RuntimeError, AssertionError)):
        runner.phase_a(run_id, runner.RUNS / run_id, auth)
    assert calls == []
