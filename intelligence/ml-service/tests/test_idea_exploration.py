"""IDEA exploration through the existing image adapter; all provider traffic is mocked."""
import base64
import hashlib
import json
import struct
import zlib
import httpx
import pytest
from openai import OpenAI
from app.llm.openai_provider import OpenAIProvider
from app.workflow import start_frame_generation as service


def png(w=9,h=16):
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\xff\xff\xff'*w)*h))+chunk(b'IEND',b'')


def setup(tmp_path,monkeypatch,mode='success'):
    monkeypatch.setenv('POMPOM_DATA_ROOT',str(tmp_path))
    monkeypatch.setenv('GPT_IMAGE_MODEL','gpt-image-2')
    monkeypatch.setenv('GPT_IMAGE_COST_USD','.053')
    ref=tmp_path/'VERIFIED_TEST_REFERENCE.png';ref.write_bytes(png())
    request=dict(draftId='11111111-1111-1111-1111-111111111111',explorationId='22222222-2222-2222-2222-222222222222',ideaRevision=3,
        sourceFirstFrame='Small Arda beside an enormous blanket; one strawberry at the opposite end.',
        contentProfile='CURIOSITY_ADVENTURE',characterId='arda',characterName='Arda',referenceId='test-ref',referenceImagePath=str(ref),referenceSha256=hashlib.sha256(ref.read_bytes()).hexdigest(),maxCostUsd=.1)
    calls=[]
    def handler(req):
        calls.append(req)
        if mode=='timeout':raise httpx.ReadTimeout('mock timeout',request=req)
        return httpx.Response(200,headers={'x-request-id':'req-image-test'},json={
            'created':1,'data':[{'b64_json':base64.b64encode(png(9,15) if mode=='wrong_size' else png()).decode()}],
            'usage':{'input_tokens':20,'output_tokens':80,'total_tokens':100}})
    provider=OpenAIProvider(api_key='test-key')
    provider.client=OpenAI(api_key='test-key',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(service,'OpenAIProvider',lambda **kwargs:provider)
    return request,calls


def test_saved_idea_uses_one_reference_edit_and_retains_asset_receipt(tmp_path,monkeypatch):
    request,calls=setup(tmp_path,monkeypatch)
    result=service.generate_idea_exploration(request)
    assert result['status']=='GENERATED' and len(calls)==1
    assert calls[0].url.path=='/v1/images/edits'
    assert result['draftId']==request['draftId'] and result['ideaRevision']==3
    assert request['sourceFirstFrame'] in result['imagePrompt']
    assert result['providerRequest']['size']=='1152x2048' and result['providerRequest']['n']==1
    assert result['providerRequest']['referenceImages'][0]['sha256']==request['referenceSha256']
    assert result['usage']['total_tokens']==100 and result['calculatedCostUsd']==.053
    assert result['providerResponseMetadata']['httpRequestId']=='req-image-test'
    assert 'b64_json' not in result['providerResponse']['data'][0]
    assert (tmp_path/'exploratory-frames'/request['draftId']/'3'/request['explorationId']) in __import__('pathlib').Path(result['imagePath']).parents
    assert not result['firstFrameEligible'] and not result['renderAuthorized'] and not result['publishAuthorized']
    assert 'contentId' not in result and 'promptVersionId' not in result
    assert result['label']=='EXPLORATORY — NOT PRODUCTION APPROVED'


def test_missing_or_changed_reference_and_budget_do_not_dispatch(tmp_path,monkeypatch):
    request,calls=setup(tmp_path,monkeypatch)
    bad={**request,'referenceSha256':'0'*64}
    assert service.generate_idea_exploration(bad)['providerDispatched'] is False
    assert service.generate_idea_exploration({**request,'maxCostUsd':.001})['status']=='REJECTED_COST_CEILING'
    assert calls==[]


def test_timeout_preserves_unknown_cost_and_does_not_retry(tmp_path,monkeypatch):
    request,calls=setup(tmp_path,monkeypatch,'timeout')
    result=service.generate_idea_exploration(request)
    assert result['status']=='PROVIDER_OUTCOME_UNKNOWN' and len(calls)==1
    assert result['calculatedCostUsd'] is None and result['usage'] is None
    assert result['providerRequest']['n']==1 and result['automaticRetries']==0
    assert not result['renderAuthorized']


def test_wrong_size_is_not_reported_as_a_valid_vertical_asset(tmp_path,monkeypatch):
    request,calls=setup(tmp_path,monkeypatch,'wrong_size')
    result=service.generate_idea_exploration(request)
    assert len(calls)==1 and result['status']=='GENERATED_SIZE_MISMATCH'
    assert result['calculatedCostUsd']==.053 and not result['firstFrameEligible']


def test_exploration_api_cannot_accept_production_ids_or_unsigned_dispatch(tmp_path,monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.workflow.api import router
    request,calls=setup(tmp_path,monkeypatch)
    app=FastAPI();app.include_router(router);client=TestClient(app)
    monkeypatch.setenv('WORKFLOW_ADAPTIVE_DISPATCH_TOKEN','a'*40)
    assert client.post('/api/v1/workflow/idea-exploration/generate',json=request).status_code==403
    assert client.post('/api/v1/workflow/idea-exploration/generate',json={**request,'contentId':1}).status_code==422
    assert calls==[]
