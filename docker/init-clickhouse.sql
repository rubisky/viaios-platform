-- VIAIOS ClickHouse Analytics Schema
-- Time-series analytics storage for all services.
-- Usage: docker exec -i viaios-clickhouse clickhouse-client --user viaios --password viaios123 < init-clickhouse.sql

-- ===== Database =====
CREATE DATABASE IF NOT EXISTS viaios;

-- ===== Inference Events (AI model predictions, alarms) =====
CREATE TABLE IF NOT EXISTS viaios.inference_events (
    timestamp       DateTime64(3) CODEC(DoubleDelta, ZSTD(3)),
    camera_id       LowCardinality(String),
    event_type      LowCardinality(String),   -- 'detection', 'recognition', 'pose', 'behavior'
    model_name      LowCardinality(String),   -- 'yolov8', 'clip-vit-b-32', 'pp-yolo', etc.
    severity        LowCardinality(String),   -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    confidence      Float32 CODEC(Gorilla, ZSTD(1)),
    object_class    LowCardinality(String),
    object_count    UInt16,
    bbox_x          Float32,
    bbox_y          Float32,
    bbox_w          Float32,
    bbox_h          Float32,
    cpu_percent     Float32,
    memory_percent  Float32,
    gpu_utilization Float32,
    gpu_memory_mb   Float32,
    latency_ms      UInt32,
    frame_id        UInt64,
    labels          Array(String),
    metadata        JSON
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (camera_id, event_type, timestamp)
TTL timestamp + INTERVAL 90 DAY DELETE
SETTINGS index_granularity = 8192;

-- ===== Video Frame Events (camera stream health) =====
CREATE TABLE IF NOT EXISTS viaios.video_frame_events (
    timestamp       DateTime64(3) CODEC(DoubleDelta, ZSTD(3)),
    camera_id       LowCardinality(String),
    status          LowCardinality(String),   -- 'online', 'offline', 'degraded'
    fps             Float32 CODEC(Gorilla, ZSTD(1)),
    bitrate         UInt32,
    resolution_x    UInt16,
    resolution_y    UInt16,
    codec           LowCardinality(String),
    packet_loss     Float32,
    jitter_ms       Float32,
    frame_bytes     UInt32,
    keyframe_count  UInt32,
    dropped_frames  UInt32
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (camera_id, status, timestamp)
TTL timestamp + INTERVAL 30 DAY DELETE
SETTINGS index_granularity = 8192;

-- ===== API Access Logs (gateway traffic analytics) =====
CREATE TABLE IF NOT EXISTS viaios.api_access_logs (
    timestamp       DateTime64(3) CODEC(DoubleDelta, ZSTD(3)),
    method          LowCardinality(String),   -- GET, POST, PUT, DELETE
    path            String,
    query_string    String,
    status_code     UInt16,
    latency_ms      UInt32 CODEC(T64, ZSTD(1)),
    response_bytes  UInt32,
    user_agent      String,
    client_ip       IPv6,
    user_id         String,
    tenant_id       String,
    search_type     LowCardinality(String),   -- 'image', 'text', 'attribute', 'composite'
    result_count    UInt16,
    error_message   String,
    correlation_id  String
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (path, status_code, timestamp)
TTL timestamp + INTERVAL 90 DAY DELETE
SETTINGS index_granularity = 8192;

-- ===== Agent Execution Logs (Agent OS runtime) =====
CREATE TABLE IF NOT EXISTS viaios.agent_execution_logs (
    timestamp        DateTime64(3) CODEC(DoubleDelta, ZSTD(3)),
    agent_id         LowCardinality(String),
    agent_name       String,
    agent_type       LowCardinality(String),
    execution_id     String,
    status           LowCardinality(String),  -- 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'
    goal             String,
    strategy         LowCardinality(String),
    steps_total      UInt16,
    steps_completed  UInt16,
    duration_ms      UInt32,
    tokens_used      UInt32,
    model_name       LowCardinality(String),
    error            String,
    output_summary   String
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (agent_id, status, timestamp)
TTL timestamp + INTERVAL 180 DAY DELETE
SETTINGS index_granularity = 8192;

-- ===== System Resource Metrics (1-minute resolution) =====
CREATE TABLE IF NOT EXISTS viaios.system_metrics (
    timestamp        DateTime64(3) CODEC(DoubleDelta, ZSTD(3)),
    host             LowCardinality(String),
    cpu_percent      Float32 CODEC(Gorilla, ZSTD(1)),
    memory_total_mb  Float32,
    memory_used_mb   Float32,
    memory_percent   Float32,
    disk_read_mbps   Float32,
    disk_write_mbps  Float32,
    net_rx_mbps      Float32,
    net_tx_mbps      Float32,
    gpu_index        UInt8,
    gpu_name         LowCardinality(String),
    gpu_utilization  Float32,
    gpu_memory_mb    Float32,
    gpu_temp_c       Float32,
    process_count    UInt16,
    load_1m          Float32,
    load_5m          Float32,
    load_15m         Float32
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (host, timestamp)
TTL timestamp + INTERVAL 30 DAY DELETE,
    timestamp + INTERVAL 365 DAY TO VOLUME 'archive'
SETTINGS index_granularity = 8192;

-- ===== Materialized Views — Real-time aggregations =====

-- Hourly alarm summary
CREATE MATERIALIZED VIEW IF NOT EXISTS viaios.alarms_hourly_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, hour, camera_id, severity)
TTL date + INTERVAL 365 DAY
AS SELECT
    toDate(timestamp) AS date,
    toHour(timestamp) AS hour,
    camera_id,
    severity,
    event_type,
    count() AS event_count,
    avg(confidence) AS avg_confidence,
    min(latency_ms) AS min_latency,
    max(latency_ms) AS max_latency
FROM viaios.inference_events
WHERE severity IN ('CRITICAL', 'HIGH')
GROUP BY date, hour, camera_id, severity, event_type;

-- Hourly API traffic summary
CREATE MATERIALIZED VIEW IF NOT EXISTS viaios.api_hourly_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, hour, path, method, status_code)
TTL date + INTERVAL 365 DAY
AS SELECT
    toDate(timestamp) AS date,
    toHour(timestamp) AS hour,
    path,
    method,
    status_code,
    count() AS request_count,
    avg(latency_ms) AS avg_latency,
    quantile(0.95)(latency_ms) AS p95_latency,
    quantile(0.99)(latency_ms) AS p99_latency,
    sum(response_bytes) AS total_bytes,
    countIf(status_code >= 400) AS error_count
FROM viaios.api_access_logs
GROUP BY date, hour, path, method, status_code;

-- Hourly camera health summary
CREATE MATERIALIZED VIEW IF NOT EXISTS viaios.camera_health_hourly_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, hour, camera_id, status)
TTL date + INTERVAL 365 DAY
AS SELECT
    toDate(timestamp) AS date,
    toHour(timestamp) AS hour,
    camera_id,
    status,
    count() AS frame_count,
    avg(fps) AS avg_fps,
    avg(bitrate) AS avg_bitrate,
    avg(packet_loss) AS avg_packet_loss,
    sum(dropped_frames) AS total_dropped
FROM viaios.video_frame_events
GROUP BY date, hour, camera_id, status;

-- ===== Kafka Engine Tables — Real-time ingestion from Kafka =====

-- Kafka consumer for inference events
CREATE TABLE IF NOT EXISTS viaios.inference_events_kafka
ENGINE = Kafka()
SETTINGS
    kafka_broker_list = 'kafka:9092',
    kafka_topic_list = 'viaios.inference.events',
    kafka_group_name = 'clickhouse-inference',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 2,
    kafka_skip_broken_messages = 100;

-- Kafka consumer for API logs
CREATE TABLE IF NOT EXISTS viaios.api_access_logs_kafka
ENGINE = Kafka()
SETTINGS
    kafka_broker_list = 'kafka:9092',
    kafka_topic_list = 'viaios.api.access',
    kafka_group_name = 'clickhouse-api-logs',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 2,
    kafka_skip_broken_messages = 100;

-- Materialized views to pipe Kafka → MergeTree tables
CREATE MATERIALIZED VIEW IF NOT EXISTS viaios.inference_events_mv
TO viaios.inference_events
AS SELECT * FROM viaios.inference_events_kafka;

CREATE MATERIALIZED VIEW IF NOT EXISTS viaios.api_access_logs_mv
TO viaios.api_access_logs
AS SELECT * FROM viaios.api_access_logs_kafka;
