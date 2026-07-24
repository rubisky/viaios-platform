CREATE TABLE IF NOT EXISTS templates (
    id              BIGSERIAL       PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    type            VARCHAR(32)     NOT NULL,
    content         TEXT            NOT NULL,
    version         INTEGER         NOT NULL DEFAULT 1,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_templates_name        ON templates (name);
CREATE INDEX idx_templates_type        ON templates (type);
CREATE INDEX idx_templates_name_ver    ON templates (name, version DESC);

CREATE TABLE IF NOT EXISTS reports (
    id              BIGSERIAL       PRIMARY KEY,
    case_id         BIGINT          NOT NULL,
    template_id     BIGINT,
    status          VARCHAR(20)     NOT NULL DEFAULT 'PENDING',
    output_format   VARCHAR(10)     NOT NULL DEFAULT 'PDF',
    output_url      VARCHAR(1024),
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reports_case_id       ON reports (case_id);
CREATE INDEX idx_reports_status        ON reports (status);
CREATE INDEX idx_reports_template_id   ON reports (template_id);
CREATE INDEX idx_reports_case_template ON reports (case_id, template_id);
