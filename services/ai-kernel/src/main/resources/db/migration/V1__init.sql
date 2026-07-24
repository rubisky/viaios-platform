-- V1__init.sql — AI Kernel schema (matches JPA entities)
CREATE TABLE IF NOT EXISTS model_registry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(128) NOT NULL,
    version         VARCHAR(32),
    runtime         VARCHAR(64),
    task            VARCHAR(64),
    status          VARCHAR(32) DEFAULT 'REGISTERED',
    registry_path   VARCHAR(512),
    model_path      VARCHAR(512),
    input_shape     VARCHAR(128),
    output_shape    VARCHAR(128),
    precision       VARCHAR(16),
    gpu_memory_mb   INTEGER,
    avg_latency_ms  INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inference_tasks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id            UUID REFERENCES model_registry(id),
    status              VARCHAR(32) DEFAULT 'PENDING',
    input_data          TEXT,
    output_data         TEXT,
    error_message       TEXT,
    latency_ms          BIGINT,
    gpu_memory_used_mb  INTEGER,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS resource_allocations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workload_id VARCHAR(36) NOT NULL,
    gpu_count   INT DEFAULT 1,
    memory_mb   INT NOT NULL,
    node_name   VARCHAR(255),
    status      VARCHAR(32) DEFAULT 'PENDING',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
