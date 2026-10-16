import json,hashlib,subprocess,urllib.request
from pathlib import Path
p=Path('intelligence/docs');out=p/'mimi-v3-actual-canonical-evidence'
with urllib.request.urlopen('http://127.0.0.1:4200/api/v1/intelligence/workflow/records/f0d36feb-ee0f-4da8-ae21-2071a3ddea18',timeout=30) as r:saved=json.load(r)
v2=(p/'CPQ_V1_MIMI_CREATIVE_IMPROVEMENT_V2.txt').read_text().split('PROMPT BODY\n\n',1)[1].rstrip('\n');original=saved['originalPrompt']
h=lambda s:hashlib.sha256(s.encode()).hexdigest()
assert h(v2)=='44779084f986b4a7b1b3a5d1eab9c617f2e6f518a9c5b771cab02bce446cd219'
assert h(original)=='0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98'
v3=(p/'CPQ_V1_MIMI_CREATIVE_IMPROVEMENT_V3.txt').read_text().split('PROMPT BODY\n\n',1)[1].rstrip('\n')
assert h(v3)=='f362df56f7a54ee37002ee9e6f756edd59eb50fe5d0c484ee80416b4d954498a'
previousV2=json.loads((p/'mimi-v2-actual-canonical-evidence/actual-evaluations.json').read_text())['results']['v2']['canonical']
q={**saved['boundRequest'],'canonicalRulesetVersion':'1.11'}
assert q['contentProfile']=='ABSURD_PHYSICS' and q['generator']=='SEEDANCE_2_0_MINI' and q['desiredDuration']==15 and q['settings']['mode']=='image2video' and q['settings']['resolution']=='480p' and q['settings']['aspectRatio']=='9:16'
def sql(q):return subprocess.check_output(['docker','exec','intelligence-postgres-1','psql','-U','pompom','-d','pompom','-Atc',q],text=True).strip()
digestq="SELECT encode(sha256(convert_to(jsonb_agg(to_jsonb(r) ORDER BY id)::text,'UTF8')),'hex') FROM post_family_workflow_events r"
promptq="SELECT encode(sha256(convert_to(jsonb_agg(to_jsonb(r) ORDER BY id)::text,'UTF8')),'hex') FROM prompt_versions r"
before={'workflowRows':sql(digestq),'promptRows':sql(promptq)}
input={'original':original,'v2':v2,'v3':v3,'previousV2':previousV2,'request':q,'savedCanonical':saved['canonicalRuleEvaluation']}
code=r'''
import sys,json,hashlib,socket
from pathlib import Path
sys.dont_write_bytecode=True
payload=json.load(sys.stdin)
from app.workflow.review import _run_canonical_evaluation
from app.parser.prompt_parser import parse_prompt,ParserConfig
from app.rules.rule_engine import RuleEngine
from app.quality.canonical_evidence import is_evidence_gap
from app.quality.family_weights import CANONICAL_FAMILY_WEIGHTS
from app.config import settings
from app.quality.contracts import RuleOutcome,Severity
networkAttempts=[]
def denied(*a,**k):
 networkAttempts.append('blocked');raise RuntimeError('Offline canonical run forbids network access')
socket.socket.connect=denied
socket.create_connection=denied
files=[Path(__import__('app.workflow.review',fromlist=['x']).__file__),Path(__import__('app.rules.rule_engine',fromlist=['x']).__file__),Path(__import__('app.parser.prompt_parser',fromlist=['x']).__file__),Path(__import__('app.parser.actor_attempts',fromlist=['x']).__file__),Path(__import__('app.quality.canonical_evidence',fromlist=['x']).__file__),settings.rules_dir/'RULESET_1.11.yaml',Path(__import__('app.quality.family_weights',fromlist=['x']).__file__)]
fingerprints={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
results={}
for label in ['original','v2','v3']:
 req={**payload['request'],'prompt':payload[label]}
 canonical=_run_canonical_evaluation(req)
 assert canonical['status']=='EVALUATED',canonical
 assert canonical['rulesetVersion']=='1.11'
 if label=='original':
  assert abs(canonical['score']-88.40625)<1e-10 and canonical['grade']=='B',canonical
  assert json.loads(json.dumps(canonical))==payload['savedCanonical'], 'JSON-normalized control must reproduce saved result'
  controlProjectionEqual=canonical==payload['savedCanonical']
  controlChangedTopLevelKeys=[k for k in canonical if canonical.get(k)!=payload['savedCanonical'].get(k)]
 if label=='v2':
  assert abs(canonical['score']-80.25520833333334)<1e-10 and canonical['grade']=='B'
  assert json.loads(json.dumps(canonical))==payload['previousV2'], 'Unchanged V2 control must reproduce full previous result'
 # Same production parser/engine, evaluated again solely to expose aggregation,
 # values and weights omitted by the public canonical projection.
 ir=parse_prompt(payload[label],ParserConfig(attempt_evidence_policy='ACTOR_SOURCE_BOUND_V2',motion_evidence_policy='TOKEN_MOTION_V2')).video_plan_ir
 ir['metadata']['contentProfile']=req['contentProfile']
 engine=RuleEngine(str(settings.rules_dir/'RULESET_1.11.yaml'));report=engine.evaluate(ir)
 assert report.overall_score==canonical['score']
 fam=engine._calculate_family_scores(list(report.evaluations));den=sum(CANONICAL_FAMILY_WEIGHTS.get(k,.05) for k,v in fam.items() if v is not None)
 counts={f:sum(e.family==f and e.evaluation_state.value=='EVALUATED' and e.outcome.value in ['PASS','FAIL'] and not is_evidence_gap(e) for e in report.evaluations) for f in fam}
 rows=[]
 for e in report.evaluations:
  eligible=e.evaluation_state.value=='EVALUATED' and e.outcome.value in ['PASS','FAIL'] and not is_evidence_gap(e)
  points=(100 if e.configured_severity is Severity.PASS else 85) if e.outcome is RuleOutcome.PASS else (0 if e.configured_severity is Severity.BLOCKER else 40 if e.configured_severity is Severity.CRITICAL else 70)
  coefficient=CANONICAL_FAMILY_WEIGHTS.get(e.family,.05)/den/counts[e.family] if eligible else None
  rows.append(dict(ruleId=e.rule_id,family=e.family,outcome=e.outcome.value,severity=e.configured_severity.value,evaluationState=e.evaluation_state.value,scoreEligible=eligible,rowPoints=points if eligible else None,familyWeight=CANONICAL_FAMILY_WEIGHTS.get(e.family,.05),scoredFamilyRows=counts[e.family],overallContribution=points*coefficient if eligible else None,overallLoss=(100-points)*coefficient if eligible else None,message=e.message,actualValue=e.actual_value,requiredValue=e.required_value,thresholdValue=e.threshold_value,details=dict(e.details)))
 assert abs(sum(r['overallContribution'] or 0 for r in rows)-canonical['score'])<1e-9
 results[label]=dict(canonical=canonical,engineStatus=report.status.value,familyScores=fam,eligibleWeightDenominator=den,rules=rows,request=req)
assert not networkAttempts
print(json.dumps(dict(evaluator='app.workflow.review._run_canonical_evaluation',runtimeSourceSha256=fingerprints,networkAttempts=networkAttempts,productionDatabaseAccess=False,controlProjectionEqual=controlProjectionEqual,controlChangedTopLevelKeys=controlChangedTopLevelKeys,savedCanonical=payload['savedCanonical'],results=results),ensure_ascii=False))
'''
r=subprocess.run(['docker','exec','-i','-e','PYTHONDONTWRITEBYTECODE=1','intelligence-ml-service-1','python','-c',code],input=json.dumps(input),text=True,capture_output=True)
(out/'execution-stderr.log').write_text(r.stderr)
if r.returncode:print(r.stderr);raise SystemExit(r.returncode)
result=json.loads(r.stdout)
after={'workflowRows':sql(digestq),'promptRows':sql(promptq)};assert before==after
result['productionIntegrity']={'before':before,'after':after,'unchanged':True};result['v3BodySha256']=h(v3);result['v2BodySha256']=h(v2);result['originalBodySha256']=h(original)
(out/'actual-evaluations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:{'score':v['canonical']['score'],'grade':v['canonical']['grade'],'engineStatus':v['engineStatus'],'scoredDenominator':v['eligibleWeightDenominator']} for k,v in result['results'].items()},indent=2))
