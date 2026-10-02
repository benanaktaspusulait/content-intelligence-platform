PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS videos (
  id TEXT PRIMARY KEY,
  content_hash TEXT NOT NULL,
  path TEXT NOT NULL UNIQUE,
  filename TEXT NOT NULL,
  series TEXT NOT NULL,
  duration REAL NOT NULL,
  fps REAL NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  codec TEXT NOT NULL,
  has_audio INTEGER NOT NULL,
  size_bytes INTEGER NOT NULL,
  discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_videos_hash ON videos(content_hash);
CREATE INDEX IF NOT EXISTS idx_videos_series ON videos(series);

CREATE TABLE IF NOT EXISTS analysis_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  analysis_version TEXT NOT NULL,
  rubric_version TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  classification TEXT NOT NULL,
  classification_reason TEXT NOT NULL,
  diagnosis TEXT NOT NULL,
  action_dna REAL NOT NULL,
  confidence REAL NOT NULL,
  result_json TEXT NOT NULL,
  artifact_dir TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(video_id, analysis_version, rubric_version)
);

CREATE TABLE IF NOT EXISTS scores (
  analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
  dimension TEXT NOT NULL,
  score REAL NOT NULL,
  PRIMARY KEY(analysis_id, dimension)
);

CREATE TABLE IF NOT EXISTS timeline_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
  start_time REAL NOT NULL,
  end_time REAL NOT NULL,
  kind TEXT NOT NULL,
  detail TEXT NOT NULL,
  confidence REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS issues (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  severity TEXT NOT NULL,
  start_time REAL NOT NULL,
  end_time REAL NOT NULL,
  evidence TEXT NOT NULL,
  consequence TEXT NOT NULL,
  proposed_change TEXT NOT NULL,
  auto_fixable INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fix_plans (
  analysis_id INTEGER PRIMARY KEY REFERENCES analysis_runs(id) ON DELETE CASCADE,
  operations_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'PROPOSED',
  human_note TEXT
);

CREATE TABLE IF NOT EXISTS edits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
  output_path TEXT NOT NULL,
  status TEXT NOT NULL,
  comparison_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS performance_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  published_at TEXT,
  views INTEGER,
  reach INTEGER,
  average_watch_seconds REAL,
  three_second_views INTEGER,
  fifteen_second_views INTEGER,
  likes INTEGER,
  comments INTEGER,
  shares INTEGER,
  saves INTEGER,
  follows INTEGER,
  country_distribution_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS human_reviews (
  video_id TEXT PRIMARY KEY REFERENCES videos(id) ON DELETE CASCADE,
  confirmed_classification TEXT,
  override_classification TEXT,
  analysis_wrong INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  fix_decision TEXT,
  reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tags (
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  tag TEXT NOT NULL,
  PRIMARY KEY(video_id, tag)
);

