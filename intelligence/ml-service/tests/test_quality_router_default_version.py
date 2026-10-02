"""Confirms the quality API's ruleset_version defaults to the pinned stable
version (1.0), not an auto-resolved "latest" semver, so that RULESET_1.1.yaml
existing on disk never silently changes behavior for a caller that omits
ruleset_version. See the final whole-branch review finding (Critical) in
docs/superpowers/plans/2026-10-02-creative-intelligence-qc-ruleset-1.1.md,
Task 12, for the full rationale.
"""

from app.api.quality import AutoFixRequest, ValidateRequest


def test_validate_request_defaults_to_pinned_1_0_not_latest() -> None:
    request = ValidateRequest(prompt="x" * 100)
    assert request.ruleset_version == "1.0"


def test_autofix_request_defaults_to_pinned_1_0_not_latest() -> None:
    request = AutoFixRequest(prompt="x" * 100)
    assert request.ruleset_version == "1.0"


def test_validate_request_still_accepts_explicit_1_1() -> None:
    """1.1 remains fully usable — this is an opt-in change, not a removal."""
    request = ValidateRequest(prompt="x" * 100, ruleset_version="1.1")
    assert request.ruleset_version == "1.1"


def test_validate_request_still_accepts_explicit_latest() -> None:
    """A caller who explicitly wants newest-on-disk semver can still ask for
    it by name — only the unspecified-default behavior changed."""
    request = ValidateRequest(prompt="x" * 100, ruleset_version="latest")
    assert request.ruleset_version == "latest"
