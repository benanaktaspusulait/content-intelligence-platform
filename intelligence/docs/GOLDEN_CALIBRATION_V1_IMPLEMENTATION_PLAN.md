# POMPOM GOLDEN CALIBRATION V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Freeze the approved nine real prompt artifacts, capture the current v1.7 behavior, and add a deterministic Golden Truth versus policy-aware regression gate without changing Prompt Intelligence behavior.

**Architecture:** Add a manifest-driven calibration harness beside the existing parser/canonical-evidence/RuleEngine/scorer pipeline. The harness passes only frozen prompt text into the existing pipeline, keeps `corpusRole` outside engine input, stores independently authored Gold Truth separately from ruleset-scoped Policy Expectations, captures version/hash provenance, compares Gold/Baseline/Current results, and emits JSON/Markdown release reports. Existing `RegressionChecker`, `RuleVersionManager`, `QualityReportSnapshots`, PDF DTO, and frontend percent helpers are reused; no second parser, Rule Engine, scorer, or prediction path is introduced.

**Tech Stack:** Python 3.14/pytest/PyYAML/FastAPI contracts, existing Java 21 Spring Boot/OpenPDF DTO/PDF tests, Angular/Vitest representation tests, YAML/JSON/Markdown artifacts, GitHub Actions.

## Global Constraints

- Freeze exactly the approved nine assets: 3 winner corpus, 3 middle corpus, 3 negative corpus.
- `corpusRole` is curation metadata only and must never enter `PromptParser`, `CanonicalEvidence`, `RuleEngine`, `Assessment`, `Scoring`, `RenderAuthorization`, or `PromptAnalysisEngine` input.
- Use the exact mounted source bytes; do not rewrite, normalize, retimestamp, clean, simplify, or reformat prompts before hashing/copying.
- Historical views, reach, watch time, likes, shares, publication outcomes, `PerformanceObservation`, platform metrics, prediction output, and winner labels are forbidden inputs to pre-render Golden analysis.
- Keep Gold Truth independent from current parser/rule/scorer output.
- Keep Policy Expectations separate and scoped to the current ruleset/assessment/scoring stack.
- Do not modify `PromptParser`, `canonical_evidence.py`, any ruleset YAML, `RuleEngine`, scorer thresholds, assessment policy, PDF renderer behavior, or frontend product behavior in this infrastructure phase.
- Preserve parser-incompatible source prompts as baseline evidence; do not edit prompts to make the parser pass.
- Deterministic Golden CI must not require OpenAI, OpenArt, Meta, TikTok, YouTube, video rendering, or network access.
- Use explicit `UNKNOWN` when a version identity does not exist; never fabricate a version.
- Keep critical calibration documents under tracked `intelligence/docs`, not ignored root `/docs`.
- Do not create a commit unless the user explicitly requests one.

---

### Task 1: Freeze the approved source artifacts and manifest

**Files:**
- Create: `intelligence/data/golden/pompom-golden-v1/manifest.yaml`
- Create: `intelligence/data/golden/pompom-golden-v1/prompts/sticky-ball-01.txt`
- Create: `intelligence/data/golden/pompom-golden-v1/prompts/ball-crocodile-01.txt`
- Create: `intelligence/data/golden/pompom-golden-v1/prompts/upside-chair-01.md`
- Create: `intelligence/data/golden/pompom-golden-v1/prompts/lamp-01.md`
- Create: `intelligence/data/golden/pompom-golden-v1/prompts/snack-box-01.md`
- Create: `intelligence/data/golden/pompom-golden-v1/prompts/box-cat-01.md`
- Create: `intelligence/data/golden/pompom-golden-v1/prompts/spot-cat-01.md`
- Create: `intelligence/data/golden/pompom-golden-v1/prompts/sneaky-door-01.md`
- Create: `intelligence/data/golden/pompom-golden-v1/prompts/island-journal-01.txt`
- Test: `intelligence/ml-service/tests/test_pompom_golden_manifest.py`

**Interfaces:**
- Consumes: the nine approved mounted paths and their exact bytes.
- Produces: a tracked, hash-checked manifest containing `goldenSetVersion`, `goldenId`, `displayName`, `sourceType`, `sourceLocation`, `promptFile`, `promptHash`, `character`, `mechanicFamily`, `contentFamily`, `corpusRole`, `sourceLineageConfidence`, and `knownIssues`.

- [x] **Step 1: Write the manifest/hash test before copying artifacts**

```python
APPROVED = {
    "sticky-ball-01": "POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Absurd_Moments/01_luca_sticky_ball/01_video_prompt.txt",
    "ball-crocodile-01": "POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Absurd_Moments/07_luca_ball_spitting_crocodile/01_video_prompt.txt",
    "upside-chair-01": "POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/What’s Wrong? uploaded/1-The Upside-Down Chair/prompt.md",
    "lamp-01": "POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/easy uploaded/4- Kiko and the Lamp That Hates Being Watched /prompt.md",
    "snack-box-01": "POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/easy uploaded/2- Mimi and the Snack Box That Keeps Changing/prompt.md",
    "box-cat-01": "POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/pompom_vs_animals/03_luca_vs_box_cat/prompt.md",
    "spot-cat-01": "POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/pompom_vs_animals/04_kiko_vs_spot_stealing_cat/prompt.md",
    "sneaky-door-01": "POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/archive/MIMI_VS_THE_SNEAKY_DOOR/mimi-sneaky-door-compact-generation-prompt.md",
    "island-journal-01": "POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/classic story-1/03_luca_and_the_island_journal/01_video_prompt.txt",
}


def test_manifest_has_exact_approved_corpus_without_engine_role_input():
    manifest = yaml.safe_load(MANIFEST.read_text())
    assets = manifest["assets"]
    assert manifest["goldenSetVersion"] == "POMPOM_GOLDEN_V1"
    assert {item["goldenId"] for item in assets} == set(APPROVED)
    assert len(assets) == 9
    assert Counter(item["corpusRole"] for item in assets) == {
        "WINNER": 3,
        "MIDDLE": 3,
        "NEGATIVE": 3,
    }
    assert all(
        item["corpusRole"] not in (MANIFEST.parent / item["promptFile"]).read_text(encoding="utf-8")
        for item in assets
    )
```

- [x] **Step 2: Run the manifest test and confirm it fails because artifacts/manifest do not exist**

Run:

```bash
cd intelligence/ml-service
.venv/bin/python -m pytest -q tests/test_pompom_golden_manifest.py --no-header -p no:cacheprovider
```

Expected: collection/assertion failure for the missing manifest.

- [x] **Step 3: Copy exact source bytes and record the approved manifest**

Copy each approved source file byte-for-byte into the tracked `prompts/` directory. The manifest must record the mounted source path and copied artifact hash; `corpusRole` must be metadata adjacent to, not embedded in, prompt text or parsed IR.

- [x] **Step 4: Run the manifest/hash-drift test**

Expected: exactly nine assets, 3/3/3 role counts, copied hash equals manifest hash, and no role field is passed to engine input.

---

### Task 2: Add independently authored Gold Truth and policy expectations

**Files:**
- Create: `intelligence/data/golden/pompom-golden-v1/truth/gold_truth.yaml`
- Create: `intelligence/data/golden/pompom-golden-v1/policy/policy_expectations_v1.7.yaml`
- Create: `intelligence/ml-service/tests/test_pompom_golden_truth_schema.py`

**Interfaces:**
- Consumes: frozen prompt artifacts and the human-reviewed structural notes in the approved curation report.
- Produces: separate `goldTruthVersion`, dimension assertions, evidence references, confidence/status fields, and `rulesetVersion: 1.7` policy expectations.

- [x] **Step 1: Write schema tests before the truth files**

```python
REQUIRED_DIMENSIONS = {
    "HOOK", "GOAL", "CENTRAL_MECHANIC", "ACTIVE_ATTEMPT_COUNT",
    "DISTINCT_STRATEGY_COUNT", "DISTINCT_STRATEGIES", "ESCALATION",
    "PROGRESSION", "REALIZATION", "FAKE_RESOLUTION", "PAYOFF", "LOOP",
    "CHARACTER_PERFORMANCE", "PRODUCIBILITY", "SOUND_OFF_READABILITY",
    "TIMING_PACING", "CONTENT_FAMILY_FIT", "FIRST_FRAME_ANOMALY_INTENT",
    "SPECIALIZED_RULE_APPLICABILITY",
}


def test_gold_truth_is_independent_and_evidence_backed():
    truth = yaml.safe_load(TRUTH.read_text())
    assert truth["goldLabelVersion"]
    assert set(truth["assets"]) == APPROVED_IDS
    for asset in truth["assets"].values():
        for dimension in asset["dimensions"].values():
            assert {"expected", "applicable", "confidence", "evidenceReferences", "notes"} <= set(dimension)
            if dimension["confidence"] == "HIGH" and dimension["applicable"]:
                assert dimension["evidenceReferences"]


def test_policy_expectations_are_not_embedded_in_gold_truth():
    truth_text = TRUTH.read_text()
    assert "creativeGrade" not in truth_text
    assert "familyScores" not in truth_text
    policy = yaml.safe_load(POLICY.read_text())
    assert policy["rulesetVersion"] == "1.7"
    assert set(policy["assets"]) == APPROVED_IDS
```

- [x] **Step 2: Author truth from prompt evidence, not parser output**

For Sticky Ball, independently record `PULL` and `TEST/SQUEEZE`, `ESCALATION: STRONG`, `FAKE_RESOLUTION: PRESENT`, and evidence excerpts from the exact copied prompt. For Box Cat and Spot Cat, record human-reviewed attempts and recurrence even though current parser timeline evidence is unavailable; set confidence/notes to explain the parser incompatibility. Mark ambiguous semantics `MEDIUM` or `LOW` with `HUMAN_REVIEW_REQUIRED` rather than converting them to `UNKNOWN`.

- [x] **Step 3: Author version-scoped policy expectations separately**

Use nullable/range-aware policy fields for creative score/grade, family scores, evidence completeness, render authorization, blockers, criticals, warnings, unknowns, and NOT_APPLICABLE dimensions. Record known baseline issue expectations explicitly rather than silently treating a current defect as Gold Truth.

- [x] **Step 4: Run schema tests**

Expected: all nine assets have structural dimensions and evidence references; policy values exist only in the policy file.

---

### Task 3: Add full-stack provenance fingerprint and frozen semantic mode

**Files:**
- Create: `intelligence/ml-service/app/golden/provenance.py`
- Create: `intelligence/ml-service/app/golden/deterministic_runner.py`
- Create: `intelligence/ml-service/tests/test_golden_provenance.py`
- Create: `intelligence/data/golden/pompom-golden-v1/frozen-semantic/README.md`
- Modify only if required: existing provider-boundary test modules

**Interfaces:**
- Consumes: manifest hash, parser settings, `CANONICAL_EVIDENCE_VERSION`, ruleset file/version, configured rule engine/assessment/scoring versions, semantic provider identity, package versions, renderer/frontend versions, and Git commit.
- Produces: `GoldenFingerprint` with explicit `
`UNKNOWN` values for semantic prompt/schema, renderer, frontend, or Git identities when unavailable; never substitute a guessed version.

- [x] **Step 1: Write provenance and role-isolation tests**

```python
def test_fingerprint_contains_explicit_unknowns_and_no_corpus_role():
    fingerprint = build_golden_fingerprint(manifest, ruleset_path=RULESET_17)
    assert fingerprint.golden_set_version == "POMPOM_GOLDEN_V1"
    assert fingerprint.ruleset_version == "1.7"
    assert fingerprint.canonical_evidence_version == "canonical-attempt-evidence-v2"
    assert fingerprint.semantic_prompt_version in {None, "UNKNOWN"}
    assert fingerprint.semantic_schema_version in {None, "UNKNOWN"}
    assert "corpusRole" not in fingerprint.engine_input_metadata


def test_deterministic_runner_receives_prompt_text_only(monkeypatch):
    observed = {}
    def capture(prompt_text, **kwargs):
        observed.update(kwargs)
        return fake_report
    monkeypatch.setattr("app.golden.deterministic_runner._run_existing_pipeline", capture)
    run_golden_asset(asset_id="sticky-ball-01", manifest=manifest)
    assert "corpusRole" not in observed
    assert "winner" not in str(observed).lower()
```

- [x] **Step 2: Run the provenance tests and verify the missing module/contract failure**

Run:

```bash
cd intelligence/ml-service
.venv/bin/python -m pytest -q tests/test_golden_provenance.py --no-header -p no:cacheprovider
```

- [x] **Step 3: Implement only harness-level provenance and deterministic execution**

`GoldenFingerprint` must include: Golden Set version, Gold-label version, prompt hash, parser version, canonical evidence version, ruleset version, rule engine version, assessment version, scoring version, semantic provider/model, semantic prompt/schema versions, report renderer version, frontend representation version, and Git commit. Use `None` or the literal `UNKNOWN` according to the existing contract; do not fabricate values. The runner must call the existing parser/evidence/rules/assessment/scorer conversion path and pass only exact prompt text.

- [x] **Step 4: Keep semantic-provider calls frozen or explicitly unavailable**

The deterministic runner may inject frozen semantic evidence through the existing semantic-check call boundary. It must never call a live provider in deterministic mode. If a required semantic fixture is absent, return a typed `SERVICE_ERROR`/`UNKNOWN` according to existing contracts and record the gap; do not silently pass.

- [x] **Step 5: Run the provenance and no-role tests**

Expected: fingerprint fields are stable, unknown versions are explicit, and corpus metadata is absent from engine input.

---

### Task 4: Capture the current v1.7 baseline before calibration fixes

**Files:**
- Create: `intelligence/ml-service/app/golden/baseline.py`
- Create: `intelligence/ml-service/tests/test_pompom_golden_baseline.py`
- Create: `intelligence/data/golden/pompom-golden-v1/baselines/v1.7/README.md`
- Create: generated baseline artifacts under `intelligence/data/golden/pompom-golden-v1/baselines/v1.7/`

**Interfaces:**
- Consumes: frozen manifest, copied exact prompt artifacts, Gold Truth metadata only for comparison labels (never as engine input), deterministic runner, and current immutable RULESET 1.7.
- Produces: one baseline snapshot per golden asset containing parsed IR, canonical evidence, rule results, dimension assessments, family scores/assessments, creative score/grade, evidence completeness, render authorization, severity counts, parser confidence, priority fixes, representation values, and full-stack fingerprint.

- [x] **Step 1: Write baseline shape and corpus-role isolation tests**

```python
def test_baseline_has_all_nine_assets_and_current_ruleset():
    baseline = capture_baseline(manifest, ruleset_version="1.7")
    assert set(baseline.assets) == APPROVED_IDS
    assert baseline.fingerprint.ruleset_version == "1.7"
    assert len(baseline.assets) == 9


def test_baseline_preserves_parser_incompatibility_as_observed_evidence():
    asset = capture_baseline_asset("box-cat-01", manifest, ruleset_version="1.7")
    assert asset.knownIssues
    assert any(issue["code"] == "TIMELINE_PARSE_INCOMPATIBLE" for issue in asset.knownIssues)
    assert asset.goldTruth is not used in asset.engineInput
```

- [x] **Step 2: Run the baseline tests before baseline artifacts exist**

Run:

```bash
cd intelligence/ml-service
.venv/bin/python -m pytest -q tests/test_pompom_golden_baseline.py --no-header -p no:cacheprovider
```

Expected: failure for missing baseline artifacts/runner.

- [x] **Step 3: Capture all nine current v1.7 outputs without fixing any engine behavior**

Run one deterministic cohort command:

```bash
cd intelligence/ml-service
.venv/bin/python -m app.golden.baseline --manifest ../data/golden/pompom-golden-v1/manifest.yaml --ruleset 1.7 --out ../data/golden/pompom-golden-v1/baselines/v1.7
```

The command must fail if any prompt hash differs from the manifest or if a baseline asset cannot be captured. It must not use the corpus role when constructing the prompt analysis input.

- [x] **Step 4: Record known baseline issues from observed output only**

Tag issues only when the captured output proves them. Expected candidate codes include `TIMELINE_PARSE_INCOMPATIBLE`, `SEMANTIC_EVIDENCE_GAP`, `SPECIALIZED_RULE_SCOPE_REVIEW`, and `REPRESENTATION_PENDING`; do not add a known-issue tag merely because the curation role is NEGATIVE.

- [x] **Step 5: Run baseline tests and inspect the nine-artifact summary**

Expected: nine artifacts, current ruleset `1.7`, explicit provenance, source hashes, no performance fields, and no engine code changes.

---

### Task 5: Implement the Golden comparator and semantic/policy release gate

**Files:**
- Create: `intelligence/ml-service/app/golden/comparator.py`
- Create: `intelligence/ml-service/tests/test_golden_comparator.py`
- Create: `intelligence/data/golden/pompom-golden-v1/reports/README.md`

**Interfaces:**
- Consumes: Gold Truth, v1.7 baseline, current run snapshots, Policy Expectations, and fingerprints.
- Produces: assertion-level classifications `PASS`, `FAIL`, `IMPROVED_FROM_BASELINE`, `REGRESSED_FROM_BASELINE`, `UNCHANGED_KNOWN_ISSUE`, `GOLD_REVIEW_REQUIRED`, `NOT_APPLICABLE`; summary counts; release gate status.

- [x] **Step 1: Write comparator tests first**

```python
def test_strategy_improvement_is_not_a_new_regression():
    result = compare_dimension(
        gold={"expectedFamilies": ["PULL", "TEST"], "confidence": "HIGH"},
        baseline={"families": ["PULL", "CATCH"]},
        current={"families": ["PULL", "TEST"]},
        assertion_type="SET_EQUALS",
    )
    assert result.classification == "IMPROVED_FROM_BASELINE"
    assert result.is_new_semantic_regression is False


def test_unchanged_known_issue_is_not_new_regression():
    result = compare_dimension(
        gold={"expected": "STRONG"},
        baseline={"actual": "FAIL"},
        current={"actual": "FAIL"},
        known_issue=True,
        assertion_type="ENUM",
    )
    assert result.classification == "UNCHANGED_KNOWN_ISSUE"
    assert result.is_new_semantic_regression is False


def test_policy_only_change_is_expected_when_policy_version_changed():
    result = compare_policy(
        baseline={"creativeGrade": "B", "rulesetVersion": "1.7"},
        current={"creativeGrade": "C", "rulesetVersion": "1.8"},
        expectation_updated=True,
    )
    assert result.classification == "EXPECTED_POLICY_CHANGE"
    assert result.is_unexpected_policy_regression is False


def test_release_gate_fails_for_new_semantic_or_unexpected_policy_regression():
    report = GoldenRegressionReport(new_semantic_regressions=1, unexpected_policy_regressions=0)
    assert report.release_gate == "FAIL"
    report = GoldenRegressionReport(new_semantic_regressions=0, unexpected_policy_regressions=0)
    assert report.release_gate == "PASS"
```

- [x] **Step 2: Run comparator tests before implementation**

Run:

```bash
cd intelligence/ml-service
.venv/bin/python -m pytest -q tests/test_golden_comparator.py --no-header -p no:cacheprovider
```

- [x] **Step 3: Implement assertion types without duplicating engine logic**

Support `EXACT`, `ENUM`, `COUNT`, `SET_EQUALS`, `SET_CONTAINS`, `RANGE`, `APPLICABILITY`, `EVIDENCE_EXISTS`, and `STATUS`. Compare semantic/canonical dimensions separately from policy fields. A Gold Truth mismatch with HIGH-confidence evidence is a semantic failure; a MEDIUM/LOW mismatch is `GOLD_REVIEW_REQUIRED` unless an explicit policy says otherwise.

- [x] **Step 4: Implement known-issue and baseline classification**

A baseline failure that remains unchanged and is explicitly tagged is `UNCHANGED_KNOWN_ISSUE`. A current result matching Gold after a baseline failure is `IMPROVED_FROM_BASELINE`. A current result diverging from Gold when baseline matched is `NEW_SEMANTIC_REGRESSION`. Policy changes are evaluated only against the ruleset/assessment/scoring-scoped Policy Expectations.

- [x] **Step 5: Emit machine-readable and human-readable reports**

Produce `golden-regression-report.json` and `golden-regression-report.md` with Golden Set identity, fingerprint, assertion totals, semantic passed/failed, improvements, unchanged known issues, new semantic regressions, expected policy changes, unexpected policy regressions, Gold review count, per-asset matrices, evidence references, and a prominent release gate.

- [x] **Step 6: Run comparator tests**

Expected: the gate is `PASS` only when `NEW SEMANTIC REGRESSIONS == 0` and `UNEXPECTED POLICY REGRESSIONS == 0`.

---

### Task 6: Add performance-dependency and role-isolation architecture tests

**Files:**
- Create: `intelligence/ml-service/tests/test_golden_architecture_boundary.py`
- Modify only if required: `intelligence/ml-service/pyproject.toml`

**Interfaces:**
- Consumes: the source tree and deterministic Golden runner.
- Produces: automated protection that pre-render Golden analysis cannot import or receive performance/prediction/corpus-role data.

- [x] **Step 1: Write failing architecture tests**

```python
FORBIDDEN_IMPORT_ROOTS = {
    "app.performance", "app.prediction", "app.retention", "lab", "PerformanceObservation",
}


def test_pre_render_quality_modules_do_not_import_performance_modules():
    violations = scan_imports(Path("app/parser"), Path("app/quality"), Path("app/rules"), Path("app/assessment"), Path("app/scoring"))
    assert violations == []


def test_golden_runner_does_not_pass_corpus_role_or_outcome_fields():
    calls = capture_pipeline_inputs(run_all_golden_assets)
    for call in calls:
        assert "corpusRole" not in call.ir
        assert "winner" not in json.dumps(call.ir).lower()
        assert "middle" not in json.dumps(call.ir).lower()
        assert "negative" not in json.dumps(call.ir).lower()
        assert not any(key in call.ir for key in {"views", "reach", "likes", "watch_time", "performance"})
```

- [x] **Step 2: Run the architecture tests and confirm they fail for missing scanner/harness**

Run:

```bash
cd intelligence/ml-service
.venv/bin/python -m pytest -q tests/test_golden_architecture_boundary.py --no-header -p no:cacheprovider
```

- [x] **Step 3: Implement a static import scanner and runner-input probe**

Scan Python AST imports for forbidden roots only within pre-render quality packages. Do not forbid the separate lab package from existing performance workflows; the test boundary is specifically the Prompt Quality pre-render path. Probe the deterministic runner’s actual call payload rather than relying only on source-text grep.

- [x] **Step 4: Run the architecture tests**

Expected: zero forbidden imports and zero performance/corpus-role fields in Golden engine inputs.

---

### Task 7: Add cross-layer representation contracts

**Files:**
- Create: `intelligence/ml-service/tests/test_golden_representation_contract.py`
- Modify: `intelligence/backend/src/test/java/com/pompomhills/intelligence/quality/QualityReportDtoTest.java` only if a missing Golden fixture field is exposed
- Modify: `intelligence/backend/src/test/java/com/pompomhills/intelligence/quality/QualityReportPdfServiceTest.java` only if a missing fixture assertion is exposed
- Modify: `intelligence/frontend/src/app/pages/quality-validator/state-share.spec.ts` only if a missing canonical fixture assertion is exposed

**Interfaces:**
- Consumes: one canonical state-share fixture and one quality outcome fixture.
- Produces: a single contract proving canonical 0–100 state shares, outcome categories, parser/canonical confidence, and three-outcome status remain consistent across ML/API/PDF/frontend representations.

- [x] **Step 1: Write the cross-layer fixture test**

```python
def test_state_share_contract_is_percent_once_everywhere():
    canonical = {"percentage": 20.0}
    assert format_state_share_for_frontend(canonical["percentage"]) == "20%"
    assert format_state_share_for_pdf(canonical["percentage"]) == "20%"
    assert format_state_share_for_frontend(canonical["percentage"]) != "2000%"
    assert format_state_share_for_pdf(canonical["percentage"]) != "2000%"


def test_creative_evidence_render_are_independent_outcomes():
    report = make_golden_report_fixture()
    assert report["creative_grade"]
    assert report["evidence_completeness"]
    assert report["render_authorization"]
    assert report["creative_grade"] != report["render_authorization"]
```

- [x] **Step 2: Run the representation test before adding the unified fixture**

Run the existing ML/backend/frontend targeted commands and the new Python test. Expected: the new shared fixture/helpers are missing.

- [x] **Step 3: Reuse existing representation paths**

Use the existing scorer 0–100 output, backend `QualityReportDto`/`QualityReportPdfService`, and frontend `state-share.ts` helper. Do not add a second formatter or alter production units. The Golden fixture should assert canonical values at each boundary, not screenshot pixels.

- [x] **Step 4: Run representation validation**

```bash
cd intelligence/ml-service
.venv/bin/python -m pytest -q tests/test_golden_representation_contract.py --no-header -p no:cacheprovider
cd ../backend
mvn -q -Dtest=QualityReportDtoTest,QualityReportPdfServiceTest test
cd ../frontend
NG_CLI_ANALYTICS=false npx ng test --watch=false --include 'src/app/pages/quality-validator/**/*.spec.ts'
```

Expected: every layer renders 20% as `20%`, and creative/evidence/render outcomes remain separate.

---

### Task 8: Generate baseline/report documentation in tracked locations

**Files:**
- Create: `intelligence/docs/GOLDEN_CALIBRATION_AUDIT.md`
- Create: `intelligence/docs/GOLDEN_CALIBRATION_ARCHITECTURE.md`
- Create: `intelligence/docs/GOLDEN_V17_BASELINE_REPORT.md`
- Create: `intelligence/docs/GOLDEN_REGRESSION_WORKFLOW.md`
- Modify: `intelligence/docs/GOLDEN_SET_V1_CANDIDATE_REVIEW.md` only to link the frozen manifest after approval

**Interfaces:**
- Consumes: audit evidence, manifest, truth/policy schema, fingerprint, baseline report, comparator report, and CI gate command.
- Produces: tracked operational documentation; no ignored-root `/docs` dependency.

- [x] **Step 1: Write documentation contract checks**

Assert each document exists and includes the required statements: corpus role is metadata only, Gold Truth is independent, Policy Expectations are versioned, v1.7 baseline is preserved including known issues, performance dependencies are zero, deterministic CI is no-network, and release gate requires zero new semantic/unexpected policy regressions.

- [x] **Step 2: Generate the audit and architecture documents**

Record the previous audit status as `EXISTS`, `PARTIAL`, `MISSING`, `DUPLICATED`, or `STALE`; document why tracked `intelligence/docs` was chosen over ignored root `/docs`; document future prediction flow as canonical feature snapshot plus historical outcome after creative feature generation.

- [x] **Step 3: Generate the baseline and workflow documents from actual artifacts**

Do not hand-copy scores into documentation. Include links/paths to JSON baseline and comparator reports, the full-stack fingerprint, nine asset hashes, known parser issues, report classifications, and exact local/CI commands.

- [x] **Step 4: Run documentation checks**

Expected: all required tracked documents exist and contain no placeholder language or unverified claims.

---

### Task 9: Add the deterministic CI release gate

**Files:**
- Create: `.github/workflows/pompom-golden.yml`
- Create: `intelligence/ml-service/scripts/run_pompom_golden_ci.py`
- Create: `intelligence/ml-service/tests/test_golden_ci_gate.py`
- Modify: `intelligence/ml-service/pyproject.toml` only if a test command needs a repository-native entry point

**Interfaces:**
- Consumes: frozen manifest, Gold Truth, Policy Expectations, v1.7 baseline, deterministic runner, comparator.
- Produces: CI failure when hashes drift, provenance is invalid, live providers are requested, new semantic regressions exist, or unexpected policy regressions exist.

- [x] **Step 1: Write CI gate tests first**

```python
def test_ci_gate_passes_only_with_zero_new_regressions():
    assert evaluate_ci_gate({"newSemanticRegressions": 0, "unexpectedPolicyRegressions": 0}) == "PASS"


def test_ci_gate_fails_on_hash_drift():
    with pytest.raises(GoldenGateFailure, match="GOLDEN_FIXTURE_DRIFT"):
        verify_manifest_hashes(manifest_with_changed_prompt)


def test_ci_gate_fails_when_live_provider_is_requested():
    with pytest.raises(GoldenGateFailure, match="LIVE_PROVIDER_NOT_ALLOWED"):
        run_ci_mode(provider_mode="LIVE")
```

- [x] **Step 2: Run CI gate tests before implementation**

Run:

```bash
cd intelligence/ml-service
.venv/bin/python -m pytest -q tests/test_golden_ci_gate.py --no-header -p no:cacheprovider
```

- [x] **Step 3: Implement the small CI entry point**

The script must verify prompt hashes, artifact schema, full-stack fingerprint completeness, deterministic provider mode, comparator output, and the two zero-regression conditions. It must emit the report paths and exit nonzero on gate failure.

- [x] **Step 4: Add the source-controlled workflow**

The workflow installs the existing ML dependencies, runs only the deterministic Golden command and its focused tests, and does not configure credentials or call external services. It must not run video rendering or social APIs.

- [x] **Step 5: Run the CI command locally**

```bash
cd intelligence/ml-service
.venv/bin/python scripts/run_pompom_golden_ci.py --manifest ../data/golden/pompom-golden-v1/manifest.yaml --baseline ../data/golden/pompom-golden-v1/baselines/v1.7
```

Expected for the initial baseline comparison: a valid report with known baseline issues separated from new regressions; the gate result must be explicit rather than inferred from a total pass count.

---

### Task 10: Final infrastructure validation and handoff before calibration family fixes

**Files:**
- Modify only generated reports or focused test/docs files required by validation findings.
- Do not modify parser, canonical evidence, rulesets, RuleEngine, scorer, assessment, PDF behavior, frontend product behavior, or producibility policy.

- [x] **Step 1: Run the complete deterministic Golden gate**

```bash
cd intelligence/ml-service
.venv/bin/python scripts/run_pompom_golden_ci.py --manifest ../data/golden/pompom-golden-v1/manifest.yaml --baseline ../data/golden/pompom-golden-v1/baselines/v1.7
```

- [x] **Step 2: Run existing relevant suites without live providers**

```bash
.venv/bin/python -m pytest -vv --no-header -p no:cacheprovider tests/test_prompt_quality_consistency_golden.py tests/test_ruleset_1_6_story_density.py tests/test_ruleset_1_7_stubborn_return.py tests/test_regression_checker.py tests/test_pompom_golden_manifest.py tests/test_pompom_golden_truth_schema.py tests/test_golden_provenance.py tests/test_pompom_golden_baseline.py tests/test_golden_comparator.py tests/test_golden_architecture_boundary.py tests/test_golden_representation_contract.py tests/test_golden_ci_gate.py
```

- [x] **Step 3: Verify backend/frontend representation contracts**

```bash
cd ../backend
mvn -q -Dtest=QualityReportDtoTest,QualityReportPdfServiceTest test
cd ../frontend
NG_CLI_ANALYTICS=false npx ng test --watch=false --include 'src/app/pages/quality-validator/**/*.spec.ts'
```

- [x] **Step 4: Verify infrastructure-only scope**

Check that the diff contains no changes to parser/rules/canonical/scorer production behavior, no social performance imports, no corpus-role fields in engine input, no live-provider CI configuration, and exactly nine frozen prompt artifacts.

- [x] **Step 5: Generate the final baseline report and stop**

The final report must state:

```text
Golden Set: POMPOM_GOLDEN_V1
Assets: 9
Winner corpus: 3
Middle corpus: 3
Negative corpus: 3
Gold assertions: <actual>
High confidence: <actual>
Medium confidence: <actual>
Human review required: <actual>
Ruleset: 1.7
Full-stack fingerprint: <actual>
Performance dependencies detected: 0
Golden deterministic CI: PASS/FAIL
Next calibration family: STRATEGY / ATTEMPT CANONICALIZATION
```

Do not start Family 1 calibration fixes in this plan. Infrastructure phase ends after baseline/comparator/gate verification and human review of Gold Truth confidence flags.
