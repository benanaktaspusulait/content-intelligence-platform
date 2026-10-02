PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS performance_imports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_filename TEXT NOT NULL,
  source_path TEXT NOT NULL,
  file_hash TEXT NOT NULL UNIQUE,
  file_size INTEGER NOT NULL,
  imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  platform TEXT,
  detected_export_type TEXT NOT NULL,
  parser_version TEXT NOT NULL,
  schema_mapping_version TEXT NOT NULL,
  account_timezone TEXT NOT NULL,
  timezone_assumption TEXT NOT NULL,
  sheet_count INTEGER NOT NULL,
  row_count INTEGER NOT NULL,
  column_mapping_json TEXT NOT NULL,
  quality_report_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'COMMITTED'
);

CREATE TABLE IF NOT EXISTS raw_import_rows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  import_id INTEGER NOT NULL REFERENCES performance_imports(id) ON DELETE RESTRICT,
  sheet_name TEXT NOT NULL,
  source_row_number INTEGER NOT NULL,
  raw_json TEXT NOT NULL,
  row_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(import_id,sheet_name,source_row_number)
);

CREATE TABLE IF NOT EXISTS import_row_matches (
  raw_row_id INTEGER PRIMARY KEY REFERENCES raw_import_rows(id) ON DELETE CASCADE,
  video_id TEXT REFERENCES videos(id) ON DELETE SET NULL,
  variant_id INTEGER REFERENCES creative_variants(id) ON DELETE SET NULL,
  match_method TEXT NOT NULL,
  confidence REAL NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('MATCHED','SUGGESTED','UNRESOLVED','REJECTED')),
  candidates_json TEXT NOT NULL DEFAULT '[]',
  resolution_note TEXT,
  resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS platform_content_mappings (
  platform TEXT NOT NULL,
  platform_content_id TEXT NOT NULL,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  variant_id INTEGER REFERENCES creative_variants(id) ON DELETE SET NULL,
  source TEXT NOT NULL DEFAULT 'HUMAN',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(platform,platform_content_id)
);

CREATE TABLE IF NOT EXISTS normalised_performance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_import_id INTEGER NOT NULL REFERENCES performance_imports(id) ON DELETE RESTRICT,
  source_row_id INTEGER NOT NULL UNIQUE REFERENCES raw_import_rows(id) ON DELETE RESTRICT,
  platform TEXT NOT NULL,
  platform_content_id TEXT,
  video_id TEXT REFERENCES videos(id) ON DELETE SET NULL,
  variant_id INTEGER REFERENCES creative_variants(id) ON DELETE SET NULL,
  publication_timestamp_raw TEXT,
  publication_timezone TEXT,
  publication_timestamp_utc TEXT,
  publication_timestamp_local TEXT,
  measurement_timestamp_raw TEXT,
  measurement_timezone TEXT,
  measurement_timestamp_utc TEXT,
  measurement_timestamp_local TEXT,
  measurement_date TEXT,
  metric_semantics TEXT NOT NULL CHECK(metric_semantics IN ('DAILY_INCREMENT','CUMULATIVE','SNAPSHOT','UNKNOWN')),
  views INTEGER,
  reach INTEGER,
  unique_viewers INTEGER,
  three_second_views INTEGER,
  fifteen_second_views INTEGER,
  average_watch_seconds REAL,
  total_watch_seconds REAL,
  likes INTEGER,
  comments INTEGER,
  shares INTEGER,
  saves INTEGER,
  follows INTEGER,
  recommendation_watch_seconds REAL,
  recommendation_percentage REAL,
  followers_watch_percentage REAL,
  nonfollowers_watch_percentage REAL,
  country_distribution_json TEXT,
  is_paid INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_normalised_video_time ON normalised_performance(video_id,platform,measurement_timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_normalised_content ON normalised_performance(platform,platform_content_id);

CREATE TABLE IF NOT EXISTS performance_conflicts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT NOT NULL,
  video_id TEXT REFERENCES videos(id) ON DELETE SET NULL,
  platform_content_id TEXT,
  measurement_key TEXT NOT NULL,
  metric TEXT NOT NULL,
  existing_observation_id INTEGER REFERENCES normalised_performance(id) ON DELETE CASCADE,
  incoming_raw_row_id INTEGER REFERENCES raw_import_rows(id) ON DELETE CASCADE,
  existing_value TEXT,
  incoming_value TEXT,
  status TEXT NOT NULL DEFAULT 'OPEN',
  resolution TEXT,
  resolved_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS performance_trajectories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  variant_id INTEGER REFERENCES creative_variants(id) ON DELETE SET NULL,
  platform TEXT NOT NULL,
  checkpoint_minutes INTEGER NOT NULL,
  measurement_timestamp_utc TEXT,
  views REAL,
  reach REAL,
  likes REAL,
  comments REAL,
  shares REAL,
  saves REAL,
  follows REAL,
  average_watch_seconds REAL,
  views_per_hour REAL,
  reach_per_hour REAL,
  acceleration REAL,
  follows_per_1000_views REAL,
  shares_per_1000_views REAL,
  performance_band TEXT,
  trajectory_label TEXT,
  source_observation_ids_json TEXT NOT NULL,
  rebuilt_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(video_id,platform,checkpoint_minutes)
);

CREATE TABLE IF NOT EXISTS interventions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  kind TEXT NOT NULL,
  detail TEXT,
  paid_spend REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS import_quality_issues (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  import_id INTEGER NOT NULL REFERENCES performance_imports(id) ON DELETE CASCADE,
  raw_row_id INTEGER REFERENCES raw_import_rows(id) ON DELETE CASCADE,
  severity TEXT NOT NULL CHECK(severity IN ('INFO','WARNING','ERROR')),
  code TEXT NOT NULL,
  message TEXT NOT NULL,
  detail_json TEXT NOT NULL DEFAULT '{}'
);
