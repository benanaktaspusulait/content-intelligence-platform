# Performance Feedback Loop

The feedback loop connects quality validation predictions with actual video performance metrics to continuously improve rule accuracy.

## Architecture

```
Prompt → Quality Engine → [Validation Score/Status]
                              ↓
                         [RENDER VIDEO]
                              ↓
                         [PUBLISH TO YOUTUBE/SOCIAL]
                              ↓
                         [COLLECT METRICS: views, retention, engagement]
                              ↓
                         [Feedback Collector]
                              ↓
                    [Performance Analyzer: actual vs predicted]
                              ↓
                    [Rule Learner: adjust thresholds, weights]
                              ↓
                    [Generate RULESET_1.1 / 2.0]
```

## Components

### `performance_metrics.py`
Defines performance metric data structures.

**Key Metrics:**
- **Views:** Total view count, view velocity (views/hour)
- **Retention:** Average watch percentage, drop-off points
- **Engagement:** Likes, comments, shares, CTR
- **Platform-specific:** YouTube watch time, TikTok completion rate, Instagram saves

**Performance Tiers:**
- **EXCELLENT:** Top 10% of similar content
- **GOOD:** Top 25%
- **ACCEPTABLE:** Top 50%
- **WEAK:** Bottom 50%
- **POOR:** Bottom 25%

### `feedback_collector.py`
Collects and stores performance data for rendered videos.

**Data Flow:**
1. Video published → YouTube/TikTok/Instagram API data
2. Manual entry via UI (for testing)
3. Batch import from analytics CSV
4. PostgreSQL storage with video_performance table

**Tracking:**
- Links prompt_id → video_id → performance metrics
- Time-series data (24h, 7d, 30d snapshots)
- Platform-specific metrics

### `performance_analyzer.py`
Compares predicted quality vs actual performance.

**Analysis:**
- **Correlation:** Quality score vs view count
- **Prediction accuracy:** RENDER_READY prompts that performed poorly
- **False negatives:** BLOCKED prompts that would have performed well (requires human override test)
- **Family analysis:** Which quality families correlate strongest with performance

**Output:**
- Correlation matrix (11 families × performance metrics)
- Misprediction report (over-optimistic, over-pessimistic)
- Family importance ranking

### `rule_learner.py`
Adjusts rule thresholds and weights based on performance data.

**Learning Strategies:**

1. **Threshold Adjustment:**
   - If BEAT_004 (static state 30%) videos perform well → relax to 35%
   - If videos with 4 consequences still fail → raise CONCEPT_006 to 5

2. **Weight Adjustment:**
   - If Visual Novelty family correlates strongly with views → increase weight from 18% to 22%
   - If Escalation shows weak correlation → decrease weight

3. **Severity Adjustment:**
   - If WARNING violations don't hurt performance → downgrade to INFO
   - If consistent CRITICAL failures → upgrade to BLOCKER

4. **New Rule Discovery:**
   - Detect patterns in high-performers that aren't captured by current rules
   - Generate candidate rules for human review

**Safety:**
- Minimum 50 samples before threshold adjustment
- Maximum 20% change per version
- Human approval required for BLOCKER changes
- A/B testing for controversial changes

### `version_generator.py`
Creates new ruleset versions based on learned adjustments.

**Versioning:**
- **Patch (1.0 → 1.0.1):** Threshold tweaks <10%, no severity changes
- **Minor (1.0 → 1.1):** New rules, weight adjustments, WARNING severity changes
- **Major (1.0 → 2.0):** Breaking changes, BLOCKER/CRITICAL severity changes, removed rules

**Output:**
- New RULESET_X.Y.yaml
- Updated versions.yaml with changelog
- Migration guide for users
- Performance comparison report

## Database Schema

### `video_performance` Table

```sql
CREATE TABLE video_performance (
    id BIGSERIAL PRIMARY KEY,
    video_id VARCHAR(255) NOT NULL UNIQUE,
    prompt_id VARCHAR(255),
    validation_id BIGINT REFERENCES quality_validations(id),
    
    -- Video metadata
    title TEXT,
    platform VARCHAR(50),
    published_at TIMESTAMP,
    duration_seconds INT,
    
    -- Performance metrics (updated periodically)
    views_24h INT DEFAULT 0,
    views_7d INT DEFAULT 0,
    views_30d INT DEFAULT 0,
    views_total INT DEFAULT 0,
    
    retention_avg_pct DECIMAL(5,2),
    retention_30s_pct DECIMAL(5,2),
    
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    shares INT DEFAULT 0,
    
    ctr_pct DECIMAL(5,2),
    engagement_rate DECIMAL(5,2),
    
    -- Performance tier
    performance_tier VARCHAR(20), -- EXCELLENT/GOOD/ACCEPTABLE/WEAK/POOR
    
    -- Prediction vs reality
    predicted_score DECIMAL(5,2),
    predicted_status VARCHAR(20),
    actual_performance_match BOOLEAN,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_video_performance_prompt ON video_performance(prompt_id);
CREATE INDEX idx_video_performance_validation ON video_performance(validation_id);
CREATE INDEX idx_video_performance_tier ON video_performance(performance_tier);
CREATE INDEX idx_video_performance_published ON video_performance(published_at);
```

### `rule_learning_history` Table

```sql
CREATE TABLE rule_learning_history (
    id BIGSERIAL PRIMARY KEY,
    ruleset_version_from VARCHAR(10),
    ruleset_version_to VARCHAR(10),
    
    rule_id VARCHAR(50),
    change_type VARCHAR(50), -- THRESHOLD_ADJUST/WEIGHT_ADJUST/SEVERITY_CHANGE
    
    old_value JSONB,
    new_value JSONB,
    
    reason TEXT,
    evidence_sample_size INT,
    confidence_score DECIMAL(5,2),
    
    approved BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(100),
    approved_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage

### 1. Record Performance Data

```python
from app.feedback.feedback_collector import FeedbackCollector

collector = FeedbackCollector()

# After video published
collector.record_performance(
    video_id="yt_abc123",
    prompt_id="prompt_001",
    validation_id=42,
    platform="youtube",
    metrics={"views_24h": 1500, "retention_avg_pct": 68.5, "likes": 45, "comments": 12, "ctr_pct": 8.2},
)
```

### 2. Analyze Performance

```python
from app.feedback.performance_analyzer import PerformanceAnalyzer

analyzer = PerformanceAnalyzer()

# Analyze last 100 videos
report = analyzer.analyze_recent(limit=100)

print(f"Correlation: Quality Score vs Views = {report.correlation_score_views:.2f}")
print(f"False positives: {report.false_positive_count}")
print(f"False negatives: {report.false_negative_count}")
print(f"Top correlated family: {report.top_family}")
```

### 3. Learn and Generate New Ruleset

```python
from app.feedback.rule_learner import RuleLearner
from app.feedback.version_generator import VersionGenerator

learner = RuleLearner(min_samples=50)
adjustments = learner.learn_from_performance(ruleset_version="1.0")

print(f"Proposed adjustments: {len(adjustments)}")
for adj in adjustments:
    print(f"  {adj.rule_id}: {adj.change_type} ({adj.confidence:.0%} confidence)")

# Generate new version (requires approval)
generator = VersionGenerator()
new_version = generator.create_version(
    from_version="1.0",
    adjustments=adjustments,
    description="Performance-based threshold adjustments from 100 video sample",
)

print(f"New version: {new_version.version}")
print(f"Breaking: {new_version.is_breaking}")
```

## API Endpoints

### POST `/api/v1/feedback/record`
Record video performance metrics

### POST `/api/v1/feedback/analyze`
Analyze prediction accuracy and correlations

### GET `/api/v1/feedback/insights/{ruleset_version}`
Get performance insights for a ruleset version

### POST `/api/v1/feedback/learn`
Trigger learning process and generate adjustment proposals

### POST `/api/v1/feedback/approve-adjustment/{adjustment_id}`
Approve a proposed rule adjustment (requires admin)

## Metrics Dashboard (Angular)

Performance insights UI showing:
- Correlation heatmap (families vs metrics)
- Prediction accuracy chart
- Misprediction case studies
- Proposed adjustments with approve/reject
- A/B test results

## Safety & Ethics

### Human-in-the-Loop
- All BLOCKER/CRITICAL adjustments require human approval
- Proposed changes reviewed by content team
- Override capability for domain expertise

### Sample Size Requirements
- Minimum 50 videos before threshold adjustment
- Minimum 100 videos before weight adjustment
- Confidence intervals displayed for all metrics

### Avoid Overfitting
- Holdout validation set (20% of data)
- Performance on unseen videos tracked
- Rolling window (last 90 days) to adapt to trends

### Explainability
- Every adjustment includes evidence (sample videos, correlation stats)
- Changelog documents why each change was made
- Revert capability if new version underperforms

## Phase 2 Enhancements

1. **A/B Testing:** Deploy two ruleset versions, compare performance
2. **Multi-objective optimization:** Balance views + retention + engagement
3. **Reinforcement learning:** Treat validation as RL policy, optimize for long-term performance
4. **Causal inference:** Distinguish correlation from causation
5. **Real-time adaptation:** Adjust rules dynamically based on live performance

## Performance Targets

- **Prediction accuracy:** 75%+ of RENDER_READY prompts perform GOOD or better
- **False positive rate:** <10% of RENDER_READY prompts perform POOR
- **False negative rate:** <5% of BLOCKED prompts would have performed EXCELLENT
- **Correlation:** Quality score vs views r>0.6

## Monitoring

- Weekly performance report emailed to content team
- Slack alert if prediction accuracy drops below 70%
- Dashboard showing live validation→performance pipeline health
