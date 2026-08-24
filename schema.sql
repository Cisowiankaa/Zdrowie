CREATE TABLE IF NOT EXISTS slack_actions_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    record_id TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'slack',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    processed_at TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_slack_actions_status
ON slack_actions_queue(status);

CREATE INDEX IF NOT EXISTS idx_slack_actions_record_id
ON slack_actions_queue(record_id);
