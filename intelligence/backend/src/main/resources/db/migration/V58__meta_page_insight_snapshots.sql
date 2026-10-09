CREATE TABLE meta_page_insight_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id VARCHAR(100) NOT NULL,
    measured_at TIMESTAMP NOT NULL,
    availability VARCHAR(20) NOT NULL,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_meta_page_insight_snapshots_object_time
    ON meta_page_insight_snapshots (object_id, measured_at DESC);
