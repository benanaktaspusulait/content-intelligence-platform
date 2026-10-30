"""Representation-only native schema repair and exact SDK-boundary validation.

Legacy experiment builders are frozen for replay. New corrected native requests
select this version explicitly; domain fields and creative validators are reused.
"""
from copy import deepcopy
import json
from urllib.parse import unquote
from jsonschema import Draft202012Validator

from .concept_fingerprint import digest
from .semantic_concept_provider import SemanticIdea

VERSION='semantic-native-schema-integrity-v1'


def pointer_token(value):return value.replace('~','~0').replace('/','~1')


def reference_audit(schema):
    """Inspect every reference,including unused definitions. Never fetch a URI."""
    found=[]
    def walk(value,path=''):
        if isinstance(value,dict):
            if '$ref' in value:found.append((path,value['$ref']))
            for key,item in value.items():walk(item,path+'/'+pointer_token(key))
        elif isinstance(value,list):
            for i,item in enumerate(value):walk(item,path+'/'+str(i))
    def resolve(reference):
        if not isinstance(reference,str) or not (reference=='#' or reference.startswith('#/')):
            return 'UNSUPPORTED_REFERENCE_FORM',None,None
        path=unquote(reference[1:]);current=schema
        for token in path[1:].split('/') if path else []:
            if any(token[i]=='~' and (i+1==len(token) or token[i+1] not in '01') for i in range(len(token))):
                return 'UNSUPPORTED_REFERENCE_FORM',None,None
            token=token.replace('~1','/').replace('~0','~')
            if isinstance(current,dict) and token in current:current=current[token]
            elif isinstance(current,list) and token.isdigit() and str(int(token))==token and int(token)<len(current):current=current[int(token)]
            else:return 'UNRESOLVED',path,None
        if not isinstance(current,(dict,bool)):return 'UNSUPPORTED_REFERENCE_FORM',path,None
        return 'RESOLVED',path,current
    def cyclic(value,targets):
        if isinstance(value,dict):
            if '$ref' in value:
                status,path,target=resolve(value['$ref'])
                if status=='RESOLVED':
                    if path in targets:return True
                    if cyclic(target,targets|{path}):return True
            return any(cyclic(item,targets) for key,item in value.items() if key!='$ref')
        if isinstance(value,list):return any(cyclic(item,targets) for item in value)
        return False
    walk(schema);result=[]
    for origin,reference in found:
        status,target_path,target=resolve(reference)
        if status=='RESOLVED' and cyclic(target,{target_path}):status='CYCLIC_REFERENCE'
        result.append(dict(reference=reference,originPath=origin+'/$ref',resolvedTargetPath=target_path if status in ('RESOLVED','CYCLIC_REFERENCE') else None,
            attemptedTargetPath=target_path,
            status=status,scope='Final provider document root; no external URI retrieval'))
    return result


def final_provider_schema_validation(schema):
    """Validate the exact object to be transmitted,not merely a source model."""
    Draft202012Validator.check_schema(schema)
    audit=reference_audit(schema)
    bad=[r for r in audit if r['status'] in ('UNRESOLVED','UNSUPPORTED_REFERENCE_FORM')]
    if bad:raise ValueError('FINAL_PROVIDER_SCHEMA_VALIDATION failed: unresolved/unsupported reference')
    if schema.get('type')!='object':raise ValueError('Native semantic envelope root must be object')
    if schema.get('additionalProperties') is not False:raise ValueError('Native envelope must retain additionalProperties=false')
    # Serialization must preserve the same final JSON object.
    encoded=json.loads(json.dumps(schema,ensure_ascii=False,allow_nan=False))
    if encoded!=schema:raise ValueError('Provider schema is not stable JSON')
    return dict(step='FINAL_PROVIDER_SCHEMA_VALIDATION',version=VERSION,syntax='VALID_DRAFT202012',
        schemaSha256=digest(schema),references=audit,unresolvedReferences=0,unsupportedReferences=0,
        cyclicReferences=sum(r['status']=='CYCLIC_REFERENCE' for r in audit),serializationRoundTripIdentical=True)


def native_response_format(candidate_count=1):
    if type(candidate_count) is not int or not 1<=candidate_count<=60:raise ValueError('Bounded explicit candidate count required')
    candidate=deepcopy(SemanticIdea.model_json_schema())
    definitions=candidate.pop('$defs',{})
    schema=dict(type='object',additionalProperties=False,
        properties=dict(ideas=dict(type='array',minItems=candidate_count,maxItems=candidate_count,items=candidate)),required=['ideas'])
    if definitions:schema['$defs']=definitions
    final_provider_schema_validation(schema)
    return dict(type='json_schema',json_schema=dict(name='semantic_raw_ideas_v1',strict=False,schema=schema))


def semantic_equivalence_proof(provider_schema):
    """Expand only local acyclic references and ignore definition storage sites."""
    canonical=SemanticIdea.model_json_schema()
    def resolve(root,reference):
        current=root
        for token in unquote(reference[2:]).split('/'):current=current[token.replace('~1','/').replace('~0','~')]
        return current
    def logical(value,root,seen=frozenset()):
        if isinstance(value,list):return [logical(v,root,seen) for v in value]
        if not isinstance(value,dict):return value
        if '$ref' in value:
            ref=value['$ref']
            if ref in seen:raise ValueError('Equivalence proof requires an acyclic actual contract')
            target=logical(resolve(root,ref),root,seen|{ref})
            siblings={k:v for k,v in value.items() if k not in ('$ref','$defs')}
            return {'allOf':[target,logical(siblings,root,seen)]} if siblings else target
        return {k:logical(v,root,seen) for k,v in value.items() if k!='$defs'}
    before=logical(canonical,canonical)
    after=logical(provider_schema['properties']['ideas']['items'],provider_schema)
    if before!=after:raise ValueError('Semantic candidate contract changed')
    return dict(candidateLogicalSchemaIdentical=True,canonicalLogicalSha256=digest(before),providerCandidateLogicalSha256=digest(after),
        compared=['all candidate/beat fields','field types','required lists','min/max bounds','enums','nullability','defaults','additionalProperties','annotations'],
        onlyRepresentationChange='$defs ownership moved from embedded candidate root to actual provider root; $ref strings unchanged.')


def native_compatibility_audit(fmt):
    schema=fmt['json_schema']['schema'];objects=[];keywords=set()
    def walk(value,path=''):
        if isinstance(value,dict):
            keywords.update(value.keys())
            if value.get('type')=='object':
                props=value.get('properties',{});required=value.get('required',[])
                objects.append(dict(path=path or '/',properties=list(props),required=required,
                    requiredAreDeclared=set(required)<=set(props),allPropertiesRequired=set(required)==set(props),
                    additionalProperties=value.get('additionalProperties')))
            for key,item in value.items():walk(item,path+'/'+key)
        elif isinstance(value,list):
            for i,item in enumerate(value):walk(item,path+'/'+str(i))
    walk(schema)
    if any(not v['requiredAreDeclared'] or v['additionalProperties'] is not False for v in objects):
        raise ValueError('Object contract policy changed')
    return dict(mode=fmt['type'],strict=fmt['json_schema']['strict'],rootObject=True,objects=objects,
        strictModeAssessment='NOT_ENABLED; defaults/optional fields intentionally preserved; no claim of strict=true compatibility.',
        knownUnsupportedKeywordsFromRepository=None,
        limitation='Repository adapter passes this JSON Schema directly. No undocumented remote keyword restriction or stricter contract is invented. Live acceptance remains unverified before probe.')


class LastMileSchemaGuard:
    """Instance-local call boundary: validate actual kwargs and forward once."""
    def __init__(self,create,expected_format,record):
        self.create=create;self.expected_hash=digest(expected_format);self.record=record;self.forwarded=0
    def __call__(self,**kwargs):
        if self.forwarded:raise ValueError('One SDK request only; no retry')
        fmt=kwargs.get('response_format')
        if digest(fmt)!=self.expected_hash:raise ValueError('Last-mile format differs from validated expected schema')
        schema=fmt['json_schema']['schema'];before=digest(schema)
        receipt=final_provider_schema_validation(schema)
        if digest(schema)!=before:raise ValueError('Schema mutated during validation')
        if digest(json.loads(json.dumps(kwargs,ensure_ascii=False,allow_nan=False)))!=digest(kwargs):
            raise ValueError('SDK request serialization changed')
        request_hash=digest(kwargs)
        self.record(kwargs,dict(**receipt,formatSha256=self.expected_hash,sameSchemaObjectForwarded=True,forwardOrdinal=1))
        if digest(kwargs)!=request_hash:raise ValueError('Request mutated after final validation')
        self.forwarded=1
        return self.create(**kwargs)
