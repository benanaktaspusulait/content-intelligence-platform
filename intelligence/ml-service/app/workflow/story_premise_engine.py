"""Duration-scoped, offline premise screening; never a canonical score or approval.

Evidence is extracted conservatively from source sentences, with exact offsets.
Pattern matches are textual support, not verified semantics, images or audience
outcomes. Missing/ambiguous evidence stays unresolved. Physical action counts do
not contribute to this engine. No provider, persistence or rendering dependencies.
"""

from __future__ import annotations

import math
import re
from hashlib import sha256
from typing import Any

VERSION = "story-premise-engine-v1"
MODES = {"POMPOM_STORIES", "POMPOM_STORY", "LONG_FORM", "LONG_FORM_STORY", "LONG_NARRATIVE"}
TIME = re.compile(r"(?mi)^\s*(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*(?:s|sec|seconds?)\b\s*[:—-]?\s*")
GOAL = r"\b(?:wants?|needs?|must|has\s+to|(?:goal|task)\s+is\s+to|plans?\s+to|intends?\s+to|aims?\s+to|sets?\s+out\s+to)\s+(?:to\s+)?(?!be\b|look\b|seem\b|not\b|never\b)([a-z]+)\b"
PASSIVE = r"\b(?:looks?\s+(?:scary|different)|is\s+misunderstood|misunderstands?|scary\s+costume|nice\s+all\s+along|always\s+(?:nice|good|harmless))\b"
FRICTION = (
    r"\b(?:but|cannot|can't|refuses?|fails?|won't|not\s+(?:scared|afraid)|unafraid|backfires?|resists?)\b"
)
BOND = r"\b(?:befriends?|bonds?|begins?\s+to\s+trust|wins?\s+[^.]{0,30}trust|shares?\s+[^.]{0,50}(?:with|together)|laughs?\s+together|comforts?)\b"
HIDDEN = r"\b(?:secretly|disguised|disguises|pretends?|conceals?|hidden\s+(?:intent|motive)|hides?\s+(?:his|her|their|a)\s+(?:secret|motive|intent))\b"
OPPORTUNITY = r"\b(?:can\s+(?:now|finally)|could\s+(?:now|finally)|now\s+(?:can|could)|has\s+(?:a|the)\s+(?:real\s+)?(?:chance|opportunity)|finally\s+has\s+(?:a|the)\s+chance)\b"
CHOICE = r"\b(?:deliberately|consciously|chooses?|decides?|instead\s+of)\b"
REJECTION = (
    r"\b(?:rejects?|refuses?|abandons?|forgoes?|surrenders?|drops?|gives?\s+up|turns?\s+away|instead\s+of)\b"
)
HELP = r"\b(?:protect\w*|defend\w*|rescu\w*|shelter\w*|shield\w*|sav(?:e|es|ing)|guard\w*|catch\w*|return\w*|help\w*)\b"
COST = r"\b(?:loses?|forfeits?|fails?\s+(?:his|her|their|the|an?)|gives?\s+up|surrenders?|sacrifices?|risks?\s+(?:exposure|being\s+exposed))\b"
ACCIDENT = r"\b(?:accidentally|by\s+accident|without\s+(?:choosing|realizing)|always\s+(?:good|nice)|nice\s+all\s+along)\b"
TRAITS = {
    "roar": r"\broar\w*\b",
    "strength": r"\b(?:strength|strong|powerful)\b",
    "teeth": r"\b(?:teeth|fangs)\b",
    "size": r"\b(?:giant\s+size|huge\s+body|enormous\s+size)\b",
    "deception": r"\b(?:lying\s+skill|deception\s+skill)\b",
    "thief_thinking": r"\b(?:thief[- ]thinking|thief's\s+thinking|thieves?\s+think|lock[- ]picking)\b",
    "costume": r"\b(?:scary\s+costume|costume)\b",
}
STATUS = r"\b(?:becomes?\s+(?:a\s+|the\s+|their\s+)?(?:protector|guard|friend|member)|welcomes?\s+[^.]{0,40}(?:member|family)|best\s+monster|(?:threat|outsider|enemy|thief)\s*(?:→|->|to)\s*(?:protector|member|friend|guard))\b"
NEGATED = re.compile(r"\b(?:no|never|not|without|doesn't|does\s+not|cannot)\b", re.I)


def _supported_matches(pattern: str, text: str, *, negation: bool = True):
    for match in re.finditer(pattern, text, re.I):
        prefix = re.split(r"[.;,:]|\bbut\b", text[: match.start()], flags=re.I)[-1]
        if not negation or not NEGATED.search(" ".join(prefix.split()[-5:])):
            yield match


def _matches(pattern: str, text: str, *, negation: bool = True) -> bool:
    return next(_supported_matches(pattern, text, negation=negation), None) is not None


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result > 0 else None


def scope(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    target = context.get("targetConfiguration") or {}
    metadata = context.get("metadata") or {}
    duration = next(
        (
            n
            for value in (
                context.get("plannedEditedDuration"),
                context.get("desiredDuration"),
                context.get("targetDuration"),
                target.get("duration"),
                context.get("durationSeconds"),
                context.get("duration"),
                metadata.get("duration"),
            )
            if (n := _number(value)) is not None
        ),
        None,
    )
    declaration = re.search(r"(?mi)^\s*(?:target\s+)?duration\s*[:=\]]?\s*(\d+(?:\.\d+)?)", text)
    if duration is None and declaration:
        duration = _number(declaration.group(1))
    # An explicit format declaration is evidence; a character mentioning sixty
    # seconds in dialogue is not a requested duration.
    if duration is None:
        declaration = re.search(r"(?mi)^\s*(\d+(?:\.\d+)?)[ -]second\s+(?:video|story|film)\b", text)
        if declaration:
            duration = _number(declaration.group(1))
    if duration is None:
        times = list(TIME.finditer(text))
        if times and float(times[0].group(1)) == 0:
            duration = _number(times[-1].group(2))
    modes = [context.get(k) for k in ("storyType", "seriesType", "narrativeMode")]
    modes += [target.get("storyType"), metadata.get("seriesType")]
    declared_mode = re.search(r"(?mi)^\s*(?:story\s*type|series\s*type|narrative\s*mode)\s*:\s*(.+)$", text)
    if declared_mode:
        modes.append(declared_mode.group(1))
    normalized = {re.sub(r"[\s-]+", "_", str(mode or "").strip().upper()) for mode in modes}
    explicit_mode = bool(normalized & MODES)
    return {
        "active": explicit_mode or duration is not None and duration >= 45,
        "requestedDurationSeconds": duration,
        "explicitStoryMode": explicit_mode,
        "calibratedDurationRange": [45, 75],
    }


def _records(text: str) -> list[dict[str, Any]]:
    times = list(TIME.finditer(text))
    records = []
    # Keep the exact source span even when removing a timestamp/heading prefix.
    for match in re.finditer(r"[^\n]+?(?:[.!?](?=\s|$)|(?=\n|$))", text):
        start, end = match.span()
        raw = match.group()
        prefix = TIME.match(raw)
        if prefix:
            start += prefix.end()
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        quote = text[start:end]
        if not quote or re.match(
            r"(?i)^(?:title|duration|story\s*type|series\s*type|narrative\s*mode)\s*:", quote
        ):
            continue
        stamp = next((t for t in reversed(times) if t.start() <= start), None)
        records.append(
            {
                "id": f"s{len(records) + 1}",
                "quote": quote,
                "sourceSpan": [start, end],
                "timeRange": [float(stamp.group(1)), float(stamp.group(2))] if stamp else None,
            }
        )
    return records


def _actor(goal: dict[str, Any] | None) -> tuple[str, ...]:
    if not goal:
        return ()
    match = re.search(GOAL, goal["quote"], re.I)
    prefix = goal["quote"][: match.start()].strip() if match else ""
    prefix = re.sub(r"(?i)^goal\s*:\s*", "", prefix)
    # Support "Moro the monster", "the monster", and a named protagonist.
    words = re.findall(r"[A-Za-z]+", re.sub(r"['’]s\b", "", prefix))
    words = [w.lower() for w in words if w.lower() not in {"the", "a", "an", "secretly", "young", "little"}]
    return tuple(words[-2:])


def _belongs(record: dict[str, Any], actor: tuple[str, ...]) -> bool:
    # Explicit subject binding is deliberately conservative. Mere mention of
    # the protagonist as an object cannot credit another character's choice.
    subject = re.split(r"[,;:]", record["quote"], maxsplit=1)[0].lower()
    subject = re.sub(r"^(?:but|instead|then|finally|now)\s+", "", subject)
    return any(re.match(rf"(?:the\s+)?{re.escape(name)}\b", subject) for name in actor)


def assess(text: str, context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return None for short-form callers, preserving their response and gates."""
    activation = scope(text, context)
    if not activation["active"]:
        return None
    records = _records(text)

    def bound(record, match):
        start = record["sourceSpan"][0]
        return {**record, "matchedSpan": [start + match.start(), start + match.end()]}

    def find(
        pattern: str,
        *,
        after: dict | None = None,
        actor: tuple[str, ...] = (),
        negation: bool = True,
        extra=None,
    ) -> dict | None:
        for record in records:
            if actor and not _belongs(record, actor) or extra is not None and not extra(record):
                continue
            for match in _supported_matches(pattern, record["quote"], negation=negation):
                evidence = bound(record, match)
                if (
                    not after
                    or evidence["matchedSpan"][0] >= after.get("matchedSpan", after["sourceSpan"])[1]
                ):
                    return evidence
        return None

    # A fixed opening window prevents padding later physical beats from
    # expanding the evidence admitted for the premise.
    opening = [r for r in records[:4] if not r["timeRange"] or r["timeRange"][0] <= 15]
    goal = next((bound(r, match) for r in opening for match in _supported_matches(GOAL, r["quote"])), None)
    actor = _actor(goal)
    self_interested_goal = bool(
        goal
        and re.search(
            r"\b(?:scar\w*|steal\w*|infiltrat\w*|deceiv\w*|win\w*|pass|exam|escape|hid\w*|accepted|acceptance|reward|status|food|treasure|selfish|own\s+benefit|for\s+(?:himself|herself|themselves))\b",
            goal["quote"],
            re.I,
        )
    )
    friction = find(FRICTION, after=goal, negation=False) if goal else None
    hidden = find(HIDDEN, actor=actor) if actor else None
    bond = find(BOND, after=goal) if goal else None
    # Link the later opportunity and cost to the original action or stake,
    # rather than awarding points for an unrelated opportunity or sacrifice.
    goal_clause = re.split(r"\bbut\b", goal["quote"], maxsplit=1, flags=re.I)[0] if goal else ""
    participants = {word.lower() for word in re.findall(r"\b[A-Z][a-z]+\b", goal_clause)}
    goal_words = (
        set(re.findall(r"[a-z]+", goal_clause.lower()))
        - {
            "a",
            "an",
            "the",
            "to",
            "his",
            "her",
            "their",
            "must",
            "wants",
            "needs",
            "plans",
            "secretly",
            "and",
            "for",
            "with",
            "from",
            "using",
            "into",
            "that",
            "this",
            "when",
            *actor,
            *participants,
        }
        if goal
        else set()
    )
    goal_words = {w.rstrip("s") for w in goal_words if len(w) >= 3}

    def original_goal(r):
        return bool(goal_words & {w.rstrip("s") for w in re.findall(r"[a-z]+", r["quote"].lower())})

    def goal_opportunity(r):
        overlap = goal_words & {w.rstrip("s") for w in re.findall(r"[a-z]+", r["quote"].lower())}
        action = re.search(GOAL, goal["quote"], re.I).group(1).lower() if goal else ""
        return len(overlap) >= 2 or bool(
            action and re.search(rf"\b{re.escape(action.rstrip('e'))}(?:e|es|s|ed|ing)?\b", r["quote"], re.I)
        )

    opportunity = (
        find(OPPORTUNITY, after=bond, actor=actor, extra=goal_opportunity) if bond and actor else None
    )
    choice = (
        find(
            CHOICE,
            after=opportunity,
            actor=actor,
            extra=lambda r: (
                _matches(REJECTION, r["quote"])
                and _matches(HELP, r["quote"])
                and original_goal(r)
                and not _matches(ACCIDENT, r["quote"])
            ),
        )
        if opportunity and self_interested_goal
        else None
    )
    cost = find(COST, after=choice, actor=actor, extra=original_goal) if choice else None
    # A later restoration of the same original prize removes the claimed cost.
    restored = (
        find(
            r"\b(?:gets?\s+everything|wins?\s+back|regains?|receives?\s+[^.]{0,35}(?:anyway|after\s+all))\b",
            after=cost,
            actor=actor,
            extra=original_goal,
        )
        if cost
        else None
    )
    if restored:
        cost = None
    passive = find(PASSIVE, negation=False) if not choice else None
    accidental = find(ACCIDENT) if not choice else None
    traits = []
    for name, pattern in TRAITS.items():
        initial = next((r for r in opening if _matches(pattern, r["quote"]) and _belongs(r, actor)), None)
        reuse = (
            find(pattern, after=choice or bond, actor=actor, extra=lambda r: _matches(HELP, r["quote"]))
            if initial and (choice or bond)
            else None
        )
        if initial and reuse and reuse["sourceSpan"][0] > initial["sourceSpan"][0]:
            traits.append({"trait": name, "initial": initial, "reuse": reuse})
    reversal = (
        find(
            STATUS,
            after=choice or bond,
            extra=lambda r: (
                _belongs(r, actor)
                or any(
                    re.search(
                        rf"\b(?:calls?|names?|welcomes?|accepts?)\s+(?:the\s+)?{re.escape(name)}\b",
                        r["quote"],
                        re.I,
                    )
                    for name in actor
                )
            ),
        )
        if choice or bond
        else None
    )
    explicit_question = (
        find(r"\b(?:whether|must\s+choose|will\s+[^.?!]{1,70}\?)", after=bond) if bond else None
    )
    resolution_time = (
        max(choice["timeRange"][1], reversal["timeRange"][1])
        if (choice and reversal and choice.get("timeRange") and reversal.get("timeRange"))
        else None
    )
    resolved_early = resolution_time is not None and resolution_time <= 20
    open_question = bool(opportunity and choice or explicit_question) and not resolved_early
    high_risk = bool(resolved_early or not open_question and (passive or not opportunity))
    archetype = (
        "ACTIVE_MORAL_ARC"
        if choice and cost
        else "ACTIVE_CONTRADICTION"
        if goal and friction
        else "PASSIVE_MISUNDERSTANDING"
        if passive
        else "INSUFFICIENT_STORY_EVIDENCE"
    )

    checks: list[dict[str, Any]] = []

    def check(
        key: str,
        supported: bool,
        evidence: list,
        reason: str,
        weight: int,
        *,
        hard: bool = False,
        missing: str = "UNKNOWN",
    ):
        checks.append(
            {
                "checkId": key,
                "outcome": "PASS" if supported else missing,
                "strength": 1.0 if supported else 0.0,
                "weight": weight,
                "gate": "HARD" if hard else "SOFT",
                "reason": reason,
                "evidence": [r for r in evidence if r],
                "basis": "SOURCE_TEXT_PATTERN_SUPPORT",
            }
        )

    premise = bool(goal and any(_matches(FRICTION, r["quote"], negation=False) for r in opening))
    check(
        "PREMISE_STRENGTH",
        premise,
        [goal, friction],
        "Opening goal and contradiction create a textual dramatic question."
        if premise
        else "The opening lacks a supported active goal/contradiction before execution detail.",
        12,
    )
    check(
        "ACTIVE_PROTAGONIST_OR_GUEST_GOAL",
        bool(goal),
        [goal],
        "An explicit active goal drives the story."
        if goal
        else "No explicit driving goal; appearance or misunderstanding is insufficient.",
        10,
        hard=True,
    )
    role_support = bool(
        goal
        and friction
        and not passive
        and (
            re.search(r"\bmonster\b", goal["quote"], re.I)
            and re.search(r"\bscar\w*\b", goal["quote"], re.I)
            or re.search(r"\b(?:wolf|predator)\b", goal["quote"], re.I)
            and reversal
            and re.search(r"\bprotector\b", reversal["quote"], re.I)
            or re.search(r"\bthief\b", goal["quote"], re.I)
            and reversal
            and re.search(r"\bguard\b", reversal["quote"], re.I)
            or re.search(r"\bpirate\b.*\b(?:afraid|fears?)\b.*\btreasure\b", goal["quote"], re.I)
            or re.search(r"\bgenie\b.*\brefus\w*\b.*\bwishes\b", goal["quote"], re.I)
        )
    )
    check(
        "ROLE_CONTRADICTION",
        role_support,
        [goal, friction],
        "The driving goal meets explicit resistance; role/goal contradiction needs editorial confirmation.",
        8,
    )
    check(
        "ACTIVE_DECEPTION_OR_HIDDEN_INTENT",
        bool(hidden),
        [hidden],
        "Hidden intent supports dramatic irony; it is positive, not mandatory.",
        5,
        missing="NOT_APPLICABLE",
    )
    check(
        "MORAL_CHOICE_GATE",
        bool(choice),
        [goal, bond, opportunity, choice],
        "The same actor rejects an opportunity linked to the original goal to help another."
        if choice
        else "No source-supported deliberate rejection of a real opportunity to complete the original goal.",
        20,
        hard=True,
    )
    check(
        "SACRIFICE_OR_COST",
        bool(cost),
        [cost, restored],
        "The choice costs an original stake."
        if cost
        else "No lasting cost tied to the original goal is established.",
        12,
        hard=True,
    )
    check(
        "TRAIT_REPURPOSING",
        bool(traits),
        [r for t in traits for r in (t["initial"], t["reuse"])],
        "The same established trait is used to help later."
        if traits
        else "No linked reuse of an established trait; a late new skill is insufficient.",
        10,
    )
    check(
        "STATUS_REVERSAL",
        bool(reversal),
        [reversal],
        "A changed social/emotional role is explicit."
        if reversal
        else "A meaningful final role change is not established.",
        8,
    )
    check(
        "PREDICTABILITY_EARLY_SOLVE_RISK",
        open_question and not high_risk,
        [opportunity, choice, explicit_question, passive],
        "A later opportunity/decision keeps the outcome structurally open."
        if open_question
        else "High early-solve risk: the setup suggests its payoff without a later consequential decision.",
        5,
        hard=True,
        missing="FAIL" if high_risk else "UNKNOWN",
    )

    events = []
    for kind, record in (
        ("RELATIONSHIP_CHANGE", bond),
        ("NEW_OPPORTUNITY", opportunity),
        ("MORAL_CHOICE", choice),
        ("COST", cost),
        ("TRAIT_REINTERPRETATION", traits[0]["reuse"] if traits else None),
        ("STATUS_CHANGE", reversal),
    ):
        if record:
            dimensions = {
                "RELATIONSHIP_CHANGE": ["RELATIONSHIP_CHANGE"],
                "NEW_OPPORTUNITY": ["NEW_INFORMATION"],
                "MORAL_CHOICE": ["MORAL_CHOICE", "GOAL_CHANGE"],
                "COST": ["CONSEQUENCE"],
                "TRAIT_REINTERPRETATION": ["REINTERPRETATION"],
                "STATUS_CHANGE": ["STATUS_CHANGE"],
            }[kind]
            events.append({"kind": kind, "dimensions": dimensions, "evidence": record})
    meaning_count = len(events)
    check(
        "MEANING_SHIFT_DENSITY",
        meaning_count >= 4,
        [e["evidence"] for e in events],
        f"{meaning_count} distinct meaning changes; repeated physical attempts earn no credit.",
        6,
        missing="FAIL" if meaning_count < 4 else "UNKNOWN",
    )

    duration = activation["requestedDurationSeconds"]
    intervals = [(float(m.group(1)), float(m.group(2))) for m in TIME.finditer(text)]
    timing_complete = bool(
        duration
        and intervals
        and intervals[0][0] == 0
        and intervals[-1][1] == duration
        and all(a < b for a, b in intervals)
        and all(a[1] == b[0] for a, b in zip(intervals, intervals[1:]))
    )
    payoff_times = sorted({e["evidence"]["timeRange"][1] for e in events if e["evidence"]["timeRange"]})
    boundaries = [0.0, *payoff_times, duration] if timing_complete else []
    gaps = (
        [
            {"start": a, "end": b, "seconds": b - a}
            for a, b in zip(boundaries, boundaries[1:])
            if b - a > max(15, duration / 4)
        ]
        if duration
        else []
    )
    check(
        "PAYOFF_DENSITY",
        bool(timing_complete and not gaps and meaning_count >= 4),
        [e["evidence"] for e in events],
        "Meaning changes are distributed across the timed plan."
        if timing_complete and not gaps
        else "Long stretches lack a meaningful consequence/reinterpretation."
        if gaps
        else "Payoff timing is unknown: a complete, ordered timecoded plan is required.",
        4,
        missing="FAIL" if gaps else "UNKNOWN",
    )

    failures = [c for c in checks if c["gate"] == "HARD" and c["outcome"] != "PASS"]
    reasons = [
        {"code": c["checkId"], "severity": "STORY_REVISION_REQUIRED", "message": c["reason"]}
        for c in failures
    ]
    if passive:
        reasons.insert(
            0,
            {
                "code": "PASSIVE_MISUNDERSTANDING",
                "severity": "STORY_REVISION_REQUIRED",
                "message": "Passive misunderstanding supplies appearance/reveal, not an active moral arc.",
            },
        )
    if accidental:
        reasons.append(
            {
                "code": "ACCIDENTAL_TRANSFORMATION",
                "severity": "STORY_REVISION_REQUIRED",
                "message": "Accidental heroism or being good all along does not establish a conscious transformation.",
            }
        )
    score = sum(c["weight"] for c in checks if c["outcome"] == "PASS")
    if not choice or not cost:
        score = min(score, 59)
    if passive:
        score = min(score, 39)
    if meaning_count < 4:
        reasons.append(
            {
                "code": "LOW_MEANING_SHIFT_DENSITY",
                "severity": "WARN",
                "message": "Physical activity cannot compensate for too few relationship, goal, status or meaning changes.",
            }
        )
    for c in checks:
        if c["gate"] == "SOFT" and c["outcome"] in {"FAIL", "UNKNOWN"}:
            reasons.append({"code": c["checkId"], "severity": "WARN", "message": c["reason"]})
    if choice and not _matches(
        r"\b(?:drops?|tears?|turns?|shields?|steps?|pushes?|hands?|places?)\b", choice["quote"]
    ):
        reasons.append(
            {
                "code": "MORAL_CHOICE_VISUALLY_UNCLEAR",
                "severity": "WARN",
                "message": "The choice is stated; specify an observable action that communicates it.",
            }
        )
    guest = (context or {}).get("guestCharacter") or (context or {}).get("guestCharacterName")
    if isinstance(guest, str) and guest.strip() and not any(name in guest.lower() for name in actor):
        reasons.append(
            {
                "code": "DECORATIVE_GUEST",
                "severity": "WARN",
                "message": "The named guest has no source-supported driving goal in this premise.",
            }
        )
    if duration is not None and not 45 <= duration <= 75:
        reasons.append(
            {
                "code": "OUTSIDE_CALIBRATED_DURATION",
                "severity": "WARN",
                "message": "This policy is designed for 45–75s; the selected story mode/duration needs editorial review.",
            }
        )
    status = (
        "STORY_REVISION_REQUIRED"
        if failures or passive or accidental or score < 70
        else "PASS_WITH_WARNINGS"
        if reasons
        else "PASS"
    )
    suitability = {
        "10_20_SECONDS": {
            "status": "SUITABLE" if passive or premise else "REVIEW_REQUIRED",
            "reason": "A single setup/reveal can sustain a short; this is not a global concept rejection."
            if passive
            else "An active premise can work as a short; condense to one consequential turn.",
        },
        "20_35_SECONDS": {
            "status": "REVIEW_REQUIRED" if passive else "SUITABLE" if premise else "REVISION_REQUIRED",
            "reason": "Needs a distinct development and payoff within this duration.",
        },
        "45_75_SECONDS": {
            "status": "REVISION_REQUIRED" if status == "STORY_REVISION_REQUIRED" else "SUITABLE",
            "score": score,
            "reason": "A sustained active arc needs a real choice, cost and multiple meaning changes.",
        },
    }
    summary = {
        "premise": goal["quote"] if goal else records[0]["quote"] if records else None,
        "drivingGoal": goal["quote"] if goal else None,
        "drivingActor": list(actor),
        "selfInterestedGoalTextSupport": self_interested_goal,
        "contradiction": friction["quote"] if friction else None,
        "hiddenIntent": hidden["quote"] if hidden else None,
        "moralChoice": choice["quote"] if choice else None,
        "cost": cost["quote"] if cost else None,
        "traitRepurposing": [t["trait"] for t in traits],
        "finalStatusReversal": reversal["quote"] if reversal else None,
        "predictabilityRisk": "HIGH"
        if high_risk
        else "LOWER_STRUCTURAL_RISK"
        if open_question
        else "UNKNOWN",
        "openDramaticQuestionAfterOpening": "SUPPORTED_STRUCTURALLY" if open_question else "NOT_ESTABLISHED",
        "earlySolveBy15Seconds": "EARLY_RESOLUTION_TEXT_SUPPORT"
        if resolution_time is not None and resolution_time <= 15
        else "EARLY_RESOLUTION_BY20_SECONDS"
        if resolved_early
        else "UNVERIFIED_EDITORIAL_INFERENCE",
        "resolutionBySeconds": resolution_time,
        "longFormSuitability": suitability["45_75_SECONDS"]["status"],
    }
    report = (
        f"{status}: {archetype.replace('_', ' ').lower()}; premise-engine score {score}/100. "
        + (
            " ".join(r["message"] for r in reasons if r["severity"] == "STORY_REVISION_REQUIRED")
            if status == "STORY_REVISION_REQUIRED"
            else "The text supports a deliberate goal-sacrificing arc. "
        )
        + " Textual support only; visual execution and audience response remain unverified."
    )
    return {
        "version": VERSION,
        "engine": "STORY_PREMISE_ENGINE",
        "scope": activation,
        "sourceSha256": sha256(text.encode()).hexdigest(),
        "status": status,
        "score": score,
        "scoreType": "LONG_FORM_PREMISE_HEURISTIC_NOT_CANONICAL",
        "archetype": archetype,
        "checks": checks,
        "findings": reasons,
        "storyEngineSummary": summary,
        "meaningShifts": events,
        "meaningShiftCount": meaning_count,
        "payoffTiming": {
            "status": "SUPPORTED" if timing_complete else "UNKNOWN",
            "gaps": gaps,
            "timeBasis": "SUPPORTING_BEAT_ENDS_NOT_OBSERVED_EVENT_TIMES",
        },
        "durationSuitability": suitability,
        "humanReadableReport": report,
        "evidenceLimitations": [
            "Conservative English source-pattern screening, not semantic verification.",
            "Unrecognized wording and ambiguous actor references require editorial review.",
            "Early-solve risk is an editorial hypothesis, not observed viewer behavior.",
            "No rendered visual or audience evidence.",
        ],
        "canonicalRulesetUnchanged": True,
        "renderAuthorized": False,
        "providerCalls": 0,
    }
