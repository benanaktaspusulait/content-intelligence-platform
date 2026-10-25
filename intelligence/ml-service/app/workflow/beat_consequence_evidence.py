"""Canonical beat presence and supported differences, without new taxonomy classes.

Source-local keys identify literal planned actions/states. They are never class
names or semantic novelty claims. Unsupported/unknown values do not earn credit.
"""
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict
from .concept_fingerprint import digest
from .short_form_evidence import tokens

VERSION = 'beat-unclassified-consequence-support-v1'


class BeatEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    beatNumber: int
    strategyPresent: bool
    strategyClassificationStatus: Literal['STRATEGY_PRESENT_CLASSIFIED','STRATEGY_PRESENT_UNCLASSIFIED','STRATEGY_MISSING','STRATEGY_AMBIGUOUS']
    consequencePresent: bool
    consequenceClassificationStatus: Literal['CONSEQUENCE_PRESENT_CLASSIFIED','CONSEQUENCE_PRESENT_UNCLASSIFIED','CONSEQUENCE_MISSING','CONSEQUENCE_AMBIGUOUS']
    rawStrategy: str
    rawConsequence: str
    strategyClassification: str | None
    consequenceClassification: str | None
    newInformation: str
    newInformationPresent: bool
    newInformationNovel: bool
    stateChangeSupported: bool
    goalStateChangeSupported: bool
    bodyStateChangeSupported: bool
    spatialChangeSupported: bool
    informationProgressionSupported: bool
    progressionSupported: bool
    strategyDiversityKey: str | None
    consequenceDiversityKey: str | None
    stateDifference: dict
    actionEvidence: dict
    evidenceRefs: list[dict]


UNCERTAIN = re.compile(r'^\s*(?:unknown|unclear|unspecified|not (?:shown|specified)|maybe|perhaps|possibly|may\b|might\b|could\b|\?)(?:\b|\s|$)',re.I)
PLACEHOLDER = re.compile(r'^\s*(?:none|n/a|not applicable|no (?:visible )?consequence|no result|no strategy)?[.\s]*$',re.I)
# Magnitude/wording does not establish a different physical state or action.
MODIFIERS = set('slightly slowly quickly gently harder faster rapidly very more most larger largest bigger biggest smaller smallest huge enormous giant really just now again tries try attempts attempt hoping hope expecting expect wanting want manually carefully finally suddenly instantly immediately still'.split())


def terms(text, actor=''):
    words=re.findall(r'[a-z]+',text.casefold())
    return tokens(' '.join(w for w in words if w not in MODIFIERS),actor)


def presence(text, classification, prefix):
    if PLACEHOLDER.fullmatch(text): return False,prefix+'_MISSING'
    if UNCERTAIN.search(text): return True,prefix+'_AMBIGUOUS'
    return True,prefix+('_PRESENT_CLASSIFIED' if classification else '_PRESENT_UNCLASSIFIED')


def action_evidence(text, actor):
    """Literal first action clause; no prose hash or synonym/taxonomy invention."""
    clause=text.strip()
    if actor: clause=re.sub(r'^\s*'+re.escape(actor)+r'\b\s*','',clause,flags=re.I)
    clause=re.sub(r'^(?:he|she|they)\s+','',clause,flags=re.I)
    clause=re.split(r'[,;.]|\b(?:hoping|expecting|because|so that|in order to)\b',clause,maxsplit=1,flags=re.I)[0]
    words=re.findall(r'[a-z]+',clause.casefold())
    words=[w for w in words if w not in MODIFIERS and not w.endswith('ly')]
    if len(words)<2 or words[0] in {'the','a','an','is','has','will','should','would','could'}:
        return dict(predicate=None,target=[],sourceClause=clause,supported=False)
    predicate=sorted(terms(words[0],actor))
    target_clause=re.split(r'\b(?:to|for|with|while|and|but)\b',' '.join(words[1:]),maxsplit=1)[0]
    target=sorted(terms(target_clause,actor)-set(predicate)-set('up down out away off on back forward around through over under'.split()))
    # A source verb plus a concrete target is required; wording alone cannot add a key.
    return dict(predicate=predicate[0] if predicate else None,target=target,sourceClause=clause,supported=bool(predicate and target))


def project(canonical, plan, data, actor):
    acquired=canonical.beat_plan(plan,data)
    source=canonical.facts['beats']
    result=[];seen_information=set();previous_consequence=set()
    for i,(row,b) in enumerate(zip(acquired,source)):
        strategy_class=row['characterStrategy'] if row['characterStrategy'] in data['strategies'] else None
        consequence_class=row['consequenceType'] if row['consequenceType'] in data['consequences'] else None
        sp,ss=presence(b['strategy'],strategy_class,'STRATEGY')
        cp,cs=presence(b['visibleConsequence'],consequence_class,'CONSEQUENCE')
        if ss.endswith('AMBIGUOUS'):strategy_class=None
        if cs.endswith('AMBIGUOUS'):consequence_class=None
        information=(set() if PLACEHOLDER.fullmatch(b['newInformation']) or UNCERTAIN.search(b['newInformation'])
            or re.search(r'^(?:no new information|nothing new|same as (?:before|previous)|unchanged)\b',b['newInformation'],re.I)
            else terms(b['newInformation'],actor))
        consequence=terms(b['visibleConsequence'],actor)
        novel=bool(information and frozenset(information) not in seen_information)
        # The accepted canonical source already verifies rule-linked state/information
        # change. Normalize magnitude/adverbs again so new wording cannot add diversity.
        changed=bool(cp and not cs.endswith('AMBIGUOUS') and b['supportedStateChange']
                     and consequence and consequence!=previous_consequence)
        info_support=bool(cp and not cs.endswith('AMBIGUOUS') and novel)
        action=action_evidence(b['strategy'],actor)
        strategy_key=(data['strategies'][strategy_class]['family'] if strategy_class else
            'source-action:'+digest([action['predicate'],action['target']])[:16]
            if sp and not ss.endswith('AMBIGUOUS') and action['supported'] else None)
        consequence_key=(consequence_class if consequence_class else
            'source-state:'+digest(sorted(consequence))[:16] if changed else None)
        result.append(BeatEvidence(
            beatNumber=i+1,strategyPresent=sp,strategyClassificationStatus=ss,
            consequencePresent=cp,consequenceClassificationStatus=cs,
            rawStrategy=b['strategy'],rawConsequence=b['visibleConsequence'],
            strategyClassification=strategy_class,consequenceClassification=consequence_class,
            newInformation=b['newInformation'],newInformationPresent=bool(information),newInformationNovel=novel,
            stateChangeSupported=changed,goalStateChangeSupported=False,
            bodyStateChangeSupported=False,spatialChangeSupported=False,
            informationProgressionSupported=info_support,progressionSupported=changed or info_support,
            strategyDiversityKey=strategy_key,consequenceDiversityKey=consequence_key,
            stateDifference=dict(before=None if not i else source[i-1]['visibleConsequence'],after=b['visibleConsequence'],
                supported=changed,basis='ACCEPTED_CANONICAL_RULE_LINKED_STATE_CHECK_PLUS_NON_MAGNITUDE_SOURCE_DIFFERENCE',
                objectState=None,goalState=None,bodyState=None,spatialState=None,
                limitation='Literal described state contrast, not a classified physical relationship or observed frames.'),
            actionEvidence=action,evidenceRefs=b['source'],
        ))
        if information:seen_information.add(frozenset(information))
        previous_consequence=consequence
    return result


def signature(beat,row):
    def known(v):return None if v in ('UNKNOWN','UNSPECIFIED','UNCLASSIFIED_TRIGGER',None) else v
    return dict(strategyType=beat.strategyDiversityKey,triggerType=known(row['trigger']),
        contactPattern=known(row['contactPattern']),bodyStateAfter=known(row['bodyStateAfter']),
        objectStateAfter=known(row['objectStateAfter']['kind']),consequenceType=beat.consequenceDiversityKey,
        goalDistanceChange=known(row['goalProgress']),relationshipAfter=known(row['relationshipAfter']))


def compare(a,b,x,y):
    left,right=signature(a,x),signature(b,y)
    observed=[k for k in left if left[k] is not None and right[k] is not None]
    matching=[k for k in observed if left[k]==right[k]]
    similarity=round(len(matching)/len(observed),6) if observed else None
    return dict(classification='UNRESOLVED_ATTEMPT' if not observed else 'IDENTICAL_ATTEMPT'
        if len(matching)==len(observed) else 'NEAR_DUPLICATE_ATTEMPT' if similarity>=0.71 else 'DISTINCT_ATTEMPT',
        similarity=similarity,matchingDimensions=matching,observedDimensions=observed,
        limitation='Only supported axes compared; matching UNKNOWN values do not establish repetition.')


def payoff_distance(beats,plan):
    if len(plan)<2:return dict(distance=0,comparisons=[],stateChange=None)
    last=beats[-1];values=[]
    for previous,row in zip(beats[-3:-1],plan[-3:-1]):
        a,b=signature(previous,row),signature(last,plan[-1])
        axes=['bodyStateAfter','consequenceType','goalDistanceChange','relationshipAfter']
        observed=[k for k in axes if a[k] is not None and b[k] is not None]
        changes=[k for k in observed if a[k]!=b[k]]
        values.append(dict(comparedWithBeat=previous.beatNumber,distance=len(changes)/len(observed) if observed else 0,
                           changedDimensions=changes,observedDimensions=observed))
    return dict(distance=round(min(v['distance'] for v in values),6),comparisons=values,
        stateChange=last.stateDifference if last.stateChangeSupported else None,
        magnitudeOnlyDoesNotCount=True,normalization='SUPPORTED_AXES_ONLY; NO_SUPPORTED_COMPARISON=0')
