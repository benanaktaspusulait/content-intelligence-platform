from unittest.mock import Mock, patch

from app.semantic_evidence import analyse_semantic_video


def _frames() -> dict:
    return {
        "assetHash": "asset-1",
        "version": "semantic-frame-selection-v2",
        "selectedFrames": [
            {"timestampSeconds": 0.0, "frameAvailable": True, "framePath": "/tmp/frame.jpg"}
        ],
    }


def _completed_evidence() -> dict:
    return {
        "status": "COMPLETED",
        "assetHash": "asset-1",
        "schemaVersion": "semantic-evidence-v1",
        "frameSelection": _frames(),
        "provenance": {"requestId": "resp-test", "provider": "openai"},
        "opening": {"semanticHookReadable": True},
    }


def test_valid_semantic_evidence_is_reused_without_provider_call() -> None:
    with patch("app.semantic_evidence.get_provider") as provider:
        result = analyse_semantic_video(_frames(), cached_evidence=_completed_evidence(), semantic_requested=True)

    assert result["status"] == "CACHE_HIT"
    assert result["provenance"]["providerCallCount"] == 0
    provider.assert_not_called()


def test_requested_semantic_provider_configuration_failure_is_explicit() -> None:
    provider = Mock(side_effect=ValueError("OPENAI_API_KEY not set"))
    with patch("app.semantic_evidence.get_provider", provider), patch.dict(
        "os.environ", {"POMPOM_SEMANTIC_ENABLED": "false", "SEMANTIC_VIDEO_AI_ENABLED": "false"}
    ):
        result = analyse_semantic_video(_frames(), semantic_requested=True)

    assert result["status"] == "NOT_CONFIGURED"
    assert result["limitations"] == ["Semantic provider is not configured."]
