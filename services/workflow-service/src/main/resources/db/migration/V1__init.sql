CREATE TABLE IF NOT EXISTS workflow_executions (
    id              BIGSERIAL       PRIMARY KEY,
    workflow_def    JSONB           NOT NULL,
    status          VARCHAR(20)     NOT NULL DEFAULT 'PENDING',
    current_step    VARCHAR(128),
    result          JSONB,
    error           JSONB,
    started_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMP
);

CREATE INDEX idx_wf_exec_status       ON workflow_executions (status);
CREATE INDEX idx_wf_exec_started_at   ON workflow_executions (started_at DESC);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id              BIGSERIAL       PRIMARY KEY,
    execution_id    BIGINT          NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    step_id         VARCHAR(128)    NOT NULL,
    step_name       VARCHAR(256)    NOT NULL,
    status          VARCHAR(20)     DEFAULT 'PENDING',
    input           JSONB,
    output          JSONB,
    error           JSONB,
    retry_count     INTEGER         DEFAULT 0,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP
);

CREATE INDEX idx_wf_steps_exec_id     ON workflow_steps (execution_id);
CREATE INDEX idx_wf_steps_status      ON workflow_steps (status);
CREATE UNIQUE INDEX idx_wf_steps_exec_step ON workflow_steps (execution_id, step_id);
