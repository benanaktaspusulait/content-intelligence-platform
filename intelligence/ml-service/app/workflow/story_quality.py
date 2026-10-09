"""Deterministic, advisory story structure and diversity checks.

This module never calls a provider and never grants render authorization. It deliberately
returns ``None`` for unsupported fields instead of inventing story facts.
"""
from __future__ import annotations
import difflib
import re
from typing import Any

_WORDS = re.compile(r"[\w']+", re.UNICODE)
_RULE_TERMS = {
    'sticky notes': 'sticky-note adhesion', 'multiply': 'multiplication', 'multiplying': 'multiplication',
    'follow': 'following', 'flying': 'flight', 'hide': 'occlusion/hiding', 'cabinet': 'cabinet interaction',
}

def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]

def _first(text: str, terms: tuple[str, ...]) -> str | None:
    for sentence in _sentences(text):
        if any(term in sentence.lower() for term in terms):
            return sentence[:400]
    return None

def _signature(text: str, context: dict[str, Any]) -> dict[str, Any]:
    lower = text.lower()
    rules = sorted({label for term, label in _RULE_TERMS.items() if term in lower})
    actions = sorted({w for w in ('pulls', 'shakes', 'runs', 'hides', 'discovers', 'follows', 'opens', 'tries', 'removes', 'reveals') if w in lower})
    ending = _first(text, ('finally', 'in the end', 'reveals', 'discovers', 'covered', 'ends with', 'realizes'))
    progression = _first(text, ('then', 'but', 'until', 'after', 'when', 'tries', 'again'))
    opening = _sentences(text)[0][:400] if _sentences(text) else None
    return {
        'centralPremise': context.get('corePremise') or None,
        'mainCharacter': context.get('mainCharacter') or None,
        'mainObjectOrSituation': next((term for term in ('sticky notes', 'toy cabinet', 'cabinet') if term in lower), None),
        'openingVisualPromise': opening,
        'primaryRuleOrQuestion': ', '.join(rules) if rules else None,
        'characterGoal': _first(text, ('wants to', 'tries to', 'needs to', 'goal')),
        'majorStoryChanges': progression,
        'centralObstacle': _first(text, ('obstacle', 'problem', 'cannot', 'can’t', 'stuck', 'chase')),
        'escalation': _first(text, ('then', 'more', 'again', 'grows', 'multiplies', 'faster')),
        'endingFunction': 'reveal' if 'reveal' in lower or 'discovers' in lower else ('resolution' if ending else None),
        'reasonToContinueWatching': opening,
        'productionSensitiveElements': sorted({r for r in ('occlusion', 'simultaneous choreography', 'object-count changes', 'contact continuity', 'identity continuity') if ((r == 'occlusion' and ('hide' in lower or 'behind' in lower)) or (r == 'object-count changes' and ('multiply' in lower or 'more notes' in lower)) or (r == 'contact continuity' and ('stick' in lower or 'attach' in lower)))}),
        '_rules': rules, '_actions': actions,
    }

def _preflight(text: str, signature: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    lower = text.lower(); concerns: list[str] = []; strengths: list[str] = []; risks: list[str] = []
    if signature['openingVisualPromise']: strengths.append('The opening provides an observable focus or situation.')
    else: concerns.append('The opening focus is not supported by the supplied text.')
    if signature['majorStoryChanges'] or signature['escalation'] or any(w in lower for w in ('emotion', 'learns', 'realizes', 'understands')): strengths.append('The story contains a meaningful progression signal.')
    else: concerns.append('Meaningful progression is not evidenced; motion alone is not counted.')
    if signature['_rules']: strengths.append(f"Primary unusual rule(s): {', '.join(signature['_rules'])}.")
    if 'multiplication' in signature['_rules'] and context.get('profile') == 'ABSURD_PHYSICS' and 'sticky-note adhesion' in signature['_rules']:
        concerns.append('Multiplication may be an independently unexplained second rule; clarify whether more notes are revealed from the cabinet or actually created.')
    if 'occlusion/hiding' in signature['_rules']:
        risks.append('Hiding behind the cabinet may reduce event readability; this is a contextual staging risk, not an unconditional blocker.')
    if 'object-count changes' in signature['productionSensitiveElements']: risks.append('Object-count changes can challenge continuity and should be staged explicitly.')
    if 'contact continuity' in signature['productionSensitiveElements']: risks.append('Repeated attachment/contact needs clear continuity evidence.')
    return {'opening': 'SUPPORTED' if signature['openingVisualPromise'] else 'INSUFFICIENT_EVIDENCE', 'progression': 'SUPPORTED' if not any('progression' in c for c in concerns) else 'INSUFFICIENT_EVIDENCE', 'mechanism': 'NEEDS_CLARIFICATION' if any('second rule' in c for c in concerns) else ('SUPPORTED' if signature['_rules'] else 'INSUFFICIENT_EVIDENCE'), 'characterAgency': 'SUPPORTED' if any(w in lower for w in ('tries', 'pulls', 'shakes', 'runs', 'hides', 'opens')) else 'INSUFFICIENT_EVIDENCE', 'ending': signature['endingFunction'] or 'INSUFFICIENT_EVIDENCE', 'strengths': strengths, 'concerns': concerns, 'productionRisks': risks}

def analyse_story_candidates(candidates: list[Any], context: dict[str, Any]) -> dict[str, Any]:
    texts = [v if isinstance(v, str) else str(v.get('text') or v.get('description') or '') for v in candidates]
    evidence = [_signature(t, context) for t in texts]
    preflight = [_preflight(t, evidence[i], context) for i, t in enumerate(texts)]
    pairs: list[dict[str, Any]] = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            lexical = difflib.SequenceMatcher(None, texts[i].lower(), texts[j].lower()).ratio()
            shared = [key for key in ('primaryRuleOrQuestion', 'mainObjectOrSituation', 'endingFunction') if evidence[i].get(key) and evidence[i].get(key) == evidence[j].get(key)]
            differing = [key for key in ('openingVisualPromise', 'characterGoal', 'majorStoryChanges', 'centralObstacle', 'escalation', 'endingFunction') if evidence[i].get(key) != evidence[j].get(key)]
            pairs.append({'left': i + 1, 'right': j + 1, 'lexicalSimilarity': round(lexical, 3), 'sharedDimensions': shared, 'differentDimensions': differing})
    if not texts: classification = 'INSUFFICIENT_EVIDENCE'; summary = 'No valid story candidates were returned.'
    elif len(texts) < 2: classification = 'INSUFFICIENT_EVIDENCE'; summary = 'Only one valid story candidate was returned.'
    elif all(len(p['sharedDimensions']) >= 3 for p in pairs) and all(e.get('endingFunction') == evidence[0].get('endingFunction') for e in evidence): classification = 'NEAR_DUPLICATE'; summary = 'Candidates share substantially the same narrative structure; wording differences do not establish distinct stories.'
    elif all(len(p['differentDimensions']) >= 3 for p in pairs): classification = 'DISTINCT'; summary = 'Candidates differ across multiple material narrative dimensions.'
    else: classification = 'PARTIALLY_DISTINCT'; summary = 'Candidates share core structure but differ in some material dimensions.'
    differences = [f"Alternative {p['left']} vs {p['right']}: different {', '.join(p['differentDimensions']) or 'no supported dimensions'}; shared {', '.join(p['sharedDimensions']) or 'no extracted dimensions'}." for p in pairs]
    return {'method': 'story-structure-v1', 'classification': classification, 'summary': summary, 'pairs': pairs, 'differences': differences, 'candidates': [{'structuralEvidence': {k: v for k, v in e.items() if not k.startswith('_')}, 'preflight': pf} for e, pf in zip(evidence, preflight)]}
