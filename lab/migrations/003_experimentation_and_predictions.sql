PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS creative_fingerprints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  feature_version TEXT NOT NULL,
  source_analysis_id INTEGER REFERENCES analysis_runs(id) ON DELETE SET NULL,
  creative_quality_score REAL NOT NULL,
  features_json TEXT NOT NULL,
  evidence_json TEXT NOT NULL DEFAULT '{}',
  confidence REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(video_id, feature_version)
);

CREATE TABLE IF NOT EXISTS creative_variants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  parent_variant_id INTEGER REFERENCES creative_variants(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  hypothesis TEXT,
  changes_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'DRAFT',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(video_id, name)
);

CREATE TABLE IF NOT EXISTS experiments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  platform TEXT NOT NULL,
  design TEXT NOT NULL CHECK(design IN ('DIRECT_AB','MATCHED_CROSS_VIDEO','OBSERVATIONAL')),
  hypothesis TEXT NOT NULL,
  primary_metric TEXT NOT NULL,
  horizon_minutes INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'PLANNED',
  audience_overlap_risk TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiment_arms (
  experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
  arm_name TEXT NOT NULL,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  variant_id INTEGER REFERENCES creative_variants(id) ON DELETE SET NULL,
  planned_publish_time TEXT,
  actual_publish_time TEXT,
  PRIMARY KEY(experiment_id, arm_name, video_id)
);

CREATE TABLE IF NOT EXISTS characters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  status TEXT NOT NULL DEFAULT 'UNTESTED' CHECK(status IN ('ESTABLISHED','LIMITED_DATA','NEW','UNTESTED')),
  first_seen TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  reference_images_json TEXT NOT NULL DEFAULT '[]',
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO characters(name,status) VALUES
 ('Kiko','ESTABLISHED'),('Mimi','ESTABLISHED'),('Luca','ESTABLISHED'),
 ('Arda','ESTABLISHED'),('Noah','ESTABLISHED'),('Opa','ESTABLISHED');

CREATE TABLE IF NOT EXISTS video_characters (
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK(role IN ('PROTAGONIST','HELPER','RIVAL','OBSERVER','COMEDIC_TARGET','TEACHER','UNKNOWN')),
  is_primary INTEGER NOT NULL DEFAULT 0,
  screen_time_ratio REAL,
  action_share REAL,
  speaking_share REAL,
  reaction_intensity REAL,
  source TEXT NOT NULL DEFAULT 'HUMAN',
  confidence REAL NOT NULL DEFAULT 1.0,
  PRIMARY KEY(video_id, character_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_video_primary_character ON video_characters(video_id) WHERE is_primary=1;

CREATE TABLE IF NOT EXISTS dataset_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  version TEXT NOT NULL UNIQUE,
  as_of TEXT NOT NULL,
  platform TEXT,
  row_count INTEGER NOT NULL,
  query_json TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  version TEXT NOT NULL UNIQUE,
  platform TEXT NOT NULL,
  algorithm TEXT NOT NULL,
  feature_version TEXT NOT NULL,
  dataset_snapshot_id INTEGER REFERENCES dataset_snapshots(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'CHALLENGER' CHECK(status IN ('CHAMPION','CHALLENGER','RETIRED','BASELINE')),
  parameters_json TEXT NOT NULL,
  validation_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  promoted_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_champion_per_platform ON model_versions(platform) WHERE status='CHAMPION';

CREATE TABLE IF NOT EXISTS predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  variant_id INTEGER REFERENCES creative_variants(id) ON DELETE SET NULL,
  platform TEXT NOT NULL,
  mode TEXT NOT NULL CHECK(mode IN ('PRE_PUBLISH','EARLY_LIVE')),
  model_version_id INTEGER REFERENCES model_versions(id) ON DELETE RESTRICT,
  model_version TEXT NOT NULL,
  feature_version TEXT NOT NULL,
  dataset_version TEXT NOT NULL,
  prediction_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  planned_publish_time TEXT,
  knowledge_cutoff TEXT NOT NULL,
  creative_fingerprint_snapshot TEXT NOT NULL,
  confidence TEXT NOT NULL CHECK(confidence IN ('LOW','MEDIUM','HIGH')),
  comparable_sample_size INTEGER NOT NULL,
  historical_platform_fit_score REAL,
  learned_opportunity_score REAL,
  uncertainty_reasons_json TEXT NOT NULL DEFAULT '[]',
  payload_json TEXT NOT NULL,
  locked_at TEXT,
  lock_note TEXT
);

CREATE TABLE IF NOT EXISTS prediction_targets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  prediction_id INTEGER NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
  horizon_minutes INTEGER NOT NULL,
  metric TEXT NOT NULL DEFAULT 'views',
  expected_value REAL,
  interval_50_low REAL,
  interval_50_high REAL,
  interval_80_low REAL,
  interval_80_high REAL,
  UNIQUE(prediction_id,horizon_minutes,metric)
);

CREATE TABLE IF NOT EXISTS prediction_probabilities (
  prediction_id INTEGER NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
  horizon_minutes INTEGER NOT NULL,
  probability_type TEXT NOT NULL CHECK(probability_type IN ('BAND','TRAJECTORY')),
  label TEXT NOT NULL,
  probability REAL NOT NULL CHECK(probability>=0 AND probability<=1),
  PRIMARY KEY(prediction_id,horizon_minutes,probability_type,label)
);

CREATE TABLE IF NOT EXISTS prediction_factors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  prediction_id INTEGER NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
  direction TEXT NOT NULL CHECK(direction IN ('POSITIVE','NEGATIVE','UNCERTAINTY')),
  factor TEXT NOT NULL,
  contribution REAL,
  evidence TEXT
);

CREATE TABLE IF NOT EXISTS prediction_audits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  prediction_id INTEGER NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
  horizon_minutes INTEGER NOT NULL,
  metric TEXT NOT NULL DEFAULT 'views',
  actual_value REAL,
  absolute_error REAL,
  absolute_log_error REAL,
  inside_interval_50 INTEGER,
  inside_interval_80 INTEGER,
  predicted_band TEXT,
  actual_band TEXT,
  band_correct INTEGER,
  predicted_trajectory TEXT,
  actual_trajectory TEXT,
  trajectory_correct INTEGER,
  brier_score REAL,
  audited_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(prediction_id,horizon_minutes,metric)
);

CREATE TABLE IF NOT EXISTS human_predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  horizon_minutes INTEGER NOT NULL,
  expected_value REAL,
  predicted_band TEXT,
  rationale TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  locked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS publishing_decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  variant_id INTEGER REFERENCES creative_variants(id) ON DELETE SET NULL,
  platform TEXT NOT NULL,
  decision TEXT NOT NULL,
  rationale TEXT,
  decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_findings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scope TEXT NOT NULL,
  platform TEXT,
  statement TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  sample_size INTEGER NOT NULL,
  confidence TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OBSERVATIONAL',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS predictions_locked_update
BEFORE UPDATE ON predictions WHEN OLD.locked_at IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'locked prediction is immutable'); END;

CREATE TRIGGER IF NOT EXISTS predictions_locked_delete
BEFORE DELETE ON predictions WHEN OLD.locked_at IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'locked prediction is immutable'); END;

CREATE TRIGGER IF NOT EXISTS prediction_targets_locked_insert
BEFORE INSERT ON prediction_targets WHEN (SELECT locked_at FROM predictions WHERE id=NEW.prediction_id) IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'locked prediction targets are immutable'); END;

CREATE TRIGGER IF NOT EXISTS prediction_targets_locked_update
BEFORE UPDATE ON prediction_targets WHEN (SELECT locked_at FROM predictions WHERE id=OLD.prediction_id) IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'locked prediction targets are immutable'); END;

CREATE TRIGGER IF NOT EXISTS prediction_targets_locked_delete
BEFORE DELETE ON prediction_targets WHEN (SELECT locked_at FROM predictions WHERE id=OLD.prediction_id) IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'locked prediction targets are immutable'); END;

CREATE TRIGGER IF NOT EXISTS prediction_probabilities_locked_insert
BEFORE INSERT ON prediction_probabilities WHEN (SELECT locked_at FROM predictions WHERE id=NEW.prediction_id) IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'locked prediction probabilities are immutable'); END;

CREATE TRIGGER IF NOT EXISTS prediction_probabilities_locked_update
BEFORE UPDATE ON prediction_probabilities WHEN (SELECT locked_at FROM predictions WHERE id=OLD.prediction_id) IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'locked prediction probabilities are immutable'); END;

CREATE TRIGGER IF NOT EXISTS prediction_probabilities_locked_delete
BEFORE DELETE ON prediction_probabilities WHEN (SELECT locked_at FROM predictions WHERE id=OLD.prediction_id) IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'locked prediction probabilities are immutable'); END;

