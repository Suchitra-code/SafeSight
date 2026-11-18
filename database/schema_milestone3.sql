-- SafeSight AI Milestone 3 Database Schema
-- Adds visual chunks, chat messages, investigations, and agent execution steps
-- Only adds new tables using CREATE TABLE IF NOT EXISTS. Never drops or alters existing tables.

-- 1. Visual Chunks for camera/vision violation indexing
CREATE TABLE IF NOT EXISTS visual_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    violation_id INTEGER NOT NULL UNIQUE,
    text TEXT NOT NULL,
    camera TEXT,
    zone TEXT,
    violation_type TEXT,
    severity TEXT,
    event_time TIMESTAMP,
    snapshot_path TEXT,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (violation_id) REFERENCES violations(id) ON DELETE CASCADE
);

-- 2. Chat Messages for RAG Assistant & user interaction history
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    mode_used TEXT DEFAULT 'extractive',
    confidence TEXT DEFAULT 'Medium',
    latency_ms REAL DEFAULT 0.0,
    sources_json TEXT,
    feedback INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Investigation Runs for LangGraph incident workflows
CREATE TABLE IF NOT EXISTS investigation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    violation_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    risk_level TEXT DEFAULT 'LOW',
    risk_score INTEGER DEFAULT 1,
    summary TEXT,
    recommendations TEXT,
    approval_status TEXT DEFAULT 'pending',
    supervisor_notes TEXT,
    report_path TEXT,
    current_node TEXT DEFAULT 'load_event',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (violation_id) REFERENCES violations(id) ON DELETE CASCADE
);

-- 4. Agent Steps for trace logging and workflow visualization
CREATE TABLE IF NOT EXISTS agent_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    node_name TEXT NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    status TEXT DEFAULT 'completed',
    duration_ms REAL DEFAULT 0.0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
