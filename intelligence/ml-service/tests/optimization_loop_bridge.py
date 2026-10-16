"""Disposable test transport bridge, never imported by production routes.

No final score fixtures: local handlers, reconstruction and canonical engine are real.
"""
import json,sys
from copy import deepcopy
from test_model_authored_execution import contact,progression,inputs
from app.workflow import optimization_loop as L

def fixture_scope():
 f=inputs();return dict(analysisId='11111111-1111-4111-8111-111111111111',contentId=10,promptVersionId=10,baselinePrompt=f['text'],originalPrompt=f['text'],baselineSha256=L.fingerprint(f['text']),approvedStory=dict(text=f['context']['approvedStoryText'],storyId='22222222-2222-4222-8222-222222222222',approvalRecordId='33333333-3333-4333-8333-333333333333',revision='test-source-revision'),settings=f['context']['targetConfiguration'],request=f['boundRequest'],ownerDecisions=[])

def fake_response(data,payload):
 role=data['role']
 if role=='GENERATION':
  mode=data.get('_testMode','material')
  plan=contact() if data['round']==1 else progression()
  if mode=='equivalent':plan['interventions'][0]['layout']='UNCHANGED'
  if data['round']>=3 and mode!='equivalent': plan['interventions'][0]['camera']='TRACK'
  if mode=='story':plan['storyChangeRequested']=True
  for i in plan['interventions']:i.update(dependsOnBeatIds=[],dependencyJustification=None)
  return dict(proposals=[dict(initial=plan,revision=None)],noImprovementReason=None)
 if role=='SOURCE_FIDELITY':
  packet=payload['packets'][0];m=[]
  for i,event in enumerate(packet['requiredEvents']):
   m.append(dict(anchor=L.__dict__.get('ANCHORS',['CHARACTER_IDENTITY','APPROVED_EVENTS','EVENT_ORDER','PHYSICAL_RULE','TEMPORAL_CONSTRAINTS','REQUIRED_ENDING'])[i%6],beatId='beat_01',eventId=event['eventId'],sourceQuote=packet['approvedStory'][event['sourceStart']:event['sourceEnd']],promptQuote=packet['prompt'].splitlines()[0],consistency='PASS'))
  for change in packet['changedBeats']:m.append(dict(anchor='APPROVED_EVENTS',beatId=change['beatId'],eventId=packet['requiredEvents'][0]['eventId'],sourceQuote=packet['approvedStory'][packet['requiredEvents'][0]['sourceStart']:packet['requiredEvents'][0]['sourceEnd']],promptQuote=change['newExecution'],consistency='PASS'))
  return dict(results=[dict(neutralId='Q01',sourceBinding=packet['sourceBinding'],decision='PASS',rationale='TEST_FIXTURE source review for orchestration; not human or real-model evidence.',uncertainty='Mock transport only; actual source/creative benefit unverified.',conflict=False,omissions=[],additions=[],mappings=m,productionRisks=['TEST_FIXTURE: small contact and reflection remain unverified.'])])
 from app.workflow.owner_machine_pilot import DIMENSIONS
 packets={p['label']:p['prompt'] for p in payload['packets']}
 dims={d:dict(judgment='B_BETTER',evidence=[dict(label=k,quote=v.splitlines()[0]) for k,v in packets.items()],absentEvidenceExplanation='',reason='TEST_FIXTURE comparative support; only transport is synthetic, not the canonical score.',weaknessesOrRisks=['Actual visual behavior unverified.'],targetedSuggestion='Review the existing contact transition.',uncertainty='Machine review fixture, not actual provider evidence.') for d in DIMENSIONS}
 return dict(dimensions=dims,overall=dict(judgment='B_BETTER',rationale='TEST_FIXTURE machine preference tests orchestration only.',strongestDifference='Source-bound production instructions.',unresolvedIssue='Actual rendered evidence unavailable.',blockingRegressions=[],uncertainty='Not independently calibrated creative evidence.'))

def dispatch(operation,data):
 if operation=='scope':return fixture_scope()
 if operation=='optimization-loop/local':
  return {'CAPABILITIES':L.capabilities,'EVALUATE':lambda:L.evaluate(data),'COMPARE':lambda:L.compare(data),'PREFLIGHT_REQUEST':lambda:L.preflight(data)}[data['action']]()
 class FakeTransport:
  def __init__(self,cfg,tokens,timeout):self.cfg=cfg;self.last_usage=None;self.last_response_metadata={}
  def complete(self,prompt,**kw):
   value=fake_response(data,json.loads(prompt));self.last_raw_response=json.dumps(value)
   self.last_usage=dict(prompt_tokens=2500,completion_tokens=2000)
   self.last_response_metadata=dict(model=self.cfg['model'],finishReason='stop',requestId='TEST_FIXTURE_PROVIDER_RESPONSE')
   return self.last_raw_response
 return L.execute_request(data,FakeTransport)

if __name__=='__main__':
 q=json.load(sys.stdin);print(json.dumps(dispatch(q['operation'],q.get('input',{})),ensure_ascii=False))
