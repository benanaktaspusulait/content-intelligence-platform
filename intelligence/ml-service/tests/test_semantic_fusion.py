from app.semantic_fusion import fuse_canonical_assessments


def _semantic(status="CACHE_HIT"):
    return {
        "status": status,
        "assetHash": "asset-1",
        "schemaVersion": "semantic-evidence-v1",
        "provenance": {"requestId": "resp-test", "providerCallCount": 0},
        "opening": {"semanticHookReadable": True, "expressionReadable": True},
        "payoff": {
            "status": "completed",
            "payoffDetected": True,
            "stateChangeDetected": True,
            "characterReaction": "joyful surprise",
            "emotionalResolution": "satisfaction",
            "confidence": 0.9,
        },
        "loop": {"status": "consistent", "actionContinuity": True},
        "beats": [{"startSeconds": 0.0, "endSeconds": 1.0}],
    }


def _temporal():
    return {
        "hook": {"visualOpeningActivity": 0.9},
        "payoff": {"motionRebound": "NOT_ESTABLISHED", "visualEndingEmphasis": "AVAILABLE"},
        "loop": {"visualEndpointSimilarity": 0.8472},
        "temporalActivityEvents": [{"startSeconds": 0.0, "endSeconds": 1.0}],
    }


def test_cached_semantic_evidence_recomputes_payoff_loop_and_coverage():
    result = fuse_canonical_assessments(_temporal(), _semantic())

    assert result["semanticEvidenceAvailable"] is True
    assert result["payoff"]["semanticStatus"] == "COMPLETED"
    assert result["payoff"]["strength"] == "STRONG"
    assert result["payoff"]["motionRebound"] == "NOT_ESTABLISHED"
    assert result["loop"]["semanticEvidence"] == "CONSISTENT"
    assert result["loop"]["evidenceStatus"] == "AVAILABLE"
    assert result["coverage"]["missing"] == []
    assert result["semanticEvidenceIdentity"] == "asset-1|semantic-evidence-v1|resp-test"


def test_unavailable_semantic_evidence_does_not_create_false_canonical_coverage():
    result = fuse_canonical_assessments(_temporal(), {"status": "NOT_CONFIGURED"})

    assert result["semanticEvidenceAvailable"] is False
    assert result["payoff"]["evidenceStatus"] == "UNKNOWN"
    assert result["loop"]["evidenceStatus"] == "UNKNOWN"
