#!/usr/bin/env python3
"""Scenario data for P1, never a claim about real-model creativity or a requested score."""
import json
from pathlib import Path
import sys

folder=Path(sys.argv[1])
initial=json.loads((folder/'story.json').read_text())
# Story changes preserve the approved events/order/mechanism/ending and clarify their presentation.
r1=("Pip the rabbit wants to place one sticky note on the toy cabinet's empty front panel. "
    "Pip's fingertip and the cabinet stay visibly separated when the note sticks to the finger instead. "
    "Pip peels with the other hand and the note splits into two, one on each hand. "
    "Each pull doubles the sticky notes from two to four to eight, progressively covering Pip's arms and face. "
    "The mirror reveals Pip's note-covered reflection and Pip gasps. "
    "Pip remains covered until a sneeze scatters the notes onto the cabinet. "
    "Pip is relieved, but the cabinet remains messy.")
r1b=("Pip the rabbit brings a sticky note to a toy cabinet while its mirror shows the empty cabinet panel. "
     "The note catches on Pip's finger; the mirrored cabinet stays untouched. "
     "Pip peels it and the note splits between both hands. Each pull doubles the notes from two to four to eight until Pip's arms and face are covered. "
     "The same mirror now reveals Pip covered in notes, causing a gasp. Pip stays covered until sneezing the notes onto the cabinet. "
     "Pip is relieved beside the messy cabinet.")
r2sentences=[
    "Pip the rabbit wants to place one sticky note on the toy cabinet's empty front panel.",
    "Pip reaches toward that panel, but the note clings to the fingertip while a visible gap remains between hand and cabinet.",
    "Pip peels with the other hand and the note splits into two, one on each hand.",
    "Each pull doubles the sticky notes from two to four to eight; the paired hands stay apart so each changed note count is visible before the next doubling, progressively covering Pip's arms and face.",
    "Pip turns the note-covered face toward the mirror, sees the reflection and gasps while both the face and reflected notes remain visible.",
    "Pip remains covered until a sneeze scatters the notes onto the cabinet's formerly empty front panel.",
    "Pip is relieved, but the cabinet remains messy.",
]
r2=' '.join(r2sentences)
def candidate(cid,title,text): return dict(candidateId=cid,title=title,text=text)
(folder/'story.json').write_text(json.dumps({'rounds':{
    '0':initial,
    '1':{'alternatives':[candidate('round-1-contact','Contact gap and visible consequence',r1),candidate('round-1-mirror','Mirror anchors the changing physical state',r1b)]},
    '2':{'alternatives':[candidate('round-2-equivalent','Replay of retained story',r1),candidate('round-2-progression','Count states and mirror continuity',r2)]},
}},indent=2))

def review(round_number,candidates,recommended,reason):
    return dict(reviewId=f'fixture-independent-review-{round_number}',sourceRequestId=None,sourceFingerprint=None,
        reviewModel='ISOLATED_STORY_REVIEW',reviewModelVersion='fixture-v1',reviewPolicyVersion='story-evolution-v1',
        reviewTimestamp='TEST_FIXTURE_NOT_REAL_MODEL_TIME',reviewStatus='COMPLETED',
        diversityAssessment={'classification':'DISTINCT_STAGING','summary':'Different source-faithful contact or reflection presentation.'},
        comparativeFindings=[{'dimension':'CAUSAL_PROGRESSION','finding':reason,'supportingTextEvidence':[
            'The note sticks to Pip\'s finger instead.', 'Each pull doubles the sticky notes from two to four to eight.'],
            'severity':'OPPORTUNITY','confidenceOrEvidenceStatus':'MOCK_TEXT_REVIEW_NOT_VISUAL_EVIDENCE'}],
        candidateReviews=[dict(candidateId=c,overallStatus='STRONG_CANDIDATE' if c==recommended else 'NEEDS_REVISION',
            strengths=[reason] if c==recommended else [],concerns=[] if c==recommended else ['Mirror-first attention may hide initial contact'],
            materialFindings=[],suggestedMinimalImprovements=[],editorialRecommendation='RECOMMENDED' if c==recommended else 'NEEDS_REVISION',
            confidenceOrEvidenceStatus='MOCK_TEXT_ONLY') for c in candidates],
        recommendedCandidateId=recommended,recommendationReason=reason,
        overallConcerns=['No rendered visibility, independent source verdict or audience evidence exists.'],
        usageAndCost={'provider':'ISOLATED_FIXTURE','costUpperBoundUsd':0},
        evidenceLimitations=['Deterministic mocked reviewer; not independent real-model or human evidence.'],
        revisionComparison={'resolved':['Contact destination distinguished from attached finger'],
                            'remaining':['Readability at 480p needs a visual test'] if round_number==2 else ['Make distinct count states and mirror continuity explicit'],
                            'newFindings':[]})
(folder/'story_review.json').write_text(json.dumps({'rounds':{
    '1':review(1,['round-1-contact','round-1-mirror'],'round-1-contact','The cabinet gap makes the wrong-surface result explicit compared with the original destination ambiguity.'),
    '2':review(2,['round-2-progression'],'round-2-progression','The retained contact gap is preserved; separated hands expose the existing 2-to-4-to-8 states and the mirror reaction preserves coverage until the sneeze.'),
}},indent=2))

ranges=['0-2s','2-5s','5-10s','10-12s','12-15s']
actions=[' '.join(r2sentences[:2]),r2sentences[2],r2sentences[3],r2sentences[4],' '.join(r2sentences[5:])]
framings=['locked medium shot','medium shot','wide shot','medium close-up','medium shot']
staging=['Show the cabinet panel and reaching fingertip in the same view; preserve the visible gap.',
         'Both hands remain visible with one note on each hand.',
         'Keep separated hands and both changed note groups visible without cutting across a doubling.',
         'Keep the covered face and its mirror reflection readable in the same shot.',
         'Keep the previously empty panel visible as the sneezed notes land; end on the messy panel and relief.']
consequences=['The note attaches to the wrong surface.','One note remains on each hand.',
              'The doubling covers Pip\'s arms and face.','Pip gasps and stays covered.',
              'Pip is relieved beside the messy cabinet.']
lines=[f'{time}: {action} [{frame}; {stage}] -> {consequence}' for time,action,frame,stage,consequence in zip(ranges,actions,framings,staging,consequences)]
prompt=('TITLE / FORMAT\nPip sticky notes / 15 seconds\n\nVISUAL STYLE\nBright playful animation, clear silhouettes.\n\n'
        'CHARACTER / CONTINUITY\nPip is the same anthropomorphic rabbit throughout. No verified appearance reference is supplied.\n\n'
        'TIMED SHOT PLAN\n'+'\n'.join(lines)+'\n\nAUDIO\nPlayful background music, peeling sounds, a gasp and a sneeze. No dialogue.\n\n'
        'NEGATIVE CONSTRAINTS\nNo identity changes, extra pulls, new mechanics, readable lettering claims or additional story events.\n\n'
        'FINAL CUT\nEnd with the relieved Pip beside the visibly messy cabinet.\n\n'
        'PRODUCTION SETTINGS\nABSURD_PHYSICS. SEEDANCE_2_0_MINI. 15 seconds. image2video. 480p. 9:16.')
beats=[dict(time=time,subject='Pip',action=action,object='sticky notes and toy cabinet',stateChange=consequence,
            framing=frame,staging=stage,consequence=consequence,sourceEvidence=action,
            evidenceStatus='SOURCE_CONFIRMED',sourceRelationship='FAITHFUL_ADAPTATION',importance='CORE')
       for time,action,frame,stage,consequence in zip(ranges,actions,framings,staging,consequences)]
plan=dict(sourceIdentity={},creativeObjective='Clarify visible contact, count states and mirror continuity; no audience claim.',
          characterBindings=[],visualExecution=dict(openingState=r2sentences[0],beats=beats,
            mechanism='Each pull doubles the sticky notes from two to four to eight.',
            continuity='Same Pip, cabinet and notes. Coverage continues through mirror reaction until sneeze.',endingState=r2sentences[-1]),
          productionConstraints={},intentClassification={'status':'TEXT_ONLY'},
          evidenceLimitations=['Fixture-authored production plan; no rendered or independent source-fidelity evidence.'],
          generatorRisks=[{'affectedBeat':'beat_03','sourceEvidence':r2sentences[3],
             'risk':'Thin notes, hands and exact counts may be hard to render at 480p.',
             'confidence':'POTENTIAL_RISK','mitigation':'Keep note groups separated in one stable view.','nextAction':'Verify visually before render authorization.'}],referencePlan={})
(folder/'build_prompt.json').write_text(json.dumps({'prompt':prompt,'productionPlan':plan},indent=2))
