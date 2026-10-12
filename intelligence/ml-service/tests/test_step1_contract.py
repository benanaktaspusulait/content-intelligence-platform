"""Step 1 Input Contract verification — deterministic tests.

These tests verify the exact provider request constructed by the STORY role,
covering inputMode, storyGenerationMode, lockedRequirements and Turkish Unicode.
No paid provider calls are made.
"""
import json
import pytest
from app.workflow.creative_roles import perform_role


class FixtureProvider:
    """Captures the exact (user_json, system_prompt) sent to the provider."""
    def __init__(self, result):
        self.result = result
        self.calls = []

    def complete(self, prompt, system='', temperature=0, image=None):
        self.calls.append((json.loads(prompt), system))
        return json.dumps(self.result)


def _story_fixture(count=3):
    """Return a valid STORY response with `count` distinct alternatives."""
    alternatives = []
    for i in range(1, count + 1):
        alternatives.append({
            'candidateId': f'candidate-{i}',
            'title': f'Alternative {i}',
            'text': f'Distinct story body number {i} with unique events and progression.'
        })
    return {'alternatives': alternatives}


# ──────────────────────────────────────────────
# Scenario 1: IDEA + EXPLORE_DIFFERENT_STORIES
# ──────────────────────────────────────────────

class TestIdeaExploreDifferentStories:
    """Short concept + EXPLORE_DIFFERENT_STORIES should request meaningful diversity."""

    def test_input_mode_reaches_provider(self):
        """inputMode IDEA must be present in the context sent to DeepSeek."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'A bunny discovers a magic box.', context, provider, 'fixture')
        assert len(provider.calls) == 1
        user_json = provider.calls[0][0]
        assert user_json['context']['inputMode'] == 'IDEA'

    def test_strategy_reaches_provider(self):
        """storyGenerationMode must reach the provider context."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'A bunny discovers a magic box.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        assert user_json['context']['storyGenerationMode'] == 'EXPLORE_DIFFERENT_STORIES'

    def test_system_prompt_mentions_input_mode(self):
        """The system prompt must reference inputMode so the provider knows IDEA vs DETAILED_STORY."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'A bunny discovers a magic box.', context, provider, 'fixture')
        system_prompt = provider.calls[0][1]
        assert 'inputMode' in system_prompt
        assert 'IDEA' in system_prompt
        assert 'DETAILED_STORY' in system_prompt

    def test_system_prompt_mentions_locked_requirements(self):
        """The system prompt must explain locked requirements semantics."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'A bunny discovers a magic box.', context, provider, 'fixture')
        system_prompt = provider.calls[0][1]
        assert 'lockedRequirements' in system_prompt
        assert 'PRESERVE_CORE_PREMISE' in system_prompt
        assert 'PRESERVE_KEY_EVENTS' in system_prompt
        assert 'PRESERVE_ENDING' in system_prompt

    def test_explore_strategy_instruction_present(self):
        """System prompt must instruct EXPLORE_DIFFERENT_STORIES to generate different narratives."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'A bunny discovers a magic box.', context, provider, 'fixture')
        system_prompt = provider.calls[0][1]
        assert 'EXPLORE_DIFFERENT_STORIES' in system_prompt

    def test_locked_requirements_passed_to_context(self):
        """Only explicitly selected requirements should be in lockedRequirements."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'A bunny discovers a magic box.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        locked = user_json['context']['lockedRequirements']
        assert locked == ['PRESERVE_CORE_PREMISE']
        assert 'PRESERVE_KEY_EVENTS' not in locked
        assert 'PRESERVE_ENDING' not in locked

    def test_no_silent_locking_of_unselected_requirements(self):
        """Unselected requirements must NOT be silently enforced."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': [],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'A short concept.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        locked = user_json['context']['lockedRequirements']
        assert locked == []

    def test_requested_candidate_count_reaches_provider(self):
        """requestedAlternativeCount must reach the provider."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'A short concept.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        assert user_json['context']['requestedAlternativeCount'] == 3

    def test_source_text_preserved(self):
        """The exact source text must reach the provider unchanged."""
        source = 'A bunny discovers a magic box.'
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', source, context, provider, 'fixture')
        user_json = provider.calls[0][0]
        assert user_json['text'] == source

    def test_no_contradiction_between_system_and_user(self):
        """System prompt and user context must not contradict each other."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'A short concept.', context, provider, 'fixture')
        system_prompt = provider.calls[0][1]
        user_json = provider.calls[0][0]
        # System prompt should mention EXPLORE_DIFFERENT_STORIES
        assert 'EXPLORE_DIFFERENT_STORIES' in system_prompt
        # User context should match
        assert user_json['context']['storyGenerationMode'] == 'EXPLORE_DIFFERENT_STORIES'
        # System prompt should say only present requirements are binding
        assert 'Only the requirements present' in system_prompt or 'do not silently lock' in system_prompt


# ──────────────────────────────────────────────
# Scenario 2: IDEA + IMPROVE_EXISTING_STORY
# ──────────────────────────────────────────────

class TestIdeaImproveExistingStory:
    """Complete Turkish story in IDEA field + IMPROVE_EXISTING_STORY."""

    def test_turkish_text_preserved_unchanged(self):
        """Exact Turkish source text must reach the provider without truncation."""
        source = (
            'Mimi dolabı açar ve yapışkan notlar onu gizli bir haritaya kadar takip eder. '
            'Notlar Miminin yüzüne yapışır, sonra çoğalır ve geri döner. '
            'Mimi dolabın arkasına saklanır ama notlar onu bulur ve tamamen kaplar, '
            'sadece gözleri görünür kalır.'
        )
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', source, context, provider, 'fixture')
        user_json = provider.calls[0][0]
        assert user_json['text'] == source

    def test_turkish_unicode_preserved(self):
        """Turkish Unicode characters (ı, ş, ç, ğ, ö, ü) must survive the pipeline."""
        source = 'Miminin gözleri görünür kalır. Şekil değişir, çok özel.'
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', source, context, provider, 'fixture')
        user_json = provider.calls[0][0]
        assert user_json['text'] == source
        assert 'görünür' in user_json['text']
        assert 'Şekil' in user_json['text']
        assert 'özel' in user_json['text']

    def test_input_mode_is_idea(self):
        """Even with detailed text, inputMode remains IDEA when entered in IDEA field."""
        source = (
            'Mimi dolabı açar ve yapışkan notlar onu gizli bir haritaya kadar takip eder. '
            'Notlar Miminin yüzüne yapışır, sonra çoğalır ve geri döner.'
        )
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', source, context, provider, 'fixture')
        user_json = provider.calls[0][0]
        assert user_json['context']['inputMode'] == 'IDEA'

    def test_strategy_is_improve(self):
        """storyGenerationMode must be IMPROVE_EXISTING_STORY."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Turkish story text.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        assert user_json['context']['storyGenerationMode'] == 'IMPROVE_EXISTING_STORY'

    def test_system_prompt_mentions_improve_mode(self):
        """System prompt must explain IMPROVE_EXISTING_STORY semantics."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Turkish story text.', context, provider, 'fixture')
        system_prompt = provider.calls[0][1]
        assert 'IMPROVE_EXISTING_STORY' in system_prompt

    def test_unselected_preserve_key_events_not_enforced(self):
        """PRESERVE_KEY_EVENTS must NOT be silently locked when not selected."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Turkish story text.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        locked = user_json['context']['lockedRequirements']
        assert 'PRESERVE_KEY_EVENTS' not in locked

    def test_unselected_preserve_ending_not_enforced(self):
        """PRESERVE_ENDING must NOT be silently locked when not selected."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Turkish story text.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        locked = user_json['context']['lockedRequirements']
        assert 'PRESERVE_ENDING' not in locked

    def test_preserve_ending_enabled_is_passed(self):
        """When PRESERVE_ENDING is explicitly selected, it must reach the provider."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE', 'PRESERVE_ENDING'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Turkish story text.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        locked = user_json['context']['lockedRequirements']
        assert 'PRESERVE_ENDING' in locked
        assert 'PRESERVE_CORE_PREMISE' in locked

    def test_no_truncation_of_detailed_text(self):
        """A complete story entered in IDEA field must not be truncated or summarized."""
        source = (
            'Mimi dolabı açar ve yapışkan notlar onu gizli bir haritaya kadar takip eder. '
            'Notlar Miminin yüzüne yapışır, sonra çoğalır ve geri döner. '
            'Mimi dolabın arkasına saklanır ama notlar onu bulur ve tamamen kaplar, '
            'sadece gözleri görünür kalır. Son sahne sert bir kesimle biter.'
        )
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', source, context, provider, 'fixture')
        user_json = provider.calls[0][0]
        # Exact text must be preserved, not summarized
        assert user_json['text'] == source
        assert len(user_json['text']) == len(source)

    def test_no_summarisation_of_detailed_text(self):
        """The provider must receive the full text, not a summary."""
        source = (
            'Mimi dolabı açar ve yapışkan notlar onu gizli bir haritaya kadar takip eder. '
            'Notlar Miminin yüzüne yapışır, sonra çoğalır ve geri döner.'
        )
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', source, context, provider, 'fixture')
        user_json = provider.calls[0][0]
        # Should contain the full text, not a shortened version
        assert 'gizli bir haritaya' in user_json['text']
        assert 'çoğalır ve geri döner' in user_json['text']


# ──────────────────────────────────────────────
# Scenario 3: DETAILED_STORY
# ──────────────────────────────────────────────

class TestDetailedStory:
    """DETAILED_STORY mode with correct input mode propagation."""

    def test_input_mode_is_detailed_story(self):
        """inputMode must be DETAILED_STORY when user selects that mode."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'DETAILED_STORY',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE', 'PRESERVE_KEY_EVENTS', 'PRESERVE_ENDING'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Complete story text.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        assert user_json['context']['inputMode'] == 'DETAILED_STORY'

    def test_system_prompt_explains_detailed_story(self):
        """System prompt must distinguish DETAILED_STORY from IDEA."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'DETAILED_STORY',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Complete story text.', context, provider, 'fixture')
        system_prompt = provider.calls[0][1]
        assert 'DETAILED_STORY' in system_prompt
        assert 'complete narrative' in system_prompt or 'complete story' in system_prompt

    def test_all_locked_requirements_passed(self):
        """When all three requirements are selected, all must reach the provider."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'DETAILED_STORY',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE', 'PRESERVE_KEY_EVENTS', 'PRESERVE_ENDING'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Complete story text.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        locked = user_json['context']['lockedRequirements']
        assert 'PRESERVE_CORE_PREMISE' in locked
        assert 'PRESERVE_KEY_EVENTS' in locked
        assert 'PRESERVE_ENDING' in locked

    def test_source_text_preserved(self):
        """Source text must reach the provider unchanged."""
        source = 'Mimi opens the cabinet and the notes follow her to a hidden map.'
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'DETAILED_STORY',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', source, context, provider, 'fixture')
        user_json = provider.calls[0][0]
        assert user_json['text'] == source


# ──────────────────────────────────────────────
# Cross-scenario: System prompt consistency
# ──────────────────────────────────────────────

class TestSystemPromptConsistency:
    """The system prompt must be consistent across all scenarios."""

    def test_system_prompt_never_silently_locks_requirements(self):
        """System prompt must state that absent requirements are not binding."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': [],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        system_prompt = provider.calls[0][1]
        # The prompt must explicitly say not to silently lock absent requirements
        assert 'do not silently lock' in system_prompt or 'Only the requirements present' in system_prompt

    def test_system_prompt_requires_meaningful_differences(self):
        """System prompt must instruct against reusing same text with different title."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        system_prompt = provider.calls[0][1]
        assert 'do not reuse the same story text' in system_prompt or 'meaningfully different' in system_prompt

    def test_system_prompt_respects_requested_count(self):
        """System prompt must reference requestedAlternativeCount."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        system_prompt = provider.calls[0][1]
        assert 'requestedAlternativeCount' in system_prompt

    def test_no_render_authorization_in_story_prompt(self):
        """STORY role must never grant render authorization."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': [],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        system_prompt = provider.calls[0][1]
        assert 'render authorization' not in system_prompt or 'never grant render authorization' in system_prompt


# ──────────────────────────────────────────────
# Cross-scenario: safe_context filtering
# ──────────────────────────────────────────────

class TestSafeContextFiltering:
    """Verify that safe_context includes the required keys."""

    def test_input_mode_in_safe_context(self):
        """inputMode must be included in safe_context sent to provider."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
            'someOtherKey': 'should not appear',
        }
        perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        ctx = user_json['context']
        assert 'inputMode' in ctx
        assert ctx['inputMode'] == 'IDEA'

    def test_story_generation_mode_in_safe_context(self):
        """storyGenerationMode must be included in safe_context."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        ctx = user_json['context']
        assert 'storyGenerationMode' in ctx
        assert ctx['storyGenerationMode'] == 'IMPROVE_EXISTING_STORY'

    def test_locked_requirements_in_safe_context(self):
        """lockedRequirements must be included in safe_context."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'IMPROVE_EXISTING_STORY',
            'lockedRequirements': ['PRESERVE_CORE_PREMISE', 'PRESERVE_ENDING'],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        ctx = user_json['context']
        assert 'lockedRequirements' in ctx
        assert ctx['lockedRequirements'] == ['PRESERVE_CORE_PREMISE', 'PRESERVE_ENDING']

    def test_requested_alternative_count_in_safe_context(self):
        """requestedAlternativeCount must be included in safe_context."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': [],
            'requestedAlternativeCount': 3,
        }
        perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        ctx = user_json['context']
        assert 'requestedAlternativeCount' in ctx
        assert ctx['requestedAlternativeCount'] == 3

    def test_unknown_keys_not_leaked(self):
        """Keys not in safe_context whitelist must not reach the provider."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': [],
            'requestedAlternativeCount': 3,
            'secretApiKey': 'SHOULD_NOT_APPEAR',
            'internalNotes': 'SHOULD_NOT_APPEAR',
        }
        perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        user_json = provider.calls[0][0]
        ctx = user_json['context']
        assert 'secretApiKey' not in ctx
        assert 'internalNotes' not in ctx


# ──────────────────────────────────────────────
# Step 2 regression: approval and lineage
# ──────────────────────────────────────────────

class TestStep2Regression:
    """Ensure Step 2 approval and lineage are not regressed."""

    def test_story_result_contains_alternatives(self):
        """STORY role must return alternatives array."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': [],
            'requestedAlternativeCount': 3,
        }
        response = perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        assert 'alternatives' in response['result']
        assert len(response['result']['alternatives']) == 3

    def test_story_result_contains_story_quality(self):
        """STORY role must include storyQuality analysis."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': [],
            'requestedAlternativeCount': 3,
        }
        response = perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        assert 'storyQuality' in response['result']

    def test_candidate_ids_preserved(self):
        """Candidate IDs from provider response must be preserved."""
        result = {
            'alternatives': [
                {'candidateId': 'candidate-1', 'title': 'A', 'text': 'Story A'},
                {'candidateId': 'candidate-2', 'title': 'B', 'text': 'Story B'},
                {'candidateId': 'candidate-3', 'title': 'C', 'text': 'Story C'},
            ]
        }
        provider = FixtureProvider(result)
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': [],
            'requestedAlternativeCount': 3,
        }
        response = perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        alts = response['result']['alternatives']
        assert alts[0]['candidateId'] == 'candidate-1'
        assert alts[1]['candidateId'] == 'candidate-2'
        assert alts[2]['candidateId'] == 'candidate-3'

    def test_validation_status_not_validated(self):
        """STORY role must not self-validate."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': [],
            'requestedAlternativeCount': 3,
        }
        response = perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        assert response['validationStatus'] == 'NOT_VALIDATED'

    def test_provider_is_deepseek(self):
        """STORY role must route to DeepSeek."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': [],
            'requestedAlternativeCount': 3,
        }
        response = perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        assert response['provider'] == 'deepseek'

    def test_visual_inspected_is_false(self):
        """STORY role is text-only; visualInspected must be False."""
        provider = FixtureProvider(_story_fixture(3))
        context = {
            'inputMode': 'IDEA',
            'storyGenerationMode': 'EXPLORE_DIFFERENT_STORIES',
            'lockedRequirements': [],
            'requestedAlternativeCount': 3,
        }
        response = perform_role('STORY', 'Short concept.', context, provider, 'fixture')
        assert response['visualInspected'] is False
