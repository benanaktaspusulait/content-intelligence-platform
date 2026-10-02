-- V20: Create correlation analysis table

CREATE TABLE correlation_analyses (
    id UUID PRIMARY KEY,
    analysis_name VARCHAR(100) NOT NULL,
    description TEXT,
    sample_size INTEGER NOT NULL,
    
    -- Visual Quality correlations
    visual_quality_vs_views DECIMAL(5,4),
    visual_quality_vs_engagement DECIMAL(5,4),
    visual_quality_vs_completion DECIMAL(5,4),
    visual_quality_vs_velocity DECIMAL(5,4),
    
    -- Hook Effectiveness correlations
    hook_vs_views DECIMAL(5,4),
    hook_vs_engagement DECIMAL(5,4),
    hook_vs_completion DECIMAL(5,4),
    hook_vs_velocity DECIMAL(5,4),
    
    -- Pacing correlations
    pacing_vs_views DECIMAL(5,4),
    pacing_vs_engagement DECIMAL(5,4),
    pacing_vs_completion DECIMAL(5,4),
    pacing_vs_velocity DECIMAL(5,4),
    
    -- Emotional Impact correlations
    emotional_vs_views DECIMAL(5,4),
    emotional_vs_engagement DECIMAL(5,4),
    emotional_vs_completion DECIMAL(5,4),
    emotional_vs_velocity DECIMAL(5,4),
    
    -- Brand Consistency correlations
    brand_vs_views DECIMAL(5,4),
    brand_vs_engagement DECIMAL(5,4),
    brand_vs_completion DECIMAL(5,4),
    brand_vs_velocity DECIMAL(5,4),
    
    -- Overall Score correlations
    overall_score_vs_views DECIMAL(5,4),
    overall_score_vs_engagement DECIMAL(5,4),
    overall_score_vs_completion DECIMAL(5,4),
    overall_score_vs_velocity DECIMAL(5,4),
    
    -- Statistical significance
    strongest_correlation_factor VARCHAR(50),
    strongest_correlation_value DECIMAL(5,4),
    weakest_correlation_factor VARCHAR(50),
    weakest_correlation_value DECIMAL(5,4),
    
    -- Metadata
    p_value_threshold DECIMAL(5,4) DEFAULT 0.05,
    analysis_confidence DECIMAL(5,2),
    analyzed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_correlation_analyses_analyzed_at ON correlation_analyses(analyzed_at DESC);
CREATE INDEX idx_correlation_analyses_sample_size ON correlation_analyses(sample_size DESC);

COMMENT ON TABLE correlation_analyses IS 'Statistical correlation analysis between quality scores and performance metrics using Pearson coefficient';
COMMENT ON COLUMN correlation_analyses.visual_quality_vs_views IS 'Pearson r between visual quality score and total views';
COMMENT ON COLUMN correlation_analyses.hook_vs_engagement IS 'Pearson r between hook effectiveness and engagement rate';
COMMENT ON COLUMN correlation_analyses.overall_score_vs_velocity IS 'Pearson r between overall quality score and first 24h velocity';
COMMENT ON COLUMN correlation_analyses.p_value_threshold IS 'Statistical significance threshold (default 0.05 for 95% confidence)';
