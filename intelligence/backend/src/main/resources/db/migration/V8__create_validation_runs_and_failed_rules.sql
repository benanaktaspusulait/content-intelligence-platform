-- V8: Validation Runs and Failed Rules tables

CREATE TYPE validation_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED');
CREATE TYPE rule_severity AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW');

CREATE TABLE validation_runs (
    id BIGSERIAL PRIMARY KEY,
    prompt_version_id BIGINT NOT NULL REFERENCES prompt_versions(id) ON DELETE CASCADE,
    status validation_status NOT NULL DEFAULT 'PENDING',
    score DECIMAL(5,2),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

CREATE INDEX idx_validation_runs_prompt_version_id ON validation_runs(prompt_version_id);
CREATE INDEX idx_validation_runs_status ON validation_runs(status);
CREATE INDEX idx_validation_runs_score ON validation_runs(score);

CREATE TABLE failed_rules (
    id BIGSERIAL PRIMARY KEY,
    validation_run_id BIGINT NOT NULL REFERENCES validation_runs(id) ON DELETE CASCADE,
    rule_family VARCHAR(100) NOT NULL,
    rule_code VARCHAR(100) NOT NULL,
    severity rule_severity NOT NULL,
    message TEXT NOT NULL,
    beat_index INT,
    character_name VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_failed_rules_validation_run_id ON failed_rules(validation_run_id);
CREATE INDEX idx_failed_rules_severity ON failed_rules(severity);
CREATE INDEX idx_failed_rules_rule_family ON failed_rules(rule_family);

COMMENT ON TABLE validation_runs IS 'Validation runs for prompt versions, tracking score and status';
COMMENT ON TABLE failed_rules IS 'Failed rules detected during validation, with severity and context';
