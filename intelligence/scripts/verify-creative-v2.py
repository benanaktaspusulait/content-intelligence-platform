#!/usr/bin/env python3
"""Real built application + mocked SDK HTTP + disposable DB acceptance.

Production is SELECT-only. The test network has no external egress; no real keys.
Use --keep for manual browser QA, then --cleanup. No production mock endpoint.
"""
import argparse
import hashlib
import json
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/verification/creative-optimization-v2'
PREFIX='pompom-creative-v2-acceptance'
NETWORK=PREFIX+'-network'
NAMES={key:PREFIX+'-'+key for key in ['db','mock','ml','backend','frontend']}

def command(*args,input=None,check=True):
    result=subprocess.run(args,input=input,text=True,capture_output=True,check=False)
    if check and result.returncode: raise RuntimeError(f'{args[:3]}: {result.stderr[-2500:]} {result.stdout[-1000:]}')
    return result.stdout.strip()

def sql(container,query):
    return command('docker','exec','-i',container,'psql','-X','-v','ON_ERROR_STOP=1','-At','-U','pompom','-d','pompom',input=query)

def fetch(url,body=None):
    request=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=190) as r:return json.load(r)

def ready(url):
    deadline=time.monotonic()+150
    while time.monotonic()<deadline:
        try: return fetch(url)
        except Exception: time.sleep(.5)
    raise RuntimeError('Application readiness timeout: '+url)

def port(name,container_port):
    raw=command('docker','port',name,str(container_port)).splitlines()[0]
    return raw.rsplit(':',1)[1]

def cleanup():
    for name in reversed(list(NAMES.values())):command('docker','rm','-f',name,check=False)
    command('docker','network','rm',NETWORK,check=False)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--keep',action='store_true');parser.add_argument('--cleanup',action='store_true');args=parser.parse_args()
    if args.cleanup:cleanup();return
    OUT.mkdir(parents=True,exist_ok=True)
    prod=command('docker','compose','-f',str(ROOT/'intelligence/docker-compose.yml'),'ps','-q','postgres')
    if not prod:raise RuntimeError('Production read-only source is unavailable')
    before=sql(prod,"SELECT id::text||'|'||md5(payload::text) FROM post_family_workflow_events ORDER BY id;")
    (OUT/'production-history-before.txt').write_text(before+'\n')
    clones={
        'contents': 'id=10', 'prompt_versions':'id=10 AND content_id=10',
        'prompt_creative_provenance':'prompt_version_id=10', 'post_family_workflow_events':'true'}
    rows={table:json.loads(sql(prod,f"SELECT COALESCE(jsonb_agg(to_jsonb(r)), '[]'::jsonb) FROM (SELECT * FROM {table} WHERE {condition}) r;")) for table,condition in clones.items()}
    (OUT/'test-source-fingerprints.json').write_text(json.dumps({k:{'rows':len(v),'sha256':hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()} for k,v in rows.items()},indent=2))
    cleanup()
    command('docker','network','create','--internal',NETWORK)
    try:
        def run(key,*extra):return command('docker','run','-d','--name',NAMES[key],'--network',NETWORK,*extra)
        run('db','--network-alias','postgres','-e','POSTGRES_USER=pompom','-e','POSTGRES_PASSWORD=disposable-only','-e','POSTGRES_DB=pompom','postgres:17-alpine')
        stub=OUT/'mock-provider.py'
        stub.write_text('''import json,time\nfrom http.server import BaseHTTPRequestHandler,ThreadingHTTPServer\nfrom pathlib import Path\nclass Handler(BaseHTTPRequestHandler):\n def do_POST(self):\n  if self.path!='/v1/chat/completions': self.send_error(404);return\n  data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))\n  payload=json.loads(data['messages'][-1]['content'])\n  assert payload['contractVersion']=='creative-reconstruction-v2'\n  with open('/evidence/mock-provider-requests.jsonl','a') as f:f.write(json.dumps(data)+'\\n')\n  raw=json.loads(Path('/evidence/mock-response.json').read_text())\n  value={'id':'mock-creative-v2-'+str(time.time_ns()),'object':'chat.completion','created':int(time.time()),'model':data['model'],'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(raw)},'finish_reason':'stop'}],'usage':{'prompt_tokens':3000,'completion_tokens':1500,'total_tokens':4500}}\n  body=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)\nThreadingHTTPServer(('0.0.0.0',8081),Handler).serve_forever()\n''')
        (OUT/'mock-provider-requests.jsonl').write_text('')
        run('mock','--network-alias','mock-provider','--network-alias','creative-render-service','-v',str(OUT)+':/evidence','intelligence-ml-service','python','/evidence/mock-provider.py')
        env={'POMPOM_DATA_ROOT':'/data','POMPOM_SEMANTIC_ENABLED':'false','SEMANTIC_VIDEO_AI_ENABLED':'false',
            'WORKFLOW_CREATIVE_ROLES_ENABLED':'true','WORKFLOW_PROMPT_OPTIMIZATION_MODEL':'mock-creative-v2',
            'WORKFLOW_PROMPT_OPTIMIZATION_INPUT_USD_PER_MILLION':'0.15','WORKFLOW_PROMPT_OPTIMIZATION_OUTPUT_USD_PER_MILLION':'0.6',
            'OPENAI_API_KEY':'mock-local-only','OPENAI_BASE_URL':'http://mock-provider:8081/v1'}
        envargs=[x for k,v in env.items() for x in ('-e',k+'='+v)]
        run('ml','--network-alias','ml-service','-v',str(ROOT/'intelligence/data')+':/data:ro',*envargs,'intelligence-ml-service')
        backendenv={'SPRING_PROFILES_ACTIVE':'docker','DB_URL':'jdbc:postgresql://postgres:5432/pompom','DB_USERNAME':'pompom','DB_PASSWORD':'disposable-only',
                    'ML_SERVICE_URL':'http://ml-service:8000','ML_BASE_URL':'http://ml-service:8000','POMPOM_DATA_ROOT':'/data',
                    'WORKFLOW_PROMPT_OPTIMIZATION_MODEL':'mock-creative-v2','AI_ENABLED':'false'}
        run('backend','--network-alias','backend','-v',str(ROOT/'intelligence/data')+':/data:ro',
            *[x for k,v in backendenv.items() for x in ('-e',k+'='+v)],'intelligence-backend')
        # Only nginx has a host ingress network. Backend, ML and mock have no external route.
        command('docker','create','--name',NAMES['frontend'],'--network','bridge','-p','127.0.0.1::80','intelligence-frontend')
        command('docker','network','connect',NETWORK,NAMES['frontend'])
        command('docker','start',NAMES['frontend'])
        base='http://127.0.0.1:'+port(NAMES['frontend'],80)
        ready(base+'/api/v1/intelligence/workflow/provider-capabilities')
        if sql(NAMES['db'],'SELECT count(*) FROM prompt_versions;') != '0': raise RuntimeError('Test database not empty')
        # Full rows originate from SELECT-only reads, restored only into the distinct disposable container.
        for table,data in rows.items():
            literal=json.dumps(data,ensure_ascii=False).replace("'","''")
            sql(NAMES['db'],f"SET session_replication_role=replica; INSERT INTO {table} SELECT * FROM jsonb_populate_recordset(NULL::{table},'{literal}'::jsonb);")
        analysis='f0d36feb-ee0f-4da8-ae21-2071a3ddea18'
        prompt_before=sql(NAMES['db'],'SELECT id::text||\'|\'||md5(raw_text) FROM prompt_versions ORDER BY id;')
        request={'contentId':10,'promptVersionId':10,'operatorAuthorized':True,'maxCostUsd':0.1,'startNewPlanFirstAttempt':True}
        result=fetch(base+'/api/v1/intelligence/workflow/records/'+analysis+'/creative-optimization',request)
        (OUT/'isolated-live-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        assert not result.get('optimizationFailed'),result
        assert result['comparisonAssessment']['lineageVerified'] is True,result['comparisonAssessment']
        assert len(result['candidates']) in (1,2)
        assert result['selection'] is None and result['approval'] is None
        for c in result['candidates']:
            assert c['currentAssessment']['classification'] in ('PLAUSIBLE_IMPROVEMENT_UNVERIFIED','REGRESSION'),c['currentAssessment']
            if c['currentAssessment']['classification']=='REGRESSION': assert not c['currentAssessment']['approvalEligible']
            assert c['review']['canonicalRuleEvaluation']['rulesetVersion']=='1.11'
            assert c['review']['canonicalRuleEvaluation']['score'] <= 88.40625000000001,c['review']['canonicalRuleEvaluation']['score']
            assert c['currentAssessment']['creativeAssessment']['provenBetter'] is False
            assert c['sourceEventCoverage']['semanticFidelity']=='UNKNOWN'
        assert any(c['currentAssessment']['approvalEligible'] for c in result['candidates'])
        repeated=fetch(base+'/api/v1/intelligence/workflow/records/'+analysis+'/creative-optimization',request)
        assert repeated['recordId']==result['recordId']
        assert len((OUT/'mock-provider-requests.jsonl').read_text().splitlines())==1,'Idempotency dispatched more than once'
        assert prompt_before==sql(NAMES['db'],'SELECT id::text||\'|\'||md5(raw_text) FROM prompt_versions ORDER BY id;')
        assert sql(NAMES['db'],"SELECT count(*) FROM post_family_workflow_events WHERE kind LIKE 'GOVERNANCE_%';")=='0'
        frontend=base
        # UI is the same built artifact as production; only its network/DB/provider are disposable.
        endpoints={'backend':base,'frontend':frontend,'ml':'INTERNAL_ONLY:http://ml-service:8000',
            'step6':frontend+'/quality/detail?contentId=10&promptVersionId=10&studio=1&stage=6',
            'comparisonId':result['recordId'],'internalNetwork':NETWORK,'providerDispatches':1,'realProviderCalls':0,
            'database':NAMES['db'],'promptVersionCount':1,'selection':None,'approval':None}
        (OUT/'isolated-live-endpoints.json').write_text(json.dumps(endpoints,indent=2))
        print(json.dumps(endpoints,indent=2),flush=True)
    finally:
        after=sql(prod,"SELECT id::text||'|'||md5(payload::text) FROM post_family_workflow_events ORDER BY id;")
        (OUT/'production-history-after.txt').write_text(after+'\n')
        (OUT/'production-history-integrity.json').write_text(json.dumps({'historicalRows':len(before.splitlines()),'unchanged':before==after,'productionWrites':0},indent=2))
        if not args.keep:cleanup()

if __name__=='__main__': main()
