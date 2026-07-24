package com.viaios.alarmservice.domain;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "alarms")
public class Alarm {
    @Id @GeneratedValue
    private UUID id;

    private String type;
    private String severity;
    private String message;

    @Column(name = "camera_id")
    private String cameraId;

    @Column(name = "snapshot_url")
    private String snapshotUrl;

    private String status = "TRIGGERED";

    @Column(name = "created_at")
    private Instant createdAt = Instant.now();

    @Column(name = "resolved_at")
    private Instant resolvedAt;

    public Alarm() {}

    // Getters and Setters
    public UUID getId() { return id; }
    public String getType() { return type; }
    public void setType(String t) { type = t; }
    public String getSeverity() { return severity; }
    public void setSeverity(String s) { severity = s; }
    public String getMessage() { return message; }
    public void setMessage(String m) { message = m; }
    public String getCameraId() { return cameraId; }
    public void setCameraId(String c) { cameraId = c; }
    public String getSnapshotUrl() { return snapshotUrl; }
    public void setSnapshotUrl(String u) { snapshotUrl = u; }
    public String getStatus() { return status; }
    public void setStatus(String s) { status = s; if ("RESOLVED".equals(s)) resolvedAt = Instant.now(); }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant t) { createdAt = t; }
    public Instant getResolvedAt() { return resolvedAt; }
    public void setResolvedAt(Instant t) { resolvedAt = t; }
}
