-- V24: Create analytics tables for predictions and A/B testing

-- Performance predictions table
CREATE TABLE performance_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id BIGINT NOT NULL,
    platform VARCHAR(20) NOT NULL,
    quality_score DECIMAL(5, 2),
    success_probability DECIMAL(5, 2),
    predicted_category VARCHAR(50),
    predicted_views_24h BIGINT,
    predicted_views_7d BIGINT,
    predicted_engagement_rate DECIMAL(5, 2),
    viral_potential DECIMAL(5, 2),
    confidence_level DECIMAL(5, 2),
    model_version VARCHAR(50),
    features_used TEXT,
    recommendation TEXT,
    publication_job_id UUID,
    predicted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- A/B tests table
CREATE TABLE ab_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    hypothesis TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    platform VARCHAR(20) NOT NULL,
    variant_a_job_id UUID,
    variant_a_description TEXT,
    variant_b_job_id UUID,
    variant_b_description TEXT,
    primary_metric VARCHAR(50),
    winner VARCHAR(10),
    p_value DECIMAL(10, 8),
    confidence_level DECIMAL(5, 2),
    effect_size DECIMAL(10, 4),
    conclusion TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance predictions
CREATE INDEX idx_predictions_content_id ON performance_predictions(content_id);
CREATE INDEX idx_predictions_platform ON performance_predictions(platform);
CREATE INDEX idx_predictions_publication_job ON performance_predictions(publication_job_id);
CREATE INDEX idx_predictions_viral_potential ON performance_predictions(viral_potential DESC);
CREATE INDEX idx_predictions_predicted_at ON performance_predictions(predicted_at DESC);

-- Indexes for A/B tests
CREATE INDEX idx_ab_tests_status ON ab_tests(status);
CREATE INDEX idx_ab_tests_created_at ON ab_tests(created_at DESC);
CREATE INDEX idx_ab_tests_variant_a ON ab_tests(variant_a_job_id);
CREATE INDEX idx_ab_tests_variant_b ON ab_tests(variant_b_job_id);
