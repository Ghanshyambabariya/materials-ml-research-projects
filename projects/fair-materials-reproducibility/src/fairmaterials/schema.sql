PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS datasets (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, metadata TEXT NOT NULL,
 sha256 TEXT NOT NULL, metadata_sha256 TEXT NOT NULL, object_path TEXT NOT NULL,
 registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES datasets(id),
 manifest TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS datasets_title ON datasets(title);
CREATE INDEX IF NOT EXISTS runs_dataset ON runs(dataset_id);

CREATE TABLE IF NOT EXISTS artifacts (
 id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES datasets(id),
 run_id TEXT REFERENCES runs(id), kind TEXT NOT NULL, original_name TEXT NOT NULL,
 media_type TEXT NOT NULL, description TEXT NOT NULL, sha256 TEXT NOT NULL,
 size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0), object_path TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS artifacts_dataset ON artifacts(dataset_id);
