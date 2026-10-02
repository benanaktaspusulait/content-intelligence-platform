--liquibase formatted sql

--changeset pompom:1
CREATE TABLE rules (
    id UUID PRIMARY KEY,
    rule_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(30) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    evaluation_type VARCHAR(20) NOT NULL,
    description TEXT,
    yaml_definition JSONB NOT NULL,
    evidence_level VARCHAR(30) NOT NULL,
    active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_rules_active ON rules(active) WHERE active = true;
CREATE INDEX idx_rules_category ON rules(category);

--changeset pompom:2
CREATE TABLE concept_validations (
    id UUID PRIMARY KEY,
    external_concept_id VARCHAR(255),
    concept_text TEXT NOT NULL,
    approved BOOLEAN NOT NULL,
    overall_score DECIMAL(5,2),
    intent VARCHAR(50),
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_cv_external_id ON concept_validations(external_concept_id);
CREATE INDEX idx_cv_approved ON concept_validations(approved);
CREATE INDEX idx_cv_created_at ON concept_validations(created_at DESC);

--changeset pompom:3
CREATE TABLE rule_evaluations (
    id UUID PRIMARY KEY,
    validation_id UUID NOT NULL REFERENCES concept_validations(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES rules(id),
    passed BOOLEAN NOT NULL,
    score DECIMAL(5,2),
    reason TEXT,
    details JSONB,
    evaluated_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_re_validation ON rule_evaluations(validation_id);
CREATE INDEX idx_re_rule ON rule_evaluations(rule_id);
CREATE INDEX idx_re_passed ON rule_evaluations(passed);

--changeset pompom:4
CREATE TABLE performance_scores (
    id UUID PRIMARY KEY,
    external_video_id VARCHAR(255) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    intent VARCHAR(50),
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
    avg_watch_ratio DECIMAL(5,4),
    entry_proxy DECIMAL(5,4),
    views_per_viewer DECIMAL(5,2),
    end_retention_rate DECIMAL(5,2),
    hook_strength DECIMAL(5,2),
    progression_score DECIMAL(5,2),
    attempt_diversity_score DECIMAL(5,2),
    educational_clarity DECIMAL(5,2),
    final_payoff DECIMAL(5,2),
    loopability_score DECIMAL(5,2),
    overall_quality DECIMAL(5,2),
    classification VARCHAR(30),
    wave_pattern VARCHAR(50),
    country_distribution JSONB,
    collected_at TIMESTAMP NOT NULL,
    time_since_publish_hours INTEGER,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_ps_external_video ON performance_scores(external_video_id);
CREATE INDEX idx_ps_platform ON performance_scores(platform);
CREATE INDEX idx_ps_classification ON performance_scores(classification);
CREATE INDEX idx_ps_collected_at ON performance_scores(collected_at DESC);

--changeset pompom:5
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
    status VARCHAR(30) NOT NULL,
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    rejection_reason TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_cr_status ON candidate_rules(status);
CREATE INDEX idx_cr_created_at ON candidate_rules(created_at DESC);

--changeset pompom:6
CREATE TABLE rule_evidence (
    id UUID PRIMARY KEY,
    rule_id UUID NOT NULL REFERENCES rules(id),
    evidence_type VARCHAR(50) NOT NULL,
    video_id VARCHAR(255),
    metric_name VARCHAR(100),
    metric_value DECIMAL(10,4),
    notes TEXT,
    recorded_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_re_rule_id ON rule_evidence(rule_id);
CREATE INDEX idx_re_evidence_type ON rule_evidence(evidence_type);

--changeset pompom:7
CREATE TABLE golden_test_cases (
    id UUID PRIMARY KEY,
    test_name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(30) NOT NULL,
    concept_text TEXT NOT NULL,
    intent VARCHAR(50),
    expected_approved BOOLEAN NOT NULL,
    expected_min_score DECIMAL(5,2),
    expected_max_score DECIMAL(5,2),
    expected_passing_rules JSONB,
    expected_failing_rules JSONB,
    notes TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_gtc_category ON golden_test_cases(category);
