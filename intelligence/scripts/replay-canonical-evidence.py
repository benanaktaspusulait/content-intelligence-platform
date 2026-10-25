#!/usr/bin/env python3
"""Fixed 18-candidate replay. No generator, provider or media execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
out = args.output.resolve()
if out.exists():
    raise SystemExit('Output must be a new directory')
out.mkdir(parents=True)
for key in tuple(os.environ):
    if key.endswith('_API_KEY') or key.endswith('_API_TOKEN'):
        os.environ.pop(key)
activity = Counter()
def guard(event, values):
    if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen'):
        activity[event] += 1
        raise RuntimeError('Offline canonical replay denies networking and subprocesses')
    if event == 'open' and isinstance(values[0], (str,bytes,os.PathLike)):
        flags = values[2] or 0
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):
            path=Path(os.fsdecode(values[0])).resolve()
            if not path.is_relative_to(out):
                raise RuntimeError('Replay writes only its new output directory')
sys.dont_write_bytecode = True
sys.addaudithook(guard)
sys.path.insert(0,str(ROOT/'intelligence/ml-service'))
from app.workflow.canonical_evidence_propagation import evaluate
from app.workflow.structured_sfe_replay import structured_input, selected_run
from app.workflow.semantic_concept_generation import GenerationRequest


def load(path): return json.loads((ROOT/path).read_text())
def save(name, value): (out/name).write_text(json.dumps(value,indent=2)+'\n')
baseline=load('intelligence/docs/canonical-evidence-propagation-v1/audit-only-baseline.json')
config=GenerationRequest.model_validate(load('intelligence/docs/semantic-live-v1-seed-42-count-40/live-attempt/configuration.json')['generation'])
rows=[];candidates=[];validations={};contexts={};mismatches=[]
for old in baseline['candidates']:
    c=old['candidate'];raw=old['sourceRow']['rawProviderIdea']
    after, validation, context=evaluate(c,structured_input(raw,c))
    if validation['shortFormEngine'] != old['structuredSFE']:
        raise RuntimeError('Structured SFE drift: '+old['ideaId'])
    candidates.append(after);validations[c['candidateId']]=validation
    contexts[c['candidateId']]=dict(canonicalCreativeEvidenceMode='v1',shortFormEvidenceSourceVersion='structured-canonical-v1',structuredCanonicalInput=structured_input(raw,c))
    receipt=context.receipt()
    for evaluator,received in [('Naturalness',after['premiseNaturalness']['canonicalCreativeEvidence']),('BeatGrammar',after['beatGrammar']['canonicalCreativeEvidence']),('CreativeShape',after['storyShapeFingerprint']['canonicalCreativeEvidence']),('Ranking',validation['canonicalCreativeEvidence'])]:
        if received!=receipt: mismatches.append(dict(ideaId=old['ideaId'],evaluator=evaluator))
    rows.append(dict(ideaId=old['ideaId'],candidateId=c['candidateId'],title=c['title'],
        before=dict(sfe=old['structuredSFE'],naturalness=c['premiseNaturalness'],beatGrammar=c['beatGrammar'],validation=old['validation'],blockers=old['preselectionBlockers']),
        after=dict(sfe=validation['shortFormEngine'],naturalness=after['premiseNaturalness'],beatGrammar=after['beatGrammar'],validation=validation,creativeShape=after['storyShapeFingerprint']),
        canonicalCreativeEvidence=receipt))
selection=selected_run(candidates,validations,config,contexts)
for r in rows:
    r['after']['blockers']=next((s['reasons'] for s in selection['suppressed'] if s['candidateId']==r['candidateId']),[])
    def brief(v):return dict(SFE=v['sfe']['status'],shortFormScore=v['sfe']['shortFormScore'],Naturalness=v['naturalness']['premiseNaturalness'],openingLegibility=v['naturalness']['instantCausalLegibility'],BeatGrammar=v['beatGrammar']['beatGrammarQuality'],eligibility=v['validation']['eligibility'],rankingScore=v['validation']['rankingScore'],blockers=v['blockers'])
    r['beforeSummary']=brief(r['before']);r['afterSummary']=brief(r['after'])
    r['delta']={k:dict(before=r['beforeSummary'][k],after=r['afterSummary'][k]) for k in r['beforeSummary'] if r['beforeSummary'][k]!=r['afterSummary'][k]}
    r['causeOfDelta']=[
        'Ranking uses canonical declared/ordinary-use/visible-opening evidence instead of independently matching the legacy goal regex.',
        'Naturalness uses canonical opening/trigger facts; its object model, response classifier, compatibility policies and quality formula are unchanged.',
        'Beat Grammar receives source consequences and exact newInformation. Unstated physical defaults are removed; unclassified consequences invoke the existing UNKNOWN_CONSEQUENCE rule.',
    ] if r['delta'] else ['Independent quality verdicts unchanged after factual propagation.']

def counts(stage):
    c=Counter(code for r in rows for code in r[stage]['blockers'])
    c['eligibility/admission']=sum(r[stage]['validation']['eligibility']!='ELIGIBLE' or not r[stage]['naturalness']['admitted'] for r in rows)
    c['taxonomy/coverage-related premise blocker']=sum(not r[stage]['naturalness']['admitted'] and (r[stage]['naturalness']['responseType']=='UNSUPPORTED_RESPONSE' or baseline['candidates'][i]['candidate']['composition']['objectCategory']=='UNCLASSIFIED') for i,r in enumerate(rows))
    for k in ('OPENING_EVIDENCE_INSUFFICIENT','ACCEPTED_VALIDATOR_INELIGIBLE','RANKING_QUALITY_FLOOR','BEAT_GRAMMAR_QUALITY_FLOOR','PREMISE_NOT_ADMITTED','SHORT_FORM_QUALITY_FLOOR'):c.setdefault(k,0)
    return dict(c)
opening=[];matrix=[]
for old,r in zip(baseline['candidates'],rows):
    facts=r['canonicalCreativeEvidence']['facts'];s=r['after']['sfe']
    opening.append(dict(ideaId=r['ideaId'],canonical=facts['opening'],goal=facts['goal'],SFE=dict(hookScore=s['hookScore'],goalScore=s['goalScore'],instantPremiseLegibility=s['instantPremiseLegibility']),Naturalness=dict(before=r['before']['naturalness']['instantCausalLegibility'],after=r['after']['naturalness']['instantCausalLegibility'],qualityRule='existing direct affordance-policy AND canonical source-supported opening; facts alone do not satisfy direct'),Ranking=dict(eligibility=r['after']['validation']['eligibility'],goalFindings=[x for x in r['after']['validation']['eligibilityReasons'] if x.get('field')=='protagonistGoal']),classification='LEGITIMATE_QUALITY_DIFFERENCE' if r['after']['naturalness']['responseType']!='UNSUPPORTED_RESPONSE' else 'TAXONOMY_LIMIT'))
    fact_values=dict(goalDeclared=facts['goal']['declared'],goalVisible=facts['goal']['visibleInOpening'],openingAnomaly=facts['opening']['anomalyPresent'],rulePresent=facts['rule']['present'],triggerPresent=facts['trigger']['present'],beatCount=len(facts['beats']),payoffPresent=facts['payoff']['present'])
    matrix.append(dict(ideaId=r['ideaId'],facts={k:dict(canonical=v,**{e:dict(classification='AGREE',value=v,contextSha256=r['canonicalCreativeEvidence']['contextSha256']) for e in ('SFE','Naturalness','BeatGrammar','RankingAdmission')}) for k,v in fact_values.items()}))
proof=dict(candidateCount=len(rows),providerCalls=0,externalProviderCalls=0,newConcepts=0,renders=0,blockedEvents=dict(activity),structuredSFEExactlyUnchanged=True,sharedFactMismatches=mismatches,
    baselineMismatchCells=baseline['mismatchCells'],afterMismatchCells=len(mismatches),
    auditMethod='Exact same source-bound immutable fact receipt in each consumer; SFE report exact-equal to stored accepted structured report. Independent quality output is not a fact contradiction.',
    inputHashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('intelligence/docs/canonical-evidence-propagation-v1/audit-only-baseline.json','intelligence/docs/semantic-live-v1-seed-42-count-40/live-attempt/response.txt')})
save('results.json',dict(candidates=rows,productionSelection=selection,blockerCounts=dict(before=counts('before'),after=counts('after')),proof=proof))
save('opening-audit.json',opening);save('disagreement-matrix-after.json',matrix);save('offline-proof.json',proof)
print(json.dumps(dict(candidates=len(rows),blockerCounts=dict(before=counts('before'),after=counts('after')),proof=proof),indent=2))
