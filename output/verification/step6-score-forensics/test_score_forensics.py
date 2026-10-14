import json,copy,pytest
from app.workflow.review import _run_canonical_evaluation
from app.parser.prompt_parser import parse_prompt
from app.rules.rule_engine import RuleEngine
from app.quality.canonical_evidence import engine_profile_evidence,specialized_applicability_evidence
from app.quality.contracts import RuleEvaluation,RuleOutcome,Severity
import runpy
spoon_ir=runpy.run_path("tests/test_ruleset_1_7_stubborn_return.py")["spoon_ir"]
from pathlib import Path
INPUT=json.load(open(Path(__file__).with_name('inputs.json')))
@pytest.mark.parametrize('name',list(INPUT))
def test_saved_prompt_recomputes_exactly(name):
 s=INPUT[name];fresh=_run_canonical_evaluation({'prompt':s['originalPrompt']});old=s['canonicalRuleEvaluation']
 assert fresh['score']==old['score']==85 and fresh['grade']==old['grade']=='B'
 assert [(r['ruleId'],r['outcome']) for k in ('passedRules','failedRules','unknownRules','notApplicableRules') for r in fresh[k]]==[(r['ruleId'],r['outcome']) for k in ('passedRules','failedRules','unknownRules','notApplicableRules') for r in old[k]]
@pytest.mark.parametrize('name',list(INPUT))
def test_explicit_physical_rule_and_domain_mismatch(name):
 ir=parse_prompt(INPUT[name]['originalPrompt']).video_plan_ir;p=engine_profile_evidence(ir)
 assert 'each pull doubles the number of sticky notes' in ir['coreMechanic']['physicalRule']
 assert p.confidence=='LOW' and p.candidate_only and not p.signals['AUTONOMOUS_RETURN'] and not p.signals['RECURRENCE']
 assert specialized_applicability_evidence(ir)['STUBBORN_RETURN_LOOP'].status=='NOT_APPLICABLE'
 # Proposed predicate; engine intentionally untouched.
 assert not (p.confidence=='MEDIUM' and not p.active)
def test_proposed_predicate_preserves_supported_high_and_medium_domains():
 high=engine_profile_evidence(spoon_ir());medium=engine_profile_evidence(spoon_ir(weak=True))
 assert high.active and high.confidence=='HIGH'
 assert medium.confidence=='MEDIUM' and not medium.active and (medium.confidence=='MEDIUM' and not medium.active)
def test_all_configured_rules_pass_still_cannot_exceed_85():
 e=RuleEngine();assert len(e.ruleset['rules'])==8
 rows=[RuleEvaluation(rule_id=r['id'],rule_name=r['name'],family=r['family'],configured_severity=Severity(r['severity']),outcome=RuleOutcome.PASS,message='Algebra-only upper bound, not fabricated evidence') for r in e.ruleset['rules']]
 assert all(r.configured_severity!=Severity.PASS for r in rows)
 assert e._calculate_overall_score(e._calculate_family_scores(rows),rows)==pytest.approx(85)
@pytest.mark.parametrize('name',list(INPUT))
def test_measurable_opening_timing_improvement(name):
 e=RuleEngine();ir=parse_prompt(INPUT[name]['originalPrompt']).video_plan_ir;bad=copy.deepcopy(ir)
 bad['beats'][0]['startTime']=3;bad['beats'][0]['endTime']=5;bad['goalEvidence']['startsAt']=3
 assert e._evaluate_goal_visible_early(bad,{}).outcome==RuleOutcome.FAIL
 assert e.evaluate(bad).overall_score==pytest.approx(72.72727272727273)
 assert e._evaluate_goal_visible_early(ir,{}).outcome==RuleOutcome.PASS
 assert e.evaluate(ir).overall_score==85
def test_additive_ruleset_ancestry_is_omitted_by_current_loader():
 import yaml
 from app.config import settings
 def inherited(name):
  y=yaml.safe_load((settings.rules_dir/name).read_text())
  return (inherited(y['extends']) if y.get('extends') else [])+y.get('rules',[])
 actual={r['id'] for r in RuleEngine().ruleset['rules']};expected={r['id'] for r in inherited('RULESET_1.7.yaml')}
 assert len(actual)==8 and len(expected)==46
 assert expected-actual and 'INSTANT_VISUAL_ABSURDITY_GATE' in expected-actual
 assert actual<expected
