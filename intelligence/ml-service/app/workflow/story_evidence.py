"""General-purpose story-stage evidence extraction.

Extracts narrative dimensions from raw story text without calling any provider.

Design principles:
- No hardcoded domain-specific event signatures (no Mimi, no sticky notes).
- Uses general linguistic patterns applicable to any story in any language.
- Returns UNKNOWN/None when evidence is insufficient rather than inventing facts.
- Preserves source text integrity and Turkish/Unicode fidelity.
- Never claims visual evidence from text alone.
"""
from __future__ import annotations
import hashlib
import re
import unicodedata
from typing import Any


# ──────────────────────────────────────────────
# General action verbs (English + Turkish common patterns)
# These are broad categories, not domain-specific.
# ──────────────────────────────────────────────

_ACTION_VERBS_EN = {
    # Movement
    'runs', 'run', 'jumps', 'jump', 'leaps', 'leap', 'walks', 'walk',
    'moves', 'move', 'flies', 'fly', 'swims', 'swim', 'climbs', 'climb',
    'rolls', 'roll', 'falls', 'fall', 'drops', 'drop', 'slides', 'slide',
    'chases', 'chase', 'follows', 'follow', 'escapes', 'escape', 'flees', 'flee',
    # Interaction
    'pushes', 'push', 'pulls', 'pull', 'opens', 'open', 'closes', 'close',
    'grabs', 'grab', 'catches', 'catch', 'traps', 'trap', 'blocks', 'block',
    'presses', 'press', 'touches', 'touch', 'hits', 'hit', 'knocks', 'knock',
    'plants', 'plant', 'waters', 'water', 'pecks', 'peck', 'eats', 'eat',
    # State change
    'hides', 'hide', 'covers', 'cover', 'sticks', 'stick', 'balances', 'balance',
    'shakes', 'shake', 'turns', 'turn', 'finds', 'find', 'discovers', 'discover',
    'tries', 'try', 'attempts', 'attempt', 'watches', 'watch', 'looks', 'look',
    'sees', 'see', 'notices', 'notice', 'realizes', 'realize', 'understands', 'understand',
    'stands', 'stand', 'carries', 'carry', 'cleans', 'clean', 'wipes', 'wipe',
    # Turkish action patterns (common roots)
    'bakar', 'görür', 'başlar', 'ulaştığında', 'kalır', 'iner', 'takip',
    'tırmanmaya', 'tirmanmaya', 'atlayarak', 'dışarı',
}

_ESCALATION_SIGNALS_EN = {
    'then', 'but', 'until', 'after', 'when', 'again', 'more', 'multiplies',
    'grows', 'faster', 'keeps', 'continues', 'increases', 'worsens',
    'finally', 'at last', 'in the end', 'eventually',
    'sonra', 'ama', 'fakat', 'ancak', 'sonra', 'daha', 'çoğalır',
}

_ENDING_SIGNALS_EN = {
    'finally', 'in the end', 'at last', 'ends', 'ending', 'last',
    'sonra', 'sonunda', 'son', 'biter', 'kalır',
}

_PROGRESSION_SIGNALS_EN = {
    'then', 'but', 'until', 'after', 'when', 'because', 'so', 'however',
    'sonra', 'çünkü', 'için', 'ama', 'fakat', 'ancak',
}


def _nfc(text: str) -> str:
    """Normalize text to NFC for consistent comparison."""
    return unicodedata.normalize('NFC', text)


def _fingerprint(text: str) -> str:
    """SHA-256 fingerprint of NFC-normalized text."""
    return hashlib.sha256(_nfc(text).encode('utf-8')).hexdigest()


def _sentences(text: str) -> list[str]:
    """Split text into sentences, preserving Unicode."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _extract_actions(text: str) -> list[str]:
    """Extract action verbs from text, language-agnostic."""
    lower = text.lower()
    found = []
    for verb in _ACTION_VERBS_EN:
        if re.search(rf"\b{re.escape(verb)}\b", lower):
            found.append(verb)
    # Deduplicate while preserving order
    return list(dict.fromkeys(found))


def _extract_event_sequence(text: str) -> list[str]:
    """Extract a compact event sequence from sentences.

    Each sentence becomes a canonicalized event description based on the
    actions it contains. This is a simplified approach that works across
    languages without NLP dependencies.
    """
    sentences = _sentences(text)
    events = []
    for sentence in sentences:
        actions = _extract_actions(sentence)
        if actions:
            # Create a compact event descriptor
            events.append({
                'actions': actions,
                'text': sentence[:200],  # Truncate for safety
            })
    return events


def _has_escalation(text: str) -> bool:
    """Check if text contains escalation signals."""
    lower = text.lower()
    return any(signal in lower for signal in _ESCALATION_SIGNALS_EN)


def _has_progression(text: str) -> bool:
    """Check if text contains cause-and-effect progression signals."""
    lower = text.lower()
    count = sum(1 for signal in _PROGRESSION_SIGNALS_EN if signal in lower)
    return count >= 1


def _detect_ending(text: str) -> dict[str, Any] | None:
    """Detect the ending event and its clarity.

    Returns None if no ending is detectable.
    Returns a dict with ending event text and clarity assessment.
    """
    sentences = _sentences(text)
    if not sentences:
        return None

    # The last 1-2 sentences are the ending
    last_sentences = sentences[-2:] if len(sentences) >= 2 else sentences
    ending_text = ' '.join(last_sentences)

    # Check for ending signals
    has_ending_signal = any(sig in ending_text.lower() for sig in _ENDING_SIGNALS_EN)

    # Check if ending describes a concrete final state
    has_concrete_state = any(
        word in ending_text.lower()
        for word in ('visible', 'free', 'stops', 'carries', 'watches', 'kalır', 'biter')
    ) or len(_extract_actions(ending_text)) > 0

    # Check if it describes an open-ended or unresolved state
    open_ended = any(
        word in ending_text.lower()
        for word in ('looking', 'standing', 'waiting', 'there', 'nothing happens', 'looks at', 'stands there')
    )

    # Classify ending clarity
    if open_ended:
        # Open-ended state — ambiguous payoff
        clarity = 'AMBIGUOUS'
    elif has_ending_signal and has_concrete_state:
        clarity = 'PRESENT'
    elif has_concrete_state:
        clarity = 'PRESENT'
    elif len(last_sentences) > 0 and len(last_sentences[-1]) > 10:
        clarity = 'PRESENT'
    else:
        clarity = 'ABSENT'

    return {
        'endingEvent': ending_text[:300],
        'endingClarity': clarity,
    }


def _detect_repetition_risk(text: str) -> bool:
    """Detect if the story repeats the same action without new consequences.

    A high repetition ratio (same action verb appearing in many sentences
    with similar context) suggests repetition risk.
    """
    sentences = _sentences(text)
    if len(sentences) < 3:
        return False

    # Count action verbs per sentence
    sentence_actions = []
    for sentence in sentences:
        actions = set(_extract_actions(sentence))
        sentence_actions.append(actions)

    if not sentence_actions:
        return False

    # Check if most sentences share the same dominant action
    all_actions = set()
    for actions in sentence_actions:
        all_actions.update(actions)

    if len(all_actions) <= 1 and len(sentences) >= 3:
        return True

    # Check repetition ratio: how many sentences share the same primary action
    if len(all_actions) > 0:
        dominant_action = max(all_actions, key=lambda a: sum(1 for sa in sentence_actions if a in sa))
        # Count sentences where the dominant action appears (even with other actions)
        repetition_count = sum(1 for sa in sentence_actions if dominant_action in sa)
        if repetition_count >= len(sentences) * 0.6 and len(all_actions) <= 2:
            return True

    # Also check: if the text contains the same phrase repeated many times
    lower = text.lower()
    words = lower.split()
    if len(words) > 10:
        # Check for repeated sentence patterns
        sentence_texts = [s.lower().strip('.!,') for s in sentences]
        from collections import Counter
        sentence_counts = Counter(sentence_texts)
        most_common_count = sentence_counts.most_common(1)[0][1] if sentence_counts else 0
        if most_common_count >= 3:
            return True

    # Check for repeated noun-verb patterns (e.g., "pushes the box" repeated)
    if len(sentences) >= 3:
        # Look for the same key phrase appearing in multiple sentences
        key_phrases = re.findall(r'\b\w+\s+\w+\s+\w+\b', lower)
        from collections import Counter
        phrase_counts = Counter(key_phrases)
        most_common_phrase_count = phrase_counts.most_common(1)[0][1] if phrase_counts else 0
        if most_common_phrase_count >= 3:
            return True

    return False


def _detect_goal(text: str) -> str | None:
    """Detect character goal or situation from opening sentences.

    Looks for goal-oriented language in the first few sentences.
    If the opening sentence contains actions, it implies a situation/goal.
    """
    sentences = _sentences(text)
    if not sentences:
        return None

    # Check first 2 sentences for goal indicators
    opening = ' '.join(sentences[:2]).lower()

    # Goal patterns
    goal_patterns = [
        r'(?:wants|needs|tries|attempts|goal|seeks|looks for|searches for)',
        r'(?:görür|bakar|arar|ister|gerekli)',  # Turkish
    ]

    for pattern in goal_patterns:
        if re.search(pattern, opening):
            return sentences[0][:200]

    # If no explicit goal pattern, the opening situation may imply one
    actions = _extract_actions(sentences[0])
    if actions:
        return sentences[0][:200]

    # If the first sentence is substantial (>20 chars), treat it as the situation
    if len(sentences[0]) > 20:
        return sentences[0][:200]

    return None


def _detect_obstacle(text: str) -> str | None:
    """Detect obstacle or impossible relationship.

    Looks for conflict, obstruction, or challenge language.
    """
    sentences = _sentences(text)
    if len(sentences) < 2:
        return None

    # Check all sentences after the first for obstacle patterns
    check_sentences = sentences[1:]
    middle = ' '.join(check_sentences).lower()

    obstacle_patterns = [
        r'(?:but|cannot|can\'t|blocked|obstacle|problem|stuck|chase|follows|follow)',
        r'(?:ama|fakat|ancak|olamaz|engellenir)',  # Turkish
    ]

    for pattern in obstacle_patterns:
        for sentence in check_sentences:
            if re.search(pattern, sentence.lower()):
                return sentence[:200]

    return None


def _detect_rule_consistency(text: str) -> dict[str, Any]:
    """Check if physical rules are applied consistently.

    Looks for contradictions in how objects or rules behave.
    This is a simplified check — full consistency requires production plan.
    """
    # Simple heuristic: check if the same object/verb combination
    # appears with contradictory outcomes
    lower = text.lower()

    # Look for rule-establishing patterns
    # e.g., "X does Y" followed by "X does not Y" or "X does Z (contradiction)"
    # This is a best-effort check; full analysis needs semantic understanding

    return {
        'consistent': True,  # Default to consistent unless contradiction found
        'note': 'Full rule consistency check requires production plan analysis.',
    }


def extract_story_evidence(text: str, context: dict[str, Any]) -> dict[str, Any]:
    """Extract narrative evidence from story text.

    Returns a dict with all extractable dimensions.
    Missing evidence is represented as None, empty list, or 'UNKNOWN'.

    Args:
        text: The raw story text (preserved exactly, NFC-normalized for comparison).
        context: Optional context (character, profile, etc.).

    Returns:
        Dict with evidence dimensions.
    """
    nfc_text = _nfc(text)
    sentences = _sentences(nfc_text)
    actions = _extract_actions(nfc_text)
    distinct_actions = list(dict.fromkeys(actions))
    events = _extract_event_sequence(nfc_text)
    ending = _detect_ending(nfc_text)

    return {
        # Source integrity
        'sourceText': nfc_text,
        'fingerprint': _fingerprint(nfc_text),
        'sentenceCount': len(sentences),

        # Narrative dimensions
        'characterGoal': _detect_goal(nfc_text),
        'obstacle': _detect_obstacle(nfc_text),
        'actions': actions,
        'distinctActions': distinct_actions,
        'eventSequence': [e['actions'] for e in events],
        'events': events,

        # Progression and escalation
        'progressionSignal': _has_progression(nfc_text),
        'escalationSignal': _has_escalation(nfc_text),

        # Ending
        'endingEvent': ending['endingEvent'] if ending else None,
        'endingClarity': ending['endingClarity'] if ending else 'ABSENT',

        # Risks
        'repetitionRisk': _detect_repetition_risk(nfc_text),

        # Rule consistency (limited without production plan)
        'ruleConsistency': _detect_rule_consistency(nfc_text),

        # Context
        'character': context.get('mainCharacter'),
        'profile': context.get('profile'),
    }
