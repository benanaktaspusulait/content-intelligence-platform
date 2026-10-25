"""Versioned evidence acquisition only. No scores, findings or admission policy."""

import hashlib
import re
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .concept_fingerprint import digest
from .semantic_evidence_adapter import CanonicalEvidence, normalize_fields


class EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Timing(EvidenceModel):
    startSeconds: float
    endSeconds: float
    description: str = ""


class StoryBeat(EvidenceModel):
    strategy: str
    visibleConsequence: str
    newInformation: str


class StoryFields(EvidenceModel):
    everydayGoal: str
    primaryObject: str
    normalExpectation: str
    impossibleRule: str
    visibleTrigger: str
    frameZeroDescription: str
    finalPayoff: str
    loopPotential: str
    whyThisObject: str
    goalRuleRelationship: str
    beats: list[StoryBeat] = Field(max_length=30)


class StructuredCanonicalInput(EvidenceModel):
    projection: CanonicalEvidence
    semanticFields: StoryFields
    protagonist: str
    timing: list[Timing] = Field(max_length=30)


class BeatFeatures(EvidenceModel):
    id: str
    start: float | None
    end: float | None
    quote: str
    sourceSpan: list[int] | None
    visual: str
    rules: list[str]
    strategies: list[str]
    changes: list[str]
    stateSignals: list[str]
    goal: bool
    result: bool


class BeatAcquisition(EvidenceModel):
    resultTokens: list[str]
    magnitudeRises: bool
    endingPatterns: list[str]
    terminalStateChange: bool
    recreatedSuccess: bool
    openingLogicalExtreme: bool
    mechanismIds: list[str]
    references: list[dict] = []


class CommonFacts(EvidenceModel):
    openingDelayed: bool
    goalDeclared: bool
    mechanismIds: list[str]
    classifiedRules: list[str]
    confusion: bool
    loopCue: bool
    speechWords: int
    longSpeech: bool
    audioRequired: bool
    reactionVisible: bool
    stagingRisks: list[str]
    productionRisks: list[str]
    duplicateSignature: dict[str, list[str]]


class ShortFormCanonicalEvidence(EvidenceModel):
    version: Literal["short-form-canonical-evidence-v1"] = "short-form-canonical-evidence-v1"
    sourceKind: Literal["TIMED_TEXT_V1", "STRUCTURED_CANONICAL_V1"]
    beats: list[BeatFeatures]
    acquisition: list[BeatAcquisition]
    facts: CommonFacts
    dimensions: dict[str, dict] = {}


class ShortFormEvidenceSource(Protocol):
    def acquire(self, text: str) -> ShortFormCanonicalEvidence: ...


STAGING = {
    "PRESENTER_BLOCKING": (
        "front.facing presenter|addresses? (?:the )?viewer|speaks? to (?:the )?viewer|eye"
        " contact with (?:the )?camera|stares? (?:directly )?(?:at|into) (?:the )?camera"
    ),
    "STATIC_PERFORMANCE": r"static centered|long reaction pose|holds? .{0,20}reaction for",
}
PRODUCTION = {
    "MANY_CHARACTERS": r"crowd|many characters|(?:[3-9]|three|four|five|six|seven|eight|nine|ten) characters",
    "SIMULTANEOUS_OBJECTS": r"many .{0,20}(?:objects|balls)|simultaneous|dozens|hundreds",
    "FINE_FINGER_CONTACT": r"fine finger|individual fingers|threads? .{0,15}needle",
    "TINY_TEXT": r"tiny text|read\w* .{0,15}badge|read\w* .{0,15}sign",
    "IDENTITY_CONTINUITY": r"identity swap|costume transform|changes? .{0,15}costume",
    "MULTI_LOCATION": r"multi.location|teleports?|another room|across three",
}
DELAYED = (
    "normal (?:scene|situation).{0,60}(?:then|before)|after "
    "(?:one|two|three|[1-9]).{0,12}seconds?|after (?:the "
    ")?(?:dialogue|explanation)|only "
    "(?:after|through).{0,20}(?:dialogue|text)|count(?:ing)? "
    ".{0,20}(?:objects?|items?)|prior context"
)
AUDIO = (
    "(?:only|requires?|through|after).{0,35}(?:dialogue|explanation|narration|reading"
    "|text)|explains? (?:the |why|that)|lip.sync.{0,20}(?:long|sequence)"
)
REACTION = r"eyes|flinch|freezes?|catches? .{0,15}self|leans?|determined|cross.eyed|recoils?"


def common(beats, mechanisms, classified):
    from . import short_form_engine as sfe

    visual = " ".join(b["visual"] for b in beats)
    quoted = " ".join(b["quote"] for b in beats)
    first = beats[0]["visual"] if beats else ""
    end = beats[-1]["quote"] if beats else ""
    speech = re.findall(r'[“"]([^”"]+)[”"]', quoted)
    return CommonFacts(
        openingDelayed=sfe._has(DELAYED, first),
        goalDeclared=any(b["goal"] for b in beats),
        mechanismIds=mechanisms,
        classifiedRules=classified,
        confusion=sfe._has(r"unclear|unexplained|confusing|cannot tell|ambiguous", end),
        loopCue=sfe._has(r"loop|back to (?:the )?(?:first|opening)|reinterprets?", end),
        speechWords=sum(len(s.split()) for s in speech),
        longSpeech=any(len(s.split()) > 8 for s in speech),
        audioRequired=sfe._has(AUDIO, quoted),
        reactionVisible=sfe._has(REACTION, visual),
        stagingRisks=[k for k, v in STAGING.items() if sfe._has(v, visual)],
        productionRisks=[k for k, v in PRODUCTION.items() if sfe._has(v, visual)],
        duplicateSignature=sfe._signature(beats),
    )


class TimedTextEvidenceSource:
    def acquire(self, text):
        from . import short_form_engine as sfe

        beats = [{**b, **sfe._features(b["quote"])} for b in sfe._timeline(text)]
        rules = list(dict.fromkeys(r for b in beats for r in b["rules"]))
        if "ADHESION" in rules and "RETURN" in rules:
            rules.remove("RETURN")
        first = beats[0]["visual"] if beats else ""
        acquired = []
        for b in beats:
            acquired.append(
                BeatAcquisition(
                    resultTokens=list(set(re.findall(sfe._RESULT, b["visual"].lower()))),
                    magnitudeRises=sfe._has(
                        (
                            "\\bdoubles?\\b|grows? (?:even )?(?:larger|bigger)|gets? (?:even )?bigger|larger "
                            "than (?:before|last)"
                        ),
                        b["visual"],
                    ),
                    endingPatterns=[k for k, p in sfe._PAYOFF.items() if sfe._has(p, b["visual"])],
                    terminalStateChange=False,
                    recreatedSuccess=sfe._has(
                        r"finally|relaxes?|stays? normal|behaves?|success|closed|succeeds?", b["visual"]
                    ),
                    openingLogicalExtreme=sfe._has(sfe._PAYOFF["LOGICAL_EXTREME"], first),
                    mechanismIds=b["rules"],
                )
            )
        return ShortFormCanonicalEvidence(
            sourceKind="TIMED_TEXT_V1", beats=beats, acquisition=acquired, facts=common(beats, rules, rules)
        )


STOP = set(
    (
        "a an the and or of in on at to from into with without for by as is are was were "
        "be been being it its this that these those his her their he she they him them "
        "one every each any all only still again next exactly immediately whenever when "
        "while then but instead more most much itself themselves character user normal "
        "ordinary action object rule goal result information change new first last same "
        "exact complete original try tries trying"
    ).split()
)


def tokens(value, actor=""):
    """Morphology/overlap verification, not a semantic quality model or taxonomy."""
    words = re.findall(r"[a-z]+", value.casefold())
    result = set()
    for w in words:
        if w in STOP or w in actor.casefold().split():
            continue
        if w.endswith("ies") and len(w) > 4:
            w = w[:-3] + "y"
        elif w.endswith("ing") and len(w) > 5:
            w = w[:-3]
        elif w.endswith("ed") and len(w) > 4:
            w = w[:-2]
        elif w.endswith("es") and len(w) > 4:
            w = w[:-2]
        elif w.endswith("s") and len(w) > 3:
            w = w[:-1]
        # Final silent e is immaterial to overlap (wipe/wiping; erase/erasing).
        if w.endswith("e") and len(w) > 3:
            w = w[:-1]
        result.add(w)
    return result


def validate_projection(data):
    fields = data.semanticFields.model_dump()
    p = data.projection
    if normalize_fields(fields) != fields or digest(fields) != p.normalizedFieldsSha256:
        raise ValueError("Structured source projection digest mismatch")
    if p.describedBeatCount != len(fields["beats"]) or len(data.timing) != len(fields["beats"]):
        raise ValueError("Structured source beat/timing count mismatch")
    refs = [ref for field in p.fields.values() for ref in field.evidence]
    for beat in p.beats:
        refs.extend(
            ref
            for field in (beat.beatStrategyEvidence, beat.consequenceEvidence, beat.progressionEvidence)
            for ref in field.evidence
        )
    for ref in refs:
        m = re.fullmatch(r"beats\[(\d+)\]\.(strategy|visibleConsequence|newInformation)", ref.sourceField)
        actual = (
            fields["beats"][int(m[1])][m[2]]
            if m and int(m[1]) < len(fields["beats"])
            else fields.get(ref.sourceField)
        )
        if actual != ref.sourceText:
            raise ValueError("Structured source reference mismatch")
    return fields


class StructuredCanonicalEvidenceSource:
    def __init__(self, data):
        self.data = StructuredCanonicalInput.model_validate(data)

    def acquire(self, text):
        from . import short_form_engine as sfe

        d = self.data
        f = validate_projection(d)
        p = d.projection
        actor = d.protagonist
        rule = f["impossibleRule"]
        rule_words = tokens(sfe._visual(rule), actor)
        object_words = tokens(f["primaryObject"], actor)
        anchors = rule_words - object_words

        def classify(value):
            return [key for key, pattern in sfe._RULES.items() if sfe._has(pattern, sfe._visual(value))]

        known = classify(rule)
        if "ADHESION" in known and "RETURN" in known:
            known.remove("RETURN")

        def linked(value):
            families = classify(value)
            hits = sorted(anchors & tokens(sfe._visual(value), actor))
            supported = bool(set(known) & set(families)) or len(hits) >= 2
            return supported, hits, families

        opening_link, opening_hits, _ = linked(f["frameZeroDescription"])
        links = [linked(b["visibleConsequence"]) for b in f["beats"]]
        supported_rule = bool(rule and f["visibleTrigger"] and opening_link and sum(x[0] for x in links) >= 2)
        # IDs identify source mechanisms; they are NOT new engine taxonomy classes.
        rule_ids = (
            known[:]
            if supported_rule and known
            else ["source-rule:" + hashlib.sha256(rule.encode()).hexdigest()[:16]]
            if supported_rule
            else []
        )
        goal_words = tokens(sfe._visual(f["everydayGoal"]), actor)
        visible_goal = bool(
            goal_words
            and len(goal_words & tokens(sfe._visual(f["frameZeroDescription"]), actor))
            >= min(2, len(goal_words))
        )

        def refs(name):
            return [e.model_dump() for e in p.fields[name].evidence]

        beats = []
        acquired = []
        previous_consequence = set()
        previous_information = set()
        for i, b in enumerate(f["beats"]):
            expected = f"{actor} {b['strategy']}. {b['visibleConsequence']} {b['newInformation']}"
            if i == 0:
                expected = f["frameZeroDescription"] + " " + expected
            quote = d.timing[i].description or expected
            if quote != expected:
                raise ValueError("Structured timing carrier differs from source fields")
            consequence = tokens(sfe._visual(b["visibleConsequence"]), actor)
            info = tokens(sfe._visual(b["newInformation"]), actor)
            union = consequence | previous_consequence
            changed = bool(
                consequence and (i == 0 or len(consequence & previous_consequence) / max(1, len(union)) < 0.8)
            )
            information = bool(info and info != previous_information)
            valid, hits, families = links[i]
            strategy = tokens(sfe._visual(b["strategy"]), actor)
            # Exact objective field signatures do not include rationale/suggested labels.
            strategy_id = "strategy:" + digest(sorted(strategy))[:16] if strategy else ""
            terminal = i == len(f["beats"]) - 1
            rule_linked = valid and supported_rule
            terminal_change = (
                terminal and changed and information and f["finalPayoff"] == b["visibleConsequence"]
            )
            beat = dict(
                id=f"B{i + 1}",
                start=d.timing[i].startSeconds,
                end=d.timing[i].endSeconds,
                quote=quote,
                sourceSpan=None,
                visual=sfe._visual(quote),
                rules=families,
                strategies=[strategy_id] if strategy_id else [],
                changes=["INFORMATION"] if changed and information and rule_linked else [],
                stateSignals=["INFORMATION:" + digest(sorted(consequence))[:16]]
                if changed and information and rule_linked
                else [],
                goal=visible_goal if i == 0 else False,
                result=bool(b["visibleConsequence"]) and rule_linked,
            )
            beats.append(beat)
            acquired.append(
                BeatAcquisition(
                    resultTokens=sorted(consequence) if rule_linked else [],
                    magnitudeRises=False,
                    endingPatterns=[],
                    terminalStateChange=terminal_change,
                    recreatedSuccess=False,
                    openingLogicalExtreme=False,
                    mechanismIds=rule_ids if valid else [],
                    references=[
                        e.model_dump()
                        for e in p.beats[i].beatStrategyEvidence.evidence
                        + p.beats[i].consequenceEvidence.evidence
                        + p.beats[i].progressionEvidence.evidence
                    ],
                )
            )
            previous_consequence = consequence
            previous_information = info
        facts = common(beats, rule_ids, known)
        facts.goalDeclared = bool(f["everydayGoal"])
        # Provider declaration is not a supported loop. Only source ending/opening state
        # recreation can supply a loop cue; a merely prospective loop statement cannot.
        facts.loopCue = bool(
            beats and tokens(f["finalPayoff"], actor) == tokens(sfe._visual(f["frameZeroDescription"]), actor)
        )

        def status(present, classified):
            return (
                "PRESENT_CLASSIFIED"
                if present and classified
                else "PRESENT_UNCLASSIFIED"
                if present
                else "MISSING"
            )

        dims = dict(
            goal=dict(
                declared=bool(f["everydayGoal"]),
                openingVisible=visible_goal,
                references=refs("visibleGoalEvidence"),
            ),
            opening=dict(
                problemPresent=bool(f["frameZeroDescription"]),
                anomalySupported=opening_link,
                goalSupported=visible_goal,
                anchorMatches=opening_hits,
                references=refs("openingProblemEvidence"),
            ),
            coreRule=dict(
                presence=status(bool(rule), bool(known)),
                supported=supported_rule,
                classification=known,
                mechanismIds=rule_ids,
                references=refs("coreRuleEvidence"),
            ),
            trigger=dict(
                presence=status(
                    bool(f["visibleTrigger"]),
                    p.fields["triggerEvidence"].classification != "UNCLASSIFIED_TRIGGER",
                ),
                references=refs("triggerEvidence"),
            ),
            payoff=dict(
                presence=status(
                    p.payoffPresence == "PRESENT", p.payoffClassification != "UNCLASSIFIED_PAYOFF_PATTERN"
                ),
                ruleLinked=bool(links and links[-1][0] and supported_rule),
                stateChanging=bool(acquired and acquired[-1].terminalStateChange),
                references=refs("payoffEvidence"),
            ),
            loop=dict(
                declared=bool(f["loopPotential"]), supported=facts.loopCue, references=refs("loopEvidence")
            ),
            verification=dict(
                method="SOURCE_FIELD_OVERLAP_AND_STRUCTURAL_CHANGE_V1",
                confidence="STRUCTURED_INFERENCE",
                candidateId=p.candidateId,
                normalizedFieldsSha256=p.normalizedFieldsSha256,
                ruleAnchorMinimum=2,
                consequenceNearDuplicateJaccard=0.8,
                limitation=(
                    "Deterministic support checks, not semantic understanding or observed visual "
                    "proof. Unknown quality remains unresolved; declaration alone does not grant goal"
                    " visibility, rule support or payoff linkage."
                ),
            ),
        )
        return ShortFormCanonicalEvidence(
            sourceKind="STRUCTURED_CANONICAL_V1",
            beats=beats,
            acquisition=acquired,
            facts=facts,
            dimensions=dims,
        )


def acquire(text, context):
    mode = context.get("shortFormEvidenceSourceVersion", "timed-text-v1")
    if mode == "timed-text-v1":
        return TimedTextEvidenceSource().acquire(text)
    if mode == "structured-canonical-v1":
        return StructuredCanonicalEvidenceSource(context.get("structuredCanonicalInput")).acquire(text)
    raise ValueError("Unsupported short-form evidence source version")
