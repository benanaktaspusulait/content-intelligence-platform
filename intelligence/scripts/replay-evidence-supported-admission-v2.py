#!/usr/bin/env python3
"""Fixed18 admission replay; no provider, generator, prompt or media interface."""
import argparse
from collections import Counter
import hashlib,json,os
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);args=p.parse_args();out=args.output.resolve()
if out.exists():raise SystemExit('Output must be a fresh directory')
out.mkdir(parents=True)
for k in tuple(os.environ):
    if k.endswith('_API_KEY') or k.endswith('_API_TOKEN'):os.environ.pop(k)
activity=Counter()
def guard(event,values):
    if event in {'socket.connect','socket.getaddrinfo','subprocess.Popen'}:activity[event]+=1;raise RuntimeError('Offline admission replay forbids network and subprocesses')
    if event=='open' and isinstance(values[0],(str,bytes,os.PathLike)) and (values[2] or 0)&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):
        if not Path(os.fsdecode(values[0])).resolve().is_relative_to(out):raise RuntimeError('Writes limited to fresh output')
sys.dont_write_bytecode=True;sys.addaudithook(guard);sys.path.insert(0,str(ROOT/'intelligence/ml-service'))
from app.workflow import premise_naturalness,beat_grammar
from app.workflow.canonical_evidence_propagation import evaluate
from app.workflow.evidence_supported_admission_v2 import assess,project_naturalness
from app.workflow.structured_sfe_replay import structured_input,selected_run
from app.workflow.semantic_concept_generation import GenerationRequest

def load(p):return json.loads((ROOT/p).read_text())
def save(n,v):(out/n).write_text(json.dumps(v,indent=2)+'\n')
before=load('intelligence/docs/evidence-supported-premise-admission-v2/baseline.json')
source={r['ideaId']:r for r in load('intelligence/docs/premise-admission-opening-generalization-v1/audit-before-modification.json')['candidates']}
cfg=GenerationRequest.model_validate(load('intelligence/docs/semantic-live-v1-seed-42-count-40/live-attempt/configuration.json')['generation'])
rows=[];candidates=[];validation={};contexts={}
for row in before['candidates']:
    c=source[row['ideaId']]['candidate'];s=structured_input(row['raw'],c);after,v,ctx=evaluate(c,s)
    assert v==row['validation'],row['ideaId']+' ranking/SFE drift'
    bg=beat_grammar.assess(c['structuredBeatPlan'],canonical_creative_evidence=ctx,unclassified_consequence_support=True)
    assert bg==row['beatGrammar'],row['ideaId']+' BG drift'
    n=premise_naturalness.assess(c,canonical_creative_evidence=ctx,generalized_premise_evidence=True)
    def ordered_diagnostic(report):
        result=deepcopy(report)
        evidence=(result.get('openingEvidence') or {}).get('objectEvidence')
        if evidence and 'matches' in evidence:evidence['matches']=sorted(evidence['matches'])
        return result
    assert ordered_diagnostic(n)==ordered_diagnostic(row['afterReport']),row['ideaId']+' Naturalness/opening drift'
    # Existing frozen V1 builds this display-only list from a set. Ordering is
    # normalized only for audit comparison; no evaluator or score is modified.

    core=assess(c,ctx,opening_mandatory=False);combined=assess(c,ctx,opening_mandatory=True)
    projection=project_naturalness(n,core)
    assert all(projection[k]==value for k,value in n.items() if k!='admitted')
    after['premiseNaturalness']=projection;after['beatGrammar']=bg
    rows.append(dict(ideaId=row['ideaId'],candidateId=row['candidateId'],title=row['title'],raw=row['raw'],
        before=dict(admitted=n['admitted'],admissionReason=n['admissionCriteria'],openingScore=n['instantCausalLegibility'],productionBlockers=row['afterPreselectionBlockers']),
        after=dict(admitted=core.admitted,admissionStatus=core.status,admissionProvenance=core.provenance,openingScore=n['instantCausalLegibility']),
        admission=core.model_dump(),openingMandatoryAdmission=combined.model_dump(),naturalness=n,validation=v,beatGrammar=bg,
        legacyDiagnosticOrderingDifference=n!=row['afterReport'],
        why=core.reasons or [dict(code='SOURCE_FACTORS_ESTABLISHED',reason='All core function, trigger, goal and coherence factors supported; classification remains unchanged.')]))
    candidates.append(after);validation[c['candidateId']]=v;contexts[c['candidateId']]=dict(canonicalCreativeEvidenceMode='v1',shortFormEvidenceSourceVersion='structured-canonical-v1',structuredCanonicalInput=s)
selection=selected_run(candidates,validation,cfg,contexts)
for row in rows:
    row['after']['productionBlockers']=next((r['reasons'] for r in selection['suppressed'] if r['candidateId']==row['candidateId']),[])
    row['delta']={k:dict(before=row['before'][k],after=row['after'][k]) for k in ['admitted','openingScore','productionBlockers'] if row['before'][k]!=row['after'][k]}
new=[r for r in rows if r['after']['admitted'] and not r['before']['admitted']]
proof=dict(candidateCount=len(rows),providerCalls=0,newConcepts=0,renders=0,attemptedNetworkOrSubprocess=dict(activity),
    SFEExactlyUnchanged=True,BeatGrammarExactlyUnchanged=True,fullRankingExactlyUnchanged=True,NaturalnessMetricsExactlyUnchanged=True,openingScoresExactlyUnchanged=True,
    newFallbackAdmittedCandidates=[r['candidateId'] for r in new],admittedCount=sum(r['after']['admitted'] for r in rows),
    productionAdmissibleCount=sum(not r['after']['productionBlockers'] for r in rows),productionSlateBefore=before['preselection']['productionSelection']['productionSlate'],productionSlateAfter=selection['productionSelection']['productionSlate'],
    legacyDiagnosticOrderingOnly=[r['ideaId'] for r in rows if r['legacyDiagnosticOrderingDifference']],
    decisionCounts=dict(Counter(r['after']['admissionStatus'] for r in rows)))
save('results.json',dict(candidates=rows,newlyAdmitted=new,preselection=selection,proof=proof));save('offline-proof.json',proof)
for id in ['raw-026','raw-027','raw-013','raw-007']:save(id+'-audit.json',next(r for r in rows if r['ideaId']==id))
print(json.dumps(proof,indent=2))
