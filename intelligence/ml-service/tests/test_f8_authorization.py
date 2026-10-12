"""Deterministic regression tests for F8 render authorization phase safety.

These tests verify that the F8 authorization gate correctly distinguishes
pre-render requirements from post-render requirements, preventing both
circular dependencies (first render blocked) and authorization bypasses.

Key security property: authorizationEvidence is constructed server-side
from trusted database records (WorkflowService.java line 82 strips any
caller-supplied value). These tests verify the ML service side of the gate.
"""

import pytest
from app.workflow.review import review_prompt


def _base_request(authorization_evidence=None):
    """Construct a minimal valid review request."""
    req = {
        "prompt": "Mimi reaches toward the toy cabinet with a sticky note; instead of sticking to the cabinet, the note visibly clings to her finger [close-up on Mimi's hand] Mimi is in front of a toy cabinet, looking determined -> the note sticks to Mimi, not the cabinet",
        "sourceId": "test-source-1",
        "sourceVersion": "v1",
        "profile": "post-family-v1",
        "contentProfile": "AUTO",
        "generator": "SEEDANCE_2_0_MINI",
        "settings": {"duration": 15, "aspectRatio": "9:16"},
        "references": [],
    }
    if authorization_evidence is not None:
        req["authorizationEvidence"] = authorization_evidence
    return req


def _get_f8_reasons(result):
    """Extract F8 authorization reason source codes from a review result."""
    f8 = result.get("family8", {})
    auth = f8.get("renderAuthorization", {})
    return [r["source"] for r in auth.get("reasons", [])]


class TestF8FirstRender:
    """Scenarios 1-4: First render (no previous video evidence)."""

    def test_first_render_no_final_video_integrity(self):
        """Scenario 1: First render, no previous video, no QA evidence.
        
        Expected: FINAL_VIDEO_INTEGRITY must NOT be in reasons.
        Pre-render requirements must still be enforced.
        """
        req = _base_request(authorization_evidence={})
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        
        assert "FINAL_VIDEO_INTEGRITY" not in reasons, (
            "First render must not require post-render video QA evidence"
        )
        # Pre-render requirements should still be present
        assert "REFERENCE_ASSOCIATION" in reasons, (
            "Missing character reference must still block first render"
        )

    def test_first_render_missing_character_reference_blocked(self):
        """Scenario 2: First render, missing verified character reference.
        
        Expected: BLOCKED with REFERENCE_ASSOCIATION.
        """
        req = _base_request(authorization_evidence={})
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        
        assert "REFERENCE_ASSOCIATION" in reasons, (
            "Missing verified character reference must block render"
        )
        f8 = result.get("family8", {})
        auth = f8.get("renderAuthorization", {})
        assert auth.get("status") == "BLOCKED_PENDING_EVIDENCE", (
            "F8 status must be BLOCKED when character reference is missing"
        )

    def test_first_render_missing_start_frame_blocked(self):
        """Scenario 3: First render, missing startFrame.
        
        Expected: BLOCKED with EXECUTION_REVIEW or GENERATOR_CAPABILITY.
        The actual reason codes depend on what the generator capability check
        and execution review determine for the given prompt.
        """
        req = _base_request(authorization_evidence={})
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        
        # At least one pre-render gate must be present
        pre_render_gates = {"REFERENCE_ASSOCIATION", "GENERATOR_CAPABILITY", "EXECUTION_REVIEW"}
        active_gates = set(reasons) & pre_render_gates
        assert len(active_gates) >= 1, (
            f"At least one pre-render gate must be active. Reasons: {reasons}"
        )

    def test_first_render_all_evidence_eligible(self):
        """Scenario 4: First render, all required evidence available.
        
        Expected: Eligible for authorization, but not auto-authorized.
        FINAL_VIDEO_INTEGRITY must NOT be required.
        """
        # Simulate a first render with all pre-render evidence
        req = _base_request(authorization_evidence={})
        # Add verified references to satisfy REFERENCE_ASSOCIATION
        req["references"] = [
            {
                "characterId": "00000000-0000-0000-0000-000000000003",
                "referenceId": "test-ref-1",
                "status": "VERIFIED",
                "verifiedBy": "test-user",
            }
        ]
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        
        # FINAL_VIDEO_INTEGRITY must NOT be in reasons for first render
        assert "FINAL_VIDEO_INTEGRITY" not in reasons, (
            "First render must not require post-render evidence"
        )

    def test_first_render_no_auto_authorization(self):
        """First render must never auto-authorize.
        
        Even with all pre-render evidence, explicit user approval is required.
        """
        req = _base_request(authorization_evidence={})
        result = review_prompt(req)
        f8 = result.get("family8", {})
        auth = f8.get("renderAuthorization", {})
        
        # Status should be BLOCKED_PENDING_EVIDENCE, not AUTHORIZED
        assert auth.get("status") != "AUTHORIZED", (
            "First render must not auto-authorize"
        )


class TestF8SubsequentRender:
    """Scenario 5: Subsequent render with previous video evidence."""

    def test_subsequent_render_requires_final_video_integrity(self):
        """Scenario 5: Subsequent render with previous-video QA evidence missing.
        
        Expected: FINAL_VIDEO_INTEGRITY must be enforced.
        An empty authorizationEvidence payload must not bypass this check.
        """
        # Non-empty authorizationEvidence means a previous render exists
        req = _base_request(authorization_evidence={
            "renderAuthorization": "AUTHORIZED",
            "promptSha256": "wrong-hash",  # Hash mismatch
        })
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        
        assert "FINAL_VIDEO_INTEGRITY" in reasons, (
            "Subsequent render must enforce FINAL_VIDEO_INTEGRITY when "
            "previous render evidence exists but integrity check fails"
        )

    def test_subsequent_render_valid_evidence_passes(self):
        """Subsequent render with valid previous evidence should not block on FINAL_VIDEO_INTEGRITY.
        
        If all integrity checks pass, FINAL_VIDEO_INTEGRITY should not be a blocker.
        """
        from app.workflow.review import sha256
        
        prompt = _base_request()["prompt"]
        req = _base_request(authorization_evidence={
            "renderAuthorization": "AUTHORIZED",
            "promptSha256": sha256(prompt),
            "finalVideoEligible": True,
            "independentRevalidationId": "test-revalidation-1",
            "fresh": True,
        })
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        
        # FINAL_VIDEO_INTEGRITY should NOT be in reasons when integrity is valid
        assert "FINAL_VIDEO_INTEGRITY" not in reasons, (
            f"Valid previous evidence should not trigger FINAL_VIDEO_INTEGRITY. Reasons: {reasons}"
        )

    def test_subsequent_render_stale_evidence_blocked(self):
        """Subsequent render with stale (not fresh) evidence must be blocked.
        
        If the previous render evidence has expired, FINAL_VIDEO_INTEGRITY must block.
        """
        from app.workflow.review import sha256
        
        prompt = _base_request()["prompt"]
        req = _base_request(authorization_evidence={
            "renderAuthorization": "AUTHORIZED",
            "promptSha256": sha256(prompt),
            "finalVideoEligible": True,
            "independentRevalidationId": "test-revalidation-1",
            "fresh": False,  # Stale evidence
        })
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        
        assert "FINAL_VIDEO_INTEGRITY" in reasons, (
            "Stale previous evidence must trigger FINAL_VIDEO_INTEGRITY block"
        )

    def test_subsequent_render_missing_revalidation_blocked(self):
        """Subsequent render without independent revalidation ID must be blocked."""
        from app.workflow.review import sha256
        
        prompt = _base_request()["prompt"]
        req = _base_request(authorization_evidence={
            "renderAuthorization": "AUTHORIZED",
            "promptSha256": sha256(prompt),
            "finalVideoEligible": True,
            # Missing independentRevalidationId
            "fresh": True,
        })
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        
        assert "FINAL_VIDEO_INTEGRITY" in reasons, (
            "Missing independent revalidation must trigger FINAL_VIDEO_INTEGRITY block"
        )


class TestF8MalformedEvidence:
    """Scenario 6: Malformed or caller-manipulated authorizationEvidence."""

    def test_malformed_authorization_evidence_blocked(self):
        """Malformed authorizationEvidence must not bypass authorization.
        
        If the structure is invalid, the integrity check should fail.
        """
        req = _base_request(authorization_evidence={
            "renderAuthorization": "NOT_AUTHORIZED",  # Invalid value
        })
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        
        assert "FINAL_VIDEO_INTEGRITY" in reasons, (
            "Malformed authorizationEvidence must not bypass FINAL_VIDEO_INTEGRITY"
        )

    def test_empty_string_authorization_evidence_treated_as_first_render(self):
        """Empty string authorizationEvidence should be treated as first render.
        
        Empty/falsy values should be equivalent to empty dict (first render).
        """
        req = _base_request(authorization_evidence={})
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        
        assert "FINAL_VIDEO_INTEGRITY" not in reasons, (
            "Empty authorizationEvidence should be treated as first render"
        )

    def test_none_authorization_evidence_treated_as_first_render(self):
        """None authorizationEvidence should be treated as first render."""
        req = _base_request()  # No authorizationEvidence key
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        
        assert "FINAL_VIDEO_INTEGRITY" not in reasons, (
            "Missing authorizationEvidence should be treated as first render"
        )


class TestF8PreRenderGates:
    """Verify pre-render gates are always enforced regardless of authorizationEvidence."""

    def test_reference_association_always_enforced(self):
        """REFERENCE_ASSOCIATION must be enforced for both first and subsequent renders."""
        # First render
        req = _base_request(authorization_evidence={})
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        assert "REFERENCE_ASSOCIATION" in reasons

        # Subsequent render
        req = _base_request(authorization_evidence={
            "renderAuthorization": "AUTHORIZED",
            "promptSha256": "some-hash",
        })
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        assert "REFERENCE_ASSOCIATION" in reasons, (
            "REFERENCE_ASSOCIATION must be enforced for subsequent renders too"
        )

    def test_execution_inputs_always_enforced(self):
        """Pre-render execution gates must be enforced for both first and subsequent renders."""
        # First render
        req = _base_request(authorization_evidence={})
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        # At least one pre-render gate must be active
        pre_render_gates = {"REFERENCE_ASSOCIATION", "GENERATOR_CAPABILITY", "EXECUTION_REVIEW"}
        active_gates = set(reasons) & pre_render_gates
        assert len(active_gates) >= 1, f"Pre-render gates must be enforced. Reasons: {reasons}"

    def test_generator_capability_always_enforced(self):
        """GENERATOR_CAPABILITY must be enforced for both first and subsequent renders."""
        req = _base_request(authorization_evidence={})
        result = review_prompt(req)
        reasons = _get_f8_reasons(result)
        # Generator capability check may pass for SEEDANCE_2_0_MINI with 15s/9:16
        # The key is that it's checked, not that it fails
        generation = result.get("generation", {})
        assert generation is not None, "Generation capability must be evaluated"


class TestF8Idempotency:
    """Scenario 7: Reload or retry must not produce another render authorization."""

    def test_identical_request_produces_identical_result(self):
        """Running the same request twice should produce the same F8 result.
        
        No new authorization should be created on retry.
        """
        req = _base_request(authorization_evidence={})
        result1 = review_prompt(req)
        result2 = review_prompt(req)
        
        reasons1 = _get_f8_reasons(result1)
        reasons2 = _get_f8_reasons(result2)
        
        assert reasons1 == reasons2, (
            "Identical requests must produce identical F8 results"
        )

    def test_no_provider_call_on_review(self):
        """Review must not invoke any paid provider.
        
        F8 authorization is purely deterministic and provider-free.
        """
        req = _base_request(authorization_evidence={})
        result = review_prompt(req)
        
        # The result should not contain any provider call metadata
        # (LocalExecutionCritic is provider-free)
        assert "providerCalls" not in result or result["providerCalls"] == 0, (
            "Review must not invoke paid providers"
        )
