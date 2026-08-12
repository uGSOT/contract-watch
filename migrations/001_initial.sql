PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS endpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE,

    UNIQUE (project_id, method, path)
);

CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint_id INTEGER NOT NULL,
    schema_json TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    expected_status INTEGER NOT NULL DEFAULT 200,
    version INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (endpoint_id)
        REFERENCES endpoints(id)
        ON DELETE CASCADE,

    UNIQUE (endpoint_id, version)
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    result TEXT NOT NULL,
    status_code INTEGER,
    response_body TEXT,
    duration_ms INTEGER,
    error_message TEXT,
    acknowledged INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (contract_id)
        REFERENCES contracts(id)
        ON DELETE CASCADE,

    CHECK (result IN ('pass', 'drift', 'error'))
);

CREATE TABLE IF NOT EXISTS run_diffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    field TEXT NOT NULL,
    expected TEXT,
    actual TEXT,
    message TEXT,

    FOREIGN KEY (run_id)
        REFERENCES runs(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_endpoints_project_id
    ON endpoints(project_id);

CREATE INDEX IF NOT EXISTS idx_contracts_endpoint_id
    ON contracts(endpoint_id);

CREATE INDEX IF NOT EXISTS idx_runs_contract_created
    ON runs(contract_id, created_at);

CREATE INDEX IF NOT EXISTS idx_run_diffs_run_id
    ON run_diffs(run_id);