-- Incidents table
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'discord',
    source_message_id TEXT,
    source_channel_id TEXT,
    reporter TEXT,
    title TEXT,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'intake' CHECK(status IN ('intake', 'diagnosing', 'remediating', 'executing', 'resolved', 'failed')),
    severity TEXT DEFAULT 'medium' CHECK(severity IN ('low', 'medium', 'high', 'critical')),
    diagnosis TEXT DEFAULT '{}',
    remediation TEXT DEFAULT '{}',
    ticket TEXT DEFAULT '{}',
    pull_request TEXT DEFAULT '{}',
    discord_reply_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- Pipeline steps log
CREATE TABLE IF NOT EXISTS pipeline_steps (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    step_name TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'done', 'failed')),
    output TEXT DEFAULT '{}',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

-- Connector activity log
CREATE TABLE IF NOT EXISTS connector_activity (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    connector TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'succeeded', 'failed')),
    details TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

-- Incident memory (for semantic search of past incidents)
CREATE TABLE IF NOT EXISTS incident_memory (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    root_cause TEXT,
    resolution TEXT,
    embedding TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);
