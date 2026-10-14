import json,copy
from app.workflow.review import _run_canonical_evaluation
from app.parser.prompt_parser import parse_prompt
from app.rules.rule_engine import RuleEngine
from app.quality.canonical_evidence import engine_profile_evidence,specialized_applicability_evidence
from app.quality.family_weights import CANONICAL_FAMILY_WEIGHTS
inputs=json.load(open(__import__('pathlib').Path(__file__).with_name('inputs.json'))); engine=RuleEngine(); out={'rulesetVersion':engine.ruleset['version'],'configuredRules':[(r['id'],r['severity']) for r in engine.ruleset['rules']],'runs':{}}
for name, saved in inputs.items():
 prompt=saved['originalPrompt'];ir=parse_prompt(prompt).video_plan_ir;fresh=_run_canonical_evaluation({'prompt':prompt});report=engine.evaluate(ir)
 assert fresh['score']==saved['canonicalRuleEvaluation']['score']==85
 rows=[{'id':e.rule_id,'family':e.family,'severity':e.configured_severity.value,'outcome':e.outcome.value,'weight':CANONICAL_FAMILY_WEIGHTS.get(e.family,.05)} for e in report.evaluations]
 scored=[r for r in rows if r['outcome']=='PASS']; numerator=sum(85*r['weight'] for r in scored); denominator=sum(r['weight'] for r in scored)
 assert numerator/denominator==85
 out['runs'][name]={'score':fresh['score'],'grade':fresh['grade'],'rules':rows,'familyScores':report.family_scores,'weightedNumerator':numerator,'weightDenominator':denominator,'engineProfile':engine_profile_evidence(ir).__dict__,'genericApplicability':{k:v.to_dict() for k,v in specialized_applicability_evidence(ir).items()},'storyDensity':fresh['storyDensityEvidence'],'coreMechanic':ir.get('coreMechanic'),'renderAuthorization':saved['family8']['renderAuthorization']}
 # no evidence invention: omit observed goal information to test sensitivity downward
 no_goal=copy.deepcopy(ir);no_goal['goalEvidence']={};no_goal['beats'][0]['goal']=None
 out['runs'][name]['counterfactualGoalEvidenceRemoved']={'score':engine.evaluate(no_goal).overall_score,'goalOutcome':engine._evaluate_goal_visible_early(no_goal,{}).outcome.value}
 # change only timeline: move observed opening event later without adding events/evidence
 delayed=copy.deepcopy(ir);delayed['beats'][0]['startTime']=3;delayed['beats'][0]['endTime']=5
 delayed['goalEvidence']['startsAt']=3
 ev=engine._evaluate_goal_visible_early(delayed,{})
 out['runs'][name]['counterfactualDelayedOpening']={'score':engine.evaluate(delayed).overall_score,'goalOutcome':ev.outcome.value,'message':ev.message}
 # add no visual assertions: harmless evidence container cannot change text-only eight rules
 with_ref=copy.deepcopy(ir);with_ref['references']={'character':{'status':'UNVERIFIED'}}
 assert engine.evaluate(with_ref).overall_score==85
 # isolate correct candidate-only domain threshold as proposed, not applied to code
 p=engine_profile_evidence(ir);out['runs'][name]['proposedCandidateOnly']=p.confidence=='MEDIUM' and not p.active
open(__import__('pathlib').Path(__file__).with_name('calculation.json'),'w').write(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
