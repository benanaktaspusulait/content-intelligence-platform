CREATE TABLE IF NOT EXISTS rescue_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  analysis_version TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  classification TEXT NOT NULL,
  classification_label TEXT NOT NULL,
  creative_engine_json TEXT NOT NULL,
  core_viewer_question TEXT NOT NULL,
  hook_score REAL NOT NULL,
  ending_score REAL NOT NULL,
  publishing_use TEXT NOT NULL,
  confidence REAL NOT NULL,
  result_json TEXT NOT NULL,
  artifact_dir TEXT NOT NULL,
  performance_override INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(video_id, analysis_version, prompt_version)
);

CREATE TABLE IF NOT EXISTS rescue_reviews (
  video_id TEXT PRIMARY KEY REFERENCES videos(id) ON DELETE CASCADE,
  confirmed_classification TEXT,
  override_classification TEXT,
  engine_override TEXT,
  note TEXT,
  edit_decision TEXT,
  reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rescue_edits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  rescue_run_id INTEGER NOT NULL REFERENCES rescue_runs(id) ON DELETE CASCADE,
  variant TEXT NOT NULL,
  output_path TEXT NOT NULL,
  comparison_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rescue_class ON rescue_runs(classification);

ALTER TABLE performance_metrics ADD COLUMN source_note TEXT;
ALTER TABLE performance_metrics ADD COLUMN is_approximate INTEGER NOT NULL DEFAULT 0;
