"""Configured capability adapters for the existing reconstruction contract.

No SDK construction in readiness. No fallback, retry, model discovery or hidden
reasoning inserted into authored production evidence.
"""
import json
import math
import os
from copy import deepcopy
from pathlib import Path
from openai import OpenAI
from app.llm.provider import LLMProvider, UnsupportedProviderError

# Exact model contract, verified against the official model page on 2026-10-16.
# In particular, GPT-6.1 Sol does not support none or minimal.
MODEL_REASONING_EFFORTS = {('openai', 'gpt-6.1-sol'): ('low', 'medium', 'high', 'xhigh', 'max')}


def validate_reasoning_effort(configuration):
    supported = MODEL_REASONING_EFFORTS.get((configuration.get('provider'), configuration.get('model')))
    if supported and configuration.get('reasoningEffort') not in supported:
        raise ValueError('Unsupported reasoning effort for the exact provider/model')


def profiles():
    path=Path(os.getenv('POMPOM_DATA_ROOT','data'))/'workflow/creative-provider-profiles-v3.json'
    data=json.loads(path.read_text())
    if data.get('version')!='creative-provider-capabilities-v3-2026-10-15':raise ValueError('Verified creative provider profile configuration required')
    return data


def profile(identity):
    p=deepcopy(profiles()['profiles'].get(identity))
    if not p or p.get('provider') not in ('deepseek','openai') or not p.get('model') or p.get('deprecated') or p.get('protocol')!='chat_completions' or p.get('responseMode') not in ('json_schema','json_object'):
        raise ValueError('Explicit available provider/model capability configuration required; no fallback')
    if not all(isinstance(p.get(k),(int,float)) and math.isfinite(p[k]) and p[k]>0 for k in ('inputUsdPerMillion','outputUsdPerMillion','contextTokens','maxOutputTokens')):
        raise ValueError('Verified provider limits/prices configuration required')
    return p


def readiness():
    data=profiles()
    return {**data,'profiles':{key:{**value,'configured':bool(os.getenv(value['provider'].upper()+'_API_KEY')),'liveAvailability':'UNVERIFIED_NO_PROVIDER_CALL'} for key,value in data['profiles'].items()}}


class CreativeCapabilityProvider(LLMProvider):
    def __init__(self, configuration, max_output_tokens, timeout_seconds):
        validate_reasoning_effort(configuration)
        self.configuration=configuration
        self.model=configuration['model']
        self.max_output_tokens=max_output_tokens
        key=os.getenv(configuration['provider'].upper()+'_API_KEY')
        if not key:raise ValueError('Explicit provider API key configuration required')
        # Test harness uses a distinct mounted profile catalog on an internal
        # network; neither browser nor request can override endpoint/model/key.
        self.client=OpenAI(api_key=key,base_url=configuration['baseUrl'],timeout=timeout_seconds,max_retries=0)

    def complete(self,prompt,system='',temperature=.7,image=None):
        if image is not None:raise UnsupportedProviderError('Creative production authoring is text-only')
        p=self.configuration
        schema=deepcopy(self.response_format)
        if p['responseMode']=='json_object':
            # JSON mode does not enforce JSON Schema; transmit the exact same
            # bounded source-ID schema as data and always validate server-side.
            system+='\nReturn JSON matching this schema; use catalog IDs exactly:\n'+json.dumps(schema['json_schema']['schema'],separators=(',',':'))
            schema={'type':'json_object'}
        args={'model':self.model,'messages':[{'role':'system','content':system},{'role':'user','content':prompt}],
              'response_format':schema,p['tokenParameter']:self.max_output_tokens}
        if p.get('reasoningEffort'):args['reasoning_effort']=p['reasoningEffort']
        if p.get('temperatureSupported'):args['temperature']=temperature
        self.last_request_started=True
        response=self.client.chat.completions.create(**args)
        usage=getattr(response,'usage',None)
        self.last_usage=usage.model_dump() if usage is not None else None
        choice=response.choices[0]
        self.last_response_metadata={'requestId':response.id,'finishReason':choice.finish_reason,'apiStatus':'COMPLETED','provider':p['provider'],'model':response.model}
        self.last_raw_response=choice.message.content or ''
        if choice.finish_reason!='stop':raise ValueError('Provider response did not complete; no automatic retry')
        return self.last_raw_response
