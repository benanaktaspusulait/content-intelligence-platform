from app.semantic_quality_gate import assess_semantic_evidence
from app.semantic_routing import SemanticModelRoutingPolicy
from app.semantic_fusion import fuse_canonical_assessments


def test_quality_gate_does_not_fallback_for_honest_weak_payoff() -> None:
    result = assess_semantic_evidence(
        {
            "schemaVersion": "semantic-evidence-v1",
            "semanticCoverage": "FULL",
            "confidence": 0.92,
            "characters": [{"canonicalName": "UNKNOWN", "present": True}],
            "opening": {"summary": "A child stands beside a box"},
            "beats": [{"startSeconds": 0, "endSeconds": 2}],
            "ending": {"status": "OBSERVED", "summary": "The child remains beside the box"},
            "payoff": {"status": "NOT_ESTABLISHED"},
            "loop": {"status": "WEAK"},
        },
        8,
    )
    assert result["qualityStatus"] == "SUFFICIENT"
    assert result["qualityReasons"] == []


def test_quality_gate_marks_missing_evidence_insufficient() -> None:
    result = assess_semantic_evidence({"semanticCoverage": "NONE", "confidence": None}, 2)
    assert result["qualityStatus"] == "INSUFFICIENT"
    assert "FRAME_COVERAGE_INSUFFICIENT" in result["qualityReasons"]


def test_routing_policy_is_configurable(monkeypatch) -> None:
    monkeypatch.setenv("POMPOM_SEMANTIC_PROVIDER", "openai")
    monkeypatch.setenv("SEMANTIC_PRIMARY_MODEL", "cheap-model")
    monkeypatch.setenv("SEMANTIC_FALLBACK_MODEL", "strong-model")
    monkeypatch.setenv("SEMANTIC_ROUTING_MODE", "PRIMARY_WITH_FALLBACK")
    monkeypatch.setenv("SEMANTIC_FALLBACK_ENABLED", "true")
    policy = SemanticModelRoutingPolicy.from_environment()
    assert policy.primary.model == "cheap-model"
    assert policy.fallback is not None
    assert policy.fallback.model == "strong-model"


def test_fusion_consumes_semantic_hook_payoff_loop_without_model_call() -> None:
    result = fuse_canonical_assessments(
        {
            "hook": {"status": "MODERATE", "visualOpeningActivity": 0.22},
            "payoff": {"motionRebound": "STRONG"},
            "loop": {"visualEndpointSimilarity": 0.91, "overall": "STRONG"},
            "temporalActivityEvents": [{"eventType": "LOCAL_ACTIVITY_DIP", "startSeconds": 7.5, "endSeconds": 9.1}],
        },
        {
            "status": "COMPLETED",
            "provenance": {"requestId": "persisted"},
            "opening": {"semanticHookReadable": True, "expressionReadable": True},
            "payoff": {"status": "OBSERVED_WITH_PARTIAL_TIMING", "confidence": 0.9},
            "loop": {"status": "PARTIAL"},
            "beats": [{"startSeconds": 7.4, "endSeconds": 9.2}],
        },
    )
    assert result["hook"]["strength"] == "MODERATE"
    assert result["payoff"]["semanticStatus"] == "OBSERVED_WITH_PARTIAL_TIMING"
    assert result["loop"]["semanticEvidence"] == "PARTIAL"
    assert result["temporalStructure"]["events"][0]["semanticContextAvailable"] is True
