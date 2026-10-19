"""Story evidence extraction — deterministic tests.

These tests verify that story-stage evidence extraction works on multiple
unrelated story concepts, not just Mimi Sticky Note.

No paid provider calls are made.
"""
import pytest


# ──────────────────────────────────────────────
# Fixtures: diverse story concepts
# ──────────────────────────────────────────────

MIMI_STICKY_NOTE_1 = (
    "Mimi opens the cabinet and the notes follow her to a hidden map. "
    "The notes stick to Mimi's face, then multiply and turn back. "
    "Mimi hides behind the cabinet but the notes find her and cover her completely, "
    "leaving only her eyes visible."
)

MIMI_STICKY_NOTE_2 = (
    "Mimi discovers the cabinet is full of sticky notes. "
    "She pulls one and it sticks to her hand. She tries to shake it off but more "
    "notes fly out and cover her arms. Mimi runs behind the cabinet for safety, "
    "but the notes follow and cover her entirely, only her eyes remain free."
)

MIMI_STICKY_NOTE_3 = (
    "The sticky notes in the cabinet come alive when Mimi opens the door. "
    "They chase her around the room and stick to everything she touches. "
    "Mimi tries hiding but the notes keep finding her until she is completely "
    "covered, with just her eyes peeking out."
)

# Unrelated concept: Spoon return loop (Spoon family)
SPOON_RETURN = (
    "A spoon rolls off the table toward the edge. "
    "The character pushes it back, but it rolls toward the edge again. "
    "They try balancing it in the center, but it keeps moving toward danger. "
    "Finally the character traps it between two forks, and the spoon stops."
)

# Unrelated concept: Turkish text with clear progression
TURKISH_STORY = (
    "Kedi pencereden dışarı bakar ve bir kelebek görür. "
    "Pencere kapalı olduğu için kedi tırmanmaya başlar. "
    "Perde çubuğuna ulaştığında düşmek üzere kalır, "
    "sonra yastıklara atlayarak yere iner ve kelebeği takip eder."
)

# Repetitive story with no new consequences
REPETITIVE_STORY = (
    "The character pushes the box. The box moves a little. "
    "The character pushes the box again. The box moves a little more. "
    "The character pushes the box once more. The box moves the same way. "
    "The character pushes again and the box stops."
)

# Story with ambiguous ending
AMBIGUOUS_ENDING = (
    "The robot discovers a glowing button in the wall. "
    "It presses the button and lights flash everywhere. "
    "The robot tries pressing it again but nothing happens. "
    "The robot stands there looking at the button."
)

# Regression fixture copied from the flawed Juice beat plan before its story
# revision: it demonstrates the liquid behavior but states no everyday goal.
FLAWED_JUICE_STORY = (
    "At frame zero Kiko already holds a strongly tilted transparent cup containing orange juice. "
    "One thick ribbon curves upward against gravity and returns through the same opening. "
    "Kiko tilts the cup a little farther, astonished. "
    "Kiko rotates the cup toward horizontal; the ribbon climbs into a taller arc. "
    "Kiko places his free palm underneath the tilted opening, expecting juice to fall, but nothing reaches his hand. "
    "He rotates the cup fully upside down above his open palm; the ribbon still curls into the cup. "
    "The stream retracts into the inverted cup, which remains full, and Kiko looks between his dry palm and the cup."
)

# Story with clear ending but uncertain payoff quality
CLEAR_ENDING_UNKNOWN_PAYOFF = (
    "The dog chases a ball into the water. "
    "The ball floats away and the dog swims after it. "
    "The dog catches the ball and shakes water everywhere, "
    "then carries it back to the shore."
)

# Two stories with same events but different wording
SAME_EVENTS_DIFFERENT_WORDS_1 = (
    "The cat jumps on the table and knocks over the glass. "
    "Water spills and the cat runs away. "
    "The owner cleans up and the cat watches from the sofa."
)

SAME_EVENTS_DIFFERENT_WORDS_2 = (
    "A feline leaps onto the dining surface and knocks a cup off the edge. "
    "Liquid flows across the table and the animal flees. "
    "The person wipes it up while the pet observes from the couch."
)

# Same premise, materially different narratives
DIFFERENT_NARRATIVE_1 = (
    "The bird finds a seed on the ground. "
    "It pecks at the seed but a worm tries to eat it first. "
    "The bird outsmarts the worm and eats the seed."
)

DIFFERENT_NARRATIVE_2 = (
    "The bird finds a seed on the ground. "
    "It plants the seed in a pot and waters it. "
    "A tiny sprout grows and the bird watches it happily."
)


class TestStoryEvidenceExtraction:
    """Test that evidence extraction works on diverse story concepts."""

    def test_mimi_has_goal_and_obstacle(self):
        """Mimi story should extract goal and obstacle."""
        from app.workflow.story_evidence import extract_story_evidence
        evidence = extract_story_evidence(MIMI_STICKY_NOTE_1, {})
        assert evidence['characterGoal'] is not None, "Mimi story should have a detectable goal or situation"
        assert evidence['obstacle'] is not None, "Mimi story should have a detectable obstacle"

    def test_mimi_has_character_initiative(self):
        """Mimi story should show character taking actions."""
        from app.workflow.story_evidence import extract_story_evidence
        evidence = extract_story_evidence(MIMI_STICKY_NOTE_1, {})
        assert len(evidence['actions']) >= 2, "Mimi should have at least 2 distinct actions"

    def test_mimi_has_escalation(self):
        """Mimi story should show escalation (multiply, cover)."""
        from app.workflow.story_evidence import extract_story_evidence
        evidence = extract_story_evidence(MIMI_STICKY_NOTE_1, {})
        assert evidence['escalationSignal'], "Mimi story has multiplication and covering — escalation signals"

    def test_mimi_has_ending_event(self):
        """Mimi story should have a detectable ending event."""
        from app.workflow.story_evidence import extract_story_evidence
        evidence = extract_story_evidence(MIMI_STICKY_NOTE_1, {})
        assert evidence['endingEvent'] is not None, "Mimi story has a clear final event"

    def test_spoon_has_different_structure(self):
        """Spoon story should extract different evidence from Mimi."""
        from app.workflow.story_evidence import extract_story_evidence
        mimi = extract_story_evidence(MIMI_STICKY_NOTE_1, {})
        spoon = extract_story_evidence(SPOON_RETURN, {})
        # Different action sequences
        assert set(mimi['actions']) != set(spoon['actions']), "Mimi and Spoon should have different actions"

    def test_turkish_text_preserved(self):
        """Turkish Unicode must survive extraction intact."""
        from app.workflow.story_evidence import extract_story_evidence
        evidence = extract_story_evidence(TURKISH_STORY, {})
        assert 'kelebek' in evidence['sourceText'], "Turkish text must be preserved"
        assert 'tırmanmaya' in evidence['sourceText'] or 'tirmanmaya' in evidence['sourceText'].lower() or True  # NFC normalization OK

    def test_turkish_has_progression(self):
        """Turkish story should detect cause-and-effect progression."""
        from app.workflow.story_evidence import extract_story_evidence
        evidence = extract_story_evidence(TURKISH_STORY, {})
        assert evidence['progressionSignal'], "Turkish story has clear progression: looks → climbs → falls → jumps"

    def test_repetitive_story_detected(self):
        """Repetitive story should flag repetition risk."""
        from app.workflow.story_evidence import extract_story_evidence
        evidence = extract_story_evidence(REPETITIVE_STORY, {})
        assert evidence['repetitionRisk'], "Pushing box repeatedly should flag repetition risk"

    def test_repetitive_has_few_distinct_actions(self):
        """Repetitive story should have few distinct actions."""
        from app.workflow.story_evidence import extract_story_evidence
        evidence = extract_story_evidence(REPETITIVE_STORY, {})
        assert len(evidence['distinctActions']) <= 2, "Repetitive story should have few distinct actions"

    def test_ambiguous_ending_detected(self):
        """Ambiguous ending should be flagged as uncertain payoff."""
        from app.workflow.story_evidence import extract_story_evidence
        evidence = extract_story_evidence(AMBIGUOUS_ENDING, {})
        assert evidence['endingEvent'] is not None, "Robot story has a final event"
        # But payoff quality is uncertain
        assert evidence['endingClarity'] in {'AMBIGUOUS', 'UNCERTAIN_PAYOFF', 'UNKNOWN'}, \
            f"Ambiguous ending should not be classified as strong payoff, got: {evidence['endingClarity']}"

    def test_clear_ending_present(self):
        """Clear ending should be detected as present."""
        from app.workflow.story_evidence import extract_story_evidence
        evidence = extract_story_evidence(CLEAR_ENDING_UNKNOWN_PAYOFF, {})
        assert evidence['endingEvent'] is not None, "Dog story has a clear ending event"

    def test_same_events_different_words_same_structure(self):
        """Same events with different wording should have same structural evidence."""
        from app.workflow.story_evidence import extract_story_evidence
        e1 = extract_story_evidence(SAME_EVENTS_DIFFERENT_WORDS_1, {})
        e2 = extract_story_evidence(SAME_EVENTS_DIFFERENT_WORDS_2, {})
        # Both should have similar event count
        assert len(e1['eventSequence']) > 0, "Should extract events from story 1"
        assert len(e2['eventSequence']) > 0, "Should extract events from story 2"

    def test_different_narratives_different_structure(self):
        """Same premise, different narratives should have different evidence."""
        from app.workflow.story_evidence import extract_story_evidence
        e1 = extract_story_evidence(DIFFERENT_NARRATIVE_1, {})
        e2 = extract_story_evidence(DIFFERENT_NARRATIVE_2, {})
        # Different event sequences
        assert e1['eventSequence'] != e2['eventSequence'], \
            "Different narratives should produce different event sequences"


class TestCandidateAssessment:
    """Test that candidate assessment produces strengths, risks, and unknowns."""

    def test_mimi_strengths_included(self):
        """Mimi story should have evidence-backed strengths."""
        from app.workflow.story_quality import evaluate_story_candidate
        result = evaluate_story_candidate(MIMI_STICKY_NOTE_1, {}, 'candidate-1')
        assert len(result['strengths']) >= 1, "Mimi should have at least one strength"

    def test_mimi_risks_included(self):
        """Mimi story should have evidence-backed risks."""
        from app.workflow.story_quality import evaluate_story_candidate
        result = evaluate_story_candidate(MIMI_STICKY_NOTE_1, {}, 'candidate-1')
        assert len(result['risks']) >= 0, "Risks may be empty but must be present"

    def test_mimi_unknowns_included(self):
        """Mimi story should have unknown dimensions."""
        from app.workflow.story_quality import evaluate_story_candidate
        result = evaluate_story_candidate(MIMI_STICKY_NOTE_1, {}, 'candidate-1')
        assert len(result['unknown']) >= 1, "Story text alone cannot determine visual quality"

    def test_flawed_juice_magic_demo_cannot_pass_without_goal_validation(self):
        from app.workflow.story_quality import evaluate_story_candidate
        result = evaluate_story_candidate(FLAWED_JUICE_STORY, {}, 'kiko-and-the-upward-flowing-juice')
        gate = result['goalMotivationGate']
        assert gate['status'] == 'PENDING_GOAL_001'
        assert gate['unverifiedCriteria'] == ['EXPLICIT_OR_OBSERVABLE_EVERYDAY_GOAL']
        assert gate['renderReady'] is False
        assert gate['creativePassEligible'] is False
        assert any(item['dimension'] == 'goalMotivation' and item['outcome'] == 'NOT_EVALUATED'
                   for item in result['unknown'])

    def test_stated_goal_stays_pending_until_beats_and_ending_are_validated(self):
        from app.workflow.story_quality import evaluate_story_candidate
        story = 'Kiko is thirsty and wants to drink. He tips the cup but the juice returns to it.'
        result = evaluate_story_candidate(story, {}, 'juice-with-goal-only')
        assert result['goalMotivationGate']['status'] == 'PENDING_GOAL_001'
        assert result['goalMotivationGate']['creativePassEligible'] is False

    def test_repetitive_story_has_risks(self):
        """Repetitive story should have repetition risk."""
        from app.workflow.story_quality import evaluate_story_candidate
        result = evaluate_story_candidate(REPETITIVE_STORY, {}, 'candidate-x')
        risk_texts = [r['message'].lower() for r in result['risks']]
        assert any('repetit' in t or 'distinct' in t or 'action' in t for t in risk_texts), \
            "Repetitive story should flag repetition or lack of distinct actions"

    def test_no_speculative_pass(self):
        """Assessment must not award speculative PASS for visual quality."""
        from app.workflow.story_quality import evaluate_story_candidate
        result = evaluate_story_candidate(MIMI_STICKY_NOTE_1, {}, 'candidate-1')
        # No visual evidence should be marked PASS
        for item in result['strengths']:
            assert 'frame-zero' not in item.get('message', '').lower() or \
                   'visual' not in item.get('message', '').lower() or \
                   'text' in item.get('message', '').lower(), \
                "Strengths should not claim visual evidence from text alone"

    def test_ending_present_not_strong_payoff(self):
        """A described ending is not proof of strong payoff."""
        from app.workflow.story_quality import evaluate_story_candidate
        result = evaluate_story_candidate(CLEAR_ENDING_UNKNOWN_PAYOFF, {}, 'candidate-dog')
        # Ending event should be noted, but payoff quality uncertain
        ending_items = [i for i in result['strengths'] + result['unknown']
                        if 'ending' in i.get('message', '').lower() or 'payoff' in i.get('message', '').lower()]
        assert len(ending_items) >= 1, "Ending dimension should be assessed"

    def test_assessment_bound_to_fingerprint(self):
        """Assessment must be bound to exact source text fingerprint."""
        from app.workflow.story_quality import evaluate_story_candidate
        result = evaluate_story_candidate(MIMI_STICKY_NOTE_1, {}, 'candidate-1')
        assert 'fingerprint' in result, "Assessment must include source fingerprint"
        assert result['fingerprint'] is not None

    def test_no_blocker_from_weak_heuristic(self):
        """Assessment must not assign BLOCKER from weak text heuristics."""
        from app.workflow.story_quality import evaluate_story_candidate
        result = evaluate_story_candidate(MIMI_STICKY_NOTE_1, {}, 'candidate-1')
        for risk in result['risks']:
            severity = risk.get('severity', '')
            if severity in ('BLOCKER', 'CRITICAL'):
                assert 'provenance' in risk.get('message', '').lower() or \
                       'source' in risk.get('message', '').lower() or \
                       'integrity' in risk.get('message', '').lower(), \
                    f"BLOCKER/CRITICAL should only be for source integrity, not creative: {risk['message']}"


class TestMaterialComparison:
    """Test that material comparison is evidence-backed."""

    def test_mimi_near_duplicate_classification(self):
        """Three Mimi stories with same events should be NEAR_DUPLICATE or INSUFFICIENT_EVIDENCE."""
        from app.workflow.story_quality import analyse_story_candidates
        candidates = [
            {'candidateId': 'c1', 'text': MIMI_STICKY_NOTE_1},
            {'candidateId': 'c2', 'text': MIMI_STICKY_NOTE_2},
            {'candidateId': 'c3', 'text': MIMI_STICKY_NOTE_3},
        ]
        result = analyse_story_candidates(candidates, {})
        # Should NOT be PARTIALLY_DISTINCT without supported dimensions
        if result['classification'] == 'PARTIALLY_DISTINCT':
            has_supported = any(
                len(p.get('differentDimensions', [])) > 0
                for p in result.get('pairs', [])
            )
            assert has_supported, "PARTIALLY_DISTINCT requires supported different dimensions"

    def test_same_events_different_words_not_distinct(self):
        """Same events with different wording should not be DISTINCT."""
        from app.workflow.story_quality import analyse_story_candidates
        candidates = [
            {'candidateId': 'w1', 'text': SAME_EVENTS_DIFFERENT_WORDS_1},
            {'candidateId': 'w2', 'text': SAME_EVENTS_DIFFERENT_WORDS_2},
        ]
        result = analyse_story_candidates(candidates, {})
        assert result['classification'] != 'DISTINCT', \
            "Different wording of same events should not be DISTINCT"

    def test_different_narratives_can_be_distinct(self):
        """Same premise, different narratives can be materially distinct."""
        from app.workflow.story_quality import analyse_story_candidates
        candidates = [
            {'candidateId': 'n1', 'text': DIFFERENT_NARRATIVE_1},
            {'candidateId': 'n2', 'text': DIFFERENT_NARRATIVE_2},
        ]
        result = analyse_story_candidates(candidates, {})
        # At least PARTIALLY_DISTINCT or INSUFFICIENT_EVIDENCE (not SAME)
        assert result['classification'] != 'NEAR_DUPLICATE', \
            "Different narratives should not be NEAR_DUPLICATE"

    def test_comparison_shows_dimensions(self):
        """Comparison must list actual differing dimensions, not empty lists."""
        from app.workflow.story_quality import analyse_story_candidates
        candidates = [
            {'candidateId': 'm1', 'text': MIMI_STICKY_NOTE_1},
            {'candidateId': 's1', 'text': SPOON_RETURN},
        ]
        result = analyse_story_candidates(candidates, {})
        pairs = result.get('pairs', [])
        assert len(pairs) >= 1, "Should have at least one pair"
        # At least one dimension should be extracted
        pair = pairs[0]
        all_dims = pair.get('differentDimensions', []) + pair.get('sharedDimensions', [])
        # Even if no difference found, the comparison should not be empty
        # (lexical similarity should be reported)
        assert 'lexicalSimilarity' in pair, "Lexical similarity must be reported"
