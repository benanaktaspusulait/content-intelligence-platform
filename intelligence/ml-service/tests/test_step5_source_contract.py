from copy import deepcopy
from app.parser.prompt_parser import source_plan_evidence
from app.workflow.review import enrich_production_evidence, review_prompt

PROMPT = 'Duration: 5s\nCHARACTER\nNori\n0-2s: Nori stands with a wooden coin; she smiles.\n2-5s: Nori flips the coin.\nAUDIO\nQuiet music'

def request(plan):
    return dict(prompt=PROMPT, sourceId='fixture', sourceVersion='10', profile='post-family-v1', structuredPlan=plan, references=[], settings={}, segments=[], desiredDuration=5, generator='AUTO')

def tracked(plan):
    return next(c for c in enrich_production_evidence(request(plan))['claims'] if c['field']=='trackedPlan')

def test_actual_events_beats_mismatch_is_not_narrative_contradiction():
    legacy={'events':[{'action':'Nori flips the coin.', 'sourceQuote':'2-5s: Nori flips the coin.'}]}
    assert tracked(legacy)['diagnosticCode']=='EMPTY_TRACKED_BEATS'
    assert tracked(legacy)['state']=='INVALID'
    legacy['evidenceStatus']='DETERMINISTIC_SOURCE_EVENTS_ONLY'
    claims=enrich_production_evidence(request(legacy))['claims']
    assert next(c for c in claims if c['field']=='sourceEventCandidates')['state']=='INFERRED'
    assert not any(c['state']=='CONTRADICTORY' for c in claims)

def test_correct_source_bound_schema_checks_exact_spans_and_preserves_f8_block():
    quote='2-5s: Nori flips the coin.'; start=PROMPT.index(quote)
    plan={'schemaVersion':'source-bound-beats-v1','evidenceStatus':'DETERMINISTIC_SOURCE_EVENTS_ONLY','beats':[dict(id='beat_02',startTime=2,endTime=5,action='Nori flips the coin.',sourceQuote=quote,sourceSpan=[start,start+len(quote)])]}
    original=deepcopy(plan)
    assert tracked(plan)['state']=='OBSERVED'
    assert tracked(plan)['semanticVerification']=='NOT_PERFORMED'
    result=review_prompt(request(plan))
    assert result['family8']['renderAuthorization']['status']!='AUTHORIZED'
    assert plan==original
    plan['beats'][0]['sourceSpan'][0]+=1
    assert tracked(plan)['state']=='INVALID'
    assert tracked(plan)['diagnosticCode']=='INVALID_SOURCE_BOUND_BEATS'
    del plan['beats'][0]['sourceSpan']
    assert tracked(plan)['state']=='MISSING'
    assert tracked(plan)['diagnosticCode']=='SOURCE_SPANS_UNAVAILABLE'

def test_generic_entity_extraction_is_source_bound_and_read_only():
    result=source_plan_evidence(PROMPT,'fixture','10'); ir=result['videoPlanIR']
    assert result['kind']=='READ_ONLY_SOURCE_EXTRACTION'
    assert result['semanticValidationStatus']=='NOT_PERFORMED'
    assert result['authorizationStatus']=='NOT_EVALUATED'
    assert result==source_plan_evidence(PROMPT,'fixture','10')
    assert result['resultId']!=source_plan_evidence(PROMPT,'fixture','11')['resultId']
    assert ir['mainCharacter']=='Nori' and ir['principalObject']=='wooden coin'
    assert ir['entityEvidence']['principalObject']['state']=='OBSERVED'
    assert ir['beats'][1]['fieldEvidence']['primaryObject']['state']=='INFERRED'
    for beat in ir['beats']:
        assert 'AUDIO' not in beat['sourceQuote']
        assert beat['sourceAction'].startswith('Nori')
        for evidence in beat['fieldEvidence'].values():
            if evidence.get('sourceSpan'):
                a,b=evidence['sourceSpan']; assert PROMPT[a:b]==evidence['sourceQuote']
    unknown=source_plan_evidence('0-2s: Something moves.','fixture','10')['videoPlanIR']
    assert unknown['mainCharacter'] is None
    assert unknown['entityEvidence']['mainCharacter']['state']=='UNKNOWN'

def test_saved_live_fixture_reproduces_mismatch_and_corrected_five_beat_contract(monkeypatch):
    import json
    from pathlib import Path
    saved=json.loads((Path(__file__).resolve().parents[2]/'backend/src/test/resources/step5-analysis-snapshot.json').read_text())
    monkeypatch.setenv('POMPOM_DATA_ROOT',str(Path(__file__).resolve().parents[2]/'data'))
    value=deepcopy(saved['boundRequest']);before=deepcopy(saved)
    old=value['structuredPlan'];assert len(old['events'])==5 and not old.get('beats')
    # The old tracked-plan consumer saw an empty collection although five events existed.
    assert not (old.get('beats') or [])
    projection=source_plan_evidence(value['prompt'],value['sourceId'],value['sourceVersion'])
    beats=projection['videoPlanIR']['beats'];assert len(beats)==5
    value['structuredPlan']={'schemaVersion':'source-bound-beats-v1','evidenceStatus':'DETERMINISTIC_SOURCE_EVENTS_ONLY','beats':[dict(id=b['id'],startTime=b['startTime'],endTime=b['endTime'],action=b['sourceAction'],sourceQuote=b['sourceQuote'],sourceSpan=b['sourceSpan']) for b in beats]}
    claim=next(c for c in enrich_production_evidence(value)['claims'] if c['field']=='trackedPlan')
    assert claim['state']=='OBSERVED' and claim['semanticVerification']=='NOT_PERFORMED'
    capabilities=json.loads((Path(__file__).resolve().parents[2]/'data/workflow/provider-capabilities.json').read_text())['models']
    corrected=review_prompt(value,capabilities)
    assert corrected['canonicalRuleEvaluation']['videoPlanIR']['coreMechanic']['physicalRule']=='each pull doubles the number of sticky notes'
    reasons=corrected['family8']['renderAuthorization']['reasons']
    assert any(r['source']=='REFERENCE_ASSOCIATION' for r in reasons)
    assert any(r['source']=='EXECUTION_INPUTS' for r in reasons)
    assert corrected['family8']['renderAuthorization']['status']!='AUTHORIZED'
    assert not any(r['source']=='SOURCE_INTEGRITY' and r['code']=='ASSESSMENT_TECHNICAL_FAILURE' for r in reasons)
    assert saved==before and saved['canonicalRuleEvaluation']['score']==85

def test_explicit_repeated_physical_rule_keeps_exact_source_evidence_and_unknown_consistency():
    import json
    from pathlib import Path
    from app.parser.prompt_parser import parse_prompt
    saved=json.loads((Path(__file__).resolve().parents[2]/'backend/src/test/resources/step5-analysis-snapshot.json').read_text())
    prompt=saved['originalPrompt'];core=parse_prompt(prompt).video_plan_ir['coreMechanic']
    assert core['physicalRule']=='each pull doubles the number of sticky notes'
    evidence=core['physicalRuleEvidence'];a,b=evidence['sourceSpan']
    assert prompt[a:b]==evidence['sourceQuote']==core['physicalRule']
    assert evidence['state']=='OBSERVED' and evidence['semanticVerification']=='NOT_PERFORMED'
    assert core['consistency'] is None and core['mechanicCount'] is None
    generic='Duration: 5s\n0-5s: Nori works; every attempt triples the number of wooden coins [wide shot]'
    assert parse_prompt(generic).video_plan_ir['coreMechanic']['physicalRule']=='every attempt triples the number of wooden coins'
    unknown=parse_prompt('Duration: 5s\n0-5s: Nori watches wooden coins.').video_plan_ir['coreMechanic']
    assert 'physicalRuleEvidence' not in unknown and unknown['consistency'] is None
