CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL UNIQUE,
    request_id TEXT NOT NULL,
    transaction_id TEXT,
    transaction_timestamp TEXT NOT NULL,
    amount REAL,
    channel TEXT,
    risk_score REAL NOT NULL,
    risk_tier TEXT NOT NULL,
    decision_recommendation TEXT NOT NULL,
    legacy_action TEXT NOT NULL,
    reason_codes_json TEXT NOT NULL,
    case_status TEXT NOT NULL,
    analyst_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alerts_case_status ON alerts(case_status);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);

CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL UNIQUE,
    request_id TEXT NOT NULL,
    transaction_id TEXT,
    transaction_timestamp TEXT NOT NULL,
    features_json TEXT NOT NULL,
    amount REAL,
    channel TEXT,
    risk_score REAL NOT NULL,
    risk_tier TEXT NOT NULL,
    decision_recommendation TEXT NOT NULL,
    legacy_action TEXT NOT NULL,
    reason_codes_json TEXT NOT NULL,
    case_status TEXT NOT NULL,
    analyst_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    model_version TEXT NOT NULL,
    model_type TEXT,
    score_semantics TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cases_case_status ON cases(case_status);
CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases(created_at);

CREATE TABLE IF NOT EXISTS case_timeline (
    timeline_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    actor TEXT NOT NULL,
    details_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_case_timeline_case_id ON case_timeline(case_id);
CREATE INDEX IF NOT EXISTS idx_case_timeline_event_time ON case_timeline(event_time_utc);

CREATE TABLE IF NOT EXISTS audit_events (
    audit_id TEXT PRIMARY KEY,
    event_time_utc TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    role TEXT,
    endpoint TEXT,
    method TEXT,
    status_code INTEGER,
    request_id TEXT,
    case_id TEXT,
    alert_id TEXT,
    details_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_events_event_time ON audit_events(event_time_utc);
CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_actor ON audit_events(actor);
