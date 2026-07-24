-- V1__init.sql — Video Access Gateway initial schema
-- Creates the cameras table with PostGIS geometry support.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS cameras (
    id          VARCHAR(36)   PRIMARY KEY,
    name        VARCHAR(255)  NOT NULL,
    location    geometry(Point, 4326),
    stream_url  VARCHAR(1024),
    protocol    VARCHAR(32)   NOT NULL DEFAULT 'RTSP',
    status      VARCHAR(32)   NOT NULL DEFAULT 'OFFLINE',
    fps         INT           NOT NULL DEFAULT 25,
    resolution  VARCHAR(20)   NOT NULL DEFAULT '1920x1080',
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cameras_status ON cameras (status);
CREATE INDEX IF NOT EXISTS idx_cameras_protocol ON cameras (protocol);
CREATE INDEX IF NOT EXISTS idx_cameras_location ON cameras USING GIST (location);
