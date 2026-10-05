-- Part 05: evidence-to-policy governance. These tables are deliberately separate from
-- legacy rule_candidates and from the active YAML ruleset owned by the ML service.

CREATE TABLE governed_rule_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(200) NOT NULL,
    proposed_rule_key VARCHAR(200) NOT NULL,
    proposed_rule_name VARCHAR(300) NOT NULL,
    proposed_definition TEXT NOT NULL,
    proposed_family VARCHAR(100),
    proposed_severity VARCHAR(30),
    scope_type VARCHAR(40) NOT NULL,
    scope_id VARCHAR(200),
    hypothesis TEXT NOT NULL,
    rationale TEXT,
    evidence_level VARCHAR(40) NOT NULL,
    supporting_video_count INTEGER NOT NULL DEFAULT 0,
    supporting_publication_count INTEGER NOT NULL DEFAULT 0,
    supporting_observation_count INTEGER NOT NULL DEFAULT 0,
    effect_estimate NUMERIC,
    confidence_interval JSONB,
    baseline_comparison JSONB,
    source_dataset_snapshot_id UUID,
    analysis_method VARCHAR(120) NOT NULL,
    analysis_version VARCHAR(80) NOT NULL,
    feature_schema_version VARCHAR(80),
    model_version VARCHAR(120),
    known_confounders JSONB NOT NULL DEFAULT '[]'::jsonb,
    known_limitations JSONB NOT NULL DEFAULT '[]'::jsonb,
    supporting_evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    conflicting_rule_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_tier VARCHAR(20) NOT NULL,
    recommended_action TEXT,
    status VARCHAR(40) NOT NULL,
    reviewer VARCHAR(200),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_comment TEXT,
    entity_version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_governed_candidate_key UNIQUE (tenant_id, proposed_rule_key, scope_type, scope_id)
);

CREATE INDEX idx_governed_candidates_status ON governed_rule_candidates (tenant_id, status);
CREATE INDEX idx_governed_candidates_scope ON governed_rule_candidates (tenant_id, scope_type, scope_id);

CREATE TABLE governed_rule_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES governed_rule_candidates(id),
    tenant_id VARCHAR(200) NOT NULL,
    evidence_type VARCHAR(40) NOT NULL,
    evidence_level VARCHAR(40) NOT NULL,
    scope_type VARCHAR(40) NOT NULL,
    scope_id VARCHAR(200),
    dataset_snapshot_id UUID,
    video_id UUID,
    variant_id UUID,
    publication_id UUID,
    metric VARCHAR(100) NOT NULL,
    horizon VARCHAR(80),
    observed_effect NUMERIC,
    uncertainty JSONB,
    sample_size INTEGER NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,
    platform VARCHAR(40),
    provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
    confounder_controls JSONB NOT NULL DEFAULT '[]'::jsonb,
    analysis_method VARCHAR(120) NOT NULL,
    analysis_version VARCHAR(80) NOT NULL,
    feature_schema_version VARCHAR(80),
    model_version VARCHAR(120),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_rule_evidence_sample_size CHECK (sample_size >= 0)
);

CREATE INDEX idx_governed_evidence_candidate ON governed_rule_evidence (candidate_id, created_at);
CREATE INDEX idx_governed_evidence_tenant ON governed_rule_evidence (tenant_id, evidence_level);

CREATE TABLE governed_rule_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES governed_rule_candidates(id),
    tenant_id VARCHAR(200) NOT NULL,
    conflicting_rule_key VARCHAR(200) NOT NULL,
    conflict_type VARCHAR(50) NOT NULL,
    candidate_scope_type VARCHAR(40) NOT NULL,
    candidate_scope_id VARCHAR(200),
    existing_scope_type VARCHAR(40),
    existing_scope_id VARCHAR(200),
    override_policy VARCHAR(30) NOT NULL,
    resolution_status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    resolution_note TEXT,
    resolved_by VARCHAR(200),
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE governed_rule_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES governed_rule_candidates(id),
    tenant_id VARCHAR(200) NOT NULL,
    decision VARCHAR(50) NOT NULL,
    reviewer VARCHAR(200) NOT NULL,
    reason TEXT,
    evidence_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    conflicts_reviewed JSONB NOT NULL DEFAULT '[]'::jsonb,
    resulting_action VARCHAR(80),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE governed_ruleset_changesets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(200) NOT NULL,
    parent_ruleset_version VARCHAR(80) NOT NULL,
    proposed_ruleset_version VARCHAR(80) NOT NULL,
    status VARCHAR(40) NOT NULL,
    added_rules JSONB NOT NULL DEFAULT '[]'::jsonb,
    modified_rules JSONB NOT NULL DEFAULT '[]'::jsonb,
    retired_rules JSONB NOT NULL DEFAULT '[]'::jsonb,
    candidate_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    approval_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activated_at TIMESTAMP WITH TIME ZONE,
    activated_by VARCHAR(200),
    validation_summary JSONB,
    CONSTRAINT uq_governed_changeset_version UNIQUE (tenant_id, proposed_ruleset_version)
);

CREATE TABLE governed_ruleset_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(200) NOT NULL,
    ruleset_version VARCHAR(80) NOT NULL,
    parent_ruleset_version VARCHAR(80),
    source_changeset_id UUID REFERENCES governed_ruleset_changesets(id),
    rules_document JSONB NOT NULL,
    status VARCHAR(30) NOT NULL,
    activated_at TIMESTAMP WITH TIME ZONE,
    activated_by VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_governed_ruleset_version UNIQUE (tenant_id, ruleset_version)
);

CREATE TABLE governed_rule_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(200) NOT NULL,
    rule_key VARCHAR(200) NOT NULL,
    ruleset_version VARCHAR(80) NOT NULL,
    scope_type VARCHAR(40) NOT NULL,
    scope_id VARCHAR(200),
    status VARCHAR(40) NOT NULL,
    first_supported_at TIMESTAMP WITH TIME ZONE,
    last_supported_at TIMESTAMP WITH TIME ZONE,
    last_evaluated_at TIMESTAMP WITH TIME ZONE,
    current_supporting_sample_size INTEGER NOT NULL DEFAULT 0,
    support_trend VARCHAR(40),
    current_effect_estimate NUMERIC,
    review_due_at TIMESTAMP WITH TIME ZONE,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT uq_governed_rule_health UNIQUE (tenant_id, rule_key, ruleset_version, scope_type, scope_id)
);

-- A released ruleset and a review audit row are append-only. Corrections require a new
-- release/review row, preserving the evidence-to-policy history.
CREATE OR REPLACE FUNCTION reject_governed_immutable_update() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION '% is immutable; create a new version instead', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER governed_ruleset_versions_immutable
  BEFORE UPDATE OR DELETE ON governed_ruleset_versions
  FOR EACH ROW EXECUTE FUNCTION reject_governed_immutable_update();

CREATE TRIGGER governed_rule_reviews_immutable
  BEFORE UPDATE OR DELETE ON governed_rule_reviews
  FOR EACH ROW EXECUTE FUNCTION reject_governed_immutable_update();
