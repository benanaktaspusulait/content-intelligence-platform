PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS model_evaluations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model_version TEXT NOT NULL,
  platform TEXT NOT NULL,
  horizon_minutes INTEGER NOT NULL,
  evaluation_start TEXT,
  evaluation_end TEXT,
  sample_size INTEGER NOT NULL,
  metrics_json TEXT NOT NULL,
  method TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_calibration (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model_version TEXT NOT NULL,
  platform TEXT NOT NULL,
  horizon_minutes INTEGER NOT NULL,
  probability_type TEXT NOT NULL,
  bucket_low REAL NOT NULL,
  bucket_high REAL NOT NULL,
  predicted_mean REAL NOT NULL,
  observed_frequency REAL NOT NULL,
  sample_size INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS forecast_revisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  original_prediction_id INTEGER NOT NULL REFERENCES predictions(id) ON DELETE RESTRICT,
  revised_prediction_id INTEGER NOT NULL REFERENCES predictions(id) ON DELETE RESTRICT,
  revision_reason TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(original_prediction_id,revised_prediction_id)
);

CREATE TABLE IF NOT EXISTS data_connectors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  connector_type TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 0,
  configuration_json TEXT NOT NULL DEFAULT '{}',
  notes TEXT
);

INSERT OR IGNORE INTO data_connectors(name,connector_type,notes) VALUES
 ('Manual file import','FILE','Active local CSV/TSV/XLSX/JSON interface'),
 ('Meta official API','OFFICIAL_API','Future connector; no scraping'),
 ('TikTok official API','OFFICIAL_API','Future connector; no scraping');
