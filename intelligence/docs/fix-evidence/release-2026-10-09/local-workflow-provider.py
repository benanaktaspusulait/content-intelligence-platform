"""No paid network calls. Fixture critic/roles plus real local patch verification.
Run with the ML venv against disposable backend port 8086 only.
Fixture confidence/grades are synthetic and never authorize a real render.
"""
import json,sys,time,hashlib
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'ml-service'))
from app.workflow.review import review_prompt
from app.workflow.repair import repair_prompt
DATA=Path(__file__).resolve().parents[3]/'data'
CAP=json.loads((DATA/'workflow/provider-capabilities.json').read_text())['models']
CALLS=[]
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def send(self,value,status=200):
  raw=json.dumps(value,ensure_ascii=False).encode(); self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  if self.path=='/fixture-calls':return self.send(CALLS)
  return self.send({'status':'UP','fixture':'LOCAL_MOCK'})
 def do_POST(self):
  value=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
  action=self.path.rsplit('/',1)[-1]
  CALLS.append({'action':action,'body':value,'actualPaidCalls':0})
  try:
   if action=='readiness':
    return self.send({'enabled':True,'liveVerified':False,'fixture':'LOCAL_MOCK','roles':[{'role':r,'provider':p,'model':'LOCAL_MOCK-'+p,'configured':True,'modality':'TEXT_ONLY'} for r,p in [('STORY','deepseek'),('BUILD_PROMPT','openai'),('MINIMAL_REPAIR','openai')]]})
   if action=='review':
    reviewed=review_prompt(value,CAP)
    # Synthetic independent critic conditions match the backend's existing plateau fixture.
    count=3 if 'CUT' in value['prompt'] else 2
    findings=[{'confidence':'HIGH','evidenceBasis':'UNVERIFIED_HYPOTHESIS','riskCategory':'LOCAL_MOCK_FIXTURE_'+str(i),'plausibleFailure':'Synthetic contract test finding; no observed render claim','smallestChange':'Fixture-only patch','sourceQuote':'CUT' if 'CUT' in value['prompt'] else 'Hold.','sourceSpan':[0,0]} for i in range(count)]
    reviewed.update(fixture='LOCAL_MOCK independent critic',planQuality={'status':'PASS','fixture':'LOCAL_MOCK'},executionRisk={'status':'PASS','fixture':'LOCAL_MOCK'},executionReview={'status':'REWRITE','findings':findings},repairPasses=0)
    return self.send(reviewed)
   if action=='repair':return self.send(repair_prompt(value['request'],value['patches'],CAP))
   if action=='creative-role':
    role=value['role'];text=value['text'];time.sleep(.2)
    if role=='MINIMAL_REPAIR':
     quote='CUT' if 'CUT' in text else 'Hold.'; start=text.index(quote)
     result={'patches':[{'start':start,'end':start+len(quote),'sourceQuote':quote,'replacement':'Hold.' if quote=='CUT' else 'Wait.'}]}
    elif role=='STORY': result={'alternatives':['LOCAL_MOCK story: Luca pushes a box.']}
    else:result={'prompt':'0-15 SEC\nLuca pushes. CUT'}
    return self.send({'role':role,'provider':'deepseek' if role=='STORY' else 'openai','model':'LOCAL_MOCK-'+role,'fixture':True,'result':result,'costUpperBoundUsd':.001,'calls':1,'actualPaidCalls':0,'validationStatus':'NOT_VALIDATED','visualInspected':False})
   return self.send({'detail':'Unsupported fixture endpoint'},404)
  except Exception as error:return self.send({'detail':str(error)},409)
print('LOCAL_MOCK fixture listening on 8016; no live provider implementation',flush=True)
ThreadingHTTPServer(('127.0.0.1',8016),Handler).serve_forever()
