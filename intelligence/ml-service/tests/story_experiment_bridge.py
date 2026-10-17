"""Actual ML endpoints plus mocked adapter receipt, for disposable Java E2E."""
import json
import os
import sys
from unittest.mock import patch
import hashlib
import hmac
from fastapi.testclient import TestClient
from app.main import app
from story_experiment_fixture import alternatives, review, inputs

os.environ.update(WORKFLOW_STORY_MODEL='deepseek-flash', WORKFLOW_STORY_PILOT_MODEL_POLICY='DIRECT_FLASH_TEXT_V1', WORKFLOW_STORY_INPUT_USD_PER_MILLION='.3',
                  WORKFLOW_STORY_OUTPUT_USD_PER_MILLION='1.2',WORKFLOW_STORY_REVIEW_MODEL='gpt-4o-mini-2024-07-18',
                  WORKFLOW_STORY_REVIEW_INPUT_USD_PER_MILLION='.15',WORKFLOW_STORY_REVIEW_OUTPUT_USD_PER_MILLION='.6',
                  WORKFLOW_CREATIVE_ROLES_ENABLED='true',WORKFLOW_ADAPTIVE_DISPATCH_TOKEN='offline-disposable-story-dispatch-token-0001')
data=json.load(sys.stdin);operation=data['operation'];body=data['input'];mode=data.get('mode','valid')
if operation=='fixture':
    text,context=inputs()
    print(json.dumps({'text':text,'context':context}));sys.exit(0)
if operation=='offline-evidence-audit':
    from app.workflow.story_evidence import derive_source_evidence
    print(json.dumps(derive_source_evidence(body['text'],body['context'],body['candidate'])));sys.exit(0)
client=TestClient(app)

class MockAdapter:
    def __init__(self,*a,**kw): self.model=kw.get('model') or (a[0] if a else '')
    def complete(self,prompt,system='',**kwargs):
        payload=json.loads(prompt);context=body['context'];role=body['role']
        if mode in ('saved-first','saved-followup') and role=='STORY':
            from pathlib import Path
            folder='first-real-story-evolution-evidence' if mode=='saved-first' else 'real-story-identity-fidelity-followup-evidence'
            evidence=Path(__file__).resolve().parents[2]/'docs'/folder
            saved=json.loads((evidence/'provider-receipt.json').read_text())
            self.last_raw_response=(evidence/'raw-model-response.txt').read_text()
            self.last_usage=saved['usage'];self.last_response_metadata=saved['providerResponseMetadata']
            self.last_provider_response=saved['providerApiResponse']
            return self.last_raw_response
        if (role=='STORY' and mode=='story-timeout') or (role=='STORY_REVIEW' and mode=='review-timeout'):
            raise TimeoutError('Offline simulated timeout without returned usage')
        if role=='STORY_REVIEW' and mode=='review-transport':
            raise ConnectionError('Offline simulated transport error without returned usage')
        self.last_usage={'prompt_tokens':100,'completion_tokens':200}
        self.last_response_metadata={'model':self.model,'finishReason':'stop','requestId':'offline-adapter-receipt'}
        if mode=='unknown-model':self.last_response_metadata['model']='unapproved-substitute'
        if mode=='missing-model':self.last_response_metadata.pop('model')
        if role=='STORY':
            candidates=alternatives(body['text'],context['storyExperiment'])
            if mode=='zero':candidates=[]
            if mode=='one':candidates=candidates[:1]
            if mode=='three':candidates.append({**candidates[0],'candidateId':'candidate-3'})
            if mode=='duplicate-id':candidates[1]['candidateId']=candidates[0]['candidateId']
            if mode=='duplicate-text':candidates[1]['text']=candidates[0]['text']
            if mode=='incomplete':candidates[1]['text']='Short.'
            if mode=='source':candidates[1]['text']='An unrelated dragon named Rex flies to the moon. Then he lands and stays there. '*4
            if mode=='unknown':candidates[1]['sourceContract']['status']='UNKNOWN'
            if mode=='rule-mutation':
                rule=next(a['quote'] for a in context['storyExperiment']['protectedAnchors'] if a['kind']=='PHYSICAL_RULE')
                candidates[1]['text']=candidates[1]['text'].replace(rule,'walking away multiplies the notes')
            if mode=='bad-offsets':candidates[1]['sourceContract']['bindings'][0].update(candidateStart=1,candidateEnd=3)
            if mode=='proposal':candidates[1]['sourceContract'].update(status='PROTECTED_CHANGE_PROPOSAL',protectedChanges=[
                {'anchorId':context['storyExperiment']['protectedAnchors'][-1]['id'],'proposedChange':'Change the ending','justification':'Proposal only, not approved'}])
            result={'alternatives':candidates}
        else:
            result=review(context['candidates'],context)
        self.last_raw_response='{malformed' if mode=='malformed' or (mode=='review-malformed' and role=='STORY_REVIEW') else json.dumps(result)
        if mode=='missing-usage':self.last_usage=None
        if mode=='over-budget':self.last_usage={'prompt_tokens':1000000,'completion_tokens':4000}
        return self.last_raw_response

with patch('app.workflow.deepseek.DeepSeekTextProvider',MockAdapter),patch('app.llm.openai_provider.OpenAIProvider',MockAdapter):
    raw=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode()
    signature=hmac.new(os.environ['WORKFLOW_ADAPTIVE_DISPATCH_TOKEN'].encode(),raw,hashlib.sha256).hexdigest()
    response=client.post('/api/v1/workflow/'+operation,content=raw,headers={'Content-Type':'application/json','X-Adaptive-Dispatch':signature})
    if response.status_code!=200:raise RuntimeError(str(response.status_code)+': '+response.text)
    print(json.dumps(response.json(),ensure_ascii=False))
