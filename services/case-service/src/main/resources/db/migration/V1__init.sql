CREATE TABLE IF NOT EXISTS cases (
    id              BIGSERIAL       PRIMARY KEY,
    title           VARCHAR(200)    NOT NULL,
    description     TEXT,
    status          VARCHAR(20)     NOT NULL DEFAULT 'OPEN',
    priority        VARCHAR(10)    NOT NULL DEFAULT 'MEDIUM',
    created_by      VARCHAR(64)     NOT NULL,
    assigned_to     VARCHAR(64),
    timeline        JSONB,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cases_status       ON cases (status);
CREATE INDEX idx_cases_priority     ON cases (priority);
CREATE INDEX idx_cases_created_by   ON cases (created_by);
CREATE INDEX idx_cases_assigned_to  ON cases (assigned_to);
CREATE INDEX idx_cases_status_priority ON cases (status, priority);

CREATE TABLE IF NOT EXISTS evidence (
    id                  BIGSERIAL       PRIMARY KEY,
    case_id             BIGINT          NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    type                VARCHAR(32)     NOT NULL,
    url                 VARCHAR(1024)   NOT NULL,
    source              VARCHAR(256),
    hash                VARCHAR(128),
    reliability_score   DOUBLE PRECISION,
    created_at          TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_case_id  ON evidence (case_id);
CREATE INDEX idx_evidence_type     ON evidence (type);
CREATE INDEX idx_evidence_hash     ON evidence (hash);
