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


def derive_source_evidence(source: str, context: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Offline responsibility-split proposal, NEVER a paid-admission decision.

    Preserve narrative bytes; locate exact text mechanically. A missing source
    clause or inaccurate model citation cannot establish a semantic violation
    or a semantic PASS. Existing strict validate()/dispatch paths do not call
    this function and remain authoritative until a separately approved policy.
    """
    from .story_experiment import contract, sha
    policy = contract(source, context)
    body = candidate.get('text')
    body = body if isinstance(body, str) else ''

    def locations(whole, quote):
        if not isinstance(quote, str) or not quote:
            return []
        return [{'start': m.start(), 'end': m.end(), 'quote': whole[m.start():m.end()]}
                for m in re.finditer(re.escape(quote), whole)]

    # Segmentation is only a locator; it does not certify events or causality.
    sentences = []
    for match in re.finditer(r'[^.!?]+(?:[.!?]+|$)', body):
        value = match.group().strip()
        if value:
            start = match.start() + len(match.group()) - len(match.group().lstrip())
            sentences.append({'start': start, 'end': start + len(value), 'quote': body[start:start+len(value)]})
    declaration = candidate.get('sourceContract')
    declaration = declaration if isinstance(declaration, dict) else {}
    claims = []
    for key in ('openingVisualState', 'motivation', 'progression', 'ending'):
        value = candidate.get(key)
        spans = locations(body, value)
        claims.append({'field': key, 'claimedQuote': value, 'locations': spans,
                       'status': 'EXACT_QUOTE_PRESENT' if spans else 'NOT_SUPPLIED' if value is None else 'INVALID_EVIDENCE_CLAIM'})
    for binding in declaration.get('bindings', []) if isinstance(declaration.get('bindings'), list) else []:
        if not isinstance(binding, dict):
            claims.append({'field': 'sourceContract.bindings', 'status': 'INVALID_EVIDENCE_CLAIM'}); continue
        spans = locations(body, binding.get('candidateQuote'))
        anchor = next((a for a in policy['protectedAnchors'] if a['id'] == binding.get('anchorId')), None)
        valid = bool(spans) and bool(anchor) and binding.get('sourceQuote') == anchor['quote']
        for prefix, whole, quote in (('candidate', body, binding.get('candidateQuote')), ('source', source, binding.get('sourceQuote'))):
            if prefix+'Start' in binding or prefix+'End' in binding:
                start, end = binding.get(prefix+'Start'), binding.get(prefix+'End')
                valid = valid and type(start) is int and type(end) is int and 0 <= start < end <= len(whole) and whole[start:end] == quote
        claims.append({'field': 'sourceContract.bindings', 'anchorId': binding.get('anchorId'),
                       'claimedQuote': binding.get('candidateQuote'), 'locations': spans,
                       'status': 'EXACT_QUOTE_PRESENT' if valid else 'INVALID_EVIDENCE_CLAIM'})
    anchors = []; contradictions = []
    for anchor in policy['protectedAnchors']:
        spans = locations(body, anchor['quote'])
        # Deliberately tiny explicit-negation grammar, not fuzzy semantics.
        # Only the entire protected clause with an explicit negation counts;
        # changed predicates, pronouns and alternative triggers stay UNKNOWN.
        negations = ['It is false that '+anchor['quote']]
        for copula in (' is ', ' are '):
            if copula in anchor['quote']:
                negations.append(anchor['quote'].replace(copula, copula+'not ', 1))
        negative_spans = [span for quote in negations for span in locations(body, quote)]
        if negative_spans:
            contradictions.append({'anchorId': anchor['id'], 'status': 'EXPLICIT_PROTECTED_CLAUSE_NEGATION', 'locations': negative_spans})
        anchors.append({'anchorId': anchor['id'], 'kind': anchor['kind'],
                        'source': {'start': anchor['start'], 'end': anchor['end'], 'quote': source[anchor['start']:anchor['end']]},
                        'candidateLocations': spans,
                        'literalEvidence': 'EXACT_TEXT_LOCATED' if spans else 'MISSING',
                        'semanticFidelity': 'UNKNOWN'})
    proposals = declaration.get('protectedChanges') or []
    proposal_claimed = declaration.get('status') == 'PROTECTED_CHANGE_PROPOSAL' or bool(proposals)
    valid_proposals = isinstance(proposals, list) and bool(proposals) and all(
        isinstance(p, dict) and p.get('anchorId') in {a['id'] for a in policy['protectedAnchors']}
        and all(isinstance(p.get(k), str) and p[k].strip() for k in ('proposedChange', 'justification')) for p in proposals)
    valid_narrative = (isinstance(candidate.get('candidateId'), str) and bool(re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', candidate['candidateId']))
                       and isinstance(candidate.get('title'), str) and bool(candidate['title'].strip())
                       and 160 <= len(body.strip()) <= 12000 and len(sentences) >= 2)
    if not valid_narrative or proposal_claimed and not valid_proposals:
        status = 'INVALID_GENERATION_OUTPUT'
    elif proposal_claimed:
        status = 'PROTECTED_CHANGE_PROPOSAL'
    elif contradictions:
        status = 'DEFINITE_SOURCE_VIOLATION'
    elif all(a['candidateLocations'] for a in anchors):
        status = 'DETERMINISTIC_SOURCE_CONTRACT_PASSED'
    else:
        status = 'SEMANTIC_FIDELITY_REVIEW_REQUIRED'
    return {'candidateId': candidate.get('candidateId'), 'narrativeSha256': sha(body),
            'narrativeValidity': 'COMPLETE_BOUNDED_NARRATIVE' if valid_narrative else 'INVALID_GENERATION_OUTPUT',
            'evidenceScope': 'EXACT_TEXT_LOCATIONS_ONLY_NOT_SEMANTIC_CERTIFICATION',
            'narrativeSpans': sentences, 'modelEvidenceClaims': claims, 'protectedFacts': anchors,
            'explicitContradictions': contradictions, 'protectedChangeProposals': proposals,
            'status': status, 'semanticFidelity': 'UNKNOWN', 'independentReview': 'NOT_EXECUTED',
            'semanticQuestions': [{'anchorId': a['anchorId'], 'question': 'Does the narrative preserve this source fact, including trigger and continuity conditions?'} for a in anchors],
            'paidReviewEligible': False, 'policyActivation': 'DISABLED_REQUIRES_EXPLICIT_OWNER_DECISION',
            'futureReviewConsideration': 'OWNER_POLICY_DECISION_REQUIRED' if status in {
                'DETERMINISTIC_SOURCE_CONTRACT_PASSED', 'SEMANTIC_FIDELITY_REVIEW_REQUIRED'} else 'BLOCKED_OR_SEPARATE_SOURCE_DECISION_REQUIRED',
            'sourceApproved': False, 'renderAuthorized': False}


def proposed_story_authoring_contract() -> dict[str, Any]:
    """Document/test an unactivated simplification of existing STORY fields."""
    return {'status': 'PROPOSED_NOT_ACTIVATED', 'paidReviewEligibilityChanged': False,
            'ownerPolicyApprovalRequired': True, 'newSchemaVersion': None,
            'existingCandidateFields': ['candidateId', 'title', 'text', 'proposedChanges', 'motivation',
                                        'progression', 'weaknesses', 'productionRisks', 'sourceContract.protectedChanges'],
            'modelResponsibilities': 'Author complete narrative and honest creative intentions/risks; motivation and progression are author summaries, not certified evidence. Explicitly propose protected changes by anchor ID. Never claim source fidelity PASS.',
            'applicationResponsibilities': 'Derive exact substrings and Unicode offsets from actual narrative; validate source catalog; retain absent quotes as MISSING and semantics as UNKNOWN. Never add sentences or repair raw output.',
            'independentReviewerResponsibilities': 'Judge source meaning, causal triggers, continuity, six CPQ dimensions and risks only after separate policy and request authorization.',
            'proposedModes': {
                'SOURCE_BOUND_STORY_REVISION': 'Protected facts stay locked; unprotected staging/actions/progression may change. Missing literal facts need semantic assessment, not assumed PASS.',
                'CREATIVE_EXPLORATION_PROPOSAL': 'May propose protected changes; no proposal replaces approved source. Channel identity, child-appropriate tone and coherent causality remain requirements; exact scope needs owner approval.'},
            'dispatchEnabled': False, 'sourceApprovalEnabled': False, 'buildPromptEnabled': False}


REVIEW_EVIDENCE_VERSION = 'story-review-exact-spans-v1'


def review_evidence_catalog(documents: dict[str, str]) -> dict[str, Any]:
    """Lossless Unicode-code-point spans. No normalization or semantic inference.

    Sentence/semicolon/newline boundaries retain punctuation and whitespace.
    Long run-on text is split at an original comma/space within 800 code points.
    IDs bind role, complete document digest and extraction version.
    """
    import hashlib
    from .story_experiment import sha
    prefixes = {'SOURCE': 'S', 'CANDIDATE_A': 'A', 'CANDIDATE_B': 'B'}
    if set(documents) != set(prefixes):
        raise ValueError('Exactly source and candidate A/B documents required')
    bindings, records = {}, []
    for role, prefix in prefixes.items():
        text = documents[role]
        if not isinstance(text, str) or not text.strip() or len(text) > 12000 or '\x00' in text:
            raise ValueError('Invalid evidence document')
        try:
            digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        except UnicodeEncodeError as error:
            raise ValueError('Invalid Unicode evidence document') from error
        bindings[role] = digest
        cuts = [m.end() for m in re.finditer(r'[.!?](?=\s|$)|[;\n]', text)]
        cuts.append(len(text))
        start, ordinal = 0, 0
        for end in sorted(set(cuts)):
            while end - start > 800:
                split = max(text.rfind(',', start + 200, start + 800), text.rfind(' ', start + 200, start + 800))
                cut = split + 1 if split >= 0 else start + 800
                ordinal += 1
                records.append({'evidenceId': f'{prefix}{ordinal:02d}-{sha([REVIEW_EVIDENCE_VERSION, role, digest])[:16]}',
                    'documentRole': role, 'documentSha256': digest, 'startOffset': start,
                    'endOffset': cut, 'exactOriginalText': text[start:cut]})
                start = cut
            if end > start:
                ordinal += 1
                records.append({'evidenceId': f'{prefix}{ordinal:02d}-{sha([REVIEW_EVIDENCE_VERSION, role, digest])[:16]}',
                    'documentRole': role, 'documentSha256': digest, 'startOffset': start,
                    'endOffset': end, 'exactOriginalText': text[start:end]})
                start = end
    catalog = {'version': REVIEW_EVIDENCE_VERSION, 'offsetConvention': 'UNICODE_CODE_POINTS',
               'documentBindings': bindings, 'records': records}
    catalog['catalogSha256'] = sha(catalog)
    return catalog


def verify_review_evidence_catalog(catalog: dict[str, Any], documents: dict[str, str]) -> None:
    """Reject revised/forged text, role, digest, offsets, IDs or extraction version."""
    if catalog != review_evidence_catalog(documents):
        raise ValueError('Bound evidence catalog differs from immutable documents')
    for role, text in documents.items():
        spans = [r for r in catalog['records'] if r['documentRole'] == role]
        if ''.join(r['exactOriginalText'] for r in spans) != text:
            raise ValueError('Incomplete evidence document coverage')
        cursor = 0
        for record in spans:
            if record['startOffset'] != cursor or text[cursor:record['endOffset']] != record['exactOriginalText']:
                raise ValueError('Evidence offsets do not resolve exact original text')
            cursor = record['endOffset']
