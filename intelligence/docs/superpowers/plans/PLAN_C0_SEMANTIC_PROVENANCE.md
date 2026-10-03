# Plan C0 — Semantic Evaluation Provenance Threading

**Status: DESIGN ONLY. No code, YAML, or git mutations have been made as part of writing
this document.** A separate Kiro instance is concurrently modifying the exact files this
plan would touch (`app/llm/provider.py`, `app/api/quality.py`, `app/config.py`,
`app/rules/rule_engine.py`, `intelligence/data/rules/RULESET_1.*.yaml`) as part of closing
gaps from the broader audit. This document exists so that, once that work lands, it can be
compared against a concrete target design and classified per-requirement as
**DONE / PARTIAL / WRONG / MISSING** — not so implementation starts immediately from it.

**Do not implement from this document until the other instance's work has landed on
`master` and been reviewed against it.**

> **For agentic workers:** once cleared to implement, use
> superpowers:subagent-driven-development (recommended) or superpowers:executing-plans
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Before implementing
> ANY task below, re-read the current state of every file in "Files" — this document was
> written against a specific snapshot of the code (see "Snapshot basis" below) that will
> likely have changed.

**Goal:** every semantic-check-backed rule evaluation records which LLM provider and model
version actually produced its judgment — real per-check execution provenance, not a single
flat value assumed from static config — with no field fabricated to satisfy a gate it
doesn't honestly satisfy.

**Architecture:** `semantic_checks.py`'s 8 call sites each capture the `(provider, model)`
pair the specific `get_provider(...)` call actually returned, attach it to the
`RuleEvaluation` that call backs, and the report aggregates these into a
`semantic_evaluations` list — never a single collapsed pair unless every entry in that list
genuinely agrees.

**Tech Stack:** Python/FastAPI (ml-service), Java/Spring (backend DTO mirroring only, no
business logic).

## Snapshot basis

This design was written against:
- `intelligence/ml-service/app/llm/provider.py` as of commit `9c33773` (pre-parallel-work):
  `get_provider(name)` factory, each `<X>Provider.__init__` hardcodes its own default
  `model` string, no shared identity accessor exists.
- `intelligence/ml-service/app/llm/semantic_checks.py` as of `9c33773`: 8 functions
  (`find_duplicate_strategy_pairs`, `check_twist_matches_rule`, `count_independent_mechanics`,
  `check_goal_is_natural`, `check_rule_is_predictable`, `check_opening_problem_legible`,
  `check_character_performance_readable`, `check_attempts_are_generation_executable`), each
  calling `llm = get_provider(llm_provider)` then `_call_llm_safely(llm, prompt)`, returning
  only the parsed judgment, never provider/model identity.
- `intelligence/ml-service/app/rules/rule_engine.py` as of `9c33773`: 8 evaluators calling
  the above (`_evaluate_attempt_002`, `_evaluate_payoff_003`, `_evaluate_concept_007`,
  `_evaluate_goal_001`, `_evaluate_concept_008`, `_evaluate_hook_004`,
  `_evaluate_performance_001`, `_evaluate_generation_executable_attempts`), each with an
  `except SemanticCheckServiceError` returning a `RuleEvaluation(..., result="SERVICE_ERROR")`.
- `intelligence/ml-service/app/quality/contracts.py` as of `9c33773`: `RuleEvaluation` has
  no provenance field; `EnhancedQualityReport` has no `semantic_evaluations` field.
- Known in-flight parallel changes NOT yet reviewed against this design (discovered mid-session,
  uncommitted in the working tree at design-write time): `provider.py` gained a
  `get_provider_identity(name) -> tuple[str, str]` helper and `_DEFAULT_MODELS` dict;
  `quality.py` gained `QualityProvenanceResponse` (flat `semantic_provider`/
  `semantic_model_version`/`parser_version`/`rule_engine_version`/
  `producibility_validator_version`/`evaluation_stage` fields) and an `evaluation_stage`
  request field; `config.py` gained `parser_version`/`rule_engine_version`/
  `producibility_validator_version` settings; `rule_engine.py` and `RULESET_1.1/1.2/1.3.yaml`
  also showed uncommitted diffs not yet read in full. **This document's "Review Checklist"
  section (§5) is written specifically to evaluate that work once it lands.**

## Global Constraints

- Never fabricate a provenance value. If a real value cannot be determined (e.g. different
  rules used different providers and no single pair can honestly summarize that), the
  aggregate convenience field must be absent/null, not a guess.
- `producibilityValidatorVersion` must not be populated by this plan at all — Plan C1 (a
  separate, already-decided plan) removes this field from the required-evidence contract
  entirely, on the grounds that no independent "producibility validator" runtime exists;
  this plan must not reintroduce it as `deterministicRulesetVersion`'s alias or any other
  value. If the parallel instance's work populated it, that is a Plan C1 violation to flag,
  not a precedent to follow.
- Never touch `intelligence/data/rules/RULESET_1.3.yaml` for anything other than a pure
  metadata/documentation correction (e.g. a comment). Any change to rule *behavior* (new
  thresholds, new conditions, new fields consumed) must ship as a new `RULESET_1.4.yaml`
  version via the existing `RuleVersionManager.create_new_version()` path, never an in-place
  edit to 1.3. If the parallel instance edited 1.3's actual rule logic (not just comments),
  that is a global-constraint violation to flag during review, regardless of what the edit
  does.
- `evaluation_stage` (PRE_RENDER/POST_RENDER/BOTH) is explicitly **Plan D's** concept, not
  this plan's. If the parallel instance's work introduces an `evaluation_stage` field, this
  plan does not depend on it and must not assume stage-aware evaluator behavior exists yet
  — but if it exists correctly and consistently (single source of truth, not duplicated
  across YAML/engine/API), this plan should use it as a label on `semantic_evaluations`
  entries rather than fighting it, per the review checklist's stage-consistency check.
- Must leave the full ml-service test suite green and `ruff`/`mypy --strict` clean, and the
  Spring test suite green, exactly as every Plan A task did.

---

## 1. Target Data Model

### 1.1 `SemanticEvaluationProvenance` (new, `app/quality/contracts.py`)

```python
@dataclass(frozen=True)
class SemanticEvaluationProvenance:
    """Records which LLM provider/model actually produced a semantic-check
    judgment backing one or more rule evaluations.

    One instance per distinct (provider, model, semantic_check_version)
    combination actually used during a single evaluation run - if two
    different rules happen to use the same provider/model/check-version,
    they share one entry (rule_ids has two entries); if they differ, they
    get separate entries. This is deliberately NOT one entry per rule_id,
    so a report with 8 semantic-check-backed rules all using the same
    provider/model produces one entry, not eight duplicates.
    """

    provider: str
    model: str
    semantic_check_version: str
    rule_ids: tuple[str, ...]
```

**Why `rule_ids: tuple[str, ...]` and not a single `rule_id`:** today all 8 semantic-check
call sites use whatever `get_provider(None)` resolves to via `DEFAULT_LLM_PROVIDER`, so in
practice there will usually be exactly one `SemanticEvaluationProvenance` entry covering all
8 rule IDs in any given report. The list-of-rule-ids shape is what keeps that collapsing
correct automatically (one entry, many rule_ids) while still supporting the future case
where `GOAL_001` and `PERFORMANCE_001` genuinely use different providers (two entries, each
with its own `rule_ids`).

**`semantic_check_version`:** a new, independent version string — not `ruleset_version`,
not `deterministicRulesetVersion`. It identifies the version of the *prompt/scoring logic
inside `semantic_checks.py`* (e.g. the exact wording of the duplicate-strategy-pairs
prompt), which can change independently of the YAML ruleset. Starts at `"1.0"`. Lives as a
module-level constant in `semantic_checks.py`:

```python
SEMANTIC_CHECK_VERSION = "1.0"
```

Bump this constant by hand whenever a semantic-check prompt's wording changes meaningfully
(not on every unrelated commit) — this is a human judgment call documented in the module
docstring, the same way `ruleset_version` is a human-chosen string, not a hash.

### 1.2 `EnhancedQualityReport` gains one field

```python
@dataclass(frozen=True)
class EnhancedQualityReport:
    # ... existing fields unchanged ...
    semantic_evaluations: tuple[SemanticEvaluationProvenance, ...] = ()
```

Default `()` so every existing construction call site that doesn't pass this field keeps
working (same pattern as Plan A Task 5's `evidence_missing` addition to `ParserMetadata`).

### 1.3 `_call_llm_safely` and the 8 semantic-check functions return provenance too

Current shape (as of the snapshot basis):

```python
def find_duplicate_strategy_pairs(
    attempts: list[dict[str, str]], llm_provider: str | None = None
) -> list[tuple[int, int]]:
    ...
    llm = get_provider(llm_provider)
    ...
    response = _call_llm_safely(llm, prompt)
    ...
    return duplicate_pairs
```

Target shape — each function returns a `(result, provenance)` tuple instead of just
`result`:

```python
def find_duplicate_strategy_pairs(
    attempts: list[dict[str, str]], llm_provider: str | None = None
) -> tuple[list[tuple[int, int]], SemanticCheckProvenance]:
    ...
    llm = get_provider(llm_provider)
    ...
    response = _call_llm_safely(llm, prompt)
    ...
    return duplicate_pairs, SemanticCheckProvenance(provider=llm.provider_name, model=llm.model)
```

Where `SemanticCheckProvenance` (note: distinct from `SemanticEvaluationProvenance` in
`contracts.py` — this one is a lighter two-field carrier local to `semantic_checks.py`,
converted into the richer `rule_ids`-bearing one at the `rule_engine.py` call site, which is
the only place that knows which `rule_id` is asking):

```python
@dataclass(frozen=True)
class SemanticCheckProvenance:
    """Which provider/model backed one semantic-check function call.
    Converted into contracts.SemanticEvaluationProvenance by the calling
    rule_engine.py evaluator, which attaches the specific rule_id."""

    provider: str
    model: str
```

**This requires `LLMProvider` to expose a stable provider-name string**, which it does not
today — only `self.model` exists (e.g. `OpenAIProvider.model = "gpt-4o"`), and the
*provider* name (`"openai"`) is only known by `get_provider(name)`'s caller-supplied/env-var
string, not by the returned object itself. Add a `provider_name` property to the
`LLMProvider` ABC:

```python
class LLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short, stable identifier: 'openai', 'claude', 'gemini', or 'ollama'."""

    @abstractmethod
    def complete(self, ...) -> str: ...
```

Each concrete provider implements it trivially:

```python
class OpenAIProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "openai"
```

**Why not reuse the parallel instance's `get_provider_identity(name) -> tuple[str, str]`
helper (if it survives review) as the sole source of truth:** that helper computes
provider/model from the *requested name and env/config*, before any provider object is
even constructed — it tells you what *would be* used if you called `get_provider(name)`
right now, not what a *specific already-constructed* `llm` object you're holding actually
is. For this plan's purpose (recording what a specific call that already happened used),
reading `llm.provider_name`/`llm.model` off the object you already called `.complete()` on
is more direct and cannot drift from reality if, say, `get_provider_identity()` and
`get_provider()` are ever changed independently of each other. If the parallel instance's
`get_provider_identity()` is well-designed, it can remain as a useful *pre-call* convenience
(e.g. for the API's provenance response field before any check has even run), while
`llm.provider_name`/`llm.model` remains the authoritative *post-call* record — these are
different questions ("what would be used" vs. "what was used") and both can coexist. Confirm
during review which one the parallel instance chose and whether it's being used for the
right question.

### 1.4 `rule_engine.py` evaluators thread provenance into `RuleEvaluation`

`RuleEvaluation` (the `contracts.py` dataclass) does not need a new field for this — the
existing `details: dict[str, Any]` field already exists for exactly this kind of
per-evaluation extra data. Add it there:

```python
duplicate_pairs, provenance = find_duplicate_strategy_pairs(llm_attempts)
...
return RuleEvaluation(
    rule_id="ATTEMPT_002",
    ...,
    details={
        "tier": tier,
        "duplicate_pairs": duplicate_pairs,
        "semantic_provider": provenance.provider,
        "semantic_model": provenance.model,
    },
)
```

**And** the evaluator must also surface this to whatever assembles the report-level
`semantic_evaluations` list — `rule_engine.py`'s top-level `evaluate(...)` method (the one
that loops over all evaluators and builds the `QualityReport`) is the natural place to scan
all evaluations' `details` dicts for `semantic_provider`/`semantic_model` keys and
de-duplicate them into `SemanticEvaluationProvenance` entries, rather than each individual
evaluator trying to maintain a shared report-level list itself (evaluators are
independent/stateless by current design — don't break that).

### 1.5 API response (`app/api/quality.py`)

```python
class SemanticEvaluationProvenanceResponse(BaseModel):
    provider: str
    model: str
    semantic_check_version: str
    rule_ids: list[str]


class QualityReportResponse(BaseModel):
    # ... existing fields unchanged ...
    semantic_evaluations: list[SemanticEvaluationProvenanceResponse]
```

**Do not** add a flat `semantic_provider`/`semantic_model_version` pair directly to
`QualityReportResponse` in this plan. If the parallel instance's `QualityProvenanceResponse`
(flat shape) survives review as independently useful (e.g. a "what config says will be
used" summary distinct from "what was actually used per-rule"), that is a separate response
field this plan does not need to touch — but this plan's own deliverable is the honest
per-rule list, not a collapsed summary. A derived single-pair convenience value, if wanted,
belongs at the **Spring evidence-service layer** (per the roadmap's existing decision,
quoted in `PART_01_COMPLETION_ROADMAP.md` §1): computed only when every entry in
`semanticEvaluations` agrees, never fabricated when they don't.

### 1.6 Spring mirror (`DtoModels.java`, `QualityReportDto.java`)

```java
record SemanticEvaluationProvenanceDto(
    String provider,
    String model,
    String semanticCheckVersion,
    List<String> ruleIds) {}
```

Added to `QualityReportDto` as `List<SemanticEvaluationProvenanceDto> semanticEvaluations`.
Same mechanical pattern as Plan A's Task 8 — positional record, update both
`sampleReport()` test helpers, add a round-trip deserialization test.

---

## 2. Why not simpler alternatives

**Rejected: a single flat `semanticProvider`/`semanticModelVersion` string pair, computed
once per report from whatever `get_provider(None)` resolves to.** This is what the parallel
instance's `QualityProvenanceResponse` appears to do (`get_provider_identity()` called once
in `convert_quality_report`, independent of which specific rule evaluations actually ran a
semantic check). Rejected because:
1. It records what *would* be used by a hypothetical fresh call, not what each actual
   evaluator call used — if any evaluator passes an explicit `llm_provider` override (the
   function signatures already support this parameter, e.g.
   `find_duplicate_strategy_pairs(attempts, llm_provider="claude")`), the flat field would
   be wrong for that evaluation specifically.
2. It silently stays "correct-looking" even in a report where zero semantic checks actually
   ran (e.g. all evaluations short-circuited via early-return paths that never call
   `get_provider` at all, such as `ATTEMPT_002`'s `len(verb_distinct_attempts) < 2` branch) —
   the field would claim a provider/model was used when none was.
3. It cannot represent "two different rules used two different providers" at all, which the
   user explicitly flagged as a real future possibility to design for now, not discover
   later as a breaking change.

**Rejected: tagging each `RuleEvaluation.details` with provenance and stopping there (no
report-level `semantic_evaluations` aggregate).** Rejected because `ValidationEvidenceService`
(Spring) needs a single clear place to read "the semantic provenance for this validation,"
and reconstructing that by scanning every rule's `details` dict for magic string keys from
Java would be fragile and untyped. The aggregate list is a real, intentional contract
surface, not a convenience cache.

---

## 3. File Structure

- Modify: `intelligence/ml-service/app/llm/provider.py` — add `provider_name` abstract
  property to `LLMProvider`, implement in all 4 concrete providers.
- Modify: `intelligence/ml-service/app/llm/semantic_checks.py` — add module-level
  `SEMANTIC_CHECK_VERSION` constant and `SemanticCheckProvenance` dataclass; change all 8
  public functions' return types to include provenance.
- Modify: `intelligence/ml-service/app/rules/rule_engine.py` — update all 8 call sites to
  unpack `(result, provenance)` and attach to `details`; update top-level `evaluate(...)` to
  aggregate `details`-embedded provenance into `semantic_evaluations` on the `QualityReport`
  (or `EnhancedQualityReport`, whichever layer already owns report assembly — confirm exact
  insertion point by reading the current `evaluate`/`create_enhanced_report` split before
  implementing).
- Modify: `intelligence/ml-service/app/quality/contracts.py` — add
  `SemanticEvaluationProvenance` dataclass; add `semantic_evaluations` field to
  `EnhancedQualityReport`.
- Modify: `intelligence/ml-service/app/api/quality.py` — add
  `SemanticEvaluationProvenanceResponse`; add `semantic_evaluations` field to
  `QualityReportResponse`; populate in `convert_quality_report`.
- Modify: `intelligence/backend/.../quality/DtoModels.java` — add
  `SemanticEvaluationProvenanceDto` record.
- Modify: `intelligence/backend/.../quality/QualityReportDto.java` — add
  `semanticEvaluations` field.
- Test: `intelligence/ml-service/tests/test_semantic_checks.py` — provenance returned
  correctly per function.
- Test: `intelligence/ml-service/tests/test_rule_engine_*.py` — provenance threaded into
  `details` and aggregated correctly, including the "zero semantic checks ran" case
  (aggregate list is empty, not fabricated) and the "two evaluators, same provider" case
  (one aggregate entry, two `rule_ids`).
- Test: `intelligence/ml-service/tests/test_api_conversions.py` — `semantic_evaluations`
  round-trips onto the response.
- Test: `intelligence/backend/.../QualityReportDtoTest.java` — Jackson round-trip for the
  new nested DTO.

---

## 4. Task Breakdown (do not execute until cleared per §0/§5)

### Task 1: Add `provider_name` to `LLMProvider` and all 4 concrete providers

**Files:**
- Modify: `intelligence/ml-service/app/llm/provider.py`
- Modify: `intelligence/ml-service/app/llm/openai_provider.py`, `claude_provider.py`,
  `gemini_provider.py`, `ollama_provider.py`
- Test: `intelligence/ml-service/tests/test_llm_providers.py` (confirm this file's current
  name/location before writing — read it first)

**Interfaces:**
- Produces: `LLMProvider.provider_name: str` (abstract property), returning `"openai"`,
  `"claude"`, `"gemini"`, `"ollama"` respectively.

- [ ] **Step 1: Write the failing test**

Read the current `tests/test_llm_providers.py` in full first to match its existing
construction/mocking conventions for each provider class. Append:

```python
def test_openai_provider_exposes_provider_name() -> None:
    provider = OpenAIProvider(api_key="fake-key-for-test")
    assert provider.provider_name == "openai"


def test_claude_provider_exposes_provider_name() -> None:
    provider = ClaudeProvider(api_key="fake-key-for-test")
    assert provider.provider_name == "claude"


def test_gemini_provider_exposes_provider_name() -> None:
    provider = GeminiProvider(api_key="fake-key-for-test")
    assert provider.provider_name == "gemini"


def test_ollama_provider_exposes_provider_name() -> None:
    provider = OllamaProvider()
    assert provider.provider_name == "ollama"
```

(Adjust constructor arguments to match each provider's actual current `__init__` signature
— read each file first, do not assume identical signatures.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_llm_providers.py -k "provider_name" -v`

Expected: FAIL with `AttributeError: 'OpenAIProvider' object has no attribute 'provider_name'`.

- [ ] **Step 3: Add the abstract property to `LLMProvider`**

In `provider.py`:

```python
class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short, stable provider identifier used for provenance records
        (e.g. 'openai', 'claude', 'gemini', 'ollama'). Must match the name
        get_provider() accepts for this provider, so provenance recorded
        from a returned instance can be fed back into get_provider() later
        to reconstruct an equivalent provider."""

    @abstractmethod
    def complete(
        self, prompt: str, system: str = "", temperature: float = 0.7, image: str | None = None
    ) -> str:
        ...  # unchanged
```

- [ ] **Step 4: Implement in each concrete provider**

In `openai_provider.py`:

```python
class OpenAIProvider(LLMProvider):
    """OpenAI GPT-4o provider."""

    @property
    def provider_name(self) -> str:
        return "openai"

    def __init__(self, ...):  # unchanged
        ...
```

Same pattern for `claude_provider.py` (`"claude"`), `gemini_provider.py` (`"gemini"`),
`ollama_provider.py` (`"ollama"`) — read each file's current class body first and insert the
property in a sensible place (immediately after the class docstring, before `__init__`, to
match a consistent position across all 4 files).

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_llm_providers.py -v`

Expected: all PASS, including every pre-existing test in the file.

- [ ] **Step 6: Run full suite + lint/type**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest -q && ruff check . && ruff format --check . && mypy --strict app`

- [ ] **Step 7: Commit**

```bash
git add intelligence/ml-service/app/llm/provider.py intelligence/ml-service/app/llm/openai_provider.py intelligence/ml-service/app/llm/claude_provider.py intelligence/ml-service/app/llm/gemini_provider.py intelligence/ml-service/app/llm/ollama_provider.py intelligence/ml-service/tests/test_llm_providers.py
git commit -m "feat(intelligence): add provider_name identity to LLMProvider for provenance tracking"
```

### Task 2: `SemanticCheckProvenance` + `SEMANTIC_CHECK_VERSION`, threaded through all 8 semantic-check functions

**Files:**
- Modify: `intelligence/ml-service/app/llm/semantic_checks.py`
- Test: `intelligence/ml-service/tests/test_semantic_checks.py`

**Interfaces:**
- Consumes: `LLMProvider.provider_name` (Task 1).
- Produces: `SemanticCheckProvenance(provider: str, model: str)`; all 8 public functions'
  return types change from `T` to `tuple[T, SemanticCheckProvenance]`.

- [ ] **Step 1: Write the failing tests**

Read the current full signatures and return statements of all 8 functions first (do not
assume the snapshot in §0 is still accurate — re-verify with
`grep -n "^def \|^    return" app/llm/semantic_checks.py`). Append a representative set
covering at least 2 of the 8 (the others follow the identical pattern):

```python
def test_find_duplicate_strategy_pairs_returns_provenance() -> None:
    mock_llm = Mock()
    mock_llm.provider_name = "openai"
    mock_llm.model = "gpt-4o"
    mock_llm.complete.return_value = '{"duplicate_pairs": []}'

    with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
        pairs, provenance = find_duplicate_strategy_pairs(
            [
                {"primaryVerb": "PUSH", "action": "a", "consequence": "b"},
                {"primaryVerb": "PULL", "action": "c", "consequence": "d"},
            ]
        )

    assert pairs == []
    assert provenance.provider == "openai"
    assert provenance.model == "gpt-4o"


def test_find_duplicate_strategy_pairs_with_fewer_than_2_attempts_has_no_provenance() -> None:
    """When the function short-circuits before calling the LLM at all (the
    existing `len(attempts) < 2` early return), there is no real provenance
    to report -- the caller must not fabricate one."""
    pairs, provenance = find_duplicate_strategy_pairs([])
    assert pairs == []
    assert provenance is None


def test_check_twist_matches_rule_returns_provenance() -> None:
    mock_llm = Mock()
    mock_llm.provider_name = "claude"
    mock_llm.model = "claude-3-5-sonnet-20241022"
    mock_llm.complete.return_value = '{"matches": true, "reasoning": "ok"}'

    with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
        matches, reasoning, provenance = check_twist_matches_rule(
            physical_rule="rule", twist_description="twist"
        )

    assert matches is True
    assert provenance.provider == "claude"
    assert provenance.model == "claude-3-5-sonnet-20241022"
```

(Read each function's exact current return shape before writing its test —
`check_twist_matches_rule` returns a `(bool, str)` tuple today per the earlier investigation;
confirm whether this becomes a 3-tuple `(bool, str, provenance)` or a 2-tuple
`((bool, str), provenance)` and apply that choice consistently across all 8 — this plan
recommends appending provenance as the **last** element of a flattened tuple, e.g.
`(matches, reasoning, provenance)`, not nesting the original return value, since that is
the smallest change to every existing call site's unpacking.)

- [ ] **Step 2: Run to verify they fail**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_semantic_checks.py -k "provenance" -v`

Expected: FAIL (`ValueError: too many values to unpack` or `AttributeError`, depending on
current return shape).

- [ ] **Step 3: Add `SemanticCheckProvenance` and `SEMANTIC_CHECK_VERSION`**

At the top of `semantic_checks.py`, after the module docstring and before
`SemanticCheckServiceError`:

```python
from dataclasses import dataclass

# Bump by hand whenever a semantic-check prompt's wording changes meaningfully
# enough that past evaluations under the old wording should be considered a
# different check version for provenance/audit purposes. Not tied to
# ruleset_version or deterministicRulesetVersion -- this versions the
# LLM-prompt logic in this module specifically.
SEMANTIC_CHECK_VERSION = "1.0"


@dataclass(frozen=True)
class SemanticCheckProvenance:
    """Which provider/model backed one semantic-check function call."""

    provider: str
    model: str
```

- [ ] **Step 4: Update each of the 8 functions to return provenance**

For `find_duplicate_strategy_pairs` (the short-circuit case first):

```python
def find_duplicate_strategy_pairs(
    attempts: list[dict[str, str]], llm_provider: str | None = None
) -> tuple[list[tuple[int, int]], SemanticCheckProvenance | None]:
    """... (existing docstring, append:) Returns (pairs, provenance); provenance
    is None when 0 or 1 attempts are given (nothing to compare, no LLM call made)."""
    if len(attempts) < 2:
        return [], None

    try:
        llm = get_provider(llm_provider)
    except ValueError as e:
        raise SemanticCheckServiceError(f"LLM provider unavailable: {e}") from e

    provenance = SemanticCheckProvenance(provider=llm.provider_name, model=llm.model)

    # ... existing prompt-building and _call_llm_safely(llm, prompt) call, unchanged ...

    # at every existing `return <value>` in the rest of this function, change to:
    return <value>, provenance
```

Apply the identical pattern (capture `provenance` right after `get_provider(...)` succeeds,
append it to every return statement in the rest of the function body) to the remaining 7
functions: `check_twist_matches_rule`, `count_independent_mechanics`,
`check_goal_is_natural`, `check_rule_is_predictable`, `check_opening_problem_legible`,
`check_character_performance_readable`, `check_attempts_are_generation_executable`. Read
each function's full current body before editing — some may have more than one `return`
statement (e.g. an early return for an empty input list, matching
`find_duplicate_strategy_pairs`'s pattern) and every one of them must be updated, including
early returns, which get `None` for provenance exactly like the short-circuit case.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_semantic_checks.py -v`

Expected: all PASS. **This step will also break every existing caller in `rule_engine.py`**
(their unpacking assumes the old return shape) — this is expected and intentional; Task 3
fixes those call sites. Do not attempt to make `rule_engine.py`'s tests pass as part of this
task; confirm via `python -m pytest tests/test_semantic_checks.py -v` specifically (not the
full suite) that this task's own scope is green before moving on.

- [ ] **Step 6: Run ruff/mypy on just this file**

Run: `cd intelligence/ml-service && source .venv/bin/activate && ruff check app/llm/semantic_checks.py tests/test_semantic_checks.py && ruff format --check app/llm/semantic_checks.py tests/test_semantic_checks.py && mypy --strict app/llm/semantic_checks.py`

(The full-suite `mypy --strict app` will fail at this point because `rule_engine.py` hasn't
been updated yet — that's expected; Task 3 fixes it. Scope this check to just the files this
task touches.)

- [ ] **Step 7: Commit**

```bash
git add intelligence/ml-service/app/llm/semantic_checks.py intelligence/ml-service/tests/test_semantic_checks.py
git commit -m "feat(intelligence): semantic check functions return provider/model provenance"
```

(This commit will leave `rule_engine.py` broken against the new signatures until Task 3's
commit — acceptable within this plan's sequencing, but means Task 2 and Task 3 should be
executed back-to-back in the same session without leaving the repo in this intermediate
state for long, and the full-suite green check only re-applies starting at Task 3's Step 6.)

### Task 3: Update all 8 `rule_engine.py` call sites + aggregate `semantic_evaluations`

**Files:**
- Modify: `intelligence/ml-service/app/rules/rule_engine.py`
- Modify: `intelligence/ml-service/app/quality/contracts.py`
- Test: `intelligence/ml-service/tests/test_rule_engine_contract.py` (or wherever the
  top-level `evaluate(...)`/report-assembly tests live — confirm exact file first)

**Interfaces:**
- Consumes: `SemanticCheckProvenance` (Task 2), unpacked at each of the 8 call sites.
- Produces: `SemanticEvaluationProvenance` (new, in `contracts.py`); `QualityReport` (or
  `EnhancedQualityReport` — confirm exact insertion point, see Step 3 below) gains
  `semantic_evaluations: tuple[SemanticEvaluationProvenance, ...]`.

- [ ] **Step 1: Write the failing test for the aggregation behavior**

Read the current full `evaluate(...)` method and whichever report-assembly test file
exercises it end-to-end (not a single evaluator in isolation) first. Append:

```python
def test_semantic_evaluations_aggregates_shared_provider_into_one_entry() -> None:
    """Two different semantic-check-backed rules using the same provider/model
    must produce ONE SemanticEvaluationProvenance entry with both rule_ids,
    not two duplicate entries."""
    # Construct an IR that triggers both ATTEMPT_002's semantic check (>=2
    # verb-distinct attempts) and PAYOFF_003's semantic check (a twist beat
    # present) -- read _minimal_ir/_engine test helpers for the exact shape
    # already used elsewhere in this test file.
    engine = _engine()
    ir = _ir_triggering_both_attempt_002_and_payoff_003_semantic_checks()  # build per existing fixture conventions

    with patch(
        "app.rules.rule_engine.find_duplicate_strategy_pairs",
        return_value=([], SemanticCheckProvenance(provider="openai", model="gpt-4o")),
    ), patch(
        "app.rules.rule_engine.check_twist_matches_rule",
        return_value=(True, "consistent", SemanticCheckProvenance(provider="openai", model="gpt-4o")),
    ):
        report = engine.evaluate(ir)

    assert len(report.semantic_evaluations) == 1
    entry = report.semantic_evaluations[0]
    assert entry.provider == "openai"
    assert entry.model == "gpt-4o"
    assert set(entry.rule_ids) == {"ATTEMPT_002", "PAYOFF_003"}
    assert entry.semantic_check_version == SEMANTIC_CHECK_VERSION


def test_semantic_evaluations_empty_when_no_semantic_check_actually_ran() -> None:
    """A report where every semantic-check-backed evaluator short-circuited
    (e.g. too few attempts for ATTEMPT_002's dedup check) must have an EMPTY
    semantic_evaluations list, not a fabricated entry."""
    engine = _engine()
    ir = _minimal_ir(beats=[])  # no attempts, no twist beat -- adjust per actual short-circuit conditions
    report = engine.evaluate(ir)
    assert report.semantic_evaluations == ()
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_rule_engine_contract.py -k "semantic_evaluations" -v`

Expected: FAIL — the attribute doesn't exist yet, and the 8 call sites still unpack the
old 1-value return shape (this test run will likely also surface the Task 2 breakage
mentioned above; that's expected until this task's Step 4 is done).

- [ ] **Step 3: Add `SemanticEvaluationProvenance` to `contracts.py` and the field to the report**

Read `QualityReport` and `EnhancedQualityReport` in `contracts.py` in full first (both shown
in full in this plan's investigation phase) to decide definitively which one owns this field
— the recommendation is `QualityReport` (the base report, since `semantic_evaluations` is
evaluation-time data, not scoring-time data, matching where `evaluations` itself lives), but
confirm `evaluate(...)`'s actual return type matches before committing to that choice:

```python
@dataclass(frozen=True)
class SemanticEvaluationProvenance:
    """Records which LLM provider/model backed one or more rule evaluations'
    semantic checks during a single evaluation run."""

    provider: str
    model: str
    semantic_check_version: str
    rule_ids: tuple[str, ...]


@dataclass(frozen=True)
class QualityReport:
    # ... existing fields unchanged ...
    semantic_evaluations: tuple[SemanticEvaluationProvenance, ...] = ()
```

- [ ] **Step 4: Update all 8 call sites in `rule_engine.py` to unpack provenance**

For `_evaluate_attempt_002` (and identically for the other 7 — read each one's exact current
unpacking before editing):

```python
if len(verb_distinct_attempts) >= 2:
    llm_attempts = [...]
    try:
        duplicate_pairs, provenance = find_duplicate_strategy_pairs(llm_attempts)
    except SemanticCheckServiceError as e:
        return RuleEvaluation(
            rule_id="ATTEMPT_002",
            ...,
            result="SERVICE_ERROR",
            message=f"Semantic duplicate-strategy check failed: {e}",
            details={"error": str(e)},
        )
else:
    duplicate_pairs, provenance = [], None
```

Then thread `provenance` into the `details` dict of whichever `RuleEvaluation` this
evaluator ultimately returns (both the FAIL and PASS branches, not just one):

```python
details={
    "tier": tier,
    "duplicate_pairs": duplicate_pairs,
    **({"semantic_provider": provenance.provider, "semantic_model": provenance.model}
       if provenance is not None else {}),
},
```

- [ ] **Step 5: Add the aggregation logic to `evaluate(...)`**

Read the current `evaluate(...)` method's loop over evaluators in full first. After
building the full list of `RuleEvaluation`s (whatever local variable currently holds them
before being passed into `QualityReport(...)`), add:

```python
def _aggregate_semantic_evaluations(
    evaluations: list[RuleEvaluationType],
) -> tuple[SemanticEvaluationProvenance, ...]:
    """Collapse per-evaluation semantic_provider/semantic_model details into
    deduplicated SemanticEvaluationProvenance entries, one per distinct
    (provider, model) pair actually used. Evaluations with no semantic
    provider/model in their details (deterministic rules, or semantic rules
    that short-circuited without calling an LLM) contribute nothing."""
    grouped: dict[tuple[str, str], list[str]] = {}
    for ev in evaluations:
        provider = ev.details.get("semantic_provider")
        model = ev.details.get("semantic_model")
        if provider is None or model is None:
            continue
        grouped.setdefault((provider, model), []).append(ev.rule_id)
    return tuple(
        SemanticEvaluationProvenance(
            provider=provider,
            model=model,
            semantic_check_version=SEMANTIC_CHECK_VERSION,
            rule_ids=tuple(rule_ids),
        )
        for (provider, model), rule_ids in grouped.items()
    )
```

(Import `SEMANTIC_CHECK_VERSION` from `app.llm.semantic_checks` at the top of
`rule_engine.py` — it is already importing other names from that module per the existing
`from app.llm.semantic_checks import (...)` block; add it there.)

Then in `evaluate(...)`, pass the result into `QualityReport(...)`'s construction:

```python
return QualityReport(
    # ... existing fields ...
    semantic_evaluations=_aggregate_semantic_evaluations(evaluations),
)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_rule_engine_contract.py tests/test_semantic_checks.py tests/test_rule_engine_new_rules.py -v`

Expected: all PASS.

- [ ] **Step 7: Run full suite + lint/type**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest -q && ruff check . && ruff format --check . && mypy --strict app`

Expected: all green. This is the first point since Task 2 where the full suite must be
green again.

- [ ] **Step 8: Commit**

```bash
git add intelligence/ml-service/app/rules/rule_engine.py intelligence/ml-service/app/quality/contracts.py intelligence/ml-service/tests/test_rule_engine_contract.py
git commit -m "feat(intelligence): aggregate semantic-check provenance into QualityReport.semantic_evaluations"
```

### Task 4: Expose `semantic_evaluations` on the API response

**Files:**
- Modify: `intelligence/ml-service/app/api/quality.py`
- Test: `intelligence/ml-service/tests/test_api_conversions.py`

**Interfaces:**
- Consumes: `QualityReport.semantic_evaluations` (Task 3), reachable via
  `enhanced.base_report.semantic_evaluations` (confirm this exact access path once Task 3's
  implementation is final — `EnhancedQualityReport` wraps `base_report`, per contracts.py).
- Produces: `SemanticEvaluationProvenanceResponse`; `semantic_evaluations` field on
  `QualityReportResponse`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_api_conversions.py` (read its current imports/helpers first):

```python
def test_convert_quality_report_exposes_semantic_evaluations() -> None:
    parsed = parse_prompt(SAMPLE_PROMPT)  # or whatever fixture this file already uses
    report = RuleEngine(RULESET).evaluate(parsed.video_plan_ir)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)

    response = convert_quality_report(enhanced, "1.0")

    assert isinstance(response.semantic_evaluations, list)
    # Exact content depends on SAMPLE_PROMPT's fixture content and whether it
    # triggers any semantic-check-backed rule -- if it does not, this list is
    # legitimately empty; assert on whatever is actually true for this fixture
    # rather than assuming non-empty.
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_api_conversions.py -k "semantic_evaluations" -v`

Expected: FAIL with `AttributeError: 'QualityReportResponse' object has no attribute 'semantic_evaluations'`.

- [ ] **Step 3: Add the response model and field**

In `quality.py`, near the other response models:

```python
class SemanticEvaluationProvenanceResponse(BaseModel):
    provider: str
    model: str
    semantic_check_version: str
    rule_ids: list[str]


class QualityReportResponse(BaseModel):
    # ... existing fields ...
    semantic_evaluations: list[SemanticEvaluationProvenanceResponse]
```

In `convert_quality_report`:

```python
return QualityReportResponse(
    # ... existing fields ...
    semantic_evaluations=[
        SemanticEvaluationProvenanceResponse(
            provider=item.provider,
            model=item.model,
            semantic_check_version=item.semantic_check_version,
            rule_ids=list(item.rule_ids),
        )
        for item in report.semantic_evaluations
    ],
)
```

(Confirm whether `report` in this function's current body refers to `enhanced.base_report`
or something else — read the function's current full body before inserting, matching its
existing variable name for the base report.)

- [ ] **Step 4: Run tests, full suite, lint/type**

Run the test file, then the full-suite command from prior tasks' Step 7.

- [ ] **Step 5: Commit**

```bash
git add intelligence/ml-service/app/api/quality.py intelligence/ml-service/tests/test_api_conversions.py
git commit -m "feat(intelligence): expose semantic_evaluations on the quality validate API response"
```

### Task 5: Mirror onto Spring `QualityReportDto`

**Files:**
- Modify: `intelligence/backend/.../quality/DtoModels.java`
- Modify: `intelligence/backend/.../quality/QualityReportDto.java`
- Modify: both `sampleReport()` test helpers (per Plan A Task 8's precedent — grep for
  `new QualityReportDto(` across `src/test` too, not just `src/main`, learning from Task 8's
  own self-reported brief gap)
- Test: `QualityReportDtoTest.java`

**Interfaces:**
- Consumes: the Python `semantic_evaluations` JSON field (Task 4).
- Produces: `SemanticEvaluationProvenanceDto`; `semanticEvaluations` field on
  `QualityReportDto`.

- [ ] **Step 1: Write the failing test**

Append to `QualityReportDtoTest.java` (read its current content and `ObjectMapper`
construction convention first):

```java
@Test
void deserializesSemanticEvaluationsFromPythonSnakeCaseResponse() throws Exception {
  ObjectMapper mapper = new ObjectMapper();
  mapper.setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);

  String json =
      """
      { ... existing full QualityReportDto JSON fixture from the prior test ...,
        "semantic_evaluations": [
          {"provider": "openai", "model": "gpt-4o", "semantic_check_version": "1.0",
           "rule_ids": ["ATTEMPT_002", "PAYOFF_003"]}
        ]
      }
      """;

  QualityReportDto dto = mapper.readValue(json, QualityReportDto.class);

  assertThat(dto.semanticEvaluations()).hasSize(1);
  assertThat(dto.semanticEvaluations().get(0).provider()).isEqualTo("openai");
  assertThat(dto.semanticEvaluations().get(0).ruleIds()).containsExactly("ATTEMPT_002", "PAYOFF_003");
}
```

(Build the full JSON fixture by copying the existing test's fixture and adding this one key
— do not write a partial fixture, since `QualityReportDto` requires every field.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=QualityReportDtoTest`

Expected: compilation failure, `cannot find symbol: method semanticEvaluations()`.

- [ ] **Step 3: Add the DTO record and field**

In `DtoModels.java`:

```java
record SemanticEvaluationProvenanceDto(
    String provider, String model, String semanticCheckVersion, List<String> ruleIds) {}
```

In `QualityReportDto.java`, add `List<SemanticEvaluationProvenanceDto> semanticEvaluations`
as a new field (document in the Javadoc, same style as the other 9 fields Plan A's Task 8
added), in a sensible position (immediately after `evidenceMissing`, as the newest
addition).

- [ ] **Step 4: Fix the two `sampleReport()` test helpers**

Per Plan A Task 8's self-reported finding, the brief's own grep scope (`src/main` only)
missed `src/test` call sites — this task's own grep must cover both:

Run: `grep -rln "new QualityReportDto(" intelligence/backend/src/main intelligence/backend/src/test intelligence/creative-render-service/src/main intelligence/creative-render-service/src/test`

Update every positional constructor call found to pass `List.of()` (or a populated list, for
whichever test specifically wants to assert on it) for the new field, in the correct
position matching the record's field order.

- [ ] **Step 5: Run the targeted test, then the full Java suite**

Run: `cd intelligence/backend && mvn test -Dtest=QualityReportDtoTest` then
`cd intelligence/backend && mvn test`.

Expected: all green, including the previously-passing 62 tests from Plan A.

- [ ] **Step 6: Commit**

```bash
git add intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/DtoModels.java intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityReportDto.java intelligence/backend/src/test/java/com/pompomhills/intelligence/quality/QualityReportDtoTest.java
# plus any other test files Step 4 touched
git commit -m "feat(intelligence): mirror semanticEvaluations provenance list onto Spring QualityReportDto"
```

---

## 5. Review Checklist — apply once the parallel instance's work lands

Before resuming any work on this plan, read the parallel instance's actual landed diff
(not just the uncommitted snapshot seen at design time) and classify each row below.

| # | Requirement | DONE / PARTIAL / WRONG / MISSING | Evidence (file:line) | Action if not DONE |
|---|---|---|---|---|
| 1 | Provenance reflects what a **specific executed call** used, not what config/env *would* resolve to right now | | | If WRONG (flat config-derived value): keep the honest per-call model from this plan; do not adopt the shortcut. |
| 2 | Per-rule-ID granularity exists somewhere (even if collapsed into one entry when all rules share a provider) | | | If MISSING: implement Task 2-3's `rule_ids`-bearing aggregation. |
| 3 | A report where **zero** semantic checks actually ran produces an **empty** semantic-evaluations list, not a fabricated entry | | | If WRONG: this is a correctness bug (claims a provider was used when none was) — fix before anything else, highest priority. |
| 4 | `producibilityValidatorVersion` is NOT populated by any new code (per Plan C1's decision that no such runtime exists) | | | If a value was added (even `deterministicRulesetVersion`'s value): revert that specific population; defer entirely to Plan C1's removal-from-contract approach. Flag explicitly to the user — this is the single most likely point of disagreement with the parallel instance's work, since "populate the gate" is an intuitive-but-wrong fix for a missing-evidence gate. |
| 5 | `RULESET_1.3.yaml` changes, if any, are metadata/comment-only — no rule *behavior* change in-place | | | If a behavior change was made in-place: this is a global-constraint violation independent of this plan; flag to the user before writing any new code, do not silently work around it by also editing 1.3. |
| 6 | `evaluation_stage` (if introduced) has a single source of truth, not duplicated across YAML/engine/API/config | | | If duplicated: flag as a Plan D-scope issue; do not let this plan's work add a 4th copy. If this plan ends up needing stage info, read from whichever the single source of truth turns out to be. |
| 7 | The provider/model data this plan needs (`LLMProvider.provider_name` or equivalent) exists in a usable form | | | If the parallel work added an equivalent (e.g. `get_provider_identity`), confirm it answers "what was used by this specific call" vs. "what would be used right now" — see §1.3's distinction — and adapt Task 1 to reuse it if it genuinely answers the right question, instead of adding a second parallel mechanism. |
| 8 | Spring-side mirroring (if any was done) follows Plan A's established record/field-mirroring conventions (positional record, `src/test` call sites updated too) | | | If `src/test` call sites were missed (per Plan A Task 8's own documented near-miss): fix before this plan's Task 5 adds yet another field to the same broken call sites. |
| 9 | Full ml-service test suite green, `ruff`/`mypy --strict` clean, after the parallel instance's work | | | If not green: this blocks starting this plan's Task 1 at all — fix or request fix first. |
| 10 | Full Java test suite green after the parallel instance's work | | | Same as above. |

**Do not proceed past this checklist with any row marked WRONG until that row's "Action" is
resolved and re-verified** — a WRONG classification (not just MISSING) means code already
exists that this plan's own implementation would otherwise conflict with or duplicate.
