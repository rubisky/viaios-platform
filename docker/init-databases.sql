-- VIAIOS PostgreSQL Initialization Script
-- Replaces per-service H2 databases with unified PostgreSQL

-- Create databases for all services
-- (PostgreSQL doesn't support CREATE DATABASE in transactions,
--  so we'll create schemas per service instead)

-- ===== Control Center Schema =====
CREATE SCHEMA IF NOT EXISTS control_center;

-- Users table
CREATE TABLE IF NOT EXISTS control_center.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(128),
    email VARCHAR(255),
    phone VARCHAR(32),
    avatar_url VARCHAR(512),
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'DISABLED', 'LOCKED')),
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Roles table
CREATE TABLE IF NOT EXISTS control_center.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(64) UNIQUE NOT NULL,
    display_name VARCHAR(128),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Permissions table
CREATE TABLE IF NOT EXISTS control_center.permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    permission_code VARCHAR(128) UNIQUE NOT NULL,
    resource_type VARCHAR(64),
    action VARCHAR(64),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Role-Permission mapping
CREATE TABLE IF NOT EXISTS control_center.role_permissions (
    role_id UUID REFERENCES control_center.roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES control_center.permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- User-Role mapping
CREATE TABLE IF NOT EXISTS control_center.user_roles (
    user_id UUID REFERENCES control_center.users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES control_center.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- Tenants table
CREATE TABLE IF NOT EXISTS control_center.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_name VARCHAR(64) UNIQUE NOT NULL,
    display_name VARCHAR(128),
    plan VARCHAR(32) DEFAULT 'basic' CHECK (plan IN ('basic', 'pro', 'enterprise')),
    camera_limit INT DEFAULT 100,
    storage_limit_mb BIGINT DEFAULT 102400,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User-Tenant mapping
CREATE TABLE IF NOT EXISTS control_center.user_tenants (
    user_id UUID REFERENCES control_center.users(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES control_center.tenants(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT false,
    PRIMARY KEY (user_id, tenant_id)
);

-- ===== Video Access Schema =====
CREATE SCHEMA IF NOT EXISTS video_access;

CREATE TABLE IF NOT EXISTS video_access.cameras (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(128) NOT NULL,
    location VARCHAR(256),
    protocol VARCHAR(32) DEFAULT 'RTSP',
    ip_address VARCHAR(45),
    port INT DEFAULT 554,
    username VARCHAR(128),
    password_encrypted TEXT,
    stream_url TEXT,
    device_id VARCHAR(128),
    channel_id VARCHAR(64),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    status VARCHAR(20) DEFAULT 'OFFLINE',
    fps REAL,
    resolution VARCHAR(32),
    bitrate INT,
    enabled BOOLEAN DEFAULT true,
    last_seen_at TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===== Case Management Schema =====
CREATE SCHEMA IF NOT EXISTS case_management;

CREATE TABLE IF NOT EXISTS case_management.cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    case_no VARCHAR(32) UNIQUE NOT NULL,
    title VARCHAR(256) NOT NULL,
    description TEXT,
    status VARCHAR(32) DEFAULT 'NEW',
    priority VARCHAR(8) DEFAULT 'P3',
    resolution_note TEXT,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS case_management.evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES case_management.cases(id) ON DELETE CASCADE,
    evidence_type VARCHAR(32) NOT NULL,
    title VARCHAR(256),
    description TEXT,
    file_url TEXT,
    thumbnail_url TEXT,
    source_camera_id UUID,
    source_timestamp TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===== Alarm Schema =====
CREATE SCHEMA IF NOT EXISTS alarm;

CREATE TABLE IF NOT EXISTS alarm.alarms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    severity VARCHAR(16) NOT NULL CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    alarm_type VARCHAR(64),
    rule_id UUID,
    camera_id UUID,
    message TEXT,
    snapshot_url TEXT,
    video_clip_url TEXT,
    status VARCHAR(20) DEFAULT 'TRIGGERED',
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by UUID,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID,
    resolution_note TEXT,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS alarm.alarm_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    rule_name VARCHAR(128) NOT NULL,
    description TEXT,
    rule_type VARCHAR(64),
    conditions JSONB NOT NULL,
    actions JSONB,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===== Audit Log Schema =====
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS audit.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    user_id UUID,
    action VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64),
    resource_id UUID,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===== Seed Data =====
-- Default admin user (password: viaios-admin-2024, bcrypt)
INSERT INTO control_center.users (id, username, password_hash, display_name, email, status)
VALUES ('00000000-0000-0000-0000-000000000001', 'admin',
        '$2a$12$LJ3m4ys3LkBCVxJGqOjPDeFhGMRvHZqKLAqF7YxNqKJfOdYQTfMGy',
        'System Admin', 'admin@viaios.com', 'ACTIVE')
ON CONFLICT (username) DO NOTHING;

-- Default tenant
INSERT INTO control_center.tenants (id, tenant_name, display_name, plan)
VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'Default Tenant', 'enterprise')
ON CONFLICT (tenant_name) DO NOTHING;

-- Admin role
INSERT INTO control_center.roles (id, role_name, display_name, description)
VALUES ('00000000-0000-0000-0000-000000000001', 'ADMIN', 'Administrator', 'Full system access')
ON CONFLICT (role_name) DO NOTHING;

-- Operator role
INSERT INTO control_center.roles (id, role_name, display_name, description)
VALUES ('00000000-0000-0000-0000-000000000002', 'OPERATOR', 'Operator', 'Daily operations access')
ON CONFLICT (role_name) DO NOTHING;

-- Viewer role
INSERT INTO control_center.roles (id, role_name, display_name, description)
VALUES ('00000000-0000-0000-0000-000000000003', 'VIEWER', 'Viewer', 'Read-only access')
ON CONFLICT (role_name) DO NOTHING;

-- Assign admin role to admin user
INSERT INTO control_center.user_roles (user_id, role_id)
VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001')
ON CONFLICT DO NOTHING;

-- Assign admin to default tenant
INSERT INTO control_center.user_tenants (user_id, tenant_id, is_primary)
VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', true)
ON CONFLICT DO NOTHING;

-- Basic permissions
INSERT INTO control_center.permissions (id, permission_code, resource_type, action, description) VALUES
    (gen_random_uuid(), 'cameras:read', 'cameras', 'read', 'View cameras'),
    (gen_random_uuid(), 'cameras:write', 'cameras', 'write', 'Add/edit cameras'),
    (gen_random_uuid(), 'cameras:delete', 'cameras', 'delete', 'Delete cameras'),
    (gen_random_uuid(), 'search:execute', 'search', 'execute', 'Execute searches'),
    (gen_random_uuid(), 'cases:read', 'cases', 'read', 'View cases'),
    (gen_random_uuid(), 'cases:write', 'cases', 'write', 'Create/edit cases'),
    (gen_random_uuid(), 'alarms:read', 'alarms', 'read', 'View alarms'),
    (gen_random_uuid(), 'alarms:acknowledge', 'alarms', 'acknowledge', 'Acknowledge alarms'),
    (gen_random_uuid(), 'alarms:resolve', 'alarms', 'resolve', 'Resolve alarms'),
    (gen_random_uuid(), 'reports:generate', 'reports', 'generate', 'Generate reports'),
    (gen_random_uuid(), 'admin:users', 'admin', 'users', 'Manage users'),
    (gen_random_uuid(), 'admin:roles', 'admin', 'roles', 'Manage roles'),
    (gen_random_uuid(), 'admin:tenants', 'admin', 'tenants', 'Manage tenants'),
    (gen_random_uuid(), 'admin:system', 'admin', 'system', 'System configuration')
ON CONFLICT DO NOTHING;

-- Grant all permissions to admin role
INSERT INTO control_center.role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0000-000000000001', id FROM control_center.permissions
ON CONFLICT DO NOTHING;

-- Create indices
CREATE INDEX IF NOT EXISTS idx_users_status ON control_center.users(status);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON control_center.users(created_at);
CREATE INDEX IF NOT EXISTS idx_cameras_tenant ON video_access.cameras(tenant_id);
CREATE INDEX IF NOT EXISTS idx_cameras_status ON video_access.cameras(status);
CREATE INDEX IF NOT EXISTS idx_cases_tenant ON case_management.cases(tenant_id);
CREATE INDEX IF NOT EXISTS idx_cases_status ON case_management.cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_created_at ON case_management.cases(created_at);
CREATE INDEX IF NOT EXISTS idx_evidence_case ON case_management.evidence(case_id);
CREATE INDEX IF NOT EXISTS idx_alarms_tenant ON alarm.alarms(tenant_id);
CREATE INDEX IF NOT EXISTS idx_alarms_severity ON alarm.alarms(severity);
CREATE INDEX IF NOT EXISTS idx_alarms_triggered_at ON alarm.alarms(triggered_at);
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit.audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit.audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit.audit_logs(created_at);
