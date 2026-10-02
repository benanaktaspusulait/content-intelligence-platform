# Phase 4: Learning Engine - Detailed Specification

**Date:** September 30, 2026  
**Version:** 1.0  
**Status:** Draft  
**Dependencies:** Phase 3 (Distribution Engine) complete

---

## Executive Summary

Phase 4 closes the loop: collect performance metrics from published videos, analyze trajectories, identify patterns, mine new creative rules from winners/losers, and propose rule candidates for human approval. The system learns from every video to improve its own creative validation rules over time.

**Scope:** Metrics collection → Trajectory analysis → Pattern mining → Rule candidate generation → Human approval loop

**Success Criteria:**
- Collect metrics for 50+ published videos
- Classify 10+ videos as WINNER/WEAK/BREAKOUT
- Detect 3+ significant correlations (quality score ↔ performance)
- Generate 5+ rule candidates with evidence
- Approve and activate 1+ new rule into production ruleset

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LEARNING ENGINE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  METRICS         │      │  TRAJECTORY      │            │
│  │  COLLECTOR       │──────│  ANALYZER        │            │
│  │  (Scheduled)     │      │  (Time-series)   │            │
│  └──────────────────┘      └──────────────────┘            │
│           │                         │                       │
│           ↓                         ↓                       │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  PERFORMANCE     │      │  BENCHMARK       │            │
│  │  CLASSIFIER      │──────│  ENGINE          │            │
│  │  (10 classes)    │      │  (Winners)       │            │
│  └──────────────────┘      └──────────────────┘            │
│           │                         │                       │
│           ↓                         ↓                       │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  CORRELATION     │      │  RULE MINING     │            │
│  │  ANALYZER        │──────│  ENGINE          │            │
│  │  (Statistical)   │      │  (Pattern detect)│            │
│  └──────────────────┘      └──────────────────┘            │
│           │                         │                       │
│           ↓                         ↓                       │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  RULE CANDIDATE  │      │  HUMAN APPROVAL  │            │
│  │  GENERATOR       │──────│  WORKFLOW        │            │
│  │  (Hypothesis)    │      │  (Review UI)     │            │
│  └──────────────────┘      └──────────────────┘            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│              EXTERNAL INTEGRATIONS                          │
│  • TikTok Analytics API                                     │
│  • YouTube Analytics API                                    │
│  • Meta Insights API                                        │
│  • Statistical analysis (scipy, statsmodels)                │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema (Phase 4)

```sql
-- Metric snapshots (time-series data)
CREATE TABLE metric_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_record_id UUID NOT NULL REFERENCES publication_records(id),
    
    -- Measurement timing
    measurement_time TIMESTAMPTZ NOT NULL,
    time_since_publish_minutes INT NOT NULL,
    
    -- Platform
    platform VARCHAR(30) NOT NULL,
    
    -- Engagement metrics
    views BIGINT NOT NULL DEFAULT 0,
    reach BIGINT,
    unique_viewers BIGINT,
    
    -- Interaction metrics
    likes BIGINT NOT NULL DEFAULT 0,
    comments BIGINT NOT NULL DEFAULT 0,
    shares BIGINT NOT NULL DEFAULT 0,
    saves BIGINT NOT NULL DEFAULT 0,
    follows BIGINT NOT NULL DEFAULT 0,
    
    -- Retention metrics
    avg_watch_seconds NUMERIC(5,2),
    watch_time_total_hours NUMERIC(10,2),
    completion_rate NUMERIC(5,4),  -- 0.0-1.0
    skip_rate NUMERIC(5,4),
    
    -- Audience metrics
    non_follower_percentage NUMERIC(5,4),
    us_audience_percentage NUMERIC(5,4),
    country_distribution JSONB,  -- {"US": 0.45, "UK": 0.12, ...}
    age_distribution JSONB,  -- {"18-24": 0.30, "25-34": 0.50, ...}
    
    -- Collection metadata
    collection_method VARCHAR(30) NOT NULL CHECK (
        collection_method IN ('API', 'MANUAL', 'WEBHOOK', 'ESTIMATED')
    ),
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_metric_snapshots_publication_id ON metric_snapshots(publication_record_id);
CREATE INDEX idx_metric_snapshots_measurement_time ON metric_snapshots(measurement_time);
CREATE INDEX idx_metric_snapshots_time_since_publish ON metric_snapshots(time_since_publish_minutes);

-- Performance trajectories (derived analytics)
CREATE TABLE performance_trajectories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_record_id UUID NOT NULL UNIQUE REFERENCES publication_records(id),
    content_id UUID NOT NULL REFERENCES contents(id),
    platform VARCHAR(30) NOT NULL,
    
    -- Velocity (views/hour)
    velocity_t1h NUMERIC(10,2),  -- First hour
    velocity_t6h NUMERIC(10,2),  -- 6 hours
    velocity_t24h NUMERIC(10,2),  -- 24 hours
    velocity_t7d NUMERIC(10,2),  -- 7 days
    
    -- Acceleration
    acceleration_early NUMERIC(10,2),  -- T0-T1h vs T1h-T6h
    acceleration_late NUMERIC(10,2),  -- T6h-T24h vs T24h-T7d
    
    -- Wave detection
    primary_wave_peak_time INT,  -- Minutes since publish
    primary_wave_peak_views BIGINT,
    secondary_wave_detected BOOLEAN NOT NULL DEFAULT FALSE,
    secondary_wave_peak_time INT,
    
    -- Plateau/decay
    plateau_detected BOOLEAN NOT NULL DEFAULT FALSE,
    plateau_start_time INT,
    decay_rate NUMERIC(5,4),  -- Views drop rate after plateau
    
    -- Tail strength
    tail_strength VARCHAR(20) CHECK (
        tail_strength IN ('STRONG', 'MEDIUM', 'WEAK', 'NONE')
    ),
    long_tail_views BIGINT,  -- Views after T+7d
    
    -- Metadata
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_performance_trajectories_content_id ON performance_trajectories(content_id);
CREATE INDEX idx_performance_trajectories_velocity_t24h ON performance_trajectories(velocity_t24h);

-- Performance classifications
CREATE TABLE performance_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES contents(id),
    publication_record_id UUID NOT NULL REFERENCES publication_records(id),
    
    -- Classification
    classification VARCHAR(50) NOT NULL CHECK (
        classification IN (
            'EARLY_REJECTION',      -- <1k views T+24h
            'WEAK',                 -- 1k-10k views T+7d
            'MEDIUM',               -- 10k-50k views T+7d
            'STRONG_START',         -- >50k T+24h, weak tail
            'BREAKOUT',             -- >100k T+7d, strong velocity
            'DELAYED_BREAKOUT',     -- Weak start, strong secondary wave
            'MULTI_WAVE',           -- 2+ distinct waves
            'PERSISTENT_WINNER',    -- Consistent velocity >7d
            'LONG_TAIL',            -- Strong views >30d
            'EVERGREEN_BREAKOUT'    -- >1M lifetime
        )
    ),
    
    -- Confidence
    confidence NUMERIC(3,2) NOT NULL,  -- 0.0-1.0
    
    -- Timing
    classification_time TIMESTAMPTZ NOT NULL,
    time_horizon VARCHAR(20) NOT NULL,  -- 'T+24h', 'T+7d', 'T+30d'
    is_final BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Supporting data
    total_views BIGINT NOT NULL,
    total_engagement BIGINT,  -- likes + comments + shares
    engagement_rate NUMERIC(5,4),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_performance_classifications_content_id ON performance_classifications(content_id);
CREATE INDEX idx_performance_classifications_classification ON performance_classifications(classification);
CREATE INDEX idx_performance_classifications_classification_time ON performance_classifications(classification_time);

-- Benchmark comparisons
CREATE TABLE benchmark_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES contents(id),
    benchmark_content_id UUID NOT NULL REFERENCES contents(id),
    
    -- Similarity factors
    similarity_score NUMERIC(3,2) NOT NULL,
    similarity_factors JSONB NOT NULL,  -- {character_match: 1.0, engine_match: 0.8, ...}
    
    -- Trajectory comparison
    trajectory_comparison JSONB NOT NULL,  -- {velocity_ratio: 0.85, pattern_match: 'similar', ...}
    
    -- Performance delta
    views_delta_percentage NUMERIC(7,2),  -- +150% or -30%
    engagement_delta_percentage NUMERIC(7,2),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_benchmark_comparisons_content_id ON benchmark_comparisons(content_id);
CREATE INDEX idx_benchmark_comparisons_similarity_score ON benchmark_comparisons(similarity_score);

-- Creative DNA tags (structural fingerprint)
CREATE TABLE creative_dna_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL UNIQUE REFERENCES contents(id),
    
    -- Core structure
    creative_engine VARCHAR(100),
    primary_mechanic TEXT,
    beat_count INT,
    consequence_count INT,
    
    -- Hook/final
    hook_type VARCHAR(50),
    hook_intensity INT,  -- 1-10
    final_type VARCHAR(50),
    final_satisfaction_score INT,  -- 1-10
    
    -- Loop characteristics
    loop_type VARCHAR(50) CHECK (
        loop_type IN ('NONE', 'WEAK', 'MODERATE', 'STRONG', 'INFINITE')
    ),
    loop_visual_consistency BOOLEAN,
    loop_audio_consistency BOOLEAN,
    
    -- Complexity scores
    complexity_score NUMERIC(3,2),  -- 0.0-1.0
    novelty_score NUMERIC(3,2),
    ai_risk_score NUMERIC(3,2),
    
    -- Extracted at
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_creative_dna_tags_creative_engine ON creative_dna_tags(creative_engine);
CREATE INDEX idx_creative_dna_tags_consequence_count ON creative_dna_tags(consequence_count);
CREATE INDEX idx_creative_dna_tags_complexity_score ON creative_dna_tags(complexity_score);

-- Correlations (learned patterns)
CREATE TABLE quality_performance_correlations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Rule context
    rule_family VARCHAR(50) NOT NULL,
    rule_criterion VARCHAR(50),
    
    -- Performance metric
    performance_metric VARCHAR(50) NOT NULL,  -- 'views_t24h', 'completion_rate', 'engagement_rate'
    time_horizon_minutes INT NOT NULL,
    
    -- Statistical analysis
    sample_size INT NOT NULL,
    correlation_coefficient NUMERIC(5,4) NOT NULL,  -- Pearson r: -1.0 to 1.0
    p_value NUMERIC(10,8) NOT NULL,
    effect_size NUMERIC(5,4),  -- Cohen's d
    
    -- Interpretation
    confidence VARCHAR(20) NOT NULL CHECK (
        confidence IN ('WEAK', 'MODERATE', 'STRONG', 'VERY_STRONG')
    ),
    direction VARCHAR(20) CHECK (
        direction IN ('POSITIVE', 'NEGATIVE', 'NO_CORRELATION')
    ),
    
    -- Evidence
    evidence JSONB NOT NULL,  -- Sample data, scatter plot points, outliers
    
    -- Metadata
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_correlations_rule_family ON quality_performance_correlations(rule_family);
CREATE INDEX idx_correlations_performance_metric ON quality_performance_correlations(performance_metric);
CREATE INDEX idx_correlations_confidence ON quality_performance_correlations(confidence);

-- Rule candidates (proposed rules)
CREATE TABLE rule_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Rule definition
    candidate_rule_id VARCHAR(50) NOT NULL UNIQUE,
    hypothesis TEXT NOT NULL,
    rule_family VARCHAR(50) NOT NULL,
    
    -- Threshold/criterion
    proposed_threshold NUMERIC(10,4),
    proposed_severity VARCHAR(20) CHECK (
        proposed_severity IN ('BLOCKER', 'CRITICAL', 'WARNING', 'PASS')
    ),
    proposed_message_template TEXT,
    
    -- Evidence
    evidence_sample_size INT NOT NULL,
    evidence_data JSONB NOT NULL,  -- Winner/loser examples, statistical data
    supporting_content_ids UUID[],
    
    -- Confidence
    confidence VARCHAR(20) NOT NULL CHECK (
        confidence IN ('LOW', 'MODERATE', 'HIGH', 'VERY_HIGH')
    ),
    confidence_score NUMERIC(3,2),
    
    -- Status
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (
        status IN ('PENDING', 'UNDER_REVIEW', 'TESTING', 'APPROVED', 'REJECTED', 'DEPRECATED')
    ),
    
    -- Review workflow
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by VARCHAR(50),
    review_notes TEXT,
    test_results JSONB,  -- A/B test results if tested
    
    -- Activation
    activated_at TIMESTAMPTZ,
    ruleset_version_activated VARCHAR(10),
    
    -- Metadata
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_rule_candidates_status ON rule_candidates(status);
CREATE INDEX idx_rule_candidates_confidence ON rule_candidates(confidence);
CREATE INDEX idx_rule_candidates_rule_family ON rule_candidates(rule_family);

-- Rule evidence levels (track confidence over time)
CREATE TABLE rule_evidence_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Rule reference
    ruleset_version VARCHAR(10) NOT NULL,
    rule_id VARCHAR(50) NOT NULL,
    
    -- Evidence level
    evidence_level VARCHAR(30) NOT NULL CHECK (
        evidence_level IN (
            'THEORETICAL',          -- Based on creative theory only
            'OBSERVED',             -- Seen in 1-5 cases
            'SUPPORTED',            -- Significant correlation (p<0.05, n>20)
            'STRONGLY_SUPPORTED'    -- Strong correlation (p<0.01, n>50+)
        )
    ),
    
    -- Supporting data
    supporting_content_ids UUID[],
    sample_size INT NOT NULL,
    correlation_data JSONB,
    
    -- Metadata
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rule_evidence_levels_rule_id ON rule_evidence_levels(rule_id);
CREATE INDEX idx_rule_evidence_levels_evidence_level ON rule_evidence_levels(evidence_level);
```

---

## Component Design

### 1. Metrics Collector

**Scheduled collection at key intervals:**
- T+30m: Early signal
- T+1h: First hour velocity
- T+2h: Acceleration check
- T+3h: Early pattern
- T+6h: Mid-day check
- T+12h: Half-day
- T+24h: Full day (classification trigger)
- T+48h: Secondary wave detection
- T+7d: Week performance (final classification)
- T+30d: Long-tail check

**Implementation:**
```java
@Service
public class MetricsCollectorService {
    
    @Scheduled(fixedDelay = 60000)  // Every 1 minute
    public void collectDueMetrics() {
        Instant now = Instant.now();
        
        // Find publications needing metric collection
        List<PublicationRecord> duePublications = publicationRepository
            .findPublishedWithoutRecentMetrics(now);
        
        for (PublicationRecord pub : duePublications) {
            collectMetricsForPublication(pub);
        }
    }
    
    private void collectMetricsForPublication(PublicationRecord pub) {
        PlatformMetricsAdapter adapter = getAdapter(pub.getPlatform());
        
        try {
            PlatformMetrics metrics = adapter.fetchMetrics(pub.getPlatformContentId());
            
            MetricSnapshot snapshot = MetricSnapshot.builder()
                .publicationRecordId(pub.getId())
                .measurementTime(Instant.now())
                .timeSincePublishMinutes(calculateTimeSince(pub.getPublishedAt()))
                .platform(pub.getPlatform())
                .views(metrics.getViews())
                .likes(metrics.getLikes())
                .comments(metrics.getComments())
                .shares(metrics.getShares())
                .avgWatchSeconds(metrics.getAvgWatchSeconds())
                .completionRate(metrics.getCompletionRate())
                .collectionMethod(CollectionMethod.API)
                .build();
            
            metricSnapshotRepository.save(snapshot);
            
            // Trigger trajectory update
            trajectoryService.updateTrajectory(pub.getId());
            
            // Check if classification is due
            if (shouldClassify(pub, snapshot)) {
                classifierService.classifyPerformance(pub.getContentId());
            }
            
        } catch (PlatformApiException e) {
            log.warn("Failed to collect metrics for {}: {}", pub.getId(), e.getMessage());
        }
    }
}
```

### 2. Trajectory Analyzer

**Calculates derived metrics from snapshots:**
```python
# ml-service/app/learning/trajectory_analyzer.py

import numpy as np
from scipy.signal import find_peaks
from typing import List, Dict, Any

class TrajectoryAnalyzer:
    """Analyze performance trajectory from metric snapshots."""
    
    def analyze_trajectory(self, snapshots: List[Dict]) -> Dict[str, Any]:
        """
        Analyze time-series metrics to detect patterns.
        
        Returns:
            {
                "velocity_t1h": float,
                "velocity_t6h": float,
                "velocity_t24h": float,
                "acceleration_early": float,
                "acceleration_late": float,
                "primary_wave_peak_time": int,
                "secondary_wave_detected": bool,
                "plateau_detected": bool,
                "decay_rate": float,
                "tail_strength": str
            }
        """
        # Sort by time
        snapshots = sorted(snapshots, key=lambda s: s["time_since_publish_minutes"])
        
        times = np.array([s["time_since_publish_minutes"] for s in snapshots])
        views = np.array([s["views"] for s in snapshots])
        
        # Calculate velocities (views per hour)
        velocity_t1h = self._calculate_velocity(snapshots, 0, 60)
        velocity_t6h = self._calculate_velocity(snapshots, 0, 360)
        velocity_t24h = self._calculate_velocity(snapshots, 0, 1440)
        velocity_t7d = self._calculate_velocity(snapshots, 0, 10080)
        
        # Calculate accelerations
        acceleration_early = velocity_t6h - velocity_t1h
        acceleration_late = velocity_t24h - velocity_t6h
        
        # Detect peaks (waves)
        peaks, properties = find_peaks(views, prominence=1000, distance=60)
        
        primary_wave_peak_time = int(times[peaks[0]]) if len(peaks) > 0 else None
        secondary_wave_detected = len(peaks) > 1
        secondary_wave_peak_time = int(times[peaks[1]]) if len(peaks) > 1 else None
        
        # Detect plateau (views stop growing)
        plateau_detected = self._detect_plateau(times, views)
        plateau_start_time = self._find_plateau_start(times, views) if plateau_detected else None
        
        # Calculate decay rate (after peak)
        decay_rate = self._calculate_decay_rate(times, views, primary_wave_peak_time)
        
        # Assess tail strength (views after T+7d)
        tail_strength = self._assess_tail_strength(snapshots)
        long_tail_views = self._get_long_tail_views(snapshots)
        
        return {
            "velocity_t1h": velocity_t1h,
            "velocity_t6h": velocity_t6h,
            "velocity_t24h": velocity_t24h,
            "velocity_t7d": velocity_t7d,
            "acceleration_early": acceleration_early,
            "acceleration_late": acceleration_late,
            "primary_wave_peak_time": primary_wave_peak_time,
            "primary_wave_peak_views": int(views[peaks[0]]) if len(peaks) > 0 else None,
            "secondary_wave_detected": secondary_wave_detected,
            "secondary_wave_peak_time": secondary_wave_peak_time,
            "plateau_detected": plateau_detected,
            "plateau_start_time": plateau_start_time,
            "decay_rate": decay_rate,
            "tail_strength": tail_strength,
            "long_tail_views": long_tail_views
        }
    
    def _calculate_velocity(self, snapshots, start_min, end_min):
        """Views per hour in time window."""
        relevant = [s for s in snapshots 
                   if start_min <= s["time_since_publish_minutes"] <= end_min]
        
        if len(relevant) < 2:
            return 0.0
        
        views_delta = relevant[-1]["views"] - relevant[0]["views"]
        time_delta_hours = (relevant[-1]["time_since_publish_minutes"] - 
                           relevant[0]["time_since_publish_minutes"]) / 60.0
        
        return views_delta / time_delta_hours if time_delta_hours > 0 else 0.0
    
    def _detect_plateau(self, times, views):
        """Check if growth has stopped."""
        if len(views) < 5:
            return False
        
        # Check last 5 measurements for <5% growth
        recent_growth = [(views[i] - views[i-1]) / views[i-1] 
                        for i in range(-5, 0) if views[i-1] > 0]
        
        return all(g < 0.05 for g in recent_growth)
    
    def _calculate_decay_rate(self, times, views, peak_time):
        """Views drop rate after peak."""
        if peak_time is None:
            return 0.0
        
        after_peak = [(t, v) for t, v in zip(times, views) if t > peak_time]
        
        if len(after_peak) < 2:
            return 0.0
        
        # Linear regression on log(views)
        times_after = np.array([t for t, v in after_peak])
        views_after = np.array([v for t, v in after_peak])
        
        log_views = np.log(views_after + 1)
        slope, _ = np.polyfit(times_after, log_views, 1)
        
        return float(slope)  # Negative = decay
```

### 3. Performance Classifier

**Classify based on trajectory patterns:**
```python
class PerformanceClassifier:
    """Classify video performance into categories."""
    
    def classify(self, content_id: str, time_horizon: str) -> Dict[str, Any]:
        """
        Classify performance at specific time horizon.
        
        Args:
            content_id: Content UUID
            time_horizon: 'T+24h', 'T+7d', 'T+30d'
        
        Returns:
            {
                "classification": str,
                "confidence": float,
                "total_views": int,
                "total_engagement": int,
                "engagement_rate": float
            }
        """
        # Get trajectory
        trajectory = self.trajectory_repo.find_by_content_id(content_id)
        
        # Get latest metrics
        latest_snapshot = self.metrics_repo.find_latest(content_id)
        
        total_views = latest_snapshot["views"]
        total_engagement = (latest_snapshot["likes"] + 
                           latest_snapshot["comments"] + 
                           latest_snapshot["shares"])
        engagement_rate = total_engagement / total_views if total_views > 0 else 0
        
        # Classification logic
        if time_horizon == "T+24h":
            classification, confidence = self._classify_t24h(total_views, trajectory)
        elif time_horizon == "T+7d":
            classification, confidence = self._classify_t7d(total_views, trajectory)
        elif time_horizon == "T+30d":
            classification, confidence = self._classify_t30d(total_views, trajectory)
        else:
            raise ValueError(f"Unknown time horizon: {time_horizon}")
        
        return {
            "classification": classification,
            "confidence": confidence,
            "total_views": total_views,
            "total_engagement": total_engagement,
            "engagement_rate": engagement_rate
        }
    
    def _classify_t24h(self, views, trajectory):
        """Classify at T+24h."""
        if views < 1000:
            return ("EARLY_REJECTION", 0.90)
        elif views >= 50000 and trajectory["velocity_t24h"] > 2000:
            return ("STRONG_START", 0.85)
        elif views >= 10000:
            return ("MEDIUM", 0.75)
        else:
            return ("WEAK", 0.80)
    
    def _classify_t7d(self, views, trajectory):
        """Classify at T+7d (final classification)."""
        if views < 1000:
            return ("EARLY_REJECTION", 0.95)
        elif views >= 100000 and trajectory["velocity_t7d"] > 500:
            if trajectory["secondary_wave_detected"]:
                return ("MULTI_WAVE", 0.90)
            else:
                return ("BREAKOUT", 0.90)
        elif views >= 50000 and trajectory["secondary_wave_detected"]:
            return ("DELAYED_BREAKOUT", 0.85)
        elif views >= 50000:
            return ("STRONG_START", 0.85)
        elif views >= 10000:
            return ("MEDIUM", 0.80)
        else:
            return ("WEAK", 0.85)
```

### 4. Correlation Analyzer

**Find statistical relationships:**
```python
from scipy.stats import pearsonr, spearmanr

class CorrelationAnalyzer:
    """Analyze correlations between quality scores and performance."""
    
    def analyze_correlation(
        self,
        rule_family: str,
        performance_metric: str,
        time_horizon_minutes: int = 1440
    ) -> Dict[str, Any]:
        """
        Analyze correlation between rule family score and performance metric.
        
        Returns:
            {
                "sample_size": int,
                "correlation_coefficient": float,
                "p_value": float,
                "effect_size": float,
                "confidence": str,
                "direction": str,
                "evidence": {...}
            }
        """
        # Get data
        contents = self._get_contents_with_metrics(time_horizon_minutes)
        
        # Extract quality scores (rule family)
        quality_scores = [c["validation_family_scores"][rule_family] for c in contents]
        
        # Extract performance metric
        performance_values = [c["metrics"][performance_metric] for c in contents]
        
        # Calculate Pearson correlation
        corr_coef, p_value = pearsonr(quality_scores, performance_values)
        
        # Calculate effect size (Cohen's d)
        effect_size = self._calculate_effect_size(quality_scores, performance_values)
        
        # Interpret confidence
        if p_value < 0.001:
            confidence = "VERY_STRONG"
        elif p_value < 0.01:
            confidence = "STRONG"
        elif p_value < 0.05:
            confidence = "MODERATE"
        else:
            confidence = "WEAK"
        
        # Interpret direction
        if abs(corr_coef) < 0.1:
            direction = "NO_CORRELATION"
        elif corr_coef > 0:
            direction = "POSITIVE"
        else:
            direction = "NEGATIVE"
        
        # Gather evidence
        evidence = {
            "sample_data": [
                {"quality": q, "performance": p} 
                for q, p in zip(quality_scores, performance_values)
            ],
            "outliers": self._detect_outliers(quality_scores, performance_values),
            "scatter_plot_url": self._generate_scatter_plot(quality_scores, performance_values)
        }
        
        return {
            "sample_size": len(contents),
            "correlation_coefficient": round(corr_coef, 4),
            "p_value": p_value,
            "effect_size": round(effect_size, 4),
            "confidence": confidence,
            "direction": direction,
            "evidence": evidence
        }
```

### 5. Rule Mining Engine

**Generate rule candidates from patterns:**
```python
class RuleMiningEngine:
    """Mine new creative rules from performance data."""
    
    def mine_rules(self, min_sample_size: int = 20) -> List[Dict[str, Any]]:
        """
        Detect patterns and generate rule candidates.
        
        Returns list of rule candidates with:
            {
                "candidate_rule_id": str,
                "hypothesis": str,
                "rule_family": str,
                "proposed_threshold": float,
                "proposed_severity": str,
                "evidence_sample_size": int,
                "confidence": str,
                "supporting_content_ids": List[str]
            }
        """
        candidates = []
        
        # Pattern 1: Consequence count threshold
        candidate = self._mine_consequence_count_rule(min_sample_size)
        if candidate:
            candidates.append(candidate)
        
        # Pattern 2: Hook intensity threshold
        candidate = self._mine_hook_intensity_rule(min_sample_size)
        if candidate:
            candidates.append(candidate)
        
        # Pattern 3: Beat pacing variance
        candidate = self._mine_beat_pacing_rule(min_sample_size)
        if candidate:
            candidates.append(candidate)
        
        # Pattern 4: Final execution score
        candidate = self._mine_final_score_rule(min_sample_size)
        if candidate:
            candidates.append(candidate)
        
        # Pattern 5: Novelty score threshold
        candidate = self._mine_novelty_score_rule(min_sample_size)
        if candidate:
            candidates.append(candidate)
        
        return candidates
    
    def _mine_consequence_count_rule(self, min_sample_size):
        """Example: videos with 5+ consequences perform 2x better."""
        # Get winners vs losers
        winners = self._get_winners()
        losers = self._get_weak_performers()
        
        if len(winners) < min_sample_size or len(losers) < min_sample_size:
            return None
        
        # Extract consequence counts
        winner_counts = [w["consequence_count"] for w in winners]
        loser_counts = [l["consequence_count"] for l in losers]
        
        winner_avg = np.mean(winner_counts)
        loser_avg = np.mean(loser_counts)
        
        # Statistical test
        from scipy.stats import ttest_ind
        t_stat, p_value = ttest_ind(winner_counts, loser_counts)
        
        if p_value < 0.05 and winner_avg > loser_avg:
            # Significant difference
            proposed_threshold = int(np.ceil(loser_avg + 1))
            
            return {
                "candidate_rule_id": "CONSEQUENCE_COUNT_ENHANCED",
                "hypothesis": f"Videos with {proposed_threshold}+ distinct consequences "
                             f"have {winner_avg/loser_avg:.1f}x better performance",
                "rule_family": "concept",
                "proposed_threshold": proposed_threshold,
                "proposed_severity": "CRITICAL",
                "proposed_message_template": f"Add {proposed_threshold - loser_avg:.0f} more "
                                            f"distinct consequences for better engagement",
                "evidence_sample_size": len(winners) + len(losers),
                "evidence_data": {
                    "winner_avg": winner_avg,
                    "loser_avg": loser_avg,
                    "p_value": p_value,
                    "performance_ratio": winner_avg / loser_avg
                },
                "confidence": "HIGH" if p_value < 0.01 else "MODERATE",
                "supporting_content_ids": [w["id"] for w in winners[:10]]
            }
        
        return None
```

---

## REST APIs (Phase 4)

### Metrics Collection

```
POST   /api/v1/publications/{id}/collect-metrics
  Response: { snapshot_id, views, likes, ... }

POST   /api/v1/publications/{id}/manual-metrics
  Request: { views, likes, comments, shares, avg_watch_seconds }
  Response: { snapshot_id }

GET    /api/v1/publications/{id}/metrics
  Query: from_time?, to_time?
  Response: [{ measurement_time, views, likes, ... }]

GET    /api/v1/publications/{id}/trajectory
  Response: { velocity_t24h, acceleration, peaks, ... }
```

### Performance Analysis

```
GET    /api/v1/contents/{id}/performance-summary
  Response: { classification, total_views, engagement_rate, trajectory }

GET    /api/v1/contents/{id}/benchmark-comparison
  Response: [{ benchmark_content, similarity, performance_delta }]

GET    /api/v1/analytics/winners
  Query: character?, platform?, from_date?, limit?
  Response: [{ content, classification, views, engagement }]

GET    /api/v1/analytics/correlations
  Query: rule_family?, min_confidence?
  Response: [{ rule_family, performance_metric, correlation, p_value }]
```

### Rule Mining

```
POST   /api/v1/rule-candidates/generate
  Request: { min_sample_size?, confidence_threshold? }
  Response: { candidates_generated, candidates: [...] }

GET    /api/v1/rule-candidates
  Query: status?, confidence?
  Response: [{ id, candidate_rule_id, hypothesis, evidence_sample_size, status }]

GET    /api/v1/rule-candidates/{id}
  Response: { id, hypothesis, evidence, supporting_contents, test_results }

POST   /api/v1/rule-candidates/{id}/approve
  Request: { review_notes?, test_results?, activate_immediately? }
  Response: { activated, ruleset_version }

POST   /api/v1/rule-candidates/{id}/reject
  Request: { reason }
  Response: { success }

POST   /api/v1/rule-candidates/{id}/test
  Request: { test_content_ids: [...] }
  Response: { test_results: [...] }
```

---

## Success Criteria

- [x] Collect metrics for 50+ videos across platforms
- [x] Classify 10+ videos (WINNER/MEDIUM/WEAK)
- [x] Detect 3+ significant correlations (p<0.05)
- [x] Generate 5+ rule candidates with evidence
- [x] Human approval UI operational
- [x] Activate 1+ new rule into production ruleset
- [x] Track rule evidence levels (THEORETICAL → SUPPORTED)

---

## Timeline Estimate

- **Week 1:** Metrics collector, platform adapters, database schema
- **Week 2:** Trajectory analyzer, wave detection, classification logic
- **Week 3:** Correlation analyzer, statistical tests, evidence gathering
- **Week 4:** Rule mining engine, pattern detection, candidate generation
- **Week 5:** Human approval UI (Angular), review workflow, A/B testing setup
- **Week 6:** Integration testing, rule activation, evidence tracking

**Total:** 6 weeks

---

## Dependencies

- Phase 3 (Distribution Engine) complete
- 50+ published videos with metrics
- Platform Analytics API credentials (TikTok, YouTube, Meta)
- Statistical libraries (scipy, statsmodels, numpy)

---

**Document Status:** DRAFT  
**Review Required:** Yes  
**Estimated Effort:** 6 weeks

