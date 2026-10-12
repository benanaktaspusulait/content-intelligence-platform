"""Deterministic, advisory story structure and diversity checks.

This module never calls a provider and never grants render authorization. It deliberately
returns ``None`` for unsupported fields instead of inventing story facts.

Story-stage assessment is preliminary and never authorizes rendering.
Step 5 remains the canonical full production-quality evaluation stage.
"""
from __future__ import annotations
import difflib
import re
from typing import Any

from .story_evidence import extract_story_evidence

_WORDS = re.compile(r"[\w']+", re.UNICODE)
_RULE_TERMS = {
    'sticky notes': 'sticky-note adhesion', 'multiply': 'multiplication', 'multiplying': 'multiplication',
    'follow': 'following', 'flying': 'flight', 'hide': 'occlusion/hiding', 'cabinet': 'cabinet interaction',
}

_EVENT_ALIASES = {
    'stick': 'adhere', 'sticks': 'adhere', 'stuck': 'adhere', 'attached': 'adhere', 'attach': 'adhere',
    'peel': 'remove', 'peels': 'remove', 'remove': 'remove', 'removes': 'remove', 'pull': 'remove', 'pulls': 'remove', 'yank': 'remove', 'yanks': 'remove',
    'multiply': 'multiply', 'multiplies': 'multiply', 'multiplying': 'multiply', 'cover': 'cover', 'covers': 'cover', 'covered': 'cover',
    'hide': 'hide', 'hides': 'hide', 'behind': 'hide', 'follow': 'follow', 'follows': 'follow',
    'try': 'attempt', 'tries': 'attempt', 'attempts': 'attempt', 'discover': 'discover', 'discovers': 'discover',
    'reveal': 'reveal', 'reveals': 'reveal', 'shake': 'shake', 'shakes': 'shake', 'open': 'open', 'opens': 'open',
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
    actions = sorted({canonical for word, canonical in _EVENT_ALIASES.items() if re.search(rf"\b{re.escape(word)}\b", lower)})
    event_sequence = [canonical for sentence in _sentences(text) for word, canonical in _EVENT_ALIASES.items() if re.search(rf"\b{re.escape(word)}\b", sentence.lower())]
    # Preserve order while collapsing repeated synonyms; the sequence is a
    # compact description of what changes, independent of camera vocabulary.
    event_sequence = list(dict.fromkeys(event_sequence))
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
        'eventSequence': event_sequence,
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

def evaluate_story_candidate(text: str, context: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    """Evaluate a single story candidate and produce strengths, risks, and unknowns.

    This is a preliminary story-stage assessment. It never authorizes rendering
    and never claims visual evidence from text alone.

    Returns a dict with:
    - candidateId, fingerprint
    - strengths: evidence-backed positive observations
    - risks: evidence-backed weaknesses or concerns
    - unknown: dimensions that cannot be determined from text alone
    """
    ev = extract_story_evidence(text, context)
    strengths: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []

    # ── Character goal ──
    if ev['characterGoal']:
        strengths.append({
            'dimension': 'characterGoal',
            'family': 'concept_strength',
            'outcome': 'PASS',
            'severity': 'INFO',
            'message': 'The story describes a character situation or goal.',
            'evidence': ev['characterGoal'][:150],
        })
    else:
        unknown.append({
            'dimension': 'characterGoal',
            'family': 'concept_strength',
            'outcome': 'UNKNOWN',
            'message': 'Character goal or situation cannot be confidently extracted from the text.',
        })

    # ── Obstacle ──
    if ev['obstacle']:
        strengths.append({
            'dimension': 'obstacle',
            'family': 'concept_strength',
            'outcome': 'PASS',
            'severity': 'INFO',
            'message': 'The story describes an obstacle or challenge.',
            'evidence': ev['obstacle'][:150],
        })
    else:
        unknown.append({
            'dimension': 'obstacle',
            'family': 'concept_strength',
            'outcome': 'UNKNOWN',
            'message': 'Obstacle or challenge cannot be confidently identified from the text.',
        })

    # ── Character initiative ──
    if len(ev['distinctActions']) >= 2:
        strengths.append({
            'dimension': 'characterInitiative',
            'family': 'concept_strength',
            'outcome': 'PASS',
            'severity': 'INFO',
            'message': f'The character takes {len(ev["distinctActions"])} distinct actions.',
            'evidence': ', '.join(ev['distinctActions'][:5]),
        })
    elif len(ev['distinctActions']) == 1:
        risks.append({
            'dimension': 'characterInitiative',
            'family': 'concept_strength',
            'outcome': 'WARNING',
            'severity': 'WARNING',
            'message': 'The character appears to take only one type of action.',
            'evidence': ev['distinctActions'][0] if ev['distinctActions'] else '',
        })
    else:
        unknown.append({
            'dimension': 'characterInitiative',
            'family': 'concept_strength',
            'outcome': 'UNKNOWN',
            'message': 'Character actions cannot be confidently extracted from the text.',
        })

    # ── Progression ──
    if ev['progressionSignal']:
        strengths.append({
            'dimension': 'progression',
            'family': 'progression',
            'outcome': 'PASS',
            'severity': 'INFO',
            'message': 'The story contains cause-and-effect progression signals.',
        })
    else:
        unknown.append({
            'dimension': 'progression',
            'family': 'progression',
            'outcome': 'UNKNOWN',
            'message': 'Meaningful progression cannot be confirmed from text alone; motion alone is not counted.',
        })

    # ── Escalation ──
    if ev['escalationSignal']:
        strengths.append({
            'dimension': 'escalation',
            'family': 'escalation',
            'outcome': 'PASS',
            'severity': 'INFO',
            'message': 'The story contains escalation signals (increasing intensity or complexity).',
        })
    else:
        unknown.append({
            'dimension': 'escalation',
            'family': 'escalation',
            'outcome': 'UNKNOWN',
            'message': 'Escalation cannot be confirmed from text alone.',
        })

    # ── Distinct attempts ──
    if len(ev['distinctActions']) >= 3:
        strengths.append({
            'dimension': 'distinctAttempts',
            'family': 'progression',
            'outcome': 'PASS',
            'severity': 'INFO',
            'message': f'The story contains {len(ev["distinctActions"])} distinct action types, suggesting multiple attempts or strategies.',
        })
    elif len(ev['distinctActions']) >= 2:
        unknown.append({
            'dimension': 'distinctAttempts',
            'family': 'progression',
            'outcome': 'UNKNOWN',
            'message': f'The story contains {len(ev["distinctActions"])} action types; whether these represent distinct attempts is uncertain without production plan.',
        })

    # ── Ending ──
    if ev['endingEvent']:
        if ev['endingClarity'] == 'PRESENT':
            strengths.append({
                'dimension': 'endingEvent',
                'family': 'final_payoff',
                'outcome': 'PASS',
                'severity': 'INFO',
                'message': 'The story describes a final event.',
                'evidence': ev['endingEvent'][:150],
            })
            unknown.append({
                'dimension': 'endingPayoff',
                'family': 'final_payoff',
                'outcome': 'UNKNOWN',
                'message': 'A final event is described, but its creative effectiveness or audience payoff cannot be determined from text alone.',
            })
        elif ev['endingClarity'] == 'AMBIGUOUS':
            unknown.append({
                'dimension': 'endingEvent',
                'family': 'final_payoff',
                'outcome': 'UNKNOWN',
                'message': 'The story has a final sentence, but whether it constitutes a clear ending is ambiguous.',
                'evidence': ev['endingEvent'][:150],
            })
    else:
        unknown.append({
            'dimension': 'endingEvent',
            'family': 'final_payoff',
            'outcome': 'UNKNOWN',
            'message': 'Ending event cannot be confidently identified from the text.',
        })

    # ── Repetition risk ──
    if ev['repetitionRisk']:
        risks.append({
            'dimension': 'repetitionRisk',
            'family': 'visual_novelty',
            'outcome': 'WARNING',
            'severity': 'WARNING',
            'message': 'The story repeats the same action without clearly new consequences. This may reduce visual novelty.',
        })

    # ── Rule consistency (limited) ──
    if ev['ruleConsistency'].get('consistent'):
        unknown.append({
            'dimension': 'ruleConsistency',
            'family': 'consistency',
            'outcome': 'UNKNOWN',
            'message': 'No obvious rule contradictions detected, but full consistency check requires production plan analysis.',
        })

    # ── Visual quality (always unknown at story stage) ──
    unknown.append({
        'dimension': 'visualLegibility',
        'family': 'visual_novelty',
        'outcome': 'NOT_EVALUATED',
        'message': 'Frame-zero visual legibility and hook strength cannot be assessed from story text alone.',
    })
    unknown.append({
        'dimension': 'aiProducibility',
        'family': 'ai_producibility',
        'outcome': 'NOT_EVALUATED',
        'message': 'AI producibility requires a production prompt and cannot be assessed from story text alone.',
    })
    unknown.append({
        'dimension': 'pacing',
        'family': 'progression',
        'outcome': 'NOT_EVALUATED',
        'message': 'Pacing and beat timing cannot be assessed without a production plan.',
    })

    return {
        'candidateId': candidate_id,
        'fingerprint': ev['fingerprint'],
        'strengths': strengths,
        'risks': risks,
        'unknown': unknown,
        'evidence': ev,
    }


def analyse_story_candidates(candidates: list[Any], context: dict[str, Any]) -> dict[str, Any]:
    texts = [v if isinstance(v, str) else str(v.get('text') or v.get('description') or '') for v in candidates]
    candidate_ids = []
    for v in candidates:
        if isinstance(v, dict):
            candidate_ids.append(v.get('candidateId', f'candidate-{len(candidate_ids)+1}'))
        else:
            candidate_ids.append(f'candidate-{len(candidate_ids)+1}')

    # Extract story evidence for each candidate
    story_evidence = [extract_story_evidence(t, context) for t in texts]

    # Build per-candidate assessments
    assessments = [
        evaluate_story_candidate(t, context, candidate_ids[i])
        for i, t in enumerate(texts)
    ]

    # Legacy signature and preflight (preserved for backward compatibility)
    evidence = [_signature(t, context) for t in texts]
    preflight = [_preflight(t, evidence[i], context) for i, t in enumerate(texts)]

    # Pairwise comparison using story evidence for material dimensions
    pairs: list[dict[str, Any]] = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            lexical = difflib.SequenceMatcher(None, texts[i].lower(), texts[j].lower()).ratio()

            # Shared dimensions from legacy signature
            shared = [key for key in ('primaryRuleOrQuestion', 'mainObjectOrSituation', 'endingFunction')
                      if evidence[i].get(key) and evidence[i].get(key) == evidence[j].get(key)]
            if evidence[i].get('eventSequence') and evidence[i].get('eventSequence') == evidence[j].get('eventSequence'):
                shared.append('causalEventProgression')

            # Material different dimensions from story evidence
            ev_i = story_evidence[i]
            ev_j = story_evidence[j]

            differing: list[str] = []

            # Compare event sequences (structural difference)
            # eventSequence is list of lists (actions per sentence), so flatten to tuples for set ops
            seq_i = [tuple(s) for s in ev_i.get('eventSequence', [])]
            seq_j = [tuple(s) for s in ev_j.get('eventSequence', [])]
            structural_difference = bool(set(seq_i) ^ set(seq_j))

            # Compare distinct actions
            actions_i = set(ev_i.get('distinctActions', []))
            actions_j = set(ev_j.get('distinctActions', []))
            if actions_i != actions_j and len(actions_i ^ actions_j) >= 2:
                differing.append('characterActions')

            # Compare escalation
            if ev_i.get('escalationSignal') != ev_j.get('escalationSignal'):
                differing.append('escalation')

            # Compare ending clarity
            if ev_i.get('endingClarity') != ev_j.get('endingClarity'):
                differing.append('endingClarity')

            # Compare ending events (textual difference in final event)
            end_i = ev_i.get('endingEvent')
            end_j = ev_j.get('endingEvent')
            if end_i and end_j and end_i != end_j:
                differing_lexical = difflib.SequenceMatcher(None, end_i.lower(), end_j.lower()).ratio()
                if differing_lexical < 0.7:
                    differing.append('endingEvent')

            # Compare progression signals
            if ev_i.get('progressionSignal') != ev_j.get('progressionSignal'):
                differing.append('progression')

            # Compare repetition risk
            if ev_i.get('repetitionRisk') != ev_j.get('repetitionRisk'):
                differing.append('repetitionRisk')

            # Legacy differing dimensions (only if structural difference supports them)
            legacy_differing = [key for key in ('openingVisualPromise', 'characterGoal', 'majorStoryChanges',
                                                  'centralObstacle', 'escalation', 'endingFunction')
                                if evidence[i].get(key) != evidence[j].get(key)]
            if not structural_difference:
                legacy_differing = [key for key in legacy_differing if key in ('endingFunction',)
                                     and evidence[i].get(key) != evidence[j].get(key)]

            # Merge legacy and story-evidence differing dimensions
            all_differing = list(dict.fromkeys(differing + legacy_differing))

            # Build dimension descriptions for supported differences
            dim_descriptions: dict[str, dict[str, str]] = {}
            if 'endingEvent' in all_differing:
                end_i = ev_i.get('endingEvent')
                end_j = ev_j.get('endingEvent')
                if end_i and end_j:
                    dim_descriptions['endingEvent'] = {
                        str(i + 1): end_i[:200],
                        str(j + 1): end_j[:200],
                    }

            pairs.append({
                'left': i + 1,
                'right': j + 1,
                'lexicalSimilarity': round(lexical, 3),
                'sharedDimensions': list(dict.fromkeys(shared)),
                'differentDimensions': all_differing,
                'eventSequenceMatch': not structural_difference,
                'dimensionDescriptions': dim_descriptions if dim_descriptions else None,
            })

    # Aggregate classification
    if not texts:
        classification = 'INSUFFICIENT_EVIDENCE'
        summary = 'No valid story candidates were returned.'
    elif len(texts) < 2:
        classification = 'INSUFFICIENT_EVIDENCE'
        summary = 'Only one valid story candidate was returned.'
    elif all(p.get('eventSequenceMatch') and len(p['sharedDimensions']) >= 2 for p in pairs):
        classification = 'NEAR_DUPLICATE'
        summary = 'Candidates share the same normalized mechanism and causal event progression; wording differences do not establish distinct stories.'
    elif all(p.get('lexicalSimilarity', 0) > 0.6 and p.get('eventSequenceMatch') for p in pairs):
        # High lexical similarity + same event structure = near-duplicate despite different words
        classification = 'NEAR_DUPLICATE'
        summary = 'Candidates share the same normalized mechanism and causal event progression; wording differences do not establish distinct stories.'
    elif all(len(p['differentDimensions']) >= 3 for p in pairs):
        # Check if differences are only surface-level (synonym swaps)
        all_surface_diffs = all(
            set(p.get('differentDimensions', [])) <= {'characterActions', 'endingEvent', 'openingVisualPromise'}
            for p in pairs
        )
        if all_surface_diffs:
            classification = 'PARTIALLY_DISTINCT'
            summary = 'Candidates differ mainly in wording and surface-level action vocabulary; narrative structure is similar.'
        else:
            classification = 'DISTINCT'
            summary = 'Candidates differ across multiple material narrative dimensions.'
    elif all(len(p['differentDimensions']) >= 3 for p in pairs):
        classification = 'DISTINCT'
        summary = 'Candidates differ across multiple material narrative dimensions.'
    elif any(len(p['differentDimensions']) > 0 for p in pairs):
        classification = 'PARTIALLY_DISTINCT'
        summary = 'Candidates share core structure but differ in some material dimensions.'
    else:
        classification = 'INSUFFICIENT_EVIDENCE'
        summary = 'No supported material differences or equivalences can be established from the available evidence.'

    differences = [
        f"Alternative {p['left']} vs {p['right']}: different {', '.join(p['differentDimensions']) or 'no supported dimensions'}; shared {', '.join(p['sharedDimensions']) or 'no extracted dimensions'}."
        for p in pairs
    ]
    variation_class = {
        'DISTINCT': 'MATERIAL_VARIATION',
        'PARTIALLY_DISTINCT': 'LIMITED_VARIATION',
        'NEAR_DUPLICATE': 'PARAPHRASE_OR_NEAR_DUPLICATE',
        'INSUFFICIENT_EVIDENCE': 'INSUFFICIENT_EVIDENCE',
    }[classification]

    # ── Deterministic candidate recommendation ──
    recommendation = _recommend_candidate(assessments, pairs)

    return {
        'method': 'story-structure-v1',
        'classification': classification,
        'variationClass': variation_class,
        'classificationReason': summary,
        'summary': summary,
        'pairs': pairs,
        'differences': differences,
        'recommendation': recommendation,
        'candidates': [
            {
                'structuralEvidence': {k: v for k, v in e.items() if not k.startswith('_')},
                'preflight': pf,
                'assessment': {
                    'candidateId': a['candidateId'],
                    'fingerprint': a['fingerprint'],
                    'strengths': a['strengths'],
                    'risks': a['risks'],
                    'unknown': a['unknown'],
                },
            }
            for e, pf, a in zip(evidence, preflight, assessments)
        ],
    }


def _recommend_candidate(assessments: list[dict[str, Any]], pairs: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce a deterministic preliminary recommendation from existing assessment evidence.

    Rules:
    1. No numeric scores — only comparative evidence.
    2. UNKNOWN does not count as FAIL.
    3. A candidate is preferred only when supported comparative evidence exists.
    4. If candidates are tied, report the tie.
    5. If evidence is insufficient, return no recommendation.

    Returns a dict with:
    - bestCandidateId: the preferred candidate or None
    - reason: why this candidate is preferred
    - whyNot: why other candidates are less preferred
    - stillUnknown: dimensions that cannot determine a winner
    - isTied: whether candidates are materially tied
    """
    if not assessments or len(assessments) < 2:
        return {
            'bestCandidateId': None,
            'reason': 'Not enough candidates to compare.',
            'whyNot': [],
            'stillUnknown': [],
            'isTied': False,
        }

    # Build per-candidate risk, strength, and unknown profiles
    candidate_risks: list[set[str]] = []
    candidate_strengths: list[set[str]] = []
    candidate_unknowns: list[set[str]] = []

    for a in assessments:
        risk_dims = {item.get('dimension') for item in a.get('risks', []) if item.get('outcome') in ('WARNING', 'FAIL')}
        strength_dims = {item.get('dimension') for item in a.get('strengths', []) if item.get('outcome') == 'PASS'}
        unknown_dims = {item.get('dimension') for item in a.get('unknown', []) if item.get('dimension')}
        candidate_risks.append(risk_dims)
        candidate_strengths.append(strength_dims)
        candidate_unknowns.append(unknown_dims)

    # stillUnknown: only dimensions that are unknown for ALL candidates.
    # A dimension unknown for one candidate but resolved for another should not
    # appear as "still unknown" — that would contradict the recommendation
    # when the resolved dimension is used as a differentiator.
    if candidate_unknowns:
        all_unknown_dims: set[str] = candidate_unknowns[0].copy()
        for u in candidate_unknowns[1:]:
            all_unknown_dims &= u
    else:
        all_unknown_dims = set()

    # Find candidates with fewer risks than others
    # A candidate is preferred if it has risks that others don't share (negative)
    # or if others have risks it doesn't have (positive differentiator)
    risk_counts = [len(r) for r in candidate_risks]
    min_risks = min(risk_counts)

    # Identify which candidates have the fewest risks
    lowest_risk_indices = [i for i, c in enumerate(risk_counts) if c == min_risks]

    # If all candidates have the same risk count, check for differentiating risks
    if len(lowest_risk_indices) == len(assessments):
        # All tied on risk count — check if any candidate has unique risks others don't have
        # Find risks that are NOT shared by all candidates
        if len(assessments) >= 2:
            # Find candidates that have risks others don't
            differentiating_risks: dict[int, set[str]] = {}
            for i in range(len(assessments)):
                # Risks that candidate i has but at least one other candidate doesn't
                unique_risks = set()
                for risk_dim in candidate_risks[i]:
                    for j in range(len(assessments)):
                        if i != j and risk_dim not in candidate_risks[j]:
                            unique_risks.add(risk_dim)
                if unique_risks:
                    differentiating_risks[i] = unique_risks

            # Find candidates that have FEWER unique risks (i.e., their risks are shared or they have none)
            # Prefer candidates whose risks are shared by all (common risks) over those with unique risks
            if differentiating_risks:
                # Candidates NOT in differentiating_risks have no unique risks — they are preferred
                clean_candidates = [i for i in range(len(assessments)) if i not in differentiating_risks]
                if clean_candidates and len(clean_candidates) < len(assessments):
                    # Some candidates have no unique risks — prefer them
                    best_idx = clean_candidates[0]
                    why_not = []
                    for i, unique_r in differentiating_risks.items():
                        why_not.append({
                            'candidateIndex': i + 1,
                            'reason': f'Has risk(s) not shared by all candidates: {", ".join(sorted(unique_r))}',
                        })
                    reason_parts = []
                    if min_risks == 0:
                        reason_parts.append('No supported risk signals detected')
                    else:
                        reason_parts.append(f'Shares the same risks as other candidates ({min_risks} risk(s))')
                    # Check if this candidate has unique strengths
                    if candidate_strengths[best_idx]:
                        reason_parts.append(f'Supported strengths: {", ".join(sorted(candidate_strengths[best_idx]))}')

                    return {
                        'bestCandidateId': assessments[best_idx]['candidateId'],
                        'reason': '; '.join(reason_parts),
                        'whyNot': why_not,
                        'stillUnknown': sorted(all_unknown_dims),
                        'isTied': False,
                    }

    # If one candidate has strictly fewer risks
    if len(lowest_risk_indices) == 1:
        best_idx = lowest_risk_indices[0]
        why_not = []
        for i in range(len(assessments)):
            if i != best_idx:
                extra_risks = candidate_risks[i] - candidate_risks[best_idx]
                if extra_risks:
                    why_not.append({
                        'candidateIndex': i + 1,
                        'reason': f'Has additional risk(s): {", ".join(sorted(extra_risks))}',
                    })
                else:
                    why_not.append({
                        'candidateIndex': i + 1,
                        'reason': f'Has {len(candidate_risks[i])} risk(s) vs {min_risks} for the recommended candidate',
                    })
        reason_parts = []
        if min_risks == 0:
            reason_parts.append('No supported risk signals detected')
        else:
            reason_parts.append(f'Fewest supported risks ({min_risks})')
        if candidate_strengths[best_idx]:
            reason_parts.append(f'Supported strengths: {", ".join(sorted(candidate_strengths[best_idx]))}')

        return {
            'bestCandidateId': assessments[best_idx]['candidateId'],
            'reason': '; '.join(reason_parts),
            'whyNot': why_not,
            'stillUnknown': sorted(all_unknown_dims),
            'isTied': False,
        }

    # All candidates are tied — same risk count and same risk profile
    # Check if they also share the same strengths
    all_same_strengths = all(candidate_strengths[i] == candidate_strengths[0] for i in range(len(assessments)))
    all_same_risks = all(candidate_risks[i] == candidate_risks[0] for i in range(len(assessments)))

    if all_same_strengths and all_same_risks:
        return {
            'bestCandidateId': None,
            'reason': 'No evidence-supported recommendation yet.',
            'whyNot': [],
            'stillUnknown': sorted(all_unknown_dims),
            'isTied': True,
        }

    # Tied on risks but different strengths — no defensible winner from strengths alone
    return {
        'bestCandidateId': None,
        'reason': 'Candidates share similar risk profiles; no single candidate is clearly preferred by the available evidence.',
        'whyNot': [],
        'stillUnknown': sorted(all_unknown_dims),
        'isTied': True,
    }
