#!/usr/bin/env python3
"""Fixed18 source-bound premise/opening replay; no generation/provider/media API."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib,json,os
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
    if event in {'socket.connect','socket.getaddrinfo','subprocess.Popen'}:activity[event]+=1;raise RuntimeError('Offline premise replay denies networking and subprocesses')
    if event=='open' and isinstance(values[0],(str,bytes,os.PathLike)) and (values[2] or 0)&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):
        if not Path(os.fsdecode(values[0])).resolve().is_relative_to(out):raise RuntimeError('Writes restricted to fresh output')
sys.dont_write_bytecode=True;sys.addaudithook(guard);sys.path.insert(0,str(ROOT/'intelligence/ml-service'))
from app.workflow import premise_naturalness,beat_grammar
from app.workflow.canonical_evidence_propagation import evaluate
from app.workflow.structured_sfe_replay import structured_input,selected_run
from app.workflow.semantic_concept_generation import GenerationRequest

def load(p):return json.loads((ROOT/p).read_text())
def save(n,v):(out/n).write_text(json.dumps(v,indent=2)+'\n')
before=load('intelligence/docs/premise-admission-opening-generalization-v1/audit-before-modification.json')
shape={r['ideaId']:r['after']['creativeShape'] for r in load('intelligence/docs/canonical-evidence-propagation-v1/verified-replay/results.json')['candidates']}
cfg=GenerationRequest.model_validate(load('intelligence/docs/semantic-live-v1-seed-42-count-40/live-attempt/configuration.json')['generation'])
rows=[];candidates=[];validation={};contexts={};coverage={k:Counter() for k in ['response','contradiction','goalInterference']}
for old in before['candidates']:
    c=old['candidate'];s=structured_input(old['raw'],c);after,v,ctx=evaluate(c,s)
    assert v==old['validation'],old['ideaId']+' ranking/SFE changed'
    assert after['premiseNaturalness']==old['naturalness'],old['ideaId']+' default canonical Naturalness drift'
    assert after['storyShapeFingerprint']==shape[old['ideaId']],old['ideaId']+' Creative Shape changed'
    bg=beat_grammar.assess(c['structuredBeatPlan'],canonical_creative_evidence=ctx,unclassified_consequence_support=True)
    assert bg==old['beatGrammar'],old['ideaId']+' Beat Grammar changed'
    report=premise_naturalness.assess(c,canonical_creative_evidence=ctx,generalized_premise_evidence=True)
    after['premiseNaturalness']=report;after['beatGrammar']=bg
    def summary(n):return dict(openingScore=n['instantCausalLegibility'],staticScore=n['staticFrameLegibility'],naturalness=n['premiseNaturalness'],admitted=n['admitted'],response=n['responseType'],goalInterference=n['goalInterferenceType'],findings=n['flags'])
    a,b=summary(old['naturalness']),summary(report)
    quality=report['qualityEvidence'];response=report['responseEvidence']
    state='missing' if response['state']=='RESPONSE_MISSING' else 'present-unclassified' if response['classification'] is None else 'classified'
    coverage['response'][state]+=1
    coverage['contradiction']['missing' if not quality['expectedBehaviorContradiction']['present'] else 'classified' if quality['expectedBehaviorContradiction']['classification'] else 'present-unclassified']+=1
    coverage['goalInterference']['missing' if not quality['goalInterference']['present'] else 'classified' if quality['goalInterference']['classification'] else 'present-unclassified']+=1
    rows.append(dict(ideaId=old['ideaId'],candidateId=c['candidateId'],title=c['title'],raw=old['raw'],before=a,after=b,
        beforeReport=old['naturalness'],afterReport=report,openingAudit=report['openingEvidence'],
        delta={k:dict(before=a[k],after=b[k]) for k in a if a[k]!=b[k]},
        cause='Explicit response and linked goal interference remain available without response class. Unknown compatibility/counterfactual quality is unresolved rather than absent; still-frame property witnesses are evaluated independently of taxonomy.',
        beforePreselectionBlockers=old['blockers'],validation=v,beatGrammar=bg))
    candidates.append(after);validation[c['candidateId']]=v;contexts[c['candidateId']]=dict(canonicalCreativeEvidenceMode='v1',shortFormEvidenceSourceVersion='structured-canonical-v1',structuredCanonicalInput=s)
selection=selected_run(candidates,validation,cfg,contexts)
for r in rows:r['afterPreselectionBlockers']=next((x['reasons'] for x in selection['suppressed'] if x['candidateId']==r['candidateId']),[])
for c in coverage.values():
    for s in ['classified','present-unclassified','missing']:c.setdefault(s,0)
proof=dict(candidateCount=len(rows),providerCalls=0,newConcepts=0,renders=0,attemptedNetworkOrSubprocess=dict(activity),
    SFEExactlyUnchanged=True,fullRankingExactlyUnchanged=True,BeatGrammarExactlyUnchanged=True,CreativeShapeExactlyUnchanged=True,defaultCanonicalNaturalnessExactlyUnchanged=True,
    admittedCandidateCount=sum(r['after']['admitted'] for r in rows),productionAdmissibleCount=sum(not r['afterPreselectionBlockers'] for r in rows),
    productionSlateCount=len(selection['productionSelection']['productionSlate']),productionSlate=selection['productionSelection']['productionSlate'],
    newProductionCandidates=[],openingBlockerCounts=dict(Counter(r['openingAudit']['blockerClassification'] for r in rows if 'OPENING_EVIDENCE_INSUFFICIENT' in r['afterPreselectionBlockers'])))
save('results.json',dict(candidates=rows,taxonomyCoverage={k:dict(v) for k,v in coverage.items()},preselection=selection,proof=proof));save('offline-proof.json',proof)
save('opening-audit.json',[dict(ideaId=r['ideaId'],candidateId=r['candidateId'],**r['openingAudit'],beforeScore=r['before']['openingScore'],afterScore=r['after']['openingScore']) for r in rows])
save('taxonomy-coverage.json',{k:dict(v) for k,v in coverage.items()})
for id in ['raw-013','raw-007','raw-026','raw-027']:save(id+'-audit.json',next(r for r in rows if r['ideaId']==id))
print(json.dumps(dict(proof=proof,coverage={k:dict(v) for k,v in coverage.items()}),indent=2))
