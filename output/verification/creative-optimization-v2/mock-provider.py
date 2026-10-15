import json,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
class Handler(BaseHTTPRequestHandler):
 def do_POST(self):
  if self.path!='/v1/chat/completions': self.send_error(404);return
  data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  payload=json.loads(data['messages'][-1]['content'])
  assert payload['contractVersion']=='creative-reconstruction-v2'
  with open('/evidence/mock-provider-requests.jsonl','a') as f:f.write(json.dumps(data)+'\n')
  raw=json.loads(Path('/evidence/mock-response.json').read_text())
  value={'id':'mock-creative-v2-'+str(time.time_ns()),'object':'chat.completion','created':int(time.time()),'model':data['model'],'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(raw)},'finish_reason':'stop'}],'usage':{'prompt_tokens':3000,'completion_tokens':1500,'total_tokens':4500}}
  body=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
ThreadingHTTPServer(('0.0.0.0',8081),Handler).serve_forever()
