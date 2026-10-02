# Pompom Ruleset Engine — Architecture

## Overview

Standalone Spring Boot microservice responsible for:
1. Pre-render creative validation (concept gate)
2. Post-publish performance analysis
3. Learning-based rule evolution

## Design Principles

### The Validator Must Protect Credits, Not Design the Video

The ruleset prevents bad concepts from consuming credits, but does NOT:
- Micromanage frame-by-frame choreography
- Dictate exact timing of every action
- Over-constrain the creative generation process

### Quality Over Duration — Golden Rule

Duration targets are guidelines. If progression/diversity requires more time, allow it.
If concept is complete in less time, don't artificially extend.

### Evidence-Based Rules

Every rule tracks its evidence level:
- `THEORETICAL` — Hypothesis, not yet tested
- `OBSERVED` — Seen in limited data
- `SUPPORTED` — Consistent across multiple examples
- `STRONGLY_SUPPORTED` — Repeatedly validated

Rules auto-activate only after human approval.

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    REST API Layer                            │
│  /api/ruleset/v1/validate    /api/ruleset/v1/performance     │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│                  Service Layer                               │
│                                                              │
│  ConceptValidationService  PerformanceAnalysisService       │
│  LearningEngineService     RuleEvaluationService            │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│                  Domain Model                                │
│                                                              │
│  Rule, RuleEvaluation, ConceptValidation,                   │
│  PerformanceScore, CandidateRule, RuleEvidence              │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│                  Data Layer                                  │
│                                                              │
│  PostgreSQL:  rules, evaluations, performance_scores,       │
│               candidate_rules, golden_test_cases            │
└─────────────────────────────────────────────────────────────┘
```

## Rule Evaluation Flow

### Pre-Render (Concept Gate)

```
1. Client submits concept for validation
   ↓
2. Load active rules (category=CONCEPT, severity>=HIGH)
   ↓
3. For each rule:
   - If evaluation=CODE → run Java evaluator
   - If evaluation=LLM → call OpenAI with rule prompt
   - If evaluation=HYBRID → run both, combine results
   ↓
4. Aggregate results:
   - CRITICAL fail → REJECTED
   - HIGH fail → WARNING (allow with flag)
   - MEDIUM fail → INFO
   ↓
5. Return validation response with:
   - approved: boolean
   - overallScore: 0-100
   - ruleResults: [{ruleId, passed, reason, score}]
   - recommendations: [string]
```

### Post-Publish (Performance Analysis)

```
1. Client submits videoId + platform metrics
   ↓
2. Load performance rules for platform
   ↓
3. Calculate derived metrics:
   - avgWatchRatio = avgWatchSec / duration
   - entryProxy = 3secViews / reach
   - viewsPerViewer = views / uniqueViewers
   ↓
4. Evaluate thresholds:
   - Compare against platform-specific benchmarks
   - Classify: WEAK / VIABLE / STRONG / EXCEPTIONAL
   ↓
5. Detect velocity patterns:
   - Compare snapshots (T+30m, T+1h, T+2h, ...)
   - Classify wave: EARLY_REJECTION, STRONG_START,
     SECOND_WAVE, DELAYED_BREAKOUT, etc.
   ↓
6. Calculate dimension scores:
   - hookStrength, progression, attemptDiversity,
     educationalClarity, finalPayoff, loopability
   ↓
7. Store PerformanceScore entity
   ↓
8. Trigger learning correlation check (async)
```

### Learning (Correlation Detection)

```
1. After N videos analyzed (N=10 initially):
   ↓
2. Query all PerformanceScore + RuleEvaluation pairs
   ↓
3. For each rule × performance metric:
   - Calculate correlation coefficient
   - Run statistical significance test
   ↓
4. If |correlation| > threshold AND p < 0.05:
   - Create CandidateRule entry
   - Set status = PENDING_REVIEW
   - Include evidence: correlation, sample size, examples
   ↓
5. Human reviews CandidateRule
   ↓
6. If approved:
   - Convert to active Rule
   - Set evidenceLevel = SUPPORTED
   ↓
7. If rejected:
   - Mark CandidateRule as REJECTED
   - Log reason
```

## Database Schema

### Core Tables

```sql
-- Rules definition
CREATE TABLE rules (
    id UUID PRIMARY KEY,
    rule_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(30) NOT NULL, -- CONCEPT, BEAT, MOTION, STORY, FINAL, etc.
    severity VARCHAR(20) NOT NULL, -- CRITICAL, HIGH, MEDIUM, LOW
    evaluation_type VARCHAR(20) NOT NULL, -- CODE, LLM, HYBRID
    description TEXT,
    yaml_definition JSONB NOT NULL,
    evidence_level VARCHAR(30) NOT NULL, -- THEORETICAL, OBSERVED, SUPPORTED, STRONGLY_SUPPORTED
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Validation results
CREATE TABLE concept_validations (
    id UUID PRIMARY KEY,
    external_concept_id VARCHAR(255), -- reference to Creative Intelligence system
    concept_text TEXT NOT NULL,
    approved BOOLEAN NOT NULL,
    overall_score DECIMAL(5,2), -- 0-100
    intent VARCHAR(50), -- GROWTH, EDUCATIONAL, EXPERIMENT, STOCK
    created_at TIMESTAMP NOT NULL
);

-- Individual rule evaluation results
CREATE TABLE rule_evaluations (
    id UUID PRIMARY KEY,
    validation_id UUID REFERENCES concept_validations(id),
    rule_id UUID REFERENCES rules(id),
    passed BOOLEAN NOT NULL,
    score DECIMAL(5,2),
    reason TEXT,
    details JSONB,
    evaluated_at TIMESTAMP NOT NULL
);

-- Performance scores
CREATE TABLE performance_scores (
    id UUID PRIMARY KEY,
    external_video_id VARCHAR(255) NOT NULL, -- reference to Creative Intelligence video
    platform VARCHAR(20) NOT NULL,
    intent VARCHAR(50),
    
    -- Raw metrics
    views BIGINT,
    likes BIGINT,
    comments BIGINT,
    shares BIGINT,
    saves BIGINT,
    reach BIGINT,
    impressions BIGINT,
    avg_watch_seconds DECIMAL(6,2),
    duration_seconds DECIMAL(6,2),
    completion_rate DECIMAL(5,2),
    three_second_views BIGINT,
    unique_viewers BIGINT,
    
    -- Derived metrics
    avg_watch_ratio DECIMAL(5,4),
    entry_proxy DECIMAL(5,4),
    views_per_viewer DECIMAL(5,2),
    end_retention_rate DECIMAL(5,2),
    
    -- Dimension scores
    hook_strength DECIMAL(5,2),
    progression_score DECIMAL(5,2),
    attempt_diversity_score DECIMAL(5,2),
    educational_clarity DECIMAL(5,2),
    final_payoff DECIMAL(5,2),
    loopability_score DECIMAL(5,2),
    
    -- Overall
    overall_quality DECIMAL(5,2),
    classification VARCHAR(30), -- WEAK, VIABLE, STRONG, EXCEPTIONAL
    wave_pattern VARCHAR(50),
    
    collected_at TIMESTAMP NOT NULL,
    time_since_publish_hours INTEGER
);

-- Learning: Candidate rules
CREATE TABLE candidate_rules (
    id UUID PRIMARY KEY,
    rule_code VARCHAR(50),
    name VARCHAR(255),
    category VARCHAR(30),
    description TEXT,
    correlation_metric VARCHAR(100),
    correlation_coefficient DECIMAL(5,4),
    p_value DECIMAL(10,8),
    sample_size INTEGER,
    example_video_ids JSONB,
    status VARCHAR(30), -- PENDING_REVIEW, APPROVED, REJECTED
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    rejection_reason TEXT,
    created_at TIMESTAMP NOT NULL
);

-- Learning: Rule evidence tracking
CREATE TABLE rule_evidence (
    id UUID PRIMARY KEY,
    rule_id UUID REFERENCES rules(id),
    evidence_type VARCHAR(50), -- POSITIVE_CORRELATION, NEGATIVE_EXAMPLE, A_B_TEST, etc.
    video_id VARCHAR(255),
    metric_name VARCHAR(100),
    metric_value DECIMAL(10,4),
    notes TEXT,
    recorded_at TIMESTAMP NOT NULL
);

-- Golden test cases
CREATE TABLE golden_test_cases (
    id UUID PRIMARY KEY,
    test_name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(30), -- POSITIVE, NEGATIVE
    concept_text TEXT NOT NULL,
    expected_approved BOOLEAN NOT NULL,
    expected_failing_rules JSONB, -- [rule_code1, rule_code2, ...]
    notes TEXT,
    created_at TIMESTAMP NOT NULL
);
```

## Integration Points

### From Creative Intelligence Backend

```java
// Pre-render validation
POST /api/ruleset/v1/validate/concept
{
  "externalConceptId": "content-123",
  "conceptText": "Giant spoon that gets bigger every pour...",
  "intent": "GROWTH",
  "estimatedDuration": 15.0,
  "characters": ["Kiko"],
  "location": "Kitchen Lab"
}

Response:
{
  "validationId": "uuid",
  "approved": true,
  "overallScore": 87.5,
  "ruleResults": [
    {
      "ruleCode": "CONCEPT_001",
      "ruleName": "Immediate Visual Anomaly",
      "passed": true,
      "score": 95.0,
      "reason": "Giant spoon is immediately visible and unusual"
    },
    {
      "ruleCode": "BEAT_001",
      "ruleName": "Attempt Diversity",
      "passed": true,
      "score": 80.0,
      "reason": "Multiple distinct actions: POUR, ADD, STIR, DRINK, EMPTY"
    }
  ],
  "recommendations": [
    "Strong loopability potential - final could flow back to opening"
  ]
}
```

```java
// Post-publish analysis
POST /api/ruleset/v1/performance/analyze
{
  "externalVideoId": "pub-job-uuid",
  "platform": "META_INSTAGRAM",
  "intent": "GROWTH",
  "durationSeconds": 15.0,
  "publishedAt": "2026-09-15T23:00:00Z",
  "metrics": {
    "views": 25430,
    "likes": 1240,
    "comments": 45,
    "shares": 230,
    "saves": 180,
    "reach": 31650,
    "avgWatchTimeSeconds": 16.8,
    "completionRate": 54.2,
    "threeSecondViews": 25100,
    "uniqueViewers": 8760
  },
  "timeSincePublishHours": 48
}

Response:
{
  "performanceId": "uuid",
  "overallQuality": 92.3,
  "classification": "STRONG",
  "wavePattern": "STRONG_START_THEN_SECOND_WAVE",
  "dimensionScores": {
    "hookStrength": 95.0,
    "progressionScore": 88.0,
    "attemptDiversityScore": 85.0,
    "finalPayoff": 90.0,
    "loopability": 98.0
  },
  "derivedMetrics": {
    "avgWatchRatio": 1.12,
    "entryProxy": 0.793,
    "viewsPerViewer": 2.9,
    "endRetentionRate": 54.2
  },
  "insights": [
    "Exceptional loopability: avg watch > duration suggests replay",
    "Strong entry proxy (79%) - hook works immediately",
    "High views/viewer ratio indicates replay behavior"
  ]
}
```

## Technology Stack

- **Java 21**
- **Spring Boot 3.2+**
- **PostgreSQL 15+** with JSONB support
- **OpenAI API** for LLM-based rule evaluation
- **Liquibase** for database migrations
- **JUnit 5 + Testcontainers** for testing

## Deployment

Standalone JAR, deployable via:
- Docker container
- Kubernetes pod
- Traditional app server

Environment variables:
```
DATABASE_URL=jdbc:postgresql://localhost:5432/ruleset
OPENAI_API_KEY=sk-...
SPRING_PROFILES_ACTIVE=production
```

## Monitoring

Metrics exposed via Spring Actuator:
- `/actuator/health` — Health check
- `/actuator/metrics` — Rule evaluation counts, latencies
- `/actuator/prometheus` — Prometheus export

Key metrics:
- `ruleset.validation.total` — Total validations
- `ruleset.validation.rejected` — Rejected concepts
- `ruleset.performance.analyzed` — Videos analyzed
- `ruleset.learning.correlations.detected` — Correlations found
