-- Schema additions for SafeSight Copilot & Mission Control (Milestone 4)

-- Table for storing copilot runs
CREATE TABLE IF NOT EXISTS copilot_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    question TEXT NOT NULL,
    mode VARCHAR(32) DEFAULT 'offline',
    intent VARCHAR(64),
    route TEXT,
    validation_score INT DEFAULT 0,
    validation_verdict VARCHAR(32),
    answer_headline TEXT,
    answer_text TEXT,
    key_facts TEXT,
    actions TEXT,
    total_duration_ms FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing real-time execution trace events per run
CREATE TABLE IF NOT EXISTS copilot_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    node_name VARCHAR(64),
    duration_ms FLOAT DEFAULT 0.0,
    summary TEXT,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_copilot_events_run_id (run_id)
);

-- Table for site map zones & cameras metadata (cached / synchronized)
CREATE TABLE IF NOT EXISTS site_zones (
    zone_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    risk_level VARCHAR(32) DEFAULT 'LOW',
    svg_coords TEXT
);
