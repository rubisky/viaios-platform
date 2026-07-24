-- V1__init.sql — AI Analysis initial schema
-- Creates the analysis_tasks table with JSONB support.

CREATE TABLE IF NOT EXISTS analysis_tasks (
    id           VARCHAR(36)  PRIMARY KEY,
    camera_id    VARCHAR(36)  NOT NULL,
    capability   VARCHAR(64)  NOT NULL,
    params       JSONB,
    status       VARCHAR(32)  NOT NULL DEFAULT 'PENDING',
    priority     INT          NOT NULL DEFAULT 5,
    result       JSONB,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_analysis_tasks_camera ON analysis_tasks (camera_id);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_status ON analysis_tasks (status);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_capability ON analysis_tasks (capability);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_created ON analysis_tasks (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_camera_status ON analysis_tasks (camera_id, status);
