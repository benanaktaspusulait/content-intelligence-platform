# ADR — Pre-render quality evidence and grade qualification

Status: PROPOSED / INACTIVE. No new rubric, score, threshold or waiver is approved or activated.

## Problem and measured evidence

Ruleset 1.11 canonical A starts at 92. Several successful rules retain configured BLOCKER/CRITICAL severity and receive 85 row points. Partial families contribute numerically while absent evidence stays excluded. Current Mimi has two protected attempts, a fixed-evidence optimistic ceiling 89.3125/B and absent visual/semantic evidence. An ATTEMPT_001 admission exception does not alter these numbers.

The current reconstruction producer reports `sourceEventCoverage.semanticFidelity=UNKNOWN` after preserving exact source narratives. The V3 qualifier refuses to turn that UNKNOWN into the independent semantic PASS required for a fully qualified final candidate. Hypothetical policy fixtures can exercise A routing but do not demonstrate an actual fully qualified A candidate through this producer. A complete approved golden case is needed to close that acceptance gap.

## Proposed decision to review

Keep the authoritative canonical score and all historical Ruleset 1.7–1.11 records unchanged. First specify the exact scope of prompt-only target qualification and the independent evidence required for source fidelity. Reuse existing authenticated, scoped, persisted validation evidence contracts if they can support this judgment. Do not trust a generator's self-certification, a frontend field, numeric grade, reference IDs alone or server-authored choreography.

If the architecture requires a separate pre-render prompt-quality assessment, govern it independently. Define the six existing dimensions, applicable evidence, unknown states and limits of textual assessment. Do not invent an A/A+ threshold for Mimi. Use representative approved golden stories across profiles, including legitimately improvable and unimprovable cases; blinded human comparison and independent review; calibration and held-out regression cases; repeatability and disagreement analysis. Approve versioned thresholds only after that evidence exists.

Keep prompt-text acceptance, a rule-specific exception, production-risk acknowledgement, evidence preparation, canonical grading and F8/render admission independent. Textual qualification must never grant image/video generation permission. Visual and audience effects remain unknown until separately evidenced.

## Activation conditions

An authenticated architecture decision must settle scope and evidence requirements; a versioned contract and calibration set must be approved; producer/consumer and full application golden tests must demonstrate a legitimate B→A path without changing protected events, inventing evidence or altering existing canonical semantics. Existing records remain immutable. No paid test, prompt revision, exception or render is authorized by this draft.
