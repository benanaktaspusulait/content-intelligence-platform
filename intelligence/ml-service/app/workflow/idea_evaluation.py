"""Source-bound IDEA projection over existing rules. No providers, parser or invented story beats.

Source presence is a mechanical result, never a creative PASS. Rules whose inputs
are story-plan measurements are not run on empty defaults. Semantic calls are
blocked before any SDK/provider is constructed, independent of server settings.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.config import settings
from app.rules.rule_engine import RuleEngine, SemanticEvidenceUnavailable
from app.rules.rule_versioning import RuleVersionManager

VERSION = 'idea-source-evidence-v2'
# Gate IDs stay stable; policy IDs now refer to real registry entries.
CHECKS = (
    ('FRAME_ZERO_CAUSAL_LEGIBILITY', 'HOOK_004', ('firstStaticFrame', 'frameZeroProblem', 'everydayGoal', 'impossibleRule'), 'SEMANTIC_JUDGMENT_REQUIRED', 'semantic', 'Opening goal/obstruction causality requires semantic judgment; actual pixel legibility requires a verified first frame.'),
    ('VISIBLE_EVERYDAY_GOAL', 'GOAL_001', ('everydayGoal', 'frameZeroProblem', 'impossibleRule', 'proposedProgression', 'payoff'), 'SEMANTIC_JUDGMENT_REQUIRED', 'semantic', 'Goal text is available; believability, rule obstruction and action/ending alignment are semantic, not field-presence checks.'),
    ('ONE_IMPOSSIBLE_RULE', 'CONCEPT_007', ('impossibleRule', 'concept', 'discovery', 'proposedProgression', 'payoff'), 'SEMANTIC_JUDGMENT_REQUIRED', 'semantic', 'A stated rule is not a verified count of independent mechanics or a consistency verdict.'),
    ('IMMEDIATE_CHARACTER_TROUBLE', 'HOOK_004', ('firstStaticFrame', 'frameZeroProblem', 'everydayGoal'), 'SEMANTIC_JUDGMENT_REQUIRED', 'semantic', 'A stated problem is available; whether the opening visibly obstructs Arda’s goal is not mechanically provable.'),
    ('MEANINGFUL_PROGRESSION', 'PROGRESSION_006', ('proposedProgression', 'concept', 'discovery', 'payoff'), 'SEMANTIC_JUDGMENT_REQUIRED', 'story', 'Existing PROGRESSION_006 needs canonical actor-bound attempts/primaryVerb labels. IDEA prose cannot supply those measurements. IDEA progression potential still requires semantic judgment.'),
    ('DISTINCT_CONSEQUENCES', 'CONCEPT_006', ('proposedProgression', 'discovery', 'impossibleRule'), 'SEMANTIC_JUDGMENT_REQUIRED', 'story', 'Existing CONCEPT_006 counts canonical visual consequences. Splitting IDEA prose into sentences/semicolons would invent consequence counts. Semantic distinction remains unverified.'),
    ('FINAL_VISUAL_PAYOFF', 'PAYOFF_004', ('payoff', 'firstStaticFrame', 'everydayGoal', 'impossibleRule'), 'SEMANTIC_JUDGMENT_REQUIRED', 'story', 'Existing PAYOFF_004 compares measured beat salience at a timed payoff. IDEA has no measured beat intensities or payoff boundary. Payoff strength needs semantic judgment; visual execution is separate.'),
    ('RETENTION_REPLAY', 'PAYOFF_006', ('viewerQuestion', 'firstStaticFrame', 'payoff'), 'SEMANTIC_JUDGMENT_REQUIRED', 'story', 'Existing PAYOFF_006 checks a planned loop/cut and ending, not audience retention or IDEA replay potential. No timed ending/loop evidence is present; a viewerQuestion is not an audience outcome.'),
    ('PRODUCTION_FEASIBILITY', 'PRODUCIBILITY_003', ('productionRisk', 'firstStaticFrame', 'proposedProgression', 'payoff'), 'SEMANTIC_JUDGMENT_REQUIRED', 'risk', 'The existing lexical fragile-interaction diagnostic can run on source text. Its tags are heuristic concerns, not proof that Seedance can or cannot execute this IDEA; a production plan is not yet available.'),
    ('ORIGINALITY_DUPLICATE_ENGINE', 'ENGINE_SILHOUETTE_DUPLICATE', ('concept', 'impossibleRule', 'firstStaticFrame', 'proposedProgression', 'payoff'), 'VISUAL_EVIDENCE_REQUIRED', 'visual', 'Existing silhouette comparison requires source-bound verified first/final frames or a verified creative fingerprint and winner corpus. Identical rule strings are not duplicate-engine proof.'),
)


def payload_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode()).hexdigest()


def source_spans(payload: dict[str, Any], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    result = []
    for field in fields:
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            result.append({'field': field, 'path': f'payload.{field}', 'start': 0, 'end': len(value),
                           'offsetUnit': 'UNICODE_CODE_POINT', 'quote': value,
                           'fieldSha256': hashlib.sha256(value.encode()).hexdigest()})
    return result


class _LocalIdeaRules(RuleEngine):
    """Operation-level authorization boundary; no creative thresholds/policies change."""
    def _semantic_check(self, check: Any, *args: Any, **kwargs: Any) -> Any:
        raise SemanticEvidenceUnavailable(
            'Existing semantic evaluator was reached, but this IDEA operation authorizes zero provider calls. No verified semantic judgment is bound to this candidate.')


def _invoke(engine: RuleEngine, rule: dict[str, Any], ir: dict[str, Any]) -> dict[str, Any]:
    rule_id = rule['id']
    try:
        row = engine.evaluators[rule_id](ir, rule)
        return {'ruleId': rule_id, 'invoked': True, 'completed': True,
                'outcome': row.outcome.value, 'reason': row.message, 'details': row.details,
                'implementation': f'RuleEngine.{engine.evaluators[rule_id].__name__}', 'providerCalls': 0}
    except SemanticEvidenceUnavailable as error:
        return {'ruleId': rule_id, 'invoked': True, 'completed': False, 'outcome': 'UNKNOWN',
                'reasonCode': 'SEMANTIC_PROVIDER_NOT_AUTHORIZED', 'reason': str(error),
                'implementation': f'RuleEngine.{engine.evaluators[rule_id].__name__}', 'providerCalls': 0}


def evaluate_idea(candidate: dict[str, Any], batch: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    payload = candidate.get('payload')
    if not isinstance(payload, dict) or not candidate.get('candidateId'):
        raise ValueError('Persisted IDEA identity and structured source payload required')
    version = RuleVersionManager(settings.rules_dir).get_latest_version()
    engine = _LocalIdeaRules(str(settings.rules_dir / f'RULESET_{version}.yaml'))
    registry = {r['id']: r for r in engine.ruleset['rules']}
    target = context.get('targetConfiguration') or {}
    profile = target.get('contentProfile') or context.get('profile') or 'UNKNOWN'
    character = (context.get('characterRecord') or {}).get('name') or context.get('mainCharacter') or ''
    # These are source fragments consumed by semantic rule interfaces and lexical
    # risk diagnostics, not a timed story, beat count, action label or consequence claim.
    ir = {'metadata': {'contentProfile': profile, 'analysisStage': 'IDEA', 'sourceIsTimedStory': False},
          'characters': {'primary': character}, 'coreMechanic': {'physicalRule': payload.get('impossibleRule', '')},
          'goalEvidence': {'description': payload.get('everydayGoal', ''), 'sourceField': 'everydayGoal', 'scope': 'STATED_IDEA_GOAL_ONLY'},
          'hook': {'anomaly': payload.get('frameZeroProblem', '')}, 'visualEvidence': {}, 'creativeFingerprint': {}}
    gates = []
    for gate_id, rule_id, fields, category, mode, requirement in CHECKS:
        spans = source_spans(payload, fields)
        missing = [field for field in fields if not any(s['field'] == field for s in spans)]
        rule = registry.get(rule_id)
        registered = rule is not None and rule_id in engine.evaluators
        excluded = bool(rule and not engine._rule_applies(rule, ir))
        implementation = f'RuleEngine.{engine.evaluators[rule_id].__name__}' if registered else None
        outcome = 'UNKNOWN'
        dispatch = {'ruleId': rule_id, 'invoked': False, 'completed': False, 'implementation': implementation, 'providerCalls': 0}
        applicability = {'stage': 'IDEA', 'profile': profile, 'declaredRuleStage': (rule or {}).get('evaluation_stage', engine.ruleset.get('default_evaluation_stage', 'PRE_RENDER')),
                         'status': 'NOT_APPLICABLE' if excluded else 'APPLICABLE', 'policyExcluded': excluded,
                         'policyVersion': version, 'excludedContentProfiles': (rule or {}).get('excludedContentProfiles', [])}
        concern = []
        if not registered:
            reason_code, reason = 'EVALUATOR_NOT_REGISTERED', f'{rule_id} has no registered canonical evaluator. No verdict can be fabricated.'
        elif excluded:
            outcome = 'NOT_APPLICABLE'
            reason_code, reason = 'POLICY_NOT_APPLICABLE', 'Existing ruleset profile/scope/retirement applicability excludes this rule; this is not a PASS.'
        elif missing:
            reason_code, reason = 'SOURCE_FIELDS_MISSING', 'Missing original source fields: ' + ', '.join(missing)
        elif mode == 'semantic':
            # Opening checks receive exactly opening/problem fragments; goal/rule
            # checks receive only their declared original fields. No timestamps.
            mapped_fragments = [dict(action=s['quote'], consequence=s['quote'], sourceField=s['field'], evidenceScope='IDEA_SOURCE_FRAGMENT') for s in spans]
            if rule_id == 'HOOK_004':
                # HOOK_004 reads only its first two input entries; retain goal,
                # obstruction and rule together rather than dropping fields 3+4.
                mapped_fragments = [dict(action='\n'.join(s['quote'] for s in spans), consequence='', sourceFields=list(fields), evidenceScope='IDEA_SOURCE_FRAGMENT')]
            mapped = dict(ir, beats=mapped_fragments)
            dispatch = _invoke(engine, rule, mapped)
            reason_code = dispatch.get('reasonCode', 'SEMANTIC_JUDGMENT_UNAVAILABLE')
            reason = requirement + ' ' + dispatch['reason']
            # A semantic rule must never acquire a non-UNKNOWN result from this
            # no-judgment adapter (including profile-specific short circuits).
        elif mode == 'risk':
            dispatch = _invoke(engine, rule, dict(ir, beats=[dict(action=s['quote'], consequence='', sourceField=s['field'], evidenceScope='IDEA_SOURCE_FRAGMENT') for s in spans]))
            reason_code, reason = 'HEURISTIC_ONLY_NOT_FEASIBILITY_PROOF', requirement
            for tag in dispatch.get('details', {}).get('riskTags', []):
                matches = []
                for span in spans:
                    for word in engine._FRAGILE_INTERACTION_RISK_TAGS[tag]:
                        match = re.search(re.escape(word), span['quote'], re.IGNORECASE)
                        if match:
                            matches.append({**span, 'start': match.start(), 'end': match.end(), 'quote': match.group()})
                concern.append({'kind': 'HEURISTIC_CONCERN', 'ruleId': rule_id, 'riskTag': tag, 'sourceSpans': matches,
                                'reason': 'Existing substring diagnostic only; may include lexical false positives. Not a confirmed creative failure.'})
        elif mode == 'visual':
            dispatch = _invoke(engine, rule, ir)
            reason_code, reason = 'VERIFIED_VISUAL_COMPARISON_MISSING', requirement
        else:
            reason_code, reason = 'STORY_CONTRACT_NOT_IDEA_EVIDENCE', requirement
        if gate_id == 'ORIGINALITY_DUPLICATE_ENGINE' and isinstance(payload.get('impossibleRule'), str):
            same = [p for p in batch if isinstance(p.get('impossibleRule'), str) and p['impossibleRule'].strip().casefold() == payload['impossibleRule'].strip().casefold()]
            if len(same) > 1:
                concern.append({'kind': 'HEURISTIC_CONCERN', 'reason': 'Exact rule text repeats in this batch; no semantic or silhouette duplication verdict follows.', 'sourceSpans': source_spans(payload, ('impossibleRule',))})
        dispatch.update(registered=registered, providerDispatchAllowed=False, inputSourceFields=list(fields) if mode in ('semantic', 'risk') else [])
        gates.append({'gate': gate_id, 'policy': rule_id, 'status': outcome, 'mandatory': True,
                      'evidence': '\n'.join(s['quote'] for s in spans), 'sourceSpans': spans,
                      'sourceCheck': {'status': 'PASS' if not missing else 'UNKNOWN', 'scope': 'EXACT_SOURCE_BINDING_ONLY', 'missingFields': missing, 'category': 'TEXT_VERIFIABLE', 'reason': 'Validates only original field presence and exact quote/span binding; never creative merit.'},
                      'category': category, 'requiredEvidence': requirement, 'reasonCode': reason_code, 'reason': reason,
                      'evaluator': dispatch, 'applicability': applicability, 'concerns': concern,
                      'laterStageEvidence': (['Canonical story/production measurements are deferred, not required inputs for IDEA admission; IDEA potential needs semantic judgment instead'] if mode == 'story' else []),
                      'visualEvidenceRequirement': ('Verified first/final frame comparison' if mode == 'visual' else 'Actual image legibility is separate from textual intent' if gate_id == 'FRAME_ZERO_CAUSAL_LEGIBILITY' else None)})
    counts = {status: sum(g['status'] == status for g in gates) for status in ('PASS', 'FAIL', 'UNKNOWN', 'NOT_APPLICABLE')}
    eligible = counts['PASS'] > 0 and not counts['FAIL'] and not counts['UNKNOWN']
    return {'candidateId': candidate['candidateId'], 'candidateRevision': candidate.get('revision', 1),
            'sourcePayloadSha256': payload_hash(payload), 'sourceIdeaRevision': candidate.get('sourceIdeaRevision'),
            'revision': 1, 'policyVersion': VERSION, 'canonicalRulesetVersion': version, 'profile': profile, 'stage': 'IDEA',
            'status': 'REJECTED' if counts['FAIL'] else 'PENDING_EVIDENCE' if counts['UNKNOWN'] else 'EVALUATED',
            'eligible': eligible, 'gates': gates, 'providerCalls': 0, 'additionalCostUsd': 0,
            'rejectionReasons': [g['reason'] for g in gates if g['status'] == 'FAIL'],
            'evidenceGaps': [g['reason'] for g in gates if g['status'] == 'UNKNOWN'],
            'summary': {'mandatoryChecks': len(gates), 'sourceAvailableChecks': sum(g['sourceCheck']['status'] == 'PASS' for g in gates),
                        'sourceBindingChecksExecuted': len(gates), 'sourceBindingPasses': sum(g['sourceCheck']['status'] == 'PASS' for g in gates),
                        'canonicalEvaluatorsInvoked': sum(g['evaluator']['invoked'] for g in gates),
                        'canonicalEvaluatorsCompleted': sum(g['evaluator']['completed'] for g in gates),
                        'canonicalChecksUnableToComplete': sum(not g['evaluator']['completed'] and g['status'] != 'NOT_APPLICABLE' for g in gates),
                        'heuristicConcernCount': sum(len(g['concerns']) for g in gates), 'creativeOutcomes': counts},
            'smallestSupportedNextStep': 'Preserve these IDEA sources and editorial decisions. Inspect exact source spans and resolve interpretation with a source-bound independent review; current paid STORY_REVIEW requires STORY candidate IDs and is not an IDEA evidence ingestion route. No supported provider-free IDEA semantic/visual verifier can currently close these gates. A separately authorized IDEA-compatible review/evidence path is required; do not generate STORY or images to manufacture applicability.'}
