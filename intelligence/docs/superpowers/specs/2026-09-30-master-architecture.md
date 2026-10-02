# Pompom Creative Intelligence - Master Architecture

**Date:** September 30, 2026  
**Version:** 1.0  
**Status:** Draft

---

## Executive Summary

Transform the Pompom Creative Intelligence platform from a post-render analytics system into a **closed-loop AI content production system** that learns from every video and improves its own creative rules over time.

**Vision:** Idea → Validation → Render → QA → Publish → Metrics → Learning → Better Rules → Better Next Video

**Success Criteria:**
- Catch Opa, Arda, and Kiko failures before render (Phase 1)
- Automate OpenArt render orchestration (Phase 2)
- Publish to TikTok/YouTube/Meta with one click (Phase 3)
- Learn from winners and generate rule candidates automatically (Phase 4)

---

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                    POMPOM CREATIVE INTELLIGENCE             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  CREATIVE        │      │  PRODUCTION      │            │
│  │  QUALITY ENGINE  │──────│  ENGINE          │            │
│  │  (Phase 1)       │      │  (Phase 2)       │            │
│  └──────────────────┘      └──────────────────┘            │
│           │                         │                       │
│           │                         │                       │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  DISTRIBUTION    │      │  LEARNING        │            │
│  │  ENGINE          │──────│  ENGINE          │            │
│  │  (Phase 3)       │      │  (Phase 4)       │            │
│  └──────────────────┘      └──────────────────┘            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│              SHARED INFRASTRUCTURE                          │
│  • PostgreSQL Database                                      │
│  • Local Filesystem (content library)                       │
│  • LLM Provider Abstraction (OpenAI/Claude/Gemini/Ollama)  │
│  • State Machine Engine                                     │
│  • Audit Log                                                │
│  • Secrets Management                                       │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend:** Spring Boot 4.1.1 + Java 21 + PostgreSQL 17  
**Frontend:** Angular 21 + TypeScript  
**ML Service:** FastAPI + Python 3.11  
**LLM:** OpenAI GPT-4o (primary), Claude/Gemini/Ollama (alternatives)  
**Platform APIs:** OpenArt MCP/CLI, TikTok API, YouTube Data API v3, Meta Graph API  
**Infrastructure:** Docker Compose, Flyway migrations, Spring Scheduler

---

## Core Domain Model

### Content Lifecycle State Machine

```
IDEA
  ↓
CONCEPT_REVIEW ──→ CONCEPT_REJECTED
  ↓                      ↓
PROMPT_DRAFT          ARCHIVED
  ↓
VALIDATING
  ↓
BLOCKED ←──┐
  ↓        │
NEEDS_FIX ─┘
  ↓
RENDER_READY
  ↓
RENDER_QUEUED
  ↓
RENDERING
  ↓
RENDER_FAILED ─→ RENDER_RETRY_QUEUED ─→ RENDERING
  ↓                                          ↓
RENDER_COMPLETE                             (3x max)
  ↓                                          ↓
RENDER_QA                                RENDER_ABANDONED
  ↓
RENDER_REJECTED ─→ RERENDER_QUEUED ─→ RENDERING
  ↓
ASSET_APPROVED
  ↓
SCHEDULED
  ↓
PUBLISHING
  ↓
PUBLISH_FAILED ─→ PUBLISH_RETRY_QUEUED
  ↓
PUBLISHED
  ↓
MONITORING
  ↓
MATURE
  ↓
ARCHIVED
```

### Entity Relationships

```
Content (NEW - root aggregate)
  ├─ ContentMetadata (title, character, series, engine)
  ├─ ConceptValidation (idea-only check)
  ├─ PromptVersion[] (v1, v2, v3...)
  │   ├─ PromptText
  │   ├─ VideoPlanIR (parsed structure)
  │   ├─ ValidationRun[]
  │   │   ├─ FamilyScores (11 families)
  │   │   └─ FailedRule[] (with evidence)
  │   └─ HumanOverride[]
  ├─ RenderJob[]
  │   ├─ OpenArtRequest (params, model)
  │   ├─ OpenArtResponse (job_id, credits)
  │   └─ DownloadedAsset
  ├─ RenderQA (compliance check)
  ├─ SocialMetadata[] (platform-specific captions)
  ├─ PublicationRecord[]
  │   ├─ Platform (TIKTOK/YOUTUBE/META)
  │   ├─ PlatformContentId
  │   └─ PublishState
  └─ PerformanceMetrics[]
      ├─ MetricSnapshot[] (T+30m, T+1h, T+2h...)
      ├─ Trajectory (waves, velocity, acceleration)
      └─ Classification (WINNER/MEDIUM/WEAK...)

Video (EXISTING - keep for post-render analysis)
  ├─ VideoMetadata (unchanged)
  ├─ CreativeAnalysis (unchanged)
  └─ PerformanceObservations (link to Content)

Character (EXISTING - expand)
  ├─ CharacterProfile (unchanged)
  └─ PerformanceStats (aggregate from Content)

RulesetVersion (NEW)
  ├─ Version (1.0, 1.1, 1.2...)
  ├─ RuleFamily[] (11 families)
  │   └─ RuleCriteria[]
  └─ ChangeLog

RuleCandidate (NEW)
  ├─ Hypothesis
  ├─ Evidence (correlation data)
  ├─ Confidence
  └─ ApprovalStatus (PENDING/APPROVED/REJECTED)
```

---

## Phase 1: Creative Quality Engine

**Scope:** Prompt creation, validation, versioning, fix loop, render gate

### Key Components

**1. Prompt Domain**
- `ContentEntity` (root aggregate for entire lifecycle)
- `PromptVersionEntity` (immutable versions)
- `ConceptValidationEntity` (idea-only check)

**2. LLM Parser Service**
- Provider abstraction (OpenAI/Claude/Gemini/Ollama)
- Prompt → VideoPlanIR conversion
- Beat extraction with confidence scoring
- Ambiguity flagging

**3. Rule Engine (Python ML Service)**
- 11 quality families (concept, hook, novelty, progression, escalation, motion, readability, AI producibility, consistency, final, render risk)
- YAML rule definitions (versionable, human-readable)
- Evidence extraction for each failure
- Weighted scoring with blocker/critical/warning severity

**4. Validation Orchestrator**
- Parse prompt if needed
- Evaluate against current ruleset
- Save validation results
- Update content status
- Trigger fix loop if needed

**5. Version & Regression Manager**
- Track prompt versions (V1, V2, V3...)
- Compare scores across versions
- Detect regressions (score drops, new failures)
- Block regressions or require confirmation

**6. Reference Library**
- Golden test cases (Mimi PASS, Kiko FAIL, Opa FAIL, Arda FAIL)
- Automatic regression testing on rule changes
- Winner catalog for benchmarking

**7. Fix Loop Orchestrator**
- Export structured report for ChatGPT
- Import fixed prompt
- Create new version
- Re-validate automatically
- Compare with previous version

**8. Render Gate**
- Evaluate render readiness (zero blockers, thresholds met)
- Generate render certificate
- Manual override with audit trail
- Status transition to RENDER_READY

### Data Model (Phase 1)

**New Tables:**
```sql
-- Root content aggregate
contents (
  id UUID PK,
  title VARCHAR(200),
  character_id UUID FK,
  series_type VARCHAR(50),
  target_duration_seconds INT,
  target_platforms VARCHAR[],
  learning_words VARCHAR[],
  creative_engine VARCHAR(200),
  status VARCHAR(50),  -- lifecycle state
  current_prompt_version INT,
  created_at, updated_at, entity_version
)

-- Immutable prompt versions
prompt_versions (
  id UUID PK,
  content_id UUID FK,
  version_number INT,
  prompt_text TEXT,
  video_plan_ir JSONB,
  parser_confidence NUMERIC(3,2),
  parser_warnings VARCHAR[],
  created_by VARCHAR(50),  -- USER/AI_FIX
  created_at,
  UNIQUE(content_id, version_number)
)

-- Concept validation (idea-only)
concept_validations (
  id UUID PK,
  content_id UUID FK,
  concept_text TEXT,
  is_passing BOOLEAN,
  failure_reasons VARCHAR[],
  recommendations VARCHAR[],
  confidence_score NUMERIC(3,2),
  created_at
)

-- Validation results
validation_runs (
  id UUID PK,
  prompt_version_id UUID FK,
  ruleset_version VARCHAR(10),
  overall_score NUMERIC(5,2),
  status VARCHAR(30),  -- PASS/NEEDS_REVISION/BLOCKED
  blocker_count, critical_count, warning_count INT,
  family_scores JSONB,
  execution_time_ms BIGINT,
  created_at
)

-- Failed rules with evidence
failed_rules (
  id UUID PK,
  validation_run_id UUID FK,
  family VARCHAR(50),
  rule_id VARCHAR(50),
  severity VARCHAR(20),
  actual_value TEXT,
  required_value TEXT,
  evidence TEXT,
  recommendation TEXT
)

-- Human overrides (audit trail)
human_overrides (
  id UUID PK,
  prompt_version_id UUID FK,
  validation_run_id UUID FK,
  overridden_rule_id VARCHAR(50),
  original_severity VARCHAR(20),
  reason TEXT,
  overridden_by VARCHAR(50),
  created_at
)

-- Reference library
reference_prompts (
  id UUID PK,
  prompt_version_id UUID FK,
  reference_type VARCHAR(20),  -- POSITIVE/NEGATIVE
  category VARCHAR(50),  -- WINNER/STATIC_STATE/REPETITION...
  description TEXT,
  expected_status VARCHAR(30),
  tags VARCHAR[],
  added_at
)

-- Ruleset versioning
ruleset_versions (
  id UUID PK,
  version VARCHAR(10) UNIQUE,
  description TEXT,
  rules_yaml TEXT,
  activated_at TIMESTAMPTZ,
  deprecated_at TIMESTAMPTZ
)
```

### APIs (Phase 1)

**Prompt Management**
```
POST   /api/v1/contents
GET    /api/v1/contents/{id}
GET    /api/v1/contents
POST   /api/v1/contents/{id}/concept-validate
POST   /api/v1/contents/{id}/prompt-versions
GET    /api/v1/contents/{id}/prompt-versions
POST   /api/v1/contents/{id}/validate
GET    /api/v1/contents/{id}/validation-history
POST   /api/v1/contents/{id}/export-for-fix
POST   /api/v1/contents/{id}/import-fixed
POST   /api/v1/contents/{id}/check-render-readiness
POST   /api/v1/contents/{id}/mark-render-ready
POST   /api/v1/contents/{id}/override-rule
```

**Reference Library**
```
POST   /api/v1/references
GET    /api/v1/references
POST   /api/v1/references/golden-tests
```

**ML Service (FastAPI)**
```
POST   /api/ml/parse-prompt
POST   /api/ml/validate-concept
POST   /api/ml/validate-quality
```

---

## Phase 2: Production Engine

**Scope:** OpenArt integration, render orchestration, render QA, asset management

### Key Components

**1. OpenArt Adapter**
- MCP/CLI integration (no browser automation)
- Authentication handling
- Image generation (first frame from description)
- Video generation (prompt + first frame → video)
- Job polling and download
- Credit tracking

**2. Render Job Manager**
- Queue management (FIFO with priority)
- State machine (QUEUED → GENERATING → COMPLETE → DOWNLOADED)
- Retry logic (3 attempts max)
- Error handling and logging
- Concurrent job limit (respect OpenArt rate limits)

**3. Asset Library Manager**
- Local filesystem structure per content
- File naming conventions
- Metadata tracking (resolution, duration, file size)
- Version management (rerender → new asset version)

**4. Render QA Engine**
- Prompt compliance check (did AI follow instructions?)
- Dead air detection
- Character identity verification
- Physics rule consistency
- Final execution check
- Object duplication detection
- Decision: ACCEPT / RERENDER / ABANDON

**5. Rerender Decision Engine**
- Minor issues → ACCEPT
- Fatal issues → RERENDER
- Max rerender attempts (2x)
- Cost tracking (credits spent vs saved)

### Data Model (Phase 2)

**New Tables:**
```sql
-- Render jobs
render_jobs (
  id UUID PK,
  content_id UUID FK,
  prompt_version_id UUID FK,
  job_type VARCHAR(20),  -- FIRST_FRAME/VIDEO
  openart_job_id VARCHAR(100),
  openart_model VARCHAR(50),
  openart_params JSONB,
  status VARCHAR(30),  -- QUEUED/GENERATING/COMPLETE/FAILED/ABANDONED
  attempt_number INT,
  credits_used NUMERIC(10,2),
  queued_at, started_at, completed_at TIMESTAMPTZ,
  error_message TEXT
)

-- Downloaded assets
render_assets (
  id UUID PK,
  render_job_id UUID FK,
  content_id UUID FK,
  asset_type VARCHAR(20),  -- FIRST_FRAME/VIDEO
  relative_path TEXT,
  file_size_bytes BIGINT,
  duration_ms INT,
  width INT, height INT,
  downloaded_at TIMESTAMPTZ
)

-- Render QA
render_qa_results (
  id UUID PK,
  render_asset_id UUID FK,
  prompt_version_id UUID FK,
  compliance_score INT,
  compliance_issues JSONB,  -- array of detected issues
  decision VARCHAR(30),  -- ACCEPT/RERENDER/ABANDON
  decision_reason TEXT,
  reviewed_by VARCHAR(50),  -- USER/AUTOMATED
  reviewed_at TIMESTAMPTZ
)

-- OpenArt credit tracking
openart_credit_log (
  id UUID PK,
  render_job_id UUID FK,
  operation VARCHAR(50),
  credits_before NUMERIC(10,2),
  credits_spent NUMERIC(10,2),
  credits_after NUMERIC(10,2),
  logged_at TIMESTAMPTZ
)
```

### APIs (Phase 2)

**Render Management**
```
POST   /api/v1/contents/{id}/queue-render
GET    /api/v1/contents/{id}/render-jobs
GET    /api/v1/render-jobs/{id}/status
POST   /api/v1/render-jobs/{id}/cancel
GET    /api/v1/render-jobs/{id}/download
POST   /api/v1/render-assets/{id}/qa-review
POST   /api/v1/render-assets/{id}/approve
POST   /api/v1/render-assets/{id}/request-rerender
```

**Asset Management**
```
GET    /api/v1/contents/{id}/assets
GET    /api/v1/assets/{id}/download
GET    /api/v1/assets/{id}/metadata
```

---

## Phase 3: Distribution Engine

**Scope:** Multi-platform publishing, scheduling, caption generation, OAuth, state tracking

### Key Components

**1. Platform Adapter Abstraction**
```java
interface PlatformPublisher {
    AuthenticationStatus authenticate(OAuthCredentials creds);
    ValidationResult validateContent(Content content);
    PublishResult publish(Content content, PublishParams params);
    PublishStatus getStatus(String platformContentId);
    boolean supportsScheduling();
    List<String> getRequiredPermissions();
}
```

**Implementations:**
- `TikTokPublisher` (Content Posting API)
- `YouTubePublisher` (Data API v3)
- `MetaFacebookPublisher` (Graph API)
- `MetaInstagramPublisher` (Graph API)

**2. OAuth & Credentials Manager**
- Multi-platform OAuth flow
- Token refresh handling
- Encrypted credential storage (OS keychain)
- Permission verification
- Account linking UI

**3. Social Metadata Generator**
- Platform-specific caption templates
- Learning word integration
- Hashtag generation
- Title/description optimization
- A/B test caption variants

**4. Publishing Scheduler**
- Calendar view UI
- Time slot management
- Platform distribution rules (avoid same-day conflicts)
- Batch scheduling
- Time zone handling

**5. Publication State Tracker**
- Platform-specific state machines
- Webhook handlers (where available)
- Polling for non-webhook platforms
- Error recovery
- Retry logic

### Data Model (Phase 3)

**New Tables:**
```sql
-- Platform credentials (encrypted)
platform_credentials (
  id UUID PK,
  platform VARCHAR(30),
  account_name VARCHAR(100),
  encrypted_access_token TEXT,
  encrypted_refresh_token TEXT,
  token_expires_at TIMESTAMPTZ,
  permissions VARCHAR[],
  status VARCHAR(30),  -- ACTIVE/REVOKED/EXPIRED
  linked_at TIMESTAMPTZ,
  last_refresh_at TIMESTAMPTZ
)

-- Social metadata (versioned per platform)
social_metadata (
  id UUID PK,
  content_id UUID FK,
  platform VARCHAR(30),
  version_number INT,
  caption TEXT,
  hashtags VARCHAR[],
  title TEXT,
  description TEXT,
  created_by VARCHAR(50),
  created_at TIMESTAMPTZ,
  UNIQUE(content_id, platform, version_number)
)

-- Publication records
publication_records (
  id UUID PK,
  content_id UUID FK,
  render_asset_id UUID FK,
  social_metadata_id UUID FK,
  platform VARCHAR(30),
  platform_content_id VARCHAR(200),
  scheduled_for TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  status VARCHAR(30),  -- SCHEDULED/PUBLISHING/PUBLISHED/FAILED
  error_message TEXT,
  retry_count INT,
  created_at, updated_at TIMESTAMPTZ
)

-- Publishing schedule (calendar)
publishing_schedule (
  id UUID PK,
  content_id UUID FK,
  platform VARCHAR(30),
  scheduled_time TIMESTAMPTZ,
  time_slot_reason TEXT,  -- "Instagram prime time", "Avoid same-day Mimi"
  status VARCHAR(30),
  created_by VARCHAR(50),
  created_at TIMESTAMPTZ
)

-- Platform webhook events
platform_webhook_events (
  id UUID PK,
  publication_record_id UUID FK,
  platform VARCHAR(30),
  event_type VARCHAR(50),
  payload JSONB,
  received_at TIMESTAMPTZ
)
```

### APIs (Phase 3)

**OAuth & Credentials**
```
GET    /api/v1/platforms
POST   /api/v1/platforms/{platform}/auth/initiate
GET    /api/v1/platforms/{platform}/auth/callback
POST   /api/v1/platforms/{platform}/auth/refresh
DELETE /api/v1/platforms/{platform}/auth/revoke
GET    /api/v1/platforms/{platform}/permissions
```

**Social Metadata**
```
POST   /api/v1/contents/{id}/social-metadata
GET    /api/v1/contents/{id}/social-metadata
POST   /api/v1/contents/{id}/generate-caption
```

**Publishing**
```
POST   /api/v1/contents/{id}/schedule-publish
POST   /api/v1/contents/{id}/publish-now
GET    /api/v1/publications
GET    /api/v1/publications/{id}/status
POST   /api/v1/publications/{id}/cancel
GET    /api/v1/publishing-calendar
POST   /api/v1/publishing-calendar/bulk-schedule
```

**Webhooks (platform-initiated)**
```
POST   /api/v1/webhooks/tiktok
POST   /api/v1/webhooks/youtube
POST   /api/v1/webhooks/meta
```

---

## Phase 4: Learning Engine

**Scope:** Metrics collection, trajectory analysis, benchmarking, rule mining, human approval loop

### Key Components

**1. Metrics Collector**
- Scheduled polling (T+30m, T+1h, T+2h, T+3h, T+6h, T+12h, T+24h, T+48h, T+7d)
- Platform API integration
- Manual metric entry UI (for unavailable data)
- Normalized metric model across platforms

**2. Trajectory Engine**
- Time-series analysis
- Wave detection (primary, secondary, tertiary)
- Velocity/acceleration calculation
- Plateau detection
- Decay rate measurement
- Comparative trajectory plotting

**3. Performance Classifier**
- Automatic classification (EARLY_REJECTION, WEAK, MEDIUM, STRONG_START, BREAKOUT, DELAYED_BREAKOUT, MULTI_WAVE, PERSISTENT_WINNER, LONG_TAIL, EVERGREEN_BREAKOUT)
- Confidence scoring
- Reclassification on new data

**4. Benchmark Engine**
- Winner catalog (top performers per character/engine)
- Similarity matching
- Trajectory comparison
- Expected vs actual performance analysis

**5. Correlation Analyzer**
- Prompt quality scores ↔ performance metrics
- Creative structure ↔ retention/completion
- Statistical significance testing
- Effect size calculation

**6. Rule Mining Engine**
- Pattern detection across winners/losers
- Hypothesis generation
- Evidence collection
- Confidence scoring
- Rule candidate creation

**7. Rule Approval Workflow**
- Human review queue
- Evidence visualization
- A/B test suggestions
- Approve/reject/modify
- Ruleset version bump on approval

**8. Creative DNA Tagger**
- Extract creative structure from content
- Tag: engine, mechanic, beat count, consequence count, hook type, final type, loopability
- Enable structure-based queries

### Data Model (Phase 4)

**New Tables:**
```sql
-- Metric snapshots
metric_snapshots (
  id UUID PK,
  publication_record_id UUID FK,
  platform VARCHAR(30),
  measurement_time TIMESTAMPTZ,
  time_since_publish_minutes INT,
  views BIGINT, reach BIGINT, unique_viewers BIGINT,
  likes BIGINT, comments BIGINT, shares BIGINT, saves BIGINT,
  follows BIGINT, avg_watch_seconds NUMERIC(5,2),
  completion_rate NUMERIC(5,4), skip_rate NUMERIC(5,4),
  non_follower_percentage NUMERIC(5,4),
  us_audience_percentage NUMERIC(5,4),
  country_distribution JSONB,
  collected_at TIMESTAMPTZ,
  collection_method VARCHAR(30)  -- API/MANUAL/WEBHOOK
)

-- Trajectories (derived)
performance_trajectories (
  id UUID PK,
  publication_record_id UUID FK,
  platform VARCHAR(30),
  velocity_t1h NUMERIC(10,2),
  velocity_t6h NUMERIC(10,2),
  velocity_t24h NUMERIC(10,2),
  acceleration_early NUMERIC(10,2),
  acceleration_late NUMERIC(10,2),
  primary_wave_peak_time INT,  -- minutes
  secondary_wave_detected BOOLEAN,
  plateau_detected BOOLEAN,
  decay_rate NUMERIC(5,4),
  tail_strength VARCHAR(20),  -- STRONG/MEDIUM/WEAK
  calculated_at TIMESTAMPTZ
)

-- Performance classifications
performance_classifications (
  id UUID PK,
  content_id UUID FK,
  publication_record_id UUID FK,
  classification VARCHAR(50),
  confidence NUMERIC(3,2),
  classification_time TIMESTAMPTZ,  -- T+24h, T+7d
  is_final BOOLEAN
)

-- Benchmark comparisons
benchmark_comparisons (
  id UUID PK,
  content_id UUID FK,
  benchmark_content_id UUID FK,
  similarity_score NUMERIC(3,2),
  similarity_factors JSONB,
  trajectory_comparison JSONB,
  created_at TIMESTAMPTZ
)

-- Creative DNA tags
creative_dna_tags (
  id UUID PK,
  content_id UUID FK,
  creative_engine VARCHAR(100),
  primary_mechanic TEXT,
  beat_count INT,
  consequence_count INT,
  hook_type VARCHAR(50),
  final_type VARCHAR(50),
  loop_type VARCHAR(50),
  complexity_score NUMERIC(3,2),
  novelty_score NUMERIC(3,2),
  ai_risk_score NUMERIC(3,2)
)

-- Correlations (learned)
quality_performance_correlations (
  id UUID PK,
  rule_family VARCHAR(50),
  rule_criterion VARCHAR(50),
  performance_metric VARCHAR(50),
  time_horizon_minutes INT,
  sample_size INT,
  correlation_coefficient NUMERIC(5,4),
  p_value NUMERIC(10,8),
  effect_size NUMERIC(5,4),
  confidence VARCHAR(20),
  evidence JSONB,
  calculated_at TIMESTAMPTZ
)

-- Rule candidates
rule_candidates (
  id UUID PK,
  candidate_rule_id VARCHAR(50),
  hypothesis TEXT,
  rule_family VARCHAR(50),
  proposed_threshold NUMERIC(10,4),
  proposed_severity VARCHAR(20),
  evidence_sample_size INT,
  evidence_data JSONB,
  confidence VARCHAR(20),
  status VARCHAR(30),  -- PENDING/APPROVED/REJECTED/TESTING
  created_at TIMESTAMPTZ,
  reviewed_at TIMESTAMPTZ,
  reviewed_by VARCHAR(50),
  review_notes TEXT
)

-- Rule evidence levels
rule_evidence_levels (
  id UUID PK,
  ruleset_version VARCHAR(10),
  rule_id VARCHAR(50),
  evidence_level VARCHAR(30),  -- THEORETICAL/OBSERVED/SUPPORTED/STRONGLY_SUPPORTED
  supporting_content_ids UUID[],
  last_updated TIMESTAMPTZ
)
```

### APIs (Phase 4)

**Metrics Collection**
```
POST   /api/v1/publications/{id}/collect-metrics
POST   /api/v1/publications/{id}/manual-metrics
GET    /api/v1/publications/{id}/metrics
GET    /api/v1/publications/{id}/trajectory
```

**Performance Analysis**
```
GET    /api/v1/contents/{id}/performance-summary
GET    /api/v1/contents/{id}/benchmark-comparison
GET    /api/v1/analytics/winners
GET    /api/v1/analytics/underperformers
GET    /api/v1/analytics/correlations
```

**Rule Mining**
```
GET    /api/v1/rule-candidates
POST   /api/v1/rule-candidates/generate
GET    /api/v1/rule-candidates/{id}
POST   /api/v1/rule-candidates/{id}/approve
POST   /api/v1/rule-candidates/{id}/reject
POST   /api/v1/rule-candidates/{id}/test
```

**Reports**
```
GET    /api/v1/reports/daily
GET    /api/v1/reports/weekly
GET    /api/v1/reports/character/{characterId}
GET    /api/v1/reports/creative-engine/{engine}
```

---

## Shared Infrastructure

### State Machine Engine

Generic state machine implementation for:
- Content lifecycle
- Render jobs
- Publication records
- Rule candidate approvals

Features:
- Transition validation
- Audit logging
- Event hooks
- Retry logic
- Timeout handling

### LLM Provider Abstraction

```java
interface LlmProvider {
    String getName();
    boolean isAvailable();
    LlmResponse complete(LlmRequest request);
    int getTokenCount(String text);
    double estimateCost(int tokens);
}
```

Implementations:
- `OpenAiProvider` (GPT-4o)
- `ClaudeProvider` (Claude 3.5 Sonnet)
- `GeminiProvider` (Gemini 2.0 Flash)
- `OllamaProvider` (local Qwen/Llama)

Configuration:
```yaml
llm:
  provider: openai  # openai|claude|gemini|ollama
  openai:
    api-key: ${OPENAI_API_KEY}
    model: gpt-4o
  claude:
    api-key: ${CLAUDE_API_KEY}
    model: claude-3-5-sonnet-20241022
```

### Secrets Management

**Never store secrets in plain text.**

Options:
1. OS Keychain integration (macOS Keychain, Windows Credential Manager)
2. Encrypted database column (with key rotation)
3. Environment variables (local dev only)

All platform OAuth tokens encrypted at rest.

### Audit Log

Every critical action logged:
- State transitions
- Rule overrides
- Manual metric entries
- Render approvals
- Publication actions
- Rule candidate approvals

Searchable, filterable, exportable.

### Local Filesystem Structure

```
{POMPOM_DATA_ROOT}/
  content/
    {content-id}/
      concept.json
      prompt-v1.txt
      prompt-v2.txt
      prompt-v3.txt
      validation-v1.json
      validation-v2.json
      validation-v3.json
      first-frame-v1.png
      first-frame-v2.png
      render-v1.mp4
      render-v2.mp4
      render-qa-v1.json
      render-qa-v2.json
      social-metadata-tiktok-v1.json
      social-metadata-youtube-v1.json
      publication-tiktok.json
      publication-youtube.json
      metrics-tiktok.json
      metrics-youtube.json
  rules/
    ruleset-1.0.yaml
    ruleset-1.1.yaml
    ruleset-1.2.yaml
  references/
    mimi-clean-dirty/
    kiko-slippery-rough/
    opa-old-new/
    arda-sharp-blunt/
```

Database is source of truth; filesystem is durable storage.

---

## Non-Functional Requirements

### Performance
- Prompt validation: <5s
- Concept validation: <2s
- Render job polling: 30s intervals
- Metric collection: scheduled (not blocking)
- UI responsiveness: <200ms for most actions

### Scalability
- Single-user local deployment (Phase 1-3)
- Multi-user cloud deployment (future)
- 1000+ content items supported
- 10+ concurrent render jobs

### Reliability
- Retry logic for all external APIs (3 attempts)
- Graceful degradation (LLM unavailable → skip semantic validation)
- Data durability (PostgreSQL + filesystem backups)
- State recovery (interrupted jobs resume)

### Security
- Encrypted credentials at rest
- OAuth tokens never logged
- Audit trail for all sensitive actions
- No secrets in version control

### Observability
- Structured logging (JSON format)
- Metrics export (Prometheus-compatible)
- Health checks (Spring Actuator)
- Error tracking (integration with Sentry/similar)

---

## Migration Strategy

### From Current System

**Existing entities to keep:**
- `videos` table → link to `contents` via `content_id` FK
- `characters` table → unchanged, expand with stats
- `creative_analyses` → keep for post-render analysis
- `performance_observations` → link to `publication_records`

**New entities:**
- `contents` (root aggregate)
- `prompt_versions`
- `validation_runs`
- `render_jobs`
- `publication_records`
- `metric_snapshots`
- `rule_candidates`

**Migration path:**
- Phase 1: Add new tables, keep existing
- Phase 2: Link `videos` → `contents`
- Phase 3: Link `performance_observations` → `publication_records`
- Phase 4: Migrate old data (optional)

---

## Success Metrics (Per Phase)

### Phase 1
- ✅ Catch Kiko static state before render
- ✅ Catch Opa repetition before render
- ✅ Catch Arda cycle before render
- ✅ Mimi passes with score >92
- ✅ Version diff detects regressions
- ✅ Golden tests pass on rule changes

### Phase 2
- ✅ Render Mimi via OpenArt MCP/CLI
- ✅ Detect render compliance issues
- ✅ Avoid 1+ unnecessary rerenders
- ✅ Track credit savings

### Phase 3
- ✅ Publish to TikTok with one click
- ✅ Publish to YouTube with one click
- ✅ Schedule 10+ videos in calendar

### Phase 4
- ✅ Collect metrics for 20+ videos
- ✅ Detect 3+ significant correlations
- ✅ Generate 5+ rule candidates
- ✅ Approve and activate 1+ new rule

---

## Open Questions & Decisions Needed

### Technical
- [ ] OpenArt MCP server vs CLI tool? (Recommend MCP for programmatic access)
- [ ] Real-time vs scheduled metric collection? (Recommend scheduled with manual override)
- [ ] Embedded ML models for offline operation? (Recommend cloud LLM for Phase 1)

### Product
- [ ] Auto-publish without human approval? (Recommend human gate for Phase 3, conditional auto in Phase 4)
- [ ] Rule candidate auto-activation threshold? (Recommend never auto, always human approval)
- [ ] Max concurrent render jobs? (Recommend 3-5 based on OpenArt rate limits)

### Infrastructure
- [ ] Always-on service for scheduled tasks? (Local for Phase 1-3, cloud option for Phase 4)
- [ ] Backup strategy for local PostgreSQL? (Recommend automated daily backups to external drive)
- [ ] Secrets management tool? (Recommend OS Keychain for macOS, environment variables fallback)

---

## Next Steps

1. ✅ Review and approve this Master Architecture
2. → Design Phase 1 (Creative Quality Engine) in detail
3. → Implement Phase 1 (2-3 weeks)
4. → Design Phase 2 (Production Engine)
5. → Implement Phase 2 (2-3 weeks)
6. → Design Phase 3 (Distribution Engine)
7. → Implement Phase 3 (2-3 weeks)
8. → Design Phase 4 (Learning Engine)
9. → Implement Phase 4 (3-4 weeks)

---

**Document Status:** DRAFT  
**Review Required:** Yes  
**Implementation:** Not Started
