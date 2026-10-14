import json
from pathlib import Path
from unittest.mock import patch
from app.parser.prompt_parser import PromptParser,parse_prompt
from app.workflow.review import _run_canonical_evaluation
root=Path(__file__).resolve().parent;root.mkdir(parents=True,exist_ok=True);r=json.load(open(root/'analysis.json'));c=json.load(open(root/'comparison.json'));orig=PromptParser._resolve_attempt_evidence;out={}
for name,x in [('Original',r)]+[(a['candidateId'],a['review']) for a in c['candidates']]:
 traces=[]
 def capture(self,description,content,role,label):
  m=self._NATURAL_ATTEMPT_PHRASES.search(content);ret=orig(self,description,content,role,label);traces.append({'content':content,'match':m.group(0) if m else None,'verb':ret[1],'isAttempt':ret[0],'matchOffset':m.start() if m else None});return ret
 with patch.object(PromptParser,'_resolve_attempt_evidence',capture),patch('app.llm.semantic_checks.get_provider',side_effect=AssertionError('No provider')):
  fresh=_run_canonical_evaluation({**x['boundRequest'],'prompt':x['originalPrompt'],'canonicalRulesetVersion':'1.8'})
 assert fresh['score']==x['canonicalRuleEvaluation']['score'];out[name]={'score':fresh['score'],'attemptTrace':traces,'motion':[b['motionAmount'] for b in fresh['videoPlanIR']['beats']]}
a=c['candidates'][0]['review'];req={**a['boundRequest'],'prompt':a['originalPrompt'],'canonicalRulesetVersion':'1.8'}
def exclude_camera_match(self,description,content,role,label):
 m=self._NATURAL_ATTEMPT_PHRASES.search(content)
 if m and m.group(0)=='keep the' and content.rfind('[',0,m.start())>content.rfind(']',0,m.start()):return False,'','NONE',None
 return orig(self,description,content,role,label)
with patch.object(PromptParser,'_resolve_attempt_evidence',exclude_camera_match),patch('app.llm.semantic_checks.get_provider',side_effect=AssertionError('No provider')):
 corrected_diagnostic=_run_canonical_evaluation(req)
assert corrected_diagnostic['score']==r['canonicalRuleEvaluation']['score']
out['diagnosticOnlyCameraInstructionExcluded']={'score':corrected_diagnostic['score'],'grade':corrected_diagnostic['grade'],'note':'Temporary test seam only. No application code, prompt text or saved evaluation changed.'}
parser=PromptParser();motions={s:parser._estimate_motion_amount(s) for s in ['Sticky notes fly through the air.','Cards fly through the air.','Zed pulls notes; notes multiply.','Zed pulls cards; cards multiply.','Zed stands still.']};assert motions['Sticky notes fly through the air.']=='none' and motions['Cards fly through the air.']=='moderate';out['motionSubstringControls']=motions
out['trueAttemptControl']=orig(parser,'Mimi keeps pulling the note.','Mimi keeps pulling the note.','','');assert out['trueAttemptControl'][0] and out['trueAttemptControl'][1]=='PULLING'
(root/'deterministic-evidence.json').write_text(json.dumps(out,indent=2));print({k:v.get('score') for k,v in out.items() if isinstance(v,dict) and 'score' in v});print(motions)
