#!/usr/bin/env python3
"""Offline report of stored micro-batch evidence; no provider imports or calls."""
from collections import Counter
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DOCS=ROOT/'intelligence/docs'; OUT=DOCS/'semantic-compact-micro-batch-v1'; RUN=DOCS/'semantic-compact-micro-batch-v1-run-001'


def main():
    data=json.loads((RUN/'combined-analysis.json').read_text())
    j=lambda x:json.dumps(x,indent=2,ensure_ascii=False)
    lines=['SEMANTIC V2 COMPACT — REAL CREATIVE MICRO-BATCH','',
           'Execution profile and request-cap proof',j(json.loads((RUN/'plan.json').read_text())),
           j(json.loads((RUN/'execution-proof.json').read_text()))]
    for identity in ('micro-a','micro-b','micro-c'):
        lines += ['',identity+' execution result',j(json.loads((RUN/f'{identity}-result.json').read_text()))]
    lines += ['', 'Combined metrics',j({k:v for k,v in data.items() if k!='candidates'}),
              'Opening signal rule is descriptive: at most 1/4 at the existing floor signals weakness; at least 3/4 is encouraging; 2/4 is unclear. This is no new scoring/admission gate and no statistical proof.',
              'Source-only audits: no generated or rendered frames. Unknown values remain UNRESOLVED. Provider rationale/self-assessment is not evidence.']
    for row in data['candidates']:
        r=row['record']; raw=row['raw']; c=r['candidate']; v=r['validation']; o=r['observation']; a=r['admission']; e=row['creativeEvidence']
        opening=c['premiseNaturalness']['openingEvidence']
        lines += ['', '='*70,row['id']+' / '+raw['title'],
                  'GLOBALLY UNIQUE ID: '+row['candidateId'],
                  'Accepted pipeline ID: '+r['candidateId'],'Provider-local ID: '+raw['ideaId'],
                  'COMPLETE STORY (stored source; no repair)',j(raw),
                  'DEDICATED OPENING AUDIT',j(dict(
                      FRAME_ZERO_DESCRIPTION=raw['frameZeroDescription'],
                      CHARACTER_VISIBLE=opening['characterVisible'], GOAL_VISIBLE=opening['goalVisible'],
                      OBJECT_VISIBLE=opening['objectVisible'], PROBLEM_VISIBLE=opening['problemVisible'],
                      IMPOSSIBLE_RELATIONSHIP_VISIBLE=opening['impossibleRelationVisible'],
                      CAUSE_PROBLEM_RELATIONSHIP_UNDERSTANDABLE=opening['stillCausalLegibility'],
                      GOAL_PROBLEM_RELATIONSHIP=opening['goalProblemRelationship'],
                      REQUIRES_MOTION=opening['needsMotionToUnderstand'], REQUIRES_PRIOR_CONTEXT=opening['needsPriorContext'],
                      OPENING_SCORE=o['openingScore'], ACCEPTED_PRODUCTION_FLOOR=data['opening']['acceptedFloor'],
                      exactObjectContradiction=opening['sourceFunctionalContrastSupported'],
                      blocker=opening['blockerClassification'],reason=opening['blockerReason'],nullMeaning='UNRESOLVED')),
                  'PRE-SCORING CONTRACT RECEIPT',j(json.loads((DOCS/'semantic-low-reasoning-full-contract-probe-1-run-001' if row['id']=='REFERENCE-0' else RUN/row['id']).joinpath('pre-pipeline-creative-contract.json').read_text())),
                  'CREATIVE CONTRACT RESULT: '+row['creativeContract'],
                  'EXACT RULE / PER-BEAT COMPARISON',raw['impossibleRule'],j(e),
                  'PAYOFF AUDIT',j(dict(present=bool(raw['finalPayoff']),
                      visualEvidence=o['payoffEvidence']['presence'], stateChanging=o['payoffEvidence']['stateChanging'],
                      followsSameRule=o['payoffRuleLinked'], exactTerminalSource=raw['finalPayoff'],
                      introducesNewBehavior='See manual source audit in source-audits.json; no unsupported automatic assertion.',
                      merelyRepeatsPreviousBeat=raw['finalPayoff']==raw['beats'][-2]['visibleConsequence'],
                      duplicatesFinalBeat=raw['finalPayoff']==raw['beats'][-1]['visibleConsequence'])),
                  'PIPELINE RESULTS',j(dict(schemaValidity=True,normalization='PASS',creativeContract=row['creativeContract'],
                      openingScore=o['openingScore'],PremiseNaturalness=c['premiseNaturalness'],
                      admission=a,BeatGrammar=c['beatGrammar'],SFE=v['shortFormEngine'],CreativeShape=c['templateShapeRisk'],
                      historicalTerritory=c['historicalCreativeTerritory'], rankingEligibility=v['eligibility'],
                      rankingScore=v['rankingScore'],rankingEligibilityReasons=v['eligibilityReasons'],
                      productionAdmissible=r['productionAdmissible'],productionSlateRank=r['productionSlateRank'],
                      exactProductionBlockers=r['productionBlockers'],reviewReasons=row['reviewReasons']))]
    lines+=['','MICRO_BATCH_HUMAN_REVIEW_SET',j(data['MICRO_BATCH_HUMAN_REVIEW_SET'])]
    cards=[]
    for row in data['candidates']:
        if not row['reviewReasons']:continue
        r=row['record'];raw=row['raw']
        cards.append(dict(id=row['candidateId'],title=raw['title'],
            oneSentencePremise=f"{raw['protagonistSuggestion']} tries to {raw['everydayGoal']} {raw['impossibleRule']}",
            frameZeroHook=raw['frameZeroDescription'],coreRule=raw['impossibleRule'],progression=raw['beats'],
            payoff=raw['finalPayoff'],openingScore=r['observation']['openingScore'],SFE=r['validation']['shortFormScore'],
            mainSystemConcern=r['productionBlockers'],currentStatus=r['productionDisposition']))
    lines+=['','REVIEW CARDS',j(cards)]
    (OUT/'review-cards.json').write_text(j(cards))
    (OUT/'REPORT.txt').write_text('\n'.join(lines)+'\n')
    print(j({k:v for k,v in data.items() if k!='candidates'}))


if __name__=='__main__':main()
