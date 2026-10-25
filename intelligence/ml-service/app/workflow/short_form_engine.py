"""Opt-in, offline short-form plan screening, independent of canonical/long scores.

This extends the workflow's deterministic creative checks and reuses canonical
strategy normalization. Evidence is source text, never observed video or a viral
performance prediction. Unsupported language/mechanics require editorial review.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.quality.canonical_evidence import normalize_strategy_family

VERSION = "short-form-engine-v1"
_TIME = re.compile(r"(?im)^\s*(\d+(?:\.\d+)?)\s*[–—-]\s*(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)\b[^\n:]*:?\s*")
_STOP = re.compile(r"(?im)^\s*(?:MANDATORY|SAFETY|DIALOGUE\s*$|INSTAGRAM RETENTION|PRODUCTION NOTES|CAMERA LOCK)")
_RULES = {
    "INVERSION": r"upside[ -]down|\bflips?\b",
    "ADHESION": r"\bstick[sy]?\b|\bstuck\b|\bclings?\b",
    "GROWTH": r"\bgrows?\b|\blarger\b|\bgets? bigger\b|\bgiant\b|(?<!eyes )\bhuge\b",
    "RETURN": r"slides? back|returns? (?:to|into)|revers(?:es|ing) direction",
    "RECURRENCE": r"pops? (?:back )?open|springs? open|refuses? to (?:close|leave)",
    "AVOIDANCE": r"\bscares?\b|\bflee\b|\bflinch\w*\b",
    "MULTIPLICATION": r"\bmultipl\w*|\bdoubles?\b",
    "FLIGHT": r"\bflies\b|\blevitates?\b|\bfloats?\b",
    "TRANSFORMATION": r"turns? into|transforms? into",
}
_GOAL = r"\b(?:sit(?:s|ting)?|wash(?:es|ing)? (?:his |her |the )?hands|put\w* (?:a |the |his |her )?shoe on|close[sd]? (?:the |a )?(?:lid|box)|brush(?:es|ing)? (?:his |her |the )?hair|put\w* .{0,25}away|eat(?:s|ing)? (?:a |the |his |her )?(?:snack|food|berry|berries)|open[sd]? (?:the |a )?drawer|water(?:s|ing)? (?:the |a )?(?:garden|plant|seedling)|retrieve[sd]? .{0,20}ball|take[sd]? .{0,20}ball|remove[sd]? .{0,20}ball)\b"
_RESULT = r"stuck|stick[sy]?|flips?|upside[ -]down|stretches?|flexes?|snaps?|larger|bigger|grows?|giant|huge|pops? open|springs? open|slides? back|reverses?|scares?|flee|flinch\w*|spill\w*|blocks?|traps?|reveals?|exposes?|squeezes?|stays? normal|behaves?|returns?|falls?|drops?|tilts?|doubles?|flies|floats?|transforms?"
_CHANGE = {
    "MAGNITUDE": r"harder|both hands|further|larger|bigger|doubles?|enormous|giant|huge",
    "DEFORMATION": r"stretches?|flexes?|bends?|deforms?",
    "CONSTRAINT": r"blocks?|traps?|wedges?|pins?|cannot move|tighter|hemmed",
    "POSITION": r"backward|underneath|on (?:his |her )?cheek|with .{0,20}on it|overhead|behind .{0,15}back",
    "INFORMATION": r"stays? normal|behaves?|reveals?|exposes?|discovers?|only when|turns? .{0,12}away|looks? back|head away",
    "STAKES": r"last dry plant|last (?:snack|berry)|only (?:snack|berry)|about to spill|edge of the table",
}
_PAYOFF = {
    "INVERTED_RIDER": r"flips? upside down with|upside down with|with .{0,20}on it",
    "NEW_ATTACHMENT_TARGET": r"(?:cheek|face|forehead).{0,40}stick|stick\w*.{0,40}(?:cheek|face|forehead)",
    "LOGICAL_EXTREME": r"(?:fills? the (?:room|frame)|giant|enormous|towering).{0,80}(?:spoon|brush|lid|plant|object)|(?:spoon|brush|lid|plant|object).{0,80}(?:fills? the (?:room|frame)|giant|enormous|towering)",
    "REINTERPRETATION": r"(?:reveals?|exposes?).{0,100}(?:actually|inside|under|behind)|(?:birds?|flock).{0,80}(?:watering|guards?|protect\w*|scarecrow)",
    "RECREATED_PROBLEM": r"(?:again|back).{0,45}(?:pops? open|slides? back|upside.down)|(?:pops? open|slides? back).{0,45}(?:again|back)",
}


def _has(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text, re.I | re.S))


def _visual(text: str) -> str:
    """Exclude quoted speech, negated instructions and self-awarded labels."""
    text = re.sub(r'[“"].*?[”"]', '', text, flags=re.S)
    clauses = re.split(r'(?<=[.!?])\s+|\n+', text)
    return ' '.join(c for c in clauses if not _has(
        r'^\s*(?:no\b|never\b|do not\b|don.t\b|must not\b)|\b(?:not|doesn.t) (?:upside.down|sticky|stuck|giant|huge|grow\w*|flip\w*|pop\w*|float\w*|fly|scare\w*|sit\w*|wash\w*)\b|\b(?:says?|explains?|narrat\w*|text reads|claims?|should|must dominate|score|payoff:|hook:)\b', c))


def _timeline(text: str) -> list[dict[str, Any]]:
    headers = list(_TIME.finditer(text))
    result = []
    for i, header in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        stop = _STOP.search(text, header.end(), end)
        if stop:
            end = stop.start()
        start = header.end()
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        result.append({'id': f'B{i + 1}', 'start': float(header[1]), 'end': float(header[2]),
                       'quote': text[start:end], 'sourceSpan': [start, end]})
    if not headers:
        for m in re.finditer(r'[^\n]+', text):
            if m[0].strip():
                result.append({'id': f'B{len(result) + 1}', 'start': None, 'end': None,
                               'quote': m[0], 'sourceSpan': [m.start(), m.end()]})
    return result


def _features(text: str) -> dict[str, Any]:
    visual = _visual(text)
    rules = [key for key, pattern in _RULES.items() if _has(pattern, visual)]
    # Canonical strategy families, plus visible everyday methods absent from
    # the canonical mechanical verb vocabulary. Motion/reactions are excluded.
    verbs = re.findall(r'\b(pulls?|push(?:es)?|shakes?|squeezes?|throws?|toss(?:es)?|lifts?|holds?|grabs?|flips?|clamps?|wedges?|rinses?|walks? backward|turns? .{0,12}away|stares?|water(?:s)?)\b', visual, re.I)
    def strategy(verb: str) -> str:
        family = normalize_strategy_family(verb, visual)
        if not family.startswith('OTHER:'):
            return family
        for pattern, label in ((r'^flip', 'INVERT'), (r'^stare', 'OBSERVE'),
                               (r'^turn.*away$', 'BREAK_GAZE'), (r'^walk.*backward$', 'BACKWARD_APPROACH'),
                               (r'^clamp', 'CLAMP'), (r'^wedge', 'WEDGE'),
                               (r'^rinse', 'RINSE'), (r'^water', 'WATER')):
            if _has(pattern, verb):
                return label
        return family

    strategies = list(dict.fromkeys(strategy(v) for v in verbs))
    changes = [key for key, pattern in _CHANGE.items() if _has(pattern, visual)]
    state_signals = [f'{key}:{match[0].lower()}' for key, pattern in _CHANGE.items()
                     for match in re.finditer(pattern, visual, re.I)]
    return {'visual': visual, 'rules': rules, 'strategies': strategies, 'changes': changes,
            'stateSignals': state_signals, 'goal': _has(_GOAL, visual), 'result': _has(_RESULT, visual)}


def _signature(beats: list[dict[str, Any]]) -> dict[str, Any]:
    if not beats:
        return {'opening': [], 'progression': [], 'ending': []}
    return {'opening': beats[0]['rules'],
            'progression': list(dict.fromkeys(s for b in beats for s in b['strategies'])),
            'ending': [key for key, pattern in _PAYOFF.items() if _has(pattern, beats[-1]['visual'])]}


def _duplicates(text: str, signature: dict[str, Any]) -> dict[str, Any]:
    references = json.loads(Path(__file__).with_name('short_form_references.json').read_text())
    matches = []
    sha = hashlib.sha256(text.encode()).hexdigest()
    for ref in references:
        if sha == ref['sourceSha256']:
            continue  # Reviewing the source itself is not a derivative concept.
        other = ref['signature']
        axes = {key: bool(signature[key]) and signature[key] == other[key] for key in signature}
        if sum(axes.values()) >= 2:
            matches.append({'referenceId': ref['referenceId'], 'sourceSha256': ref['sourceSha256'],
                            'matchingAxes': [k for k, v in axes.items() if v],
                            'risk': 'HIGH' if all(axes.values()) else 'MODERATE'})
    return {'status': 'HIGH' if any(m['risk'] == 'HIGH' for m in matches) else ('MODERATE' if matches else 'NO_MATCH_IN_LIMITED_CORPUS'),
            'matches': matches, 'comparedReferences': len(references),
            'limitation': 'Source-bound structural comparison against a small curated corpus; not proof of originality. Names are excluded.'}


def assess(text: str, context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Opt-in, versioned evidence acquisition; one unchanged scoring evaluator."""
    context = context or {}
    if context.get('shortFormEvaluation') is not True:
        return None
    from .short_form_evidence import acquire
    evidence = acquire(text, context)
    report = _evaluate(text, context, evidence)
    if evidence.sourceKind == 'STRUCTURED_CANONICAL_V1':
        report['evidenceSourceVersion'] = 'structured-canonical-v1'
        report['canonicalEvidence'] = evidence.model_dump()
        report['findingEvidence'] = {finding['code']: [
            dict(beatId=beat.id, references=facts.references)
            for beat, facts in zip(evidence.beats, evidence.acquisition)
            if not finding['beatIds'] or beat.id in finding['beatIds']
        ] for finding in report['findings']}
    return report


def _evaluate(text, context, evidence):
    """Shared scoring/thresholds/findings. No source-specific branches."""
    beats = [b.model_dump() for b in evidence.beats]
    raw = beats
    findings: list[dict[str, Any]] = []

    def flag(code: str, message: str, severity: str = 'WARNING', ids: list[str] | None = None):
        findings.append({'code': code, 'severity': severity, 'message': message, 'beatIds': ids or []})

    duration = next((context[k] for k in ('plannedEditedDuration', 'desiredDuration', 'targetDuration')
                     if isinstance(context.get(k), (int, float)) and not isinstance(context[k], bool)), None)
    timed = bool(raw) and all(b['start'] is not None for b in raw)
    if duration is None and timed:
        duration = max(b['end'] for b in raw)
    valid_timing = timed and all(b['end'] > b['start'] >= 0 for b in beats) and all(
        a['end'] <= b['start'] for a, b in zip(beats, beats[1:]))
    complete = valid_timing and beats[0]['start'] == 0 and all(
        abs(a['end'] - b['start']) < .05 for a, b in zip(beats, beats[1:])) and duration is not None and abs(beats[-1]['end'] - duration) < .1
    if not complete:
        flag('TIMING_UNVERIFIED', 'Provide a contiguous timed plan from frame zero to the declared edited duration.', 'REVISION_REQUIRED')
    if duration is None or not 10 <= duration <= 20:
        flag('SHORT_DURATION_MISMATCH', 'This surface targets 10–20 seconds around a 15-second primary format.', 'REVISION_REQUIRED')
    first = beats[0] if beats else {'visual': '', 'goal': False, 'rules': [], 'start': None, 'end': None}
    first_mechanisms = evidence.acquisition[0].mechanismIds if beats else []
    hook = 100 if first['goal'] and first_mechanisms else (50 if first_mechanisms else 10)
    if first['start'] != 0 or (first['end'] or 99) > 4:
        hook = min(hook, 50)
    if evidence.facts.openingDelayed:
        hook = min(hook, 20)
    goal = 100 if first['goal'] else (55 if evidence.facts.goalDeclared else 0)
    if hook < 70:
        flag('OPENING_NOT_IN_TROUBLE', 'First beat lacks a source-supported visible goal plus anomaly, or establishes them too slowly.', 'REVISION_REQUIRED')
    if goal < 70:
        flag('EVERYDAY_GOAL_UNCLEAR', 'An immediate visible everyday goal must be understandable at the opening.', 'REVISION_REQUIRED')
    rules = evidence.facts.mechanismIds
    rule_score = 100 if len(rules) == 1 else (0 if not rules else max(10, 70 - 25 * (len(rules) - 1)))
    if len(rules) > 1:
        flag('MULTIPLE_UNRELATED_RULES', f'Potential independent rule families {rules}; explain their causal relationship.', 'REVISION_REQUIRED')
    elif not rules:
        flag('CORE_RULE_UNSUPPORTED', 'No supported dominant visible rule was found.', 'REVISION_REQUIRED')

    seen_strategies: set[str] = set()
    seen_changes: set[str] = set()
    seen_results: set[str] = set()
    for index, beat in enumerate(beats):
        types = []
        acquired = evidence.acquisition[index]
        results = set(acquired.resultTokens)
        magnitude_rises = acquired.magnitudeRises
        material = bool(set(beat['stateSignals']) - seen_changes) or magnitude_rises
        strategy_change = bool(set(beat['strategies']) - seen_strategies)
        if index == 0 and acquired.mechanismIds:
            types.append('UNDERSTANDING')
        if index > 0 and beat['result'] and rules:
            if strategy_change:
                types.append('STRATEGY')
            if material:
                types.append('ESCALATION')
            if results - seen_results and (material or strategy_change):
                types.append('CONSEQUENCE')
        endings = acquired.endingPatterns.copy()
        if 'RECREATED_PROBLEM' in endings and not acquired.recreatedSuccess:
            endings.remove('RECREATED_PROBLEM')
        if 'LOGICAL_EXTREME' in endings and acquired.openingLogicalExtreme and not material:
            endings.remove('LOGICAL_EXTREME')
        # A payoff must retain the established anomaly. A surprise from a new
        # magic system or merely the label "twist/reveal" earns no payoff.
        if index == len(beats) - 1 and (endings or acquired.terminalStateChange) and len(rules) == 1 and set(acquired.mechanismIds).intersection(rules) and beat['result']:
            types.append('PAYOFF')
        beat['progressTypes'] = types
        beat['materialProgress'] = bool(types)
        beat['newStrategy'] = strategy_change
        seen_strategies.update(beat['strategies'])
        seen_changes.update(beat['stateSignals'])
        seen_results.update(results)
    major = sum(b['materialProgress'] for b in beats)
    density = 100 if 4 <= major <= 5 else (85 if major == 6 else (45 if major == 3 else (25 if major < 3 else 50)))
    progress = round(100 * major / len(beats)) if beats else 0
    if major < 4:
        flag('TOO_FEW_CAUSAL_BEATS', f'{major} supported causal beats; target 4–5, normally 4–6.', 'REVISION_REQUIRED')
    if major > 6:
        flag('TEMPORAL_OVERLOAD', f'{major} major causal beats exceed the normal 4–6 beat range.')
    if len(beats) >= 4 and progress < 70:
        flag('HIGH_ACTIVITY_LOW_PROGRESS', f'{len(beats)} described blocks contain only {major} supported causal developments.', 'REVISION_REQUIRED')
    repeated = [b['id'] for b in beats[1:-1] if b['strategies'] and not b['materialProgress']]
    if repeated:
        flag('IDENTICAL_ATTEMPTS', 'Repeated actions lack a new strategy, magnitude, consequence, information, position or stakes.', 'REVISION_REQUIRED', repeated)
    # Measure between developments, including the tail; never invent timestamps.
    points = [b['start'] for b in beats if b['materialProgress'] and b['start'] is not None]
    gaps = [b - a for a, b in zip(points, points[1:])]
    if points and duration is not None:
        gaps.append(max(0, duration - points[-1]))
    plateau = max(gaps, default=0) if complete else None
    escalation = max(0, 100 - round(max(0, (plateau or 4) - 4) * 18)) if complete else 25
    if plateau is not None and plateau > 4:
        flag('ESCALATION_PLATEAU', f'Longest gap between supported developments is {plateau:g}s; aim for change every 2–4s.')
    payoff = 100 if beats and 'PAYOFF' in beats[-1]['progressTypes'] else 15
    if payoff < 70:
        flag('WEAK_VISUAL_PAYOFF', 'Ending needs a source-supported rule-linked reversal, reveal, extreme state or recreated problem.', 'REVISION_REQUIRED')
    confusion = evidence.facts.confusion
    loop = payoff >= 70 and evidence.facts.loopCue
    rewatch_type = 'CONFUSION_REWATCH' if confusion else ('INTENTIONAL_REWATCH' if loop else 'OPTIONAL_NOT_ESTABLISHED')
    rewatch = 10 if confusion else (100 if loop else 60)
    if confusion:
        flag('CONFUSION_REWATCH', 'Ambiguity is not positive intentional replay value.', 'REVISION_REQUIRED')
    words = evidence.facts.speechWords
    audio_required = evidence.facts.audioRequired
    dialogue_heavy = words > 18 or evidence.facts.longSpeech or audio_required
    if dialogue_heavy:
        flag('DIALOGUE_LOAD', 'Explanatory dialogue, long lip-sync or word load competes with visual escalation.')
    reaction = 100 if evidence.facts.reactionVisible else 55
    silent_parts = {'goal': goal, 'rule': rule_score, 'reaction': reaction, 'payoff': payoff}
    silent = round(sum(silent_parts.values()) / 4)
    if audio_required:
        silent = min(silent, 35)
        flag('AUDIO_DEPENDENT_CAUSALITY', 'Essential causality depends on speech or text.', 'REVISION_REQUIRED')
    staging = evidence.facts.stagingRisks.copy()
    for name in staging:
        flag(name, 'Prompt/execution risk: stage physical eyelines and object interaction. Premise score is independent.')
    production = evidence.facts.productionRisks.copy()
    for name in production:
        flag(name, 'Production continuity risk; review feasibility separately from premise quality.')
    if len(rules) > 1:
        production.append('MULTIPLE_PHYSICS_SYSTEMS')
    feasibility = max(0, 100 - 18 * len(production))
    duplicate = _duplicates(text, evidence.facts.duplicateSignature)
    if duplicate['status'] in {'HIGH', 'MODERATE'}:
        flag('ENGINE_DUPLICATE_RISK', 'Opening/progression/final structure overlaps a known reference; object renaming is not novelty.',
             'REVISION_REQUIRED' if duplicate['status'] == 'HIGH' else 'WARNING')
    scores = {'hookScore': hook, 'goalScore': goal, 'ruleClarityScore': rule_score,
              'beatDensityScore': density, 'progressDensityScore': progress, 'escalationScore': escalation,
              'payoffScore': payoff, 'rewatchScore': rewatch, 'silentLegibilityScore': silent,
              'productionFeasibilityScore': feasibility}
    # Production and optional loops do not veto a sound premise. No moral-arc or
    # long-form predictability features enter this independent score.
    weights = {'hookScore': .2, 'goalScore': .12, 'ruleClarityScore': .12, 'beatDensityScore': .1,
               'progressDensityScore': .14, 'escalationScore': .1, 'payoffScore': .16, 'silentLegibilityScore': .06}
    score = round(sum(scores[k] * w for k, w in weights.items()))
    revisions = any(f['severity'] == 'REVISION_REQUIRED' for f in findings)
    status = 'REJECT' if score < 25 else ('REVISION_REQUIRED' if revisions or score < 70 else ('PASS_WITH_WARNINGS' if findings else 'PASS'))
    reason = 'Opening contains a visible everyday goal and anomaly.' if hook == 100 else 'Opening goal/anomaly or immediate timing is not sufficiently supported.'
    return {'engine': 'SHORT_FORM_ENGINE', 'version': VERSION, 'status': status, 'shortFormScore': score,
            **scores, 'instantPremiseLegibility': {'score': hook, 'reason': reason},
            'alreadyInTrouble': hook == 100, 'rules': evidence.facts.classifiedRules, 'majorCausalBeatCount': major,
            'describedBlockCount': len(beats), 'beats': beats, 'findings': findings,
            'escalationCurve': {'longestPlateauSeconds': plateau, 'targetSeconds': [2, 4]},
            'continuationReason': 'Next materially different attempt, consequence or final physical state.' if major >= 4 else 'Not established beyond repeated activity.',
            'earlyRuleUnderstandingPenalized': False, 'rewatchType': rewatch_type,
            'silentLegibility': silent_parts, 'dialogue': {'words': words, 'audioDependent': audio_required},
            'stagingRisks': staging, 'productionRisks': production, 'feasibilityEvidenceStatus': 'TEXT_RISK_SCREEN_ONLY',
            'duplicateEngineRisk': duplicate,
            'requestedDurationSeconds': duration, 'timingVerifiedFromPlan': complete,
            'scoreType': 'INDEPENDENT_SHORT_FORM_EDITORIAL_HEURISTIC',
            'humanReadableReport': f'{status}: short-form {score}/100; {major} causal beats in {len(beats)} blocks. {reason}',
            'sourceSha256': hashlib.sha256(text.encode()).hexdigest(),
            'evidenceLimitations': ['Source text describes intended visuals; no actual video frames inspected.',
                                    'English pattern screening is conservative, not semantic verification or a watch-performance forecast.',
                                    'Unknown mechanics, implicit goals and unsupported wording need human review.',
                                    'Long-form quality, canonical gates and production risk are independent.'],
            'canonicalRulesetUnchanged': True, 'renderAuthorized': False, 'providerCalls': 0}
