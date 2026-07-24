CREATE TABLE IF NOT EXISTS alarm_rules (
    id              BIGSERIAL       PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    type            VARCHAR(32)     NOT NULL,
    condition       JSONB           NOT NULL,
    action          JSONB           NOT NULL,
    enabled         BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alarm_rules_type     ON alarm_rules (type);
CREATE INDEX idx_alarm_rules_enabled  ON alarm_rules (enabled);

CREATE TABLE IF NOT EXISTS alarms (
    id                  BIGSERIAL       PRIMARY KEY,
    rule_id             BIGINT          NOT NULL REFERENCES alarm_rules(id) ON DELETE RESTRICT,
    camera_id           VARCHAR(64)     NOT NULL,
    type                VARCHAR(32)     NOT NULL,
    severity            VARCHAR(10)     NOT NULL DEFAULT 'MEDIUM',
    snapshot_url        VARCHAR(1024),
    status              VARCHAR(20)     NOT NULL DEFAULT 'ACTIVE',
    acknowledged_by     VARCHAR(64),
    resolved_at         TIMESTAMP,
    created_at          TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alarms_status       ON alarms (status);
CREATE INDEX idx_alarms_severity     ON alarms (severity);
CREATE INDEX idx_alarms_camera_id    ON alarms (camera_id);
CREATE INDEX idx_alarms_rule_id      ON alarms (rule_id);
CREATE INDEX idx_alarms_status_sev   ON alarms (status, severity);
CREATE INDEX idx_alarms_created_at   ON alarms (created_at);
