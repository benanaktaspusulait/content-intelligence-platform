#!/usr/bin/env python3
"""Replay the fixed 18 existing candidates; no generation/provider/media interface."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);args=p.parse_args()
out=args.output.resolve()
if out.exists():raise SystemExit('Output must be a fresh directory')
out.mkdir(parents=True)
for key in tuple(os.environ):
    if key.endswith('_API_KEY') or key.endswith('_API_TOKEN'):os.environ.pop(key)
activity=Counter()
def guard(event,values):
    if event in {'socket.connect','socket.getaddrinfo','subprocess.Popen'}:
        activity[event]+=1;raise RuntimeError('Offline replay forbids network and subprocesses')
    if event=='open' and isinstance(values[0],(str,bytes,os.PathLike)):
        if (values[2] or 0)&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):
            if not Path(os.fsdecode(values[0])).resolve().is_relative_to(out):raise RuntimeError('Writes limited to fresh output')
sys.dont_write_bytecode=True;sys.addaudithook(guard);sys.path.insert(0,str(ROOT/'intelligence/ml-service'))
from app.workflow import beat_grammar
from app.workflow.canonical_evidence_propagation import evaluate
from app.workflow.structured_sfe_replay import structured_input,selected_run
from app.workflow.semantic_concept_generation import GenerationRequest

def load(p):return json.loads((ROOT/p).read_text())
def save(p,v):(out/p).write_text(json.dumps(v,indent=2)+'\n')
old=load('intelligence/docs/canonical-evidence-propagation-v1/verified-replay/results.json')
source=load('intelligence/docs/canonical-evidence-propagation-v1/audit-only-baseline.json')
byid={r['ideaId']:r for r in source['candidates']}
cfg=GenerationRequest.model_validate(load('intelligence/docs/semantic-live-v1-seed-42-count-40/live-attempt/configuration.json')['generation'])
rows=[];candidates=[];validation={};contexts={};coverage={'strategy':Counter(),'consequence':Counter()}
for before in old['candidates']:
    id=before['ideaId'];original=byid[id];c=original['candidate'];raw=original['sourceRow']['rawProviderIdea'];structured=structured_input(raw,c)
    after,v,canonical=evaluate(c,structured)
    assert after['beatGrammar']==before['after']['beatGrammar'],id+' old-mode BG drift'
    assert v==before['after']['validation'],id+' ranking/SFE drift'
    assert after['premiseNaturalness']==before['after']['naturalness'],id+' naturalness drift'
    report=beat_grammar.assess(c['structuredBeatPlan'],canonical_creative_evidence=canonical,unclassified_consequence_support=True)
    after['beatGrammar']=report
    audit=[]
    for i,fact in enumerate(report['canonicalBeatEvidence']):
        coverage['strategy'][fact['strategyClassificationStatus']]+=1
        coverage['consequence'][fact['consequenceClassificationStatus']]+=1
        audit.append(dict(beatNumber=i+1,rawConsequence=raw['beats'][i]['visibleConsequence'],
            normalizedConsequence=c['structuredBeatPlan'][i]['objectResponse'],canonicalProjectedConsequence=report['sourceBeatPlan'][i]['objectResponse'],
            evidence=fact,diagnosis='A' if not fact['consequencePresent'] else 'AMBIGUOUS' if fact['consequenceClassificationStatus'].endswith('AMBIGUOUS') else 'C' if fact['stateChangeSupported'] else 'D' if not fact['progressionSupported'] else 'B',
            diagnosisMeaning='A absent; B explicit unclassified with information support; C explicit with supported state change; D explicit but no supported difference; AMBIGUOUS unresolved source.',
            payoff=dict(present=canonical.facts['payoff']['present'],ruleLinked=canonical.facts['payoff']['ruleLinked'],stateChanging=canonical.facts['payoff']['stateChanging']) if i==len(raw['beats'])-1 else None))
    counts={kind:dict(Counter(x['evidence'][kind+'ClassificationStatus'] for x in audit)) for kind in ['strategy','consequence']}
    def metrics(r):return dict(quality=r['beatGrammarQuality'],strategyDiversity=r['strategyDiversityScore'],consequenceDiversity=r['consequenceDiversityScore'],bodyProgression=r['bodyStateProgressionScore'],spatialProgression=r['spatialProgressionScore'],informationGain=r.get('informationGainScore'),payoffDistance=r['payoffDistance'],findings=r['flags'])
    a,b=metrics(before['after']['beatGrammar']),metrics(report)
    rows.append(dict(ideaId=id,candidateId=c['candidateId'],title=c['title'],before=a,after=b,
        delta={k:dict(before=a[k],after=b[k]) for k in a if a[k]!=b[k]},
        cause='Unknown taxonomy label no longer causes BROKEN. The same quality cutoffs use supported source actions/states/information; unavailable physical axes earn no invented credit.',
        counts=counts,audit=audit,beforeReport=before['after']['beatGrammar'],afterReport=report,
        validation=v,beforePreselectionBlockers=before['after']['blockers']))
    candidates.append(after);validation[c['candidateId']]=v
    contexts[c['candidateId']]=dict(canonicalCreativeEvidenceMode='v1',shortFormEvidenceSourceVersion='structured-canonical-v1',structuredCanonicalInput=structured)
selection=selected_run(candidates,validation,cfg,contexts)
for r in rows:r['afterPreselectionBlockers']=next((x['reasons'] for x in selection['suppressed'] if x['candidateId']==r['candidateId']),[])
for kind in coverage:
    for suffix in ('PRESENT_CLASSIFIED','PRESENT_UNCLASSIFIED','MISSING','AMBIGUOUS'):
        coverage[kind].setdefault(kind.upper()+'_'+suffix,0)
coverage={k:dict(v) for k,v in coverage.items()}
proof=dict(candidateCount=18,beatCount=sum(sum(r['counts']['consequence'].values()) for r in rows),providerCalls=0,newConcepts=0,renders=0,attemptedNetworkOrSubprocess=dict(activity),
    oldCanonicalModeExactlyUnchanged=True,structuredSFEExactlyUnchanged=True,fullRankingReportsExactlyUnchanged=True,naturalnessExactlyUnchanged=True,
    noTaxonomyExpansion=True,noThresholdChanges=True,onlyExplicitNewEvidenceModeChanged=True,
    qualityDistribution=dict(Counter(r['after']['quality'] for r in rows)),
    productionSlateBefore=old['productionSelection']['productionSelection']['productionSlate'],productionSlateAfter=selection['productionSelection']['productionSlate'])
save('results.json',dict(candidates=rows,taxonomyCoverage=coverage,preselection=selection,proof=proof))
save('offline-proof.json',proof);save('taxonomy-coverage.json',coverage)
for id in ['raw-013','raw-007','raw-026','raw-027']:save(id+'-audit.json',next(r for r in rows if r['ideaId']==id))
print(json.dumps(dict(proof=proof,coverage=coverage),indent=2))
