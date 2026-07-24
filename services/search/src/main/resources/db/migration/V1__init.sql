CREATE TABLE IF NOT EXISTS search_history (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         VARCHAR(64)     NOT NULL,
    query_type      VARCHAR(32)     NOT NULL,
    query           JSONB           NOT NULL,
    result_count    INTEGER         NOT NULL DEFAULT 0,
    latency_ms      BIGINT          NOT NULL DEFAULT 0,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_search_history_user_id     ON search_history (user_id);
CREATE INDEX idx_search_history_query_type  ON search_history (query_type);
CREATE INDEX idx_search_history_created_at  ON search_history (created_at DESC);
CREATE INDEX idx_search_history_user_type   ON search_history (user_id, query_type);
