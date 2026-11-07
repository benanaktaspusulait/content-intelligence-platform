"""Offline diagnostics for the unchanged opening evaluator."""
import json
from pathlib import Path

from app.workflow.canonical_creative_evidence import from_structured
from app.workflow.semantic_evidence_adapter import project
from app.workflow import premise_naturalness as natural
from app.workflow.premise_admission_evidence import object_support
from app.workflow.semantic_two_stage_v1 import gate_seed

ROOT=Path(__file__).resolve().parents[3]
DOCS=ROOT/'intelligence/docs'

FIXTURES = json.loads(Path(__file__).with_name("fixtures").joinpath("opening_evaluator_calibration_v1.json").read_text())["fixtures"]


def evaluate(row, source_kind="MANUAL"):
    beats=row.get("beats",[])
    fields = dict(
        everydayGoal=row["goal"], primaryObject=row["object"], normalExpectation=row["normal"],
        impossibleRule=row["rule"], visibleTrigger=row["trigger"], frameZeroDescription=row["frame"],
        finalPayoff="", loopPotential="", whyThisObject=row["why"],
        goalRuleRelationship=row["relation"], beats=beats,
    )
    candidate = dict(candidateId=row["id"], protagonist="Mimi", everydayGoal=row["goal"],
        primaryObject=row["object"], impossibleRule=row["rule"], frameZeroDescription=row["frame"],
        normalExpectation=row["normal"], whyThisObject=row["why"])
    normalized, projection = project(fields, candidate)
    timing=[dict(startSeconds=0,endSeconds=1,description=(row['frame']+' ' if i==0 else '')+'Mimi '+b['strategy']+'. '+b['visibleConsequence']+' '+b['newInformation']) for i,b in enumerate(beats)]
    carrier="\n".join(f"{i}-{i+1}s: {t['description']}" for i,t in enumerate(timing))
    structured = dict(projection=projection.model_dump(), semanticFields=normalized, protagonist="Mimi", timing=timing)
    canonical = from_structured(carrier, structured, source_kind=source_kind)
    result = natural.assess(candidate, canonical_creative_evidence=canonical, generalized_premise_evidence=True)
    return result, canonical


def test_hand_authored_strong_openings_reach_existing_floor_and_near_maximum():
    assert evaluate(FIXTURES[3])[0]["instantCausalLegibility"] >= 60
    assert evaluate(FIXTURES[4])[0]["instantCausalLegibility"] >= 80


def test_weak_openings_stay_below_floor_and_active_problem_is_required():
    for row in FIXTURES[:3]:
        result, _ = evaluate(row)
        assert result["instantCausalLegibility"] < 60
    assert not evaluate(FIXTURES[0])[0]["openingEvidence"]["anomalyVisible"]
    assert evaluate(FIXTURES[1])[0]["openingEvidence"]["anomalyVisible"]
    # `problemVisible` is currently only nonempty-frame presence, not a quality judgment.
    assert evaluate(FIXTURES[0])[0]["openingEvidence"]["problemVisible"]
    assert not evaluate(FIXTURES[2])[0]["openingEvidence"]["stillCausalLegibility"] == "SUPPORTED"


def test_direct_manual_canonical_and_semantic_structured_projection_have_exact_parity():
    for row in FIXTURES:
        direct, direct_context = evaluate(row, "MANUAL")
        structured, structured_context = evaluate(row, "SEMANTIC")
        assert direct["instantCausalLegibility"] == structured["instantCausalLegibility"]
        assert direct["openingEvidence"] == structured["openingEvidence"]
        assert direct_context.facts == structured_context.facts


def test_unclassified_rule_is_present_and_not_rewritten_as_missing():
    result, context = evaluate(FIXTURES[5])
    assert context.facts["rule"]["present"]
    assert context.facts["rule"]["classificationStatus"] == "PRESENT_UNCLASSIFIED"
    assert result["responseEvidence"]["state"] == "RESPONSE_PRESENT_UNCLASSIFIED"
    assert result["openingEvidence"]["problemVisible"]
    assert result["instantCausalLegibility"] >= 60


def test_motion_and_prior_context_language_are_not_supported_still_evidence():
    base = dict(FIXTURES[4])
    for marker, key in (("after two seconds", "motion"), ("as before", "context")):
        altered = dict(base)
        altered["id"] += "-" + key
        altered["frame"] += " " + marker
        result, _ = evaluate(altered)
        assert result["openingEvidence"]["stillCausalLegibility"] != "SUPPORTED"
        if key == "motion":
            assert result["openingEvidence"]["needsMotionToUnderstand"] is True
        else:
            assert result["openingEvidence"]["needsPriorContext"] is True


def test_exact_score_explanation_for_known_projection_plateau():
    result, _ = evaluate(FIXTURES[3])
    opening = result["openingEvidence"]
    assert result["instantCausalLegibility"] == 90
    assert opening["sourceFunctionalContrastSupported"]
    assert opening["stillPropertyContrast"] == [{"expected": ["blue"], "shown": ["orange"]}]


def test_unclassified_strong_novel_mechanic_gets_evidence_fallback_and_receipt():
    result, _ = evaluate(FIXTURES[5])
    opening=result['openingEvidence']; fallback=opening['evidenceSupportedUnclassifiedFallback']
    assert result['responseEvidence']['state']=='RESPONSE_PRESENT_UNCLASSIFIED'
    assert result['instantCausalLegibility']>=60
    assert opening['stillCausalLegibility']=='SUPPORTED'
    assert fallback['version']=='OPENING_EVIDENCE_SUPPORTED_COVERAGE_V1'
    assert fallback['used'] and not fallback['missingConditions']
    assert fallback['evidence']['laterStoryEvidence']['used'] is False
    for dimension in ('goal','interaction','abnormalState','interference','causalRelationship','ruleOpeningAgreement'):
        assert fallback['evidence'][dimension]['references']


def test_unclassified_ambiguous_motion_goal_missing_and_conflict_stay_weak():
    cases=[]
    ambiguous=dict(FIXTURES[5],id='UNKNOWN-AMBIGUOUS',rule='Maybe the map crease could perhaps become a tower.',trigger='Mimi presses the map at its central crease.')
    cases.append((ambiguous,'ambiguous'))
    motion=dict(FIXTURES[5],id='UNKNOWN-MOTION',frame=FIXTURES[5]['frame']+' After two seconds, the tower appears.')
    cases.append((motion,'motion'))
    no_goal=dict(FIXTURES[5],id='UNKNOWN-NO-GOAL',goal='')
    cases.append((no_goal,'goal'))
    conflict=dict(FIXTURES[5],id='UNKNOWN-CONFLICT',frame=FIXTURES[5]['frame']+' The crease does not form a tower and stays flat.')
    cases.append((conflict,'conflict'))
    for row,_ in cases:
        result,_=evaluate(row); opening=result['openingEvidence']; fallback=opening['evidenceSupportedUnclassifiedFallback']
        assert result['instantCausalLegibility']<60
        assert not fallback['used']
    assert 'ambiguous' in evaluate(ambiguous)[0]['openingEvidence']['evidenceSupportedUnclassifiedFallback']['missingConditions'] or evaluate(ambiguous)[0]['responseEvidence']['state']=='RESPONSE_AMBIGUOUS'
    assert 'temporallyIndependent' in evaluate(motion)[0]['openingEvidence']['evidenceSupportedUnclassifiedFallback']['missingConditions']
    assert 'goalInterferenceVisible' in evaluate(no_goal)[0]['openingEvidence']['evidenceSupportedUnclassifiedFallback']['missingConditions']
    assert evaluate(conflict)[0]['openingEvidence']['evidenceSupportedUnclassifiedFallback']['evidence']['ruleOpeningAgreement']['status']=='CONTRADICTED'


def test_punctuated_object_label_head_preserves_explicit_unclassified_opening_evidence():
    label='An open-topped watering can with a plain spout.'
    frame=('Kiko holds an open-topped watering can at a pouring angle. '
           'The plain spout points down above dry soil while a stream curls back into the can.')
    assert object_support(label,frame)['present'] is True

    run=DOCS/'net-new-generation-v1/runs/net-new-v1-20261102-v2-e0a93c0f3e56612cd051b434f001dd9b'
    seed=json.loads((run/'phase-a/seed.json').read_text())
    request=json.loads((run/'phase-a/last-mile-sdk-request.json').read_text())
    cast=json.loads(request['messages'][1]['content'])['canonicalCast']
    record=json.loads((run/'candidate-creation-record.json').read_text())
    identity=record['candidate']['candidateId']
    gate=gate_seed(seed,cast,identity)
    opening=gate['Naturalness']['openingEvidence']
    fallback=opening['evidenceSupportedUnclassifiedFallback']
    assert gate['openingScore']==90
    assert gate['acceptedFloor']==60
    assert gate['acceptedForExpansion']
    assert opening['objectEvidence']['present'] is True
    assert opening['stillCausalLegibility']=='SUPPORTED'
    assert fallback['used'] and not fallback['missingConditions']


def test_unclassified_weak_openings_remain_below_floor_after_object_token_fix():
    for row in FIXTURES[:3]:
        result,_=evaluate(row)
        assert result['instantCausalLegibility']<60


def test_later_beat_only_anomaly_does_not_support_frame_zero_fallback():
    row=dict(FIXTURES[5],id='UNKNOWN-LATER-ONLY',frame='Mimi holds a flat paper map open on the table, with her hands beside it.',
        beats=[dict(strategy='Mimi presses the map crease.',visibleConsequence='The crease extrudes into a rigid spiral tower that lifts the sheet.',newInformation='The paper remains unfolded.')])
    result,_=evaluate(row); opening=result['openingEvidence'];fallback=opening['evidenceSupportedUnclassifiedFallback']
    assert not fallback['used']
    assert fallback['evidence']['laterStoryEvidence']['used'] is False
    assert fallback['conditions']['frameZeroOnly'] is True
    assert result['instantCausalLegibility']<60


def test_known_classified_paths_do_not_use_unclassified_fallback():
    compatible=dict(id='KNOWN-LID-INVERT',goal='Close the lid over the jar.',object='lid',normal='A lid covers the jar opening and keeps it closed.',
        rule='When pressed, the lid flips upside down instead of covering the opening.',trigger='Mimi presses the lid against the jar opening.',
        why='The lid closes this jar.',relation='Mimi needs the jar closed, but the flipped lid leaves the opening uncovered.',
        frame='Mimi is flipping a lid against the jar opening. The lid is upside down and the jar opening remains visibly open.')
    result,context=evaluate(compatible);fallback=result['openingEvidence']['evidenceSupportedUnclassifiedFallback']
    assert result['responseEvidence']['state']=='RESPONSE_PRESENT_CLASSIFIED'
    assert not fallback['used']
    assert result['instantCausalLegibility']==90
    baseline=natural.assess({'candidateId':compatible['id'],'protagonist':'Mimi','everydayGoal':compatible['goal'],
        'primaryObject':compatible['object'],'impossibleRule':compatible['rule'],'frameZeroDescription':compatible['frame'],
        'normalExpectation':compatible['normal'],'whyThisObject':compatible['why']},canonical_creative_evidence=context)
    assert result['instantCausalLegibility']==baseline['instantCausalLegibility']

    incompatible=dict(compatible,id='KNOWN-LID-FLOAT',rule='When pressed, the lid floats several inches away from the jar.',
        frame='Mimi reaches toward the lid, which floats several inches above the open jar.')
    result,context=evaluate(incompatible);fallback=result['openingEvidence']['evidenceSupportedUnclassifiedFallback']
    assert result['responseEvidence']['state']=='RESPONSE_PRESENT_INCOMPATIBLE'
    assert not fallback['used']
    baseline=natural.assess({'candidateId':incompatible['id'],'protagonist':'Mimi','everydayGoal':incompatible['goal'],
        'primaryObject':incompatible['object'],'impossibleRule':incompatible['rule'],'frameZeroDescription':incompatible['frame'],
        'normalExpectation':incompatible['normal'],'whyThisObject':incompatible['why']},canonical_creative_evidence=context)
    assert result['instantCausalLegibility']==baseline['instantCausalLegibility']


def test_rule_and_opening_conflict_is_not_repaired_by_overlap_only():
    row=dict(FIXTURES[5],id='UNKNOWN-RELATION-CONFLICT',
        frame='Mimi presses both palms on a paper map and tries to fold it into a neat rectangle. The crease does not form a tower and remains flat; the corners stay unfolded.')
    result,_=evaluate(row); fallback=result['openingEvidence']['evidenceSupportedUnclassifiedFallback']
    assert not fallback['used']
    assert fallback['evidence']['ruleOpeningAgreement']['status']=='CONTRADICTED'


def test_novel_material_property_contradiction_uses_the_same_unclassified_fallback():
    row=dict(FIXTURES[5],id='UNKNOWN-MATERIAL',
        rule='When Mimi presses the paper map, it becomes a rigid glass sheet that cannot fold.',
        trigger='Mimi presses the paper map with both palms.',
        relation='Mimi is folding the paper map into a neat rectangle, but pressing makes it a rigid glass sheet that cannot fold.',
        frame='Mimi presses both palms on a paper map while folding it into a neat rectangle. The map has become a rigid glass sheet under her hands and cannot fold; the stiff corners stand above the table.')
    result,_=evaluate(row); fallback=result['openingEvidence']['evidenceSupportedUnclassifiedFallback']
    assert result['responseEvidence']['state']=='RESPONSE_PRESENT_UNCLASSIFIED'
    assert fallback['used'] and result['instantCausalLegibility']>=60


def test_reaction_only_and_goal_unrelated_anomaly_do_not_receive_fallback_credit():
    reaction=dict(FIXTURES[5],id='UNKNOWN-REACTION-ONLY',
        frame='Mimi watches a paper map on the table. A rigid spiral tower rises from the map crease; Mimi looks startled.')
    unrelated=dict(FIXTURES[5],id='UNKNOWN-UNRELATED',
        relation='Mimi wants to eat breakfast, while an unrelated spiral tower appears on a wall.')
    for row in (reaction,unrelated):
        result,_=evaluate(row);fallback=result['openingEvidence']['evidenceSupportedUnclassifiedFallback']
        assert not fallback['used'] and result['instantCausalLegibility']<60
    assert 'interactionVisible' in evaluate(reaction)[0]['openingEvidence']['evidenceSupportedUnclassifiedFallback']['missingConditions']
    assert 'goalInterferenceVisible' in evaluate(unrelated)[0]['openingEvidence']['evidenceSupportedUnclassifiedFallback']['missingConditions']


def replay_stored_eight():
    """Deterministically replay the five stored full candidates and three saved seeds."""
    from app.workflow.semantic_concept_prompt_v2_compact import CompactPromptRequest
    from app.workflow.semantic_concept_prompt_v2_compact_1 import Compact1PromptRequest
    from app.workflow.semantic_concept_prompt_v2_compact_2 import Compact2PromptRequest
    from app.workflow.semantic_prompt_v2_experiment import analyze
    from app.workflow.semantic_two_stage_v1 import gate_seed
    specs=[('REFERENCE-0','semantic-low-reasoning-full-contract-probe-1-run-001','compact','seed42-01'),
        ('micro-b','semantic-compact-micro-batch-v1-run-001/micro-b','compact','micro-b'),
        ('micro-c','semantic-compact-micro-batch-v1-run-001/micro-c','compact','micro-c'),
        ('compact.1','semantic-compact-1-low-probe-1-run-001','compact1','paper-walls-01'),
        ('compact.2','semantic-compact-2-low-probe-1-run-001','compact2','seed42-01')]
    classes={'compact':CompactPromptRequest,'compact1':Compact1PromptRequest,'compact2':Compact2PromptRequest}
    results=[]
    for case,path,kind,wanted in specs:
        folder=DOCS/path; config=classes[kind].model_validate(json.loads((folder/'configuration.json').read_text()))
        prompt=json.loads((folder/'prompt.json').read_text()); raw=(folder/'response.txt').read_text()
        replay=analyze(raw,config,prompt)
        source=next(row for row in replay['allRawIdeas'] if row['record'])
        record=source['record']; opening=record['candidate']['premiseNaturalness']['openingEvidence']
        if case.startswith('micro'):
            summary=json.loads((DOCS/'semantic-compact-micro-batch-v1-run-001/combined-analysis.json').read_text())
            old=next(row for row in summary['candidates'] if row['id']==case)['record']
        else:
            old_pipeline=json.loads((folder/'pipeline.json').read_text())
            old=next(row for row in old_pipeline['allRawIdeas'] if row['ideaId']==wanted)['record']
        results.append(dict(caseId=case,title=record['candidate']['title'],oldOpeningScore=old['observation']['openingScore'],
            newOpeningScore=record['observation']['openingScore'],
            oldStillCausalLegibility=old['candidate']['premiseNaturalness']['openingEvidence']['stillCausalLegibility'],
            newStillCausalLegibility=opening['stillCausalLegibility'],
            fallbackUsed=opening['evidenceSupportedUnclassifiedFallback']['used'],
            fallback=opening['evidenceSupportedUnclassifiedFallback'],oldAdmission=old['admission']['status'],
            newAdmission=record['admission']['status'],newAdmissionPassed=record['admission']['admitted'],
            oldRankingEligibility=old['validation']['eligibility'],newRankingEligibility=record['validation']['eligibility'],
            newRankingScore=record['validation']['rankingScore'],newProductionBlockers=record['productionBlockers'],
            newProductionAdmissible=record['productionAdmissible'],newProductionSlateRank=record['productionSlateRank'],
            providerCallsDuringAnalysis=replay['providerCallsDuringAnalysis'],renders=replay['renders']))
    seeds=[]; cast=[{'name':'Mimi','id':'mimi'}]
    for slot in 'abc':
        folder=DOCS/f'semantic-two-stage-v1-run-001/opening-{slot}'
        seed=json.loads((folder/'seed.json').read_text()); old=json.loads((folder/'gate.json').read_text())
        current=gate_seed(seed,cast,f'offline-opening-coverage-replay/{slot}')
        opening=current['Naturalness']['openingEvidence']
        seeds.append(dict(seed=seed['seedId'],oldOpeningScore=old['openingScore'],newOpeningScore=current['openingScore'],
            oldStillCausalLegibility=old['Naturalness']['openingEvidence']['stillCausalLegibility'],
            newStillCausalLegibility=opening['stillCausalLegibility'],fallbackUsed=opening['evidenceSupportedUnclassifiedFallback']['used'],
            acceptedForExpansion=current['acceptedForExpansion'],remainingBlockers=current['blockers'],
            evidence=opening['evidenceSupportedUnclassifiedFallback']))
    return dict(architecture='OPENING_EVIDENCE_SUPPORTED_COVERAGE_V1',providerCalls=0,renders=0,
        historicalCandidates=results,phaseASeeds=seeds)


def test_all_eight_stored_candidates_and_three_seeds_replay_offline():
    replay=replay_stored_eight()
    assert len(replay['historicalCandidates'])==5 and len(replay['phaseASeeds'])==3
    assert replay['providerCalls']==0 and replay['renders']==0
    assert all(row['oldOpeningScore']==35 for row in replay['historicalCandidates'])
    assert all(row['oldOpeningScore']==35 for row in replay['phaseASeeds'])
    assert all(row['providerCallsDuringAnalysis']==0 and row['renders']==0 for row in replay['historicalCandidates'])
