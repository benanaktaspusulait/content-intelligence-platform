"""Tests for app.llm.semantic_checks.

Every test mocks app.llm.semantic_checks.get_provider directly — no real LLM
API call is made, matching the existing CharacterVerifier test convention.
"""

import json
from unittest.mock import Mock, patch

import pytest

from app.llm.semantic_checks import (
    SemanticCheckServiceError,
    check_twist_matches_rule,
    count_independent_mechanics,
    find_duplicate_strategy_pairs,
)


class TestFindDuplicateStrategyPairs:
    def test_returns_empty_list_when_llm_reports_no_duplicates(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.return_value = json.dumps({"duplicate_pairs": []})

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            result = find_duplicate_strategy_pairs(
                [
                    {"primaryVerb": "CATCH", "action": "catches the cup", "consequence": "cup stops"},
                    {"primaryVerb": "BLOCK", "action": "blocks with a book", "consequence": "cup redirects"},
                ]
            )

        assert result == []

    def test_returns_flagged_pairs_when_llm_reports_duplicates(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.return_value = json.dumps({"duplicate_pairs": [[0, 2]]})

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            result = find_duplicate_strategy_pairs(
                [
                    {"primaryVerb": "GRAB", "action": "grabs the cup", "consequence": "cup stops"},
                    {"primaryVerb": "BLOCK", "action": "blocks with a book", "consequence": "cup redirects"},
                    {"primaryVerb": "YANK", "action": "yanks the cup back", "consequence": "cup stops"},
                ]
            )

        assert result == [(0, 2)]

    def test_raises_service_error_on_unparseable_response(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.return_value = "not json at all"

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                find_duplicate_strategy_pairs(
                    [
                        {"primaryVerb": "GRAB", "action": "grabs", "consequence": "stops"},
                        {"primaryVerb": "BLOCK", "action": "blocks", "consequence": "redirects"},
                    ]
                )

    def test_parses_response_wrapped_in_markdown_code_block(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.return_value = '```json\n{"duplicate_pairs": [[0, 1]]}\n```'

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            result = find_duplicate_strategy_pairs(
                [
                    {"primaryVerb": "GRAB", "action": "grabs", "consequence": "stops"},
                    {"primaryVerb": "YANK", "action": "yanks", "consequence": "stops"},
                ]
            )

        assert result == [(0, 1)]

    def test_single_attempt_short_circuits_without_calling_llm(self) -> None:
        mock_llm = Mock()

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm) as mock_get:
            result = find_duplicate_strategy_pairs(
                [{"primaryVerb": "CATCH", "action": "catches", "consequence": "stops"}]
            )

        assert result == []
        mock_get.assert_not_called()


class TestCheckTwistMatchesRule:
    def test_returns_true_with_reasoning_when_llm_confirms_match(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.return_value = json.dumps(
            {"matches_rule": True, "reasoning": "The twist is a larger consequence of the same rug rule."}
        )

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            matches, reasoning = check_twist_matches_rule(
                physical_rule="Anything placed on the rug slides toward the edge.",
                twist_description="The whole rug slides out of the room with Mimi still on it.",
            )

        assert matches is True
        assert "rule" in reasoning.lower()

    def test_returns_false_when_llm_reports_mismatch(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.return_value = json.dumps(
            {"matches_rule": False, "reasoning": "An elephant appearing is unrelated to the rug rule."}
        )

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            matches, reasoning = check_twist_matches_rule(
                physical_rule="Anything placed on the rug slides toward the edge.",
                twist_description="An elephant appears out of nowhere.",
            )

        assert matches is False

    def test_raises_service_error_on_missing_field(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.return_value = json.dumps({"matches_rule": True})  # missing "reasoning"

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                check_twist_matches_rule(physical_rule="rule", twist_description="twist")


class TestMissingCredentialsFailClosed:
    """get_provider() (and provider __init__) raise a bare ValueError when
    credentials are missing (e.g. OPENAI_API_KEY not set). Both entry points
    must convert that into a SemanticCheckServiceError, not let it propagate
    as an unhandled exception that would crash the whole rule evaluation."""

    def test_find_duplicate_strategy_pairs_converts_missing_credentials_error(self) -> None:
        with patch("app.llm.semantic_checks.get_provider", side_effect=ValueError("OPENAI_API_KEY not set")):
            with pytest.raises(SemanticCheckServiceError):
                find_duplicate_strategy_pairs(
                    [
                        {"primaryVerb": "GRAB", "action": "grabs", "consequence": "stops"},
                        {"primaryVerb": "BLOCK", "action": "blocks", "consequence": "redirects"},
                    ]
                )

    def test_check_twist_matches_rule_converts_missing_credentials_error(self) -> None:
        with patch("app.llm.semantic_checks.get_provider", side_effect=ValueError("OPENAI_API_KEY not set")):
            with pytest.raises(SemanticCheckServiceError):
                check_twist_matches_rule(physical_rule="rule", twist_description="twist")


class TestCountIndependentMechanics:
    def test_returns_one_when_llm_reports_single_mechanic(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.return_value = json.dumps(
            {
                "mechanic_count": 1,
                "reasoning": "All consequences are escalating depths of the same puddle-contact rule.",
            }
        )

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            count, reasoning = count_independent_mechanics(
                physical_rule="Touching the puddle increases its depth.",
                beat_descriptions=[
                    "toe touches puddle, ankle-deep",
                    "foot touches puddle, knee-deep",
                    "both feet touch puddle, waist-deep",
                ],
            )

        assert count == 1
        assert "same" in reasoning.lower() or "escalat" in reasoning.lower()

    def test_returns_two_when_llm_reports_second_independent_mechanic(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.return_value = json.dumps(
            {
                "mechanic_count": 2,
                "reasoning": "The puddle deepening is one rule; the puddle chasing the character "
                "autonomously is a second, independent rule.",
            }
        )

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            count, reasoning = count_independent_mechanics(
                physical_rule="Touching the puddle increases its depth.",
                beat_descriptions=[
                    "toe touches puddle, ankle-deep",
                    "puddle grows legs and chases the character",
                ],
            )

        assert count == 2
        assert "second" in reasoning.lower() or "independent" in reasoning.lower()

    def test_raises_service_error_on_missing_field(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.return_value = json.dumps({"mechanic_count": 1})  # missing "reasoning"

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                count_independent_mechanics(physical_rule="rule", beat_descriptions=["beat one", "beat two"])

    def test_raises_service_error_on_non_integer_count(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.return_value = json.dumps({"mechanic_count": "one", "reasoning": "test"})

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                count_independent_mechanics(physical_rule="rule", beat_descriptions=["beat one", "beat two"])

    def test_raises_service_error_on_bool_count(self) -> None:
        """bool is a subclass of int in Python; a hallucinated true/false must not
        silently pass through as mechanic_count=1/0."""
        mock_llm = Mock()
        mock_llm.complete.return_value = json.dumps({"mechanic_count": True, "reasoning": "test"})

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                count_independent_mechanics(physical_rule="rule", beat_descriptions=["beat one", "beat two"])

    def test_raises_service_error_on_count_below_one(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.return_value = json.dumps({"mechanic_count": 0, "reasoning": "test"})

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                count_independent_mechanics(physical_rule="rule", beat_descriptions=["beat one", "beat two"])

    def test_raises_service_error_on_llm_provider_unavailable(self) -> None:
        with patch("app.llm.semantic_checks.get_provider", side_effect=ValueError("OPENAI_API_KEY not set")):
            with pytest.raises(SemanticCheckServiceError):
                count_independent_mechanics(physical_rule="rule", beat_descriptions=["beat one", "beat two"])

    def test_short_circuits_to_one_without_calling_llm_when_fewer_than_two_beats(self) -> None:
        mock_llm = Mock()

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm) as mock_get_provider:
            count, reasoning = count_independent_mechanics(
                physical_rule="rule", beat_descriptions=["only one beat"]
            )

        assert count == 1
        assert reasoning  # non-empty, explains the short-circuit
        mock_get_provider.assert_not_called()
        mock_llm.complete.assert_not_called()

    def test_short_circuits_to_one_without_calling_llm_when_zero_beats(self) -> None:
        mock_llm = Mock()

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm) as mock_get_provider:
            count, reasoning = count_independent_mechanics(physical_rule="rule", beat_descriptions=[])

        assert count == 1
        assert reasoning
        mock_get_provider.assert_not_called()
        mock_llm.complete.assert_not_called()


class TestLlmRuntimeFailuresNormalizeToServiceError:
    def test_find_duplicate_strategy_pairs_wraps_timeout_error(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.side_effect = TimeoutError("request timed out")

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                find_duplicate_strategy_pairs(
                    [
                        {"primaryVerb": "PUSH", "action": "a", "consequence": "b"},
                        {"primaryVerb": "PULL", "action": "c", "consequence": "d"},
                    ]
                )

    def test_find_duplicate_strategy_pairs_wraps_generic_runtime_error(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.side_effect = RuntimeError("SDK internal error")

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                find_duplicate_strategy_pairs(
                    [
                        {"primaryVerb": "PUSH", "action": "a", "consequence": "b"},
                        {"primaryVerb": "PULL", "action": "c", "consequence": "d"},
                    ]
                )

    def test_check_twist_matches_rule_wraps_network_error(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.side_effect = ConnectionError("network unreachable")

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                check_twist_matches_rule(physical_rule="rule", twist_description="twist")

    def test_count_independent_mechanics_wraps_timeout_error(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.side_effect = TimeoutError("request timed out")

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                count_independent_mechanics(physical_rule="rule", beat_descriptions=["beat one", "beat two"])

    def test_service_error_message_does_not_leak_raw_exception_type_only(self) -> None:
        """The wrapped error's message must be safe/diagnostic -- it already
        is, since SemanticCheckServiceError just carries str(original_error);
        this test documents that no API key or secret-shaped string from a
        provider's internal error ever appears literally in the raised
        message when it wasn't in the original exception's str() already
        (we are not newly adding risk here, just confirming no masking is
        accidentally stripping the diagnostic value either)."""
        mock_llm = Mock()
        mock_llm.complete.side_effect = RuntimeError("provider said: invalid request")

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            try:
                check_twist_matches_rule(physical_rule="rule", twist_description="twist")
            except SemanticCheckServiceError as e:
                assert "invalid request" in str(e)
