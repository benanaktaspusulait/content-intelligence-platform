"""Read-only deterministic controls. Synthetic controls never persist evaluations."""
import json
from copy import deepcopy
from pathlib import Path
from app.config import settings
from app.parser.prompt_parser import ParserConfig, parse_prompt
from app.rules.rule_engine import RuleEngine
from app.workflow.review import _run_canonical_evaluation

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
saved = json.loads((ROOT/'output/verification/step6-exit-check/official-analysis.json').read_text())
request = {**saved['boundRequest'], 'prompt': saved['originalPrompt'], 'canonicalRulesetVersion': '1.10'}
actual = _run_canonical_evaluation(request)
assert json.loads(json.dumps(actual)) == saved['canonicalRuleEvaluation']
engine = RuleEngine(str(settings.rules_dir/'RULESET_1.10.yaml'))
ir = parse_prompt(request['prompt'], ParserConfig(attempt_evidence_policy='ACTOR_SOURCE_BOUND_V2', motion_evidence_policy='TOKEN_MOTION_V2')).video_plan_ir
ir['metadata']['contentProfile'] = 'ABSURD_PHYSICS'
registry = {r['id']:r for r in engine.ruleset['rules']}

# The complete five-second progression is assigned one action-derived state.
beat = ir['beats'][2]
assert all(q in beat['sourceQuote'] for q in ['two to four to eight', 'arms, legs and face'])
beval = engine._evaluate_beat_004(ir, registry['BEAT_004'])
assert beval.outcome.value == 'FAIL' and beval.actual_value > 33
# No invented intermediate timestamps: lack of substate timing is reported.

# MOMENTUM counts the entire non-attempt ending as aftermath even with motion.
active = engine._evaluate_continuous_action_momentum(ir, registry['CONTINUOUS_ACTION_MOMENTUM'])
frozen = deepcopy(ir)
frozen['beats'][-1].update(action='Mimi stands still.', consequence='No change.', motionAmount='none')
frozen_result = engine._evaluate_continuous_action_momentum(frozen, registry['CONTINUOUS_ACTION_MOMENTUM'])
assert active.details['finalAftermathSeconds'] == frozen_result.details['finalAftermathSeconds'] == 3
assert ir['beats'][-1]['motionAmount'] == 'moderate'
assert 'sneezes' in ir['beats'][-1]['sourceQuote'] and 'scatter' in ir['beats'][-1]['sourceQuote']

rows={r['ruleId']:r for g in ['passedRules','failedRules','unknownRules','notApplicableRules'] for r in actual[g]}
findings=[]
classifications={
 'BEAT_004': 'EVALUATOR_DEFECT',
 'ATTEMPT_001': 'POLICY_EXCEPTION_REQUIRED',
 'PRODUCIBILITY_003': 'PRODUCTION_RISK_REVIEW',
 'CONTINUOUS_ACTION_MOMENTUM': 'EVALUATOR_DEFECT',
 'INSTANT_VISUAL_ABSURDITY_GATE': 'EVIDENCE_REQUIRED',
 'ENGINE_SILHOUETTE_DUPLICATE': 'EVIDENCE_REQUIRED',
}
for key, category in classifications.items():
 findings.append({'rule':key,'canonical':rows[key], 'governedMetadata':registry[key],
   'auditClassification':category, 'classificationAuthority':'AUDIT_ONLY_NOT_AN_ACTIVE_POLICY',
   'hasExplicitWorkflowResolutionMetadata':any(k in registry[key] for k in ['resolutionType','resolutionPolicy','waiverPolicy','workflowResolution'])})
result={
 'status':'REPRODUCED_NO_MUTATION','analysisId':saved['recordId'], 'score':actual['score'],
 'BEAT_004':{'sourceQuote':beat['sourceQuote'],'sourceSpan':beat['sourceSpan'],'visualStateId':beat['visualStateId'], 'measuredPercent':beval.actual_value,'substateTimes':'UNKNOWN_NOT_INVENTED'},
 'MOMENTUM':{'endingSourceQuote':ir['beats'][-1]['sourceQuote'],'endingSourceSpan':ir['beats'][-1]['sourceSpan'], 'activeEnding':active.details,'syntheticStillEnding':frozen_result.details},
 'sixFindings':findings,
}
(OUT/'deterministic-audit.json').write_text(json.dumps(result,indent=2))
print('Saved canonical reproduction and two evaluator controls passed. No provider or persistence path called.')
