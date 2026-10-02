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
