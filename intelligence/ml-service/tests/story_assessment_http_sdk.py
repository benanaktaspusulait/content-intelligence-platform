"""Disposable E2E: actual app + OpenAI SDK, mock external HTTP only. No paid calls."""
import os,sys,json,socket
from pathlib import Path
from unittest.mock import patch
import httpx,openai
assert os.getenv('OPENAI_API_KEY')=='offline-not-a-credential'
assert not os.getenv('DEEPSEEK_API_KEY')
def audit(event,args):
    if event=='socket.connect' and args[0].family in (socket.AF_INET,socket.AF_INET6):raise PermissionError('Offline E2E forbids all outbound sockets')
    if event=='socket.getaddrinfo' and args[0] not in ('127.0.0.1','localhost','::1'):raise PermissionError('Offline DNS denied')
sys.addaudithook(audit)
from app.workflow.story_assessment import response_format,SYSTEM
from story_assessment_cases import case_response
control=Path(os.environ['ASSESSMENT_SDK_CONTROL']);trace=Path(os.environ['ASSESSMENT_MOCK_CALL_TRACE'])
def transport(request):
    body=json.loads(request.content);mode=json.loads(control.read_text())['mode']
    assert str(request.url)=='https://api.openai.com/v1/chat/completions'
    assert body['response_format']==response_format()
    assert body['model']=='gpt-4o-mini-2024-07-18' and body['max_tokens']==4000 and body['temperature']==0
    assert body['messages'][0]=={'role':'system','content':SYSTEM}
    payload=json.loads(body['messages'][1]['content']);assert 'responseContract' not in payload
    assert [x['ref'] for x in payload['candidates']]==['A','B']
    with trace.open('a') as f:f.write(json.dumps({'mode':mode,'serializedSdkBody':body,'realProviderCalls':0})+'\n')
    if mode=='timeout':raise httpx.ReadTimeout('Offline simulated timeout',request=request)
    message={'role':'assistant','content':case_response(payload,mode),'refusal':None}
    if mode=='refusal':message.update(content=None,refusal='Offline SDK refusal example')
    return httpx.Response(200,json={'id':'MOCK_ONLY_'+mode,'object':'chat.completion','created':0,'model':body['model'],
        'choices':[{'index':0,'message':message,'finish_reason':'length' if mode=='incomplete' else 'stop'}],
        'usage':{'prompt_tokens':100,'completion_tokens':200,'total_tokens':300}})
def sdk(**kwargs):
    assert kwargs['max_retries']==0 and kwargs['timeout']==20
    return openai.OpenAI(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(transport)))
import uvicorn
from app.main import app
with patch('app.llm.openai_provider.OpenAI',side_effect=sdk),patch('app.workflow.deepseek.DeepSeekTextProvider',side_effect=AssertionError('No DeepSeek generation')):
    uvicorn.run(app,host='127.0.0.1',port=int(os.environ['POMPOM_DISPOSABLE_ML_PORT']),log_level='warning')
