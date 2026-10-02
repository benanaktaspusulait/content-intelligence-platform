-- V1: Creative Render Service schema.
--
-- The render service owns an isolated `creative_render` schema. It never references the
-- backend-owned `public` schema: content and prompt identities are stored as scalar ids plus an
-- immutable prompt snapshot captured at queue time. All foreign keys below are owned-to-owned
-- (creative_render -> creative_render). There is intentionally NO foreign key into `public`.
--
-- Flyway is configured with default-schema/schemas = creative_render, so every unqualified object
-- below is created inside creative_render and the Flyway history lives there too.

-- pgcrypto provides digest() (used by V2 to compute prompt SHA-256 over legacy raw text) and is
-- installed inside the render-owned schema so the render service carries its own dependency.
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA creative_render;

-- ---------------------------------------------------------------------------
-- Render orchestration
-- ---------------------------------------------------------------------------

CREATE TABLE render_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Scalar ownership of the intelligence content/prompt (no FK into public).
    content_id BIGINT NOT NULL,
    prompt_version_id BIGINT NOT NULL,

    -- Immutable prompt snapshot captured at queue time (updatable=false on the entity).
    content_title_snapshot VARCHAR(255) NOT NULL,
    prompt_version_number_snapshot INT NOT NULL,
    prompt_sha256 VARCHAR(64) NOT NULL,
    prompt_text_snapshot TEXT NOT NULL,

    job_type VARCHAR(20) NOT NULL CHECK (job_type IN ('FIRST_FRAME', 'VIDEO')),

    openart_job_id VARCHAR(100),
    openart_model VARCHAR(50) NOT NULL,
    openart_params JSONB,

    status VARCHAR(30) NOT NULL DEFAULT 'QUEUED' CHECK (
        status IN (
            'QUEUED', 'GENERATING', 'POLLING', 'DOWNLOADING',
            'COMPLETE', 'FAILED', 'ABANDONED'
        )
    ),
    attempt_number INT NOT NULL DEFAULT 1,
    max_attempts INT NOT NULL DEFAULT 3,

    credits_estimated NUMERIC(10,2),
    credits_actual NUMERIC(10,2),

    queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,

    error_code VARCHAR(50),
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_render_jobs_content_id ON render_jobs(content_id);
CREATE INDEX idx_render_jobs_prompt_version_id ON render_jobs(prompt_version_id);
CREATE INDEX idx_render_jobs_status ON render_jobs(status);
CREATE INDEX idx_render_jobs_openart_job_id ON render_jobs(openart_job_id);
CREATE INDEX idx_render_jobs_queued_at ON render_jobs(queued_at);

COMMENT ON TABLE render_jobs IS 'Render job orchestration for OpenArt generation (render-owned, scalar content/prompt ids + immutable snapshot)';

CREATE TABLE render_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_job_id UUID NOT NULL REFERENCES render_jobs(id) ON DELETE CASCADE,
    content_id BIGINT NOT NULL,

    asset_type VARCHAR(20) NOT NULL CHECK (asset_type IN ('FIRST_FRAME', 'VIDEO')),
    relative_path TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,

    duration_ms INT,
    width INT NOT NULL,
    height INT NOT NULL,
    frame_rate NUMERIC(5,2),
    codec VARCHAR(50),

    download_url TEXT,
    downloaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    is_current BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_render_assets_render_job_id ON render_assets(render_job_id);
CREATE INDEX idx_render_assets_content_id ON render_assets(content_id);
CREATE INDEX idx_render_assets_is_current ON render_assets(is_current);

COMMENT ON TABLE render_assets IS 'Downloaded render assets (first frames and videos)';

CREATE TABLE render_qa_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_asset_id UUID NOT NULL REFERENCES render_assets(id) ON DELETE CASCADE,
    prompt_version_id BIGINT NOT NULL,

    decision VARCHAR(30) NOT NULL CHECK (decision IN ('ACCEPT', 'RERENDER', 'ABANDON')),
    decision_reason TEXT NOT NULL,
    confidence NUMERIC(3,2),

    compliance_score INT NOT NULL,
    compliance_issues JSONB,

    has_dead_air BOOLEAN NOT NULL,
    dead_air_segments JSONB,

    character_identity_verified BOOLEAN NOT NULL,
    character_identity_issues TEXT,

    physics_consistent BOOLEAN NOT NULL,
    physics_violations TEXT,

    has_object_duplication BOOLEAN NOT NULL,
    duplication_details TEXT,

    final_execution_score INT,
    final_execution_issues TEXT,

    requires_human_review BOOLEAN NOT NULL DEFAULT FALSE,
    human_reviewed_at TIMESTAMPTZ,
    human_reviewer VARCHAR(50),
    human_decision VARCHAR(30),
    human_notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_render_qa_results_render_asset_id ON render_qa_results(render_asset_id);
CREATE INDEX idx_render_qa_results_prompt_version_id ON render_qa_results(prompt_version_id);
CREATE INDEX idx_render_qa_results_decision ON render_qa_results(decision);
CREATE INDEX idx_render_qa_results_requires_human_review ON render_qa_results(requires_human_review);

COMMENT ON TABLE render_qa_results IS 'Quality assurance results for rendered assets';

CREATE TABLE openart_credit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_job_id UUID REFERENCES render_jobs(id),

    -- Scalar reference to the intelligence prompt version (no FK into public).
    prompt_version_id BIGINT,
    job_type VARCHAR(50),
    openart_job_id VARCHAR(100),
    openart_model VARCHAR(100),

    operation VARCHAR(50) NOT NULL,
    operation_metadata JSONB,

    credits_before NUMERIC(10,2),
    credits_spent NUMERIC(10,2) NOT NULL DEFAULT 0,
    credits_used NUMERIC(10,2) NOT NULL DEFAULT 0,
    credits_after NUMERIC(10,2),

    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_openart_credit_log_render_job_id ON openart_credit_log(render_job_id);
CREATE INDEX idx_openart_credit_log_prompt_version_id ON openart_credit_log(prompt_version_id);
CREATE INDEX idx_openart_credit_log_logged_at ON openart_credit_log(logged_at);
CREATE INDEX idx_openart_credit_log_operation ON openart_credit_log(operation);

COMMENT ON TABLE openart_credit_log IS 'OpenArt credit usage tracking (render-owned)';

-- ---------------------------------------------------------------------------
-- Publication
-- ---------------------------------------------------------------------------

CREATE TABLE platform_credentials (
    id UUID PRIMARY KEY,
    platform VARCHAR(20) NOT NULL UNIQUE,
    platform_user_id VARCHAR(100),
    platform_username VARCHAR(100),
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    token_type VARCHAR(50),
    scope TEXT,
    expires_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_refreshed_at TIMESTAMP,
    connected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_platform_credentials_platform ON platform_credentials(platform);
CREATE INDEX idx_platform_credentials_active ON platform_credentials(is_active);
CREATE INDEX idx_platform_credentials_expires ON platform_credentials(expires_at);

CREATE TABLE publication_jobs (
    id UUID PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    video_path TEXT NOT NULL,
    title VARCHAR(500),
    caption TEXT,
    hashtags TEXT,
    is_private BOOLEAN,
    platform_post_id VARCHAR(100),
    platform_video_id VARCHAR(100),
    post_url TEXT,
    progress_percent INTEGER,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    queued_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    -- From backend V25 (strategic tracking), inlined here.
    manual_intervention BOOLEAN DEFAULT FALSE,
    intervention_type VARCHAR(50),
    intervention_timestamp TIMESTAMP WITH TIME ZONE,
    intervention_notes TEXT,
    is_prime_slot BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_publication_jobs_platform ON publication_jobs(platform);
CREATE INDEX idx_publication_jobs_status ON publication_jobs(status);
CREATE INDEX idx_publication_jobs_queued_at ON publication_jobs(queued_at);
CREATE INDEX idx_publication_jobs_platform_status ON publication_jobs(platform, status);
CREATE INDEX idx_publication_jobs_manual_intervention ON publication_jobs(manual_intervention);
CREATE INDEX idx_publication_jobs_prime_slot ON publication_jobs(is_prime_slot);

CREATE TABLE scheduled_publications (
    id UUID PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    video_path TEXT NOT NULL,
    title VARCHAR(500),
    caption TEXT,
    hashtags TEXT,
    is_private BOOLEAN,
    scheduled_at TIMESTAMP NOT NULL,
    timezone VARCHAR(50),
    is_executed BOOLEAN NOT NULL DEFAULT FALSE,
    executed_at TIMESTAMP,
    publication_job_id UUID,
    created_by VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scheduled_publications_platform ON scheduled_publications(platform);
CREATE INDEX idx_scheduled_publications_scheduled_at ON scheduled_publications(scheduled_at);
CREATE INDEX idx_scheduled_publications_is_executed ON scheduled_publications(is_executed);
CREATE INDEX idx_scheduled_publications_due ON scheduled_publications(is_executed, scheduled_at);

CREATE TABLE publication_analytics (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL,
    platform VARCHAR(20) NOT NULL,
    platform_post_id VARCHAR(100),
    views BIGINT,
    likes BIGINT,
    comments BIGINT,
    shares BIGINT,
    saves BIGINT,
    engagement_rate DOUBLE PRECISION,
    watch_time_seconds BIGINT,
    average_view_duration_seconds DOUBLE PRECISION,
    impressions BIGINT,
    reach BIGINT,
    clicks BIGINT,
    fetched_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(publication_job_id)
);

CREATE INDEX idx_publication_analytics_job_id ON publication_analytics(publication_job_id);
CREATE INDEX idx_publication_analytics_platform ON publication_analytics(platform);

CREATE TABLE webhook_events (
    id UUID PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    platform_post_id VARCHAR(100),
    publication_job_id UUID,
    payload TEXT NOT NULL,
    signature TEXT,
    is_processed BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMP,
    processing_error TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_webhook_events_platform ON webhook_events(platform);
CREATE INDEX idx_webhook_events_is_processed ON webhook_events(is_processed);
CREATE INDEX idx_webhook_events_job_id ON webhook_events(publication_job_id);

-- ---------------------------------------------------------------------------
-- Metrics
-- ---------------------------------------------------------------------------

CREATE TABLE video_metrics (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL REFERENCES publication_jobs(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL,
    platform_video_id VARCHAR(100) NOT NULL,
    views BIGINT NOT NULL DEFAULT 0,
    likes BIGINT NOT NULL DEFAULT 0,
    comments BIGINT NOT NULL DEFAULT 0,
    shares BIGINT NOT NULL DEFAULT 0,
    saves BIGINT NOT NULL DEFAULT 0,
    completion_rate DECIMAL(5,2),
    avg_watch_time_seconds DECIMAL(6,2),
    total_watch_time_seconds BIGINT,
    impressions BIGINT,
    reach BIGINT,
    clicks BIGINT,
    platform_specific_data JSONB,
    collected_at TIMESTAMP NOT NULL,
    time_since_publish_minutes INTEGER NOT NULL,
    collection_source VARCHAR(50),
    is_final BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_video_metrics_publication_job ON video_metrics(publication_job_id);
CREATE INDEX idx_video_metrics_platform_video ON video_metrics(platform_video_id);
CREATE INDEX idx_video_metrics_collected_at ON video_metrics(collected_at);

CREATE TABLE metrics_collection_jobs (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL REFERENCES publication_jobs(id) ON DELETE CASCADE,
    collection_point VARCHAR(20) NOT NULL,
    scheduled_at TIMESTAMP NOT NULL,
    executed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    collected_metrics_id UUID REFERENCES video_metrics(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_metrics_collection_jobs_publication ON metrics_collection_jobs(publication_job_id);
CREATE INDEX idx_metrics_collection_jobs_scheduled ON metrics_collection_jobs(scheduled_at);
CREATE INDEX idx_metrics_collection_jobs_status ON metrics_collection_jobs(status);

-- ---------------------------------------------------------------------------
-- Performance analytics / support
-- ---------------------------------------------------------------------------

CREATE TABLE performance_classifications (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL UNIQUE REFERENCES publication_jobs(id) ON DELETE CASCADE,
    category VARCHAR(30) NOT NULL,
    confidence_score DECIMAL(5,2) NOT NULL,
    final_views BIGINT,
    final_engagement_rate DECIMAL(5,2),
    peak_views BIGINT,
    peak_day INTEGER,
    velocity_score DECIMAL(5,2),
    acceleration_score DECIMAL(5,2),
    plateau_detected BOOLEAN,
    plateau_day INTEGER,
    tail_strength DECIMAL(5,2),
    primary_wave_day INTEGER,
    secondary_wave_day INTEGER,
    wave_count INTEGER,
    classification_reason TEXT,
    -- From backend V25 (strategic tracking), inlined here.
    success_tier VARCHAR(20),
    classified_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_performance_classifications_job ON performance_classifications(publication_job_id);
CREATE INDEX idx_performance_classifications_category ON performance_classifications(category);

CREATE TABLE trajectory_analyses (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL UNIQUE REFERENCES publication_jobs(id) ON DELETE CASCADE,
    velocity_first_hour DECIMAL(10,2),
    velocity_first_6h DECIMAL(10,2),
    velocity_first_24h DECIMAL(10,2),
    velocity_day_1_to_7 DECIMAL(10,2),
    velocity_day_7_to_30 DECIMAL(10,2),
    acceleration_1h_to_6h DECIMAL(10,2),
    acceleration_6h_to_24h DECIMAL(10,2),
    acceleration_day_1_to_7 DECIMAL(10,2),
    peak_views BIGINT,
    peak_timestamp TIMESTAMP,
    peak_day INTEGER,
    time_to_peak_hours INTEGER,
    plateau_detected BOOLEAN DEFAULT FALSE,
    plateau_timestamp TIMESTAMP,
    plateau_day INTEGER,
    plateau_views BIGINT,
    decay_detected BOOLEAN DEFAULT FALSE,
    decay_rate DECIMAL(5,2),
    wave_count INTEGER DEFAULT 0,
    primary_wave_day INTEGER,
    primary_wave_views BIGINT,
    secondary_wave_day INTEGER,
    secondary_wave_views BIGINT,
    tertiary_wave_day INTEGER,
    tertiary_wave_views BIGINT,
    tail_strength DECIMAL(5,4),
    tail_velocity DECIMAL(10,2),
    tail_sustainability_score DECIMAL(5,2),
    trajectory_shape VARCHAR(30),
    growth_pattern VARCHAR(50),
    data_points_count INTEGER,
    analysis_confidence DECIMAL(5,2),
    analyzed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trajectory_analyses_job ON trajectory_analyses(publication_job_id);
CREATE INDEX idx_trajectory_analyses_shape ON trajectory_analyses(trajectory_shape);

CREATE TABLE correlation_analyses (
    id UUID PRIMARY KEY,
    analysis_name VARCHAR(100) NOT NULL,
    description TEXT,
    sample_size INTEGER NOT NULL,
    visual_quality_vs_views DECIMAL(5,4),
    visual_quality_vs_engagement DECIMAL(5,4),
    visual_quality_vs_completion DECIMAL(5,4),
    visual_quality_vs_velocity DECIMAL(5,4),
    hook_vs_views DECIMAL(5,4),
    hook_vs_engagement DECIMAL(5,4),
    hook_vs_completion DECIMAL(5,4),
    hook_vs_velocity DECIMAL(5,4),
    pacing_vs_views DECIMAL(5,4),
    pacing_vs_engagement DECIMAL(5,4),
    pacing_vs_completion DECIMAL(5,4),
    pacing_vs_velocity DECIMAL(5,4),
    emotional_vs_views DECIMAL(5,4),
    emotional_vs_engagement DECIMAL(5,4),
    emotional_vs_completion DECIMAL(5,4),
    emotional_vs_velocity DECIMAL(5,4),
    brand_vs_views DECIMAL(5,4),
    brand_vs_engagement DECIMAL(5,4),
    brand_vs_completion DECIMAL(5,4),
    brand_vs_velocity DECIMAL(5,4),
    overall_score_vs_views DECIMAL(5,4),
    overall_score_vs_engagement DECIMAL(5,4),
    overall_score_vs_completion DECIMAL(5,4),
    overall_score_vs_velocity DECIMAL(5,4),
    strongest_correlation_factor VARCHAR(50),
    strongest_correlation_value DECIMAL(5,4),
    weakest_correlation_factor VARCHAR(50),
    weakest_correlation_value DECIMAL(5,4),
    p_value_threshold DECIMAL(5,4) DEFAULT 0.05,
    analysis_confidence DECIMAL(5,2),
    analyzed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_correlation_analyses_analyzed_at ON correlation_analyses(analyzed_at DESC);

CREATE TABLE rule_candidates (
    id UUID PRIMARY KEY,
    rule_name VARCHAR(200) NOT NULL,
    rule_description TEXT NOT NULL,
    condition TEXT NOT NULL,
    outcome TEXT NOT NULL,
    rule_type VARCHAR(30) NOT NULL,
    rule_category VARCHAR(30) NOT NULL,
    support_count INTEGER NOT NULL,
    total_cases INTEGER NOT NULL,
    confidence DECIMAL(5,2) NOT NULL,
    lift DECIMAL(5,2),
    is_actionable BOOLEAN NOT NULL DEFAULT TRUE,
    action_recommendation TEXT,
    validation_status VARCHAR(30) DEFAULT 'CANDIDATE',
    validated_at TIMESTAMP,
    validation_notes TEXT,
    mining_run_id UUID,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rule_candidates_rule_type ON rule_candidates(rule_type);
CREATE INDEX idx_rule_candidates_validation_status ON rule_candidates(validation_status);

CREATE TABLE winner_entries (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL UNIQUE REFERENCES publication_jobs(id) ON DELETE CASCADE,
    winner_tier VARCHAR(30) NOT NULL,
    performance_category VARCHAR(30) NOT NULL,
    total_views BIGINT NOT NULL,
    total_engagement BIGINT NOT NULL,
    engagement_rate DECIMAL(5,2),
    completion_rate DECIMAL(5,2),
    velocity_first_24h DECIMAL(10,2),
    tail_strength DECIMAL(5,4),
    trajectory_shape VARCHAR(30),
    peak_day INTEGER,
    wave_count INTEGER,
    benchmark_score DECIMAL(5,2),
    percentile_rank DECIMAL(5,2),
    notes TEXT,
    added_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_winner_entries_tier ON winner_entries(winner_tier);
CREATE INDEX idx_winner_entries_score ON winner_entries(benchmark_score DESC);

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,
    related_entity_id UUID,
    related_entity_type VARCHAR(50),
    link VARCHAR(500),
    priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX idx_notifications_type ON notifications(type);

CREATE TABLE performance_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id BIGINT NOT NULL,
    platform VARCHAR(20) NOT NULL,
    quality_score DECIMAL(5,2),
    success_probability DECIMAL(5,2),
    predicted_category VARCHAR(50),
    predicted_views_24h BIGINT,
    predicted_views_7d BIGINT,
    predicted_engagement_rate DECIMAL(5,2),
    viral_potential DECIMAL(5,2),
    confidence_level DECIMAL(5,2),
    model_version VARCHAR(50),
    features_used TEXT,
    recommendation TEXT,
    publication_job_id UUID,
    predicted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_predictions_content_id ON performance_predictions(content_id);
CREATE INDEX idx_predictions_platform ON performance_predictions(platform);

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
    p_value DECIMAL(10,8),
    confidence_level DECIMAL(5,2),
    effect_size DECIMAL(10,4),
    conclusion TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_ab_tests_status ON ab_tests(status);

CREATE TABLE follower_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_job_id UUID NOT NULL REFERENCES publication_jobs(id) ON DELETE CASCADE,
    followers_before INTEGER,
    followers_after INTEGER,
    followers_gained INTEGER,
    profile_visits INTEGER,
    follower_conversion_rate DECIMAL(5,2),
    us_audience_percentage DECIMAL(5,2),
    non_follower_percentage DECIMAL(5,2),
    top_countries TEXT,
    discovery_score DECIMAL(5,2),
    measured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_follower_metrics_publication ON follower_metrics(publication_job_id);
CREATE INDEX idx_follower_metrics_measured ON follower_metrics(measured_at DESC);

CREATE TABLE reach_further_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_job_id UUID NOT NULL REFERENCES publication_jobs(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    views_before BIGINT,
    views_1h_after BIGINT,
    views_3h_after BIGINT,
    views_6h_after BIGINT,
    views_24h_after BIGINT,
    country_distribution_snapshot TEXT,
    follower_percentage DECIMAL(5,2),
    non_follower_percentage DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reach_further_publication ON reach_further_events(publication_job_id);
CREATE INDEX idx_reach_further_platform ON reach_further_events(platform);

-- ---------------------------------------------------------------------------
-- Legacy copy audit (populated by V2)
-- ---------------------------------------------------------------------------

CREATE TABLE legacy_copy_audit (
    id BIGSERIAL PRIMARY KEY,
    source_table TEXT NOT NULL,
    source_count BIGINT NOT NULL,
    target_count BIGINT NOT NULL,
    source_hash TEXT,
    target_hash TEXT,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL
);

CREATE INDEX idx_legacy_copy_audit_source_table ON legacy_copy_audit(source_table);

COMMENT ON TABLE legacy_copy_audit IS 'Audit of the non-destructive legacy data copy performed by V2 (per source table: counts + deterministic id-set hash)';
