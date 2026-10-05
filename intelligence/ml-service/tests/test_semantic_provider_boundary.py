from types import SimpleNamespace

from app.llm.openai_provider import OpenAIProvider
from app.semantic_provider import SemanticAnalysisRequest, SemanticFrame


class _FakeResponses:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            id="req_test",
            output_text='{"semanticCoverage":"PARTIAL"}',
            usage=SimpleNamespace(input_tokens=12, output_tokens=4),
        )


def test_openai_adapter_uses_responses_api_and_selected_images_only(tmp_path) -> None:
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"jpeg-bytes")
    fake = _FakeResponses()
    provider = object.__new__(OpenAIProvider)
    provider.model = "configured-vlm"
    provider.client = SimpleNamespace(responses=fake)

    result = provider.analyze(SemanticAnalysisRequest(
        asset_hash="asset-1",
        duration_seconds=15.0,
        frames=(SemanticFrame(0.5, "OPENING_ANCHOR", str(frame)),),
        known_characters=("Kiko",),
        analysis_requirements="semanticCoverage",
    ))

    request = fake.calls[0]
    assert result.provider == "openai"
    assert result.model == "configured-vlm"
    assert "video" not in str(request).lower()
    assert request["model"] == "configured-vlm"
    assert request["text"]["format"]["type"] == "json_object"
    assert request["input"][1]["content"][1]["type"] == "input_image"
