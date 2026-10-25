"""One immutable source-bound fact base; no scores, verdicts or taxonomy extensions.

Structured and manually authored inputs use the same validated field contract.
Timed input keeps the accepted acquisition. Provenance never selects a quality rule.
"""
from copy import deepcopy
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .concept_fingerprint import digest
from .short_form_evidence import (
    StructuredCanonicalEvidenceSource, StructuredCanonicalInput, TimedTextEvidenceSource, tokens,
)

VERSION = "canonical-creative-evidence-v1"


class CreativeEvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sourceKind: Literal["TIMED_TEXT", "SEMANTIC", "MANUAL"]
    text: str
    structured: StructuredCanonicalInput | None = None


class CanonicalCreativeEvidenceContext:
    """Construct facts from verified source fields, never accept caller supplied facts.

    Snapshots are copies. Downstream scorers cannot mutate another scorer's evidence.
    Support means the accepted deterministic text-plan checks, never observed pixels.
    """
    __slots__ = ("__input", "__evidence", "__fields", "__facts", "__id")

    def __init__(self, source):
        source = CreativeEvidenceInput.model_validate(source)
        if (source.sourceKind == "TIMED_TEXT") != (source.structured is None):
            raise ValueError("Structured/manual input requires source fields; timed input forbids them")
        self.__input = source.model_copy(deep=True)
        if source.structured is None:
            evidence = TimedTextEvidenceSource().acquire(source.text)
            fields = None
        else:
            evidence = StructuredCanonicalEvidenceSource(source.structured.model_dump()).acquire(source.text)
            from .short_form_engine import _timeline
            timeline = _timeline(source.text)
            if len(timeline) != len(evidence.beats) or any(
                (b['quote'], b['start'], b['end']) != (a.quote, a.start, a.end)
                for b,a in zip(timeline,evidence.beats)
            ):
                raise ValueError('Canonical text/timing carrier mismatch')
            fields = source.structured.semanticFields.model_dump()
        self.__evidence = evidence
        self.__fields = fields
        dims = evidence.dimensions
        if fields is not None:
            g, o = dims['goal'], dims['opening']
            trigger_visible = bool(fields['visibleTrigger'] and len(
                tokens(fields['visibleTrigger'], source.structured.protagonist)
                & tokens(fields['frameZeroDescription'], source.structured.protagonist)
            ) >= 2)
            # An ordinary-use declaration is source evidence, not proof of a good premise.
            everyday = bool(fields['everydayGoal'] and fields['primaryObject'] and fields['normalExpectation'])
            self.__facts = dict(
                goal=dict(declared=g['declared'], visibleInOpening=g['openingVisible'], everyday=everyday,
                          source=deepcopy(g['references']), everydayBasis='EXPLICIT_EVERYDAY_GOAL_OBJECT_EXPECTATION_FIELDS'),
                opening=dict(goalPresent=o['goalSupported'], anomalyPresent=o['anomalySupported'],
                             problemPresent=o['problemPresent'], causalRelationshipVisible=bool(
                                 o['goalSupported'] and o['anomalySupported'] and trigger_visible),
                             source=deepcopy(o['references']), supportMethod='ACCEPTED_SOURCE_OVERLAP_PLUS_TRIGGER_OPENING_OVERLAP'),
                rule=dict(present=dims['coreRule']['presence']!='MISSING', visible=dims['coreRule']['supported'],
                          dominant=len(evidence.facts.mechanismIds)==1,
                          goalRelated=bool(fields['goalRuleRelationship']),
                          classificationStatus=dims['coreRule']['presence'], source=deepcopy(dims['coreRule']['references'])),
                trigger=dict(present=dims['trigger']['presence']!='MISSING', visible=trigger_visible,
                             classificationStatus=dims['trigger']['presence'], source=deepcopy(dims['trigger']['references'])),
                beats=[dict(beatNumber=i+1, **deepcopy(b), supportedStateChange=bool(evidence.beats[i].changes),
                            bodyState=None, spatialState=None, source=deepcopy(evidence.acquisition[i].references))
                       for i,b in enumerate(fields['beats'])],
                payoff=dict(present=dims['payoff']['presence']!='MISSING', ruleLinked=dims['payoff']['ruleLinked'],
                            stateChanging=dims['payoff']['stateChanging'], visual=bool(fields['finalPayoff']),
                            classificationStatus=dims['payoff']['presence'], source=deepcopy(dims['payoff']['references'])),
                loop=deepcopy(dims['loop']),
            )
        else:
            first = evidence.beats[0] if evidence.beats else None
            self.__facts = dict(
                goal=dict(declared=evidence.facts.goalDeclared, visibleInOpening=bool(first and first.goal), everyday=None, source=[]),
                opening=dict(goalPresent=bool(first and first.goal), anomalyPresent=bool(first and first.rules), problemPresent=bool(first), causalRelationshipVisible=None, source=[]),
                rule=dict(present=bool(evidence.facts.mechanismIds), visible=None, dominant=len(evidence.facts.mechanismIds)==1, goalRelated=None, classificationStatus='PRESENT_CLASSIFIED' if evidence.facts.classifiedRules else 'MISSING', source=[]),
                trigger=dict(present=None, visible=None, classificationStatus='UNKNOWN', source=[]),
                beats=[dict(beatNumber=i+1, description=b.quote, sourceSpan=b.sourceSpan) for i,b in enumerate(evidence.beats)],
                payoff=dict(present=None, ruleLinked=None, stateChanging=None, visual=None, classificationStatus='UNKNOWN', source=[]),
                loop=dict(declared=evidence.facts.loopCue, supported=None, references=[]),
            )
        self.__id = digest(dict(text=source.text, fields=fields, facts=self.__facts))

    @property
    def is_structured(self):
        return self.__fields is not None

    @property
    def facts(self):
        return deepcopy(self.__facts)

    @property
    def fields(self):
        return deepcopy(self.__fields)

    def receipt(self):
        return dict(version=VERSION, contextSha256=self.__id, facts=self.facts,
                    provenance=dict(sourceKind=self.__input.sourceKind,
                        structuredSourceSha256=self.__input.structured.projection.sourceSha256 if self.is_structured else None,
                        normalizedFieldsSha256=self.__input.structured.projection.normalizedFieldsSha256 if self.is_structured else None,
                        textSha256=digest(self.__input.text)),
                    limitation='Source-text evidence and deterministic support checks; no observed frames or semantic truth claim.')

    def assert_text(self, text):
        if text != self.__input.text:
            raise ValueError('Canonical evidence context is bound to a different evaluation text')

    def assert_candidate(self, candidate):
        if not self.is_structured:
            return
        if candidate.get('candidateId') != self.__input.structured.projection.candidateId:
            raise ValueError('Canonical evidence candidate ID mismatch')
        for name in ('everydayGoal','primaryObject','impossibleRule'):
            if candidate.get(name) != self.__fields[name]:
                raise ValueError('Canonical evidence candidate field mismatch: '+name)

    def assert_ranking(self, normalized):
        self.assert_text(normalized['evaluationText'])
        if not self.is_structured:
            return
        if normalized['id'] != self.__input.structured.projection.candidateId:
            raise ValueError('Canonical ranking candidate ID mismatch')
        for key, field in [('protagonistGoal','everydayGoal'),('objectOrPrimaryInteraction','primaryObject'),('impossibleRuleOrCoreContradiction','impossibleRule')]:
            if normalized.get(key) != self.__fields[field]:
                raise ValueError('Canonical ranking field mismatch: '+key)

    def assess_short_form(self, text, context):
        """The same accepted evaluator and unchanged structured report projection."""
        from . import short_form_engine as sfe
        self.assert_text(text)
        evidence = self.__evidence.model_copy(deep=True)
        report = sfe._evaluate(text, context, evidence)
        if self.is_structured:
            report['evidenceSourceVersion'] = 'structured-canonical-v1'
            report['canonicalEvidence'] = evidence.model_dump()
            report['findingEvidence'] = {finding['code']: [
                dict(beatId=beat.id, references=facts.references)
                for beat,facts in zip(evidence.beats,evidence.acquisition)
                if not finding['beatIds'] or beat.id in finding['beatIds']
            ] for finding in report['findings']}
        return report

    def naturalness_input(self, candidate):
        self.assert_candidate(candidate)
        return {**candidate, **{k:self.__fields[k] for k in (
            'everydayGoal','primaryObject','impossibleRule','frameZeroDescription')},
            'normalExpectation':self.__fields['normalExpectation'], 'whyThisObject':self.__fields['whyThisObject']}

    def beat_evidence(self, plan, data):
        """Opt-in presence/quality separation; original context facts remain identical."""
        if not self.is_structured:
            raise ValueError('Canonical beat evidence requires structured source fields')
        from .beat_consequence_evidence import project
        return project(self, plan, data, self.__input.structured.protagonist)

    def beat_plan(self, plan, data):
        """Reuse existing classes only when source supports them; never invent physical states.

        Existing semantic normalization's default CHARACTER_MOVES/OFF_BALANCE and
        synthetic tactic-based information are not observations. Unmapped consequence
        stays UNKNOWN and existing grammar reports its coverage failure independently.
        """
        from .semantic_concept_adapter import strategy
        if len(plan) != len(self.__facts['beats']):
            raise ValueError('Canonical beat count differs from plan')
        result=[]
        for i,(old,b) in enumerate(zip(plan,self.__facts['beats'])):
            row=deepcopy(old)
            if old['objectResponse'] != b['visibleConsequence']:
                raise ValueError('Canonical beat consequence differs from source plan')
            tactic=strategy(b['strategy'],i)
            text=b['visibleConsequence']
            # Existing consequence vocabulary and original adapter recognition patterns.
            consequence = (
                'ENVIRONMENT_BECOMES_BLOCKED' if re.search(r'fills? the room|room becomes',text,re.I)
                else 'PATH_BLOCKED' if re.search(r'blocks? the (route|door)',text,re.I)
                else 'SPACE_REDUCES' if re.search(r'usable space|squeez',text,re.I)
                else 'OBJECT_GROWS' if re.search(r'grow|larger|giant|enormous',text,re.I)
                else 'CHARACTER_MOVES' if re.search(r'\b(?:moves?|walks?|runs?|steps?|jumps?)\b',text,re.I)
                else 'UNKNOWN'
            )
            row.update(characterStrategy=tactic, impossibleRule=self.__fields['impossibleRule'],
                       trigger=self.__input.structured.projection.fields['triggerEvidence'].classification,
                       objectResponse=text,characterConsequence=b['newInformation'],
                       newInformation=[b['newInformation']] if b['newInformation'] else [],
                       consequenceType=consequence, bodyStateBefore='UNKNOWN',bodyStateAfter='UNKNOWN',
                       objectStateBefore={'kind':'UNKNOWN'},objectStateAfter={'kind':'UNKNOWN'},
                       spatialChange={},goalProgress='UNKNOWN',relationshipAfter='UNKNOWN',
                       contactPattern='UNKNOWN',payoffStateChange='UNKNOWN')
            # DIRECT_USE is a legacy fallback, not evidence that every unmapped tactic repeats.
            if tactic=='DIRECT_USE' and not re.search(r'\b(?:uses?|tries?|attempts?)\b',b['strategy'],re.I):
                row['characterStrategy']='UNKNOWN'
            result.append(row)
        return result


def from_structured(text, structured, source_kind='SEMANTIC'):
    return CanonicalCreativeEvidenceContext(dict(sourceKind=source_kind,text=text,structured=structured))
