"""Provider-neutral policy for cost-aware semantic analysis routing."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticModelSelection:
    provider: str
    model: str
    role: str
    reason: str


@dataclass(frozen=True)
class SemanticModelRoutingPolicy:
    mode: str
    fallback_enabled: bool
    primary: SemanticModelSelection
    fallback: SemanticModelSelection | None
    version: str = "semantic-model-routing-v1"

    @classmethod
    def from_environment(cls) -> "SemanticModelRoutingPolicy":
        provider = (os.getenv("POMPOM_SEMANTIC_PROVIDER") or os.getenv("DEFAULT_LLM_PROVIDER") or "openai").lower()
        primary = os.getenv("SEMANTIC_PRIMARY_MODEL") or os.getenv("OPENAI_VLM_MODEL") or "gpt-4o-mini"
        fallback = os.getenv("SEMANTIC_FALLBACK_MODEL") or os.getenv("OPENAI_VLM_MODEL") or "gpt-4o"
        mode = (os.getenv("SEMANTIC_ROUTING_MODE") or "PRIMARY_WITH_FALLBACK").upper()
        enabled = os.getenv("SEMANTIC_FALLBACK_ENABLED", "true").lower() == "true"
        fallback_selection = None
        if enabled and mode == "PRIMARY_WITH_FALLBACK" and fallback and fallback != primary:
            fallback_selection = SemanticModelSelection(provider, fallback, "FALLBACK", "PRIMARY_EVIDENCE_INSUFFICIENT")
        return cls(
            mode=mode,
            fallback_enabled=enabled,
            primary=SemanticModelSelection(provider, primary, "PRIMARY", "DEFAULT_PRIMARY_PASS"),
            fallback=fallback_selection,
        )
