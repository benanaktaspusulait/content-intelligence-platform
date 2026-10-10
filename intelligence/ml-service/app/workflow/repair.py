"""Bounded source patching; verification runs on the final request binding."""

from __future__ import annotations

import difflib
from copy import deepcopy
from typing import Any

from .review import review_prompt


def repair_prompt(
    request: dict[str, Any], patches: list[dict[str, Any]], capabilities: dict[str, Any] | None = None
) -> dict[str, Any]:
    if request.get("repairPasses", 0) != 0:
        raise ValueError("Normally only one repair pass is allowed; record a remaining defect first")
    if len(patches) > 3:
        raise ValueError("Use at most three local patches")
    if patches and not request.get("protectedIntent"):
        raise ValueError("Review protected creative intent before applying a patch")
    original = request["prompt"]
    if sum(patch["end"] - patch["start"] for patch in patches) > max(24, int(len(original) * 0.2)):
        raise ValueError("Repair exceeds the local patch budget; explicit intent review required")
    final = original
    previous = len(original) + 1
    for patch in sorted(patches, key=lambda item: item["start"], reverse=True):
        start, end, replacement = patch["start"], patch["end"], patch["replacement"]
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or not 0 <= start <= end <= len(original)
            or end > previous
            or not isinstance(replacement, str)
        ):
            raise ValueError("Invalid or overlapping source patch")
        if "sourceQuote" in patch and original[start:end] != patch["sourceQuote"]:
            raise ValueError("Repair source quote does not match the exact source span")
        final = final[:start] + replacement + final[end:]
        previous = start
    for protected in request.get("protectedIntent") or []:
        if protected not in original or protected not in final:
            raise ValueError(
                "Repair changes or invents protected creative intent; explicit intent review required"
            )
    for requirement in request.get("intentRequirements") or []:
        if requirement.get("level") == "ESSENTIAL":
            quote = requirement.get("sourceQuote")
            if not isinstance(quote, str) or not quote or quote not in original or quote not in final:
                raise ValueError(
                    "Repair changes explicit essential intent; "
                    "save a new version with an explicit intent decision"
                )
    for reference in request.get("references") or []:
        name = reference.get("character")
        if name and name.lower() in original.lower() and name.lower() not in final.lower():
            raise ValueError("Repair removes protected character identity")
    changed = deepcopy(request)
    changed["prompt"] = final
    result = review_prompt(changed, capabilities)
    result.update(
        originalPrompt=original,
        finalPrompt=final,
        patch=deepcopy(patches),
        repairPasses=1,
        verificationPasses=1,
        needsSavedPromptVersion=final != original,
        rationale="Local source patch; the final text was revalidated with the same profile/settings/references.",
        diff="".join(
            difflib.unified_diff(
                original.splitlines(True), final.splitlines(True), fromfile="original", tofile="final"
            )
        ),
    )
    return result
