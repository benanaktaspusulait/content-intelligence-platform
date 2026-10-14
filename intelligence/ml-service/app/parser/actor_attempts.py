"""Source-bound actor actions, separate from production directives (Ruleset 1.9)."""

from __future__ import annotations

import re
from typing import Any

VERSION = "actor-source-bound-v2"
# Physical action vocabulary is a positive grammar contract, not a stopword filter.
FORMS = {
    "PULL": ("pull", "pulls", "pulling", "pulled"),
    "PEEL": ("peel", "peels", "peeling", "peeled"),
    "PUSH": ("push", "pushes", "pushing", "pushed"),
    "REMOVE": ("remove", "removes", "removing", "removed"),
    "GRAB": ("grab", "grabs", "grabbing", "grabbed"),
    "CATCH": ("catch", "catches", "catching", "caught"),
    "BLOCK": ("block", "blocks", "blocking", "blocked"),
    "HOLD": ("hold", "holds", "holding", "held"),
    "LIFT": ("lift", "lifts", "lifting", "lifted"),
    "PLACE": ("place", "places", "placing", "placed"),
    "TURN": ("turn", "turns", "turning", "turned"),
    "ROTATE": ("rotate", "rotates", "rotating", "rotated"),
    "TUG": ("tug", "tugs", "tugging", "tugged"),
    "TWIST": ("twist", "twists", "twisting", "twisted"),
    "PIN": ("pin", "pins", "pinning", "pinned"),
    "PRESS": ("press", "presses", "pressing", "pressed"),
    "SQUEEZE": ("squeeze", "squeezes", "squeezing", "squeezed"),
    "FOLD": ("fold", "folds", "folding", "folded"),
    "TAP": ("tap", "taps", "tapping", "tapped"),
    "THROW": ("throw", "throws", "throwing", "threw", "thrown"),
    "TOSS": ("toss", "tosses", "tossing", "tossed"),
    "WALK": ("walk", "walks", "walking", "walked"),
    "STICK": ("stick", "sticks", "sticking", "stuck"),
    "REACH": ("reach", "reaches", "reaching", "reached"),
    "STEP": ("step", "steps", "stepping", "stepped"),
    "MOVE": ("move", "moves", "moving", "moved"),
    "COVER": ("cover", "covers", "covering", "covered"),
    "WRAP": ("wrap", "wraps", "wrapping", "wrapped"),
}
ROOTS = {form: root for root, forms in FORMS.items() for form in forms}
PRODUCTION = re.compile(
    r"\b(?:camera|shot|framing|close-up|wide|tracking|static|pan|tilt|zoom|visible)\b|\bin (?:the )?frame\b",
    re.I,
)
RELATION = re.compile(
    r"\b(?:again|stuck|blocked|away|off|free|release|remove|recover)\b|\b(?:from|into)\b|\bto (?:open|stop|free|remove|release|keep|control|catch|block)\b",
    re.I,
)


def classify_content(content: str, actor: str | None, role: str = "") -> dict[str, Any]:
    instructions = [
        {
            "classification": "CAMERA_INSTRUCTION" if PRODUCTION.search(m.group()) else "VISUAL_COMPOSITION",
            "quote": m.group(),
            "localSpan": [m.start(), m.end()],
        }
        for m in re.finditer(r"\[[^\]]*\]", content)
        if PRODUCTION.search(m.group())
    ]
    for segment in re.finditer(r"[^\[\];\n]+", content):
        if content.rfind("[", 0, segment.start()) > content.rfind("]", 0, segment.start()):
            continue
        cleaned = re.sub(
            r"^\s*\d+(?:\.\d+)?\s*[-–—]\s*\d+(?:\.\d+)?\s*(?:s|sec|seconds)?\s*:?\s*",
            "",
            segment.group(),
            flags=re.I,
        )
        if PRODUCTION.search(cleaned) and re.match(
            r"\s*(?:keep|camera|wide shot|close-up|tracking|static|pan|tilt|zoom)\b", cleaned, re.I
        ):
            start = segment.start() + len(segment.group()) - len(cleaned)
            cleaned = cleaned.rstrip()
            instructions.append(
                {
                    "classification": "CAMERA_INSTRUCTION",
                    "quote": cleaned,
                    "localSpan": [start, start + len(cleaned)],
                }
            )
    if not actor or actor.lower() == "unknown":
        return {
            "actions": [],
            "instructions": instructions,
            "classification": "UNKNOWN",
            "reason": "No source-established actor.",
        }
    subjects = rf"(?P<actor>{re.escape(actor)}|she|he|they)"
    prefix = r"(?P<intent>tries?\s+to\s+|attempts?\s+to\s+|continues?\s+to\s+|keeps?(?:\s+on)?\s+)?"
    pattern = re.compile(
        rf"\b{subjects}\s+(?:(?:has|have|is)\s+)?(?:just\s+)?{prefix}(?:\w+ly\s+)*(?P<verb>[a-z]+)\b", re.I
    )
    actions = []
    for match in pattern.finditer(content):
        root = ROOTS.get(match.group("verb").lower())
        if not root:
            continue
        # End at a clause boundary, retaining the exact source action (including bracket actions).
        tail = content[match.end() :]
        boundary = re.search(r";|\]|\[|->|[.!?](?:\s|$)", tail)
        end = match.end() + (boundary.start() if boundary else len(tail))
        while end > match.start() and content[end - 1].isspace():
            end -= 1
        quote = content[match.start() : end]
        intent = (match.group("intent") or "").strip()
        relation = (
            "EXPLICIT_INTENT_OR_CONTINUATION"
            if intent
            else "EXPLICIT_RECOVERY_OR_CONTROL"
            if RELATION.search(quote)
            else "STRUCTURED_ATTEMPT_ROLE"
            if role == "ATTEMPT"
            else None
        )
        actions.append(
            {
                "classification": "CHARACTER_ATTEMPT" if relation else "CHARACTER_ACTION",
                "actor": actor,
                "actorQuote": match.group("actor"),
                "actorLocalSpan": list(match.span("actor")),
                "action": quote,
                "localSpan": [match.start(), end],
                "primaryVerb": root,
                "verbQuote": match.group("verb"),
                "verbLocalSpan": list(match.span("verb")),
                "relationship": relation,
                "confidence": 0.9 if intent else 0.8 if relation else None,
                "semanticVerification": "NOT_PERFORMED",
            }
        )
    return {
        "actions": actions,
        "instructions": instructions,
        "classification": "CHARACTER_ATTEMPT"
        if any(a["classification"] == "CHARACTER_ATTEMPT" for a in actions)
        else "NOT_AN_ATTEMPT",
    }


def bind_beats(prompt: str, beats: list[dict[str, Any]], actor: str | None) -> None:
    seen: set[tuple[Any, ...]] = set()
    for beat in beats:
        quote, span = beat.get("sourceQuote"), beat.get("sourceSpan")
        valid = bool(
            isinstance(quote, str)
            and isinstance(span, list)
            and len(span) == 2
            and prompt[span[0] : span[1]] == quote
        )
        resolved = classify_content(quote or "", actor, beat.get("beatRole", ""))
        attempts = [a for a in resolved["actions"] if a["classification"] == "CHARACTER_ATTEMPT"]
        chosen = attempts[0] if valid and attempts else None
        key = (
            (
                beat.get("startTime"),
                beat.get("endTime"),
                actor,
                chosen["primaryVerb"],
                chosen["action"].lower(),
            )
            if chosen
            else None
        )
        duplicate = bool(key and key in seen)
        if key:
            seen.add(key)
        beat.update(
            isAttempt=bool(chosen and not duplicate),
            primaryVerb=chosen["primaryVerb"] if chosen and not duplicate else "",
            attemptSource="ACTOR_SOURCE_BOUND" if chosen and not duplicate else "NONE",
            attemptConfidence=chosen["confidence"] if chosen and not duplicate else None,
            attemptReason="Source-established actor, physical action and directed relationship."
            if chosen and not duplicate
            else None,
            attemptCandidate=None,
        )
        bound_actions = []
        for action in resolved["actions"]:
            item = dict(action)
            if valid:
                item["sourceSpan"] = [span[0] + v for v in action["localSpan"]]
                item["actorSourceSpan"] = [span[0] + v for v in action["actorLocalSpan"]]
                item["verbSourceSpan"] = [span[0] + v for v in action["verbLocalSpan"]]
            bound_actions.append(item)
        beat["characterActions"] = bound_actions
        beat["productionInstructions"] = [
            dict(i, sourceSpan=[span[0] + v for v in i["localSpan"]] if valid else None)
            for i in resolved["instructions"]
        ]
        beat["physicalConsequences"] = [
            {
                "classification": "PHYSICAL_CONSEQUENCE",
                "quote": m.group(1).strip(),
                "sourceSpan": [
                    span[0] + m.start(1),
                    span[0] + m.end(1) - (len(m.group(1)) - len(m.group(1).rstrip())),
                ]
                if valid
                else None,
            }
            for m in re.finditer(r"->\s*([^\[\]\n]+)", quote or "")
        ]
        for event in re.finditer(
            r"\b(?:the|a|an)\s+[^.;\[\]\n]{1,50}?\s+(?:splits?|doubles?|multiplies|flies|falls?|sticks?)\b[^.;\[\]\n]*",
            quote or "",
            re.I,
        ):
            raw = event.group()
            evidence = raw.rstrip()
            beat["physicalConsequences"].append(
                {
                    "classification": "PHYSICAL_CONSEQUENCE",
                    "quote": evidence,
                    "sourceSpan": [span[0] + event.start(), span[0] + event.start() + len(evidence)]
                    if valid
                    else None,
                    "method": "EXPLICIT_OBJECT_EVENT",
                    "semanticVerification": "NOT_PERFORMED",
                }
            )
        actor_reference = re.search(r"\b" + re.escape(actor or "") + r"\b", prompt, re.I) if actor else None
        beat["attemptEvidence"] = {
            "sourceQuote": chosen["action"] if chosen else None,
            "sourceSpan": [span[0] + v for v in chosen["localSpan"]] if chosen else None,
            "action": chosen["action"] if chosen else None,
            "primaryVerb": chosen["primaryVerb"] if chosen else None,
            "relationship": chosen["relationship"] if chosen else None,
            "actorReference": {
                "value": actor,
                "sourceQuote": actor_reference.group(),
                "sourceSpan": list(actor_reference.span()),
            }
            if actor_reference
            else None,
            "contractVersion": VERSION,
            "classification": "DUPLICATE_SOURCE_EVENT"
            if duplicate
            else "SOURCE_BOUND_ATTEMPT"
            if chosen
            else "UNKNOWN"
            if not valid
            else "NOT_AN_ATTEMPT",
            "sourceBound": valid,
            "actor": actor if chosen else None,
            "actions": bound_actions,
            "confidence": chosen["confidence"] if chosen else None,
            "duplicateSourceEvent": duplicate,
            "semanticVerification": "NOT_PERFORMED",
        }


def establish_actor(text: str) -> str | None:
    """Identify source-declared actors without matching CHARACTER REFERENCE as a name."""
    declaration = re.search(
        r"(?im)^[ \t]*(?:MAIN CHARACTER|CHARACTER(?:[ \t]*/[ \t]*CONTINUITY)?)[ \t]*(?::[ \t]*(?:\n[ \t]*)?|\n[ \t]*)([A-Z][a-zA-Z0-9_-]+)\b",
        text,
    )
    if declaration:
        return declaration.group(1).capitalize()
    reference = re.search(r"(?i:\b(?:do not redesign|preserve)\s+)([A-Z][A-Za-z0-9_-]+)\b", text)
    if reference:
        return reference.group(1).capitalize()
    reference = re.search(
        r"(?i:\b(?:official existing|existing))\s+([A-Z][A-Z0-9_-]+)\s+(?i:character reference)", text
    )
    return reference.group(1).capitalize() if reference else None
