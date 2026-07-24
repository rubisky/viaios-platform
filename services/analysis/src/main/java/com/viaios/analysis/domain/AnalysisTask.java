package com.viaios.analysis.domain;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "analysis_tasks")
public class AnalysisTask {
    @Id @GeneratedValue
    private UUID id;

    @Column(name = "camera_id")
    private String cameraId;

    private String capability;

    @Column(columnDefinition = "TEXT")
    private String result;

    private String status = "PENDING";

    private Integer priority = 5;

    @Column(name = "created_at")
    private Instant createdAt = Instant.now();

    @Column(name = "completed_at")
    private Instant completedAt;

    public AnalysisTask() {}

    public UUID getId() { return id; }
    public String getCameraId() { return cameraId; }
    public void setCameraId(String c) { cameraId = c; }
    public String getCapability() { return capability; }
    public void setCapability(String c) { capability = c; }
    public String getResult() { return result; }
    public void setResult(String r) { result = r; }
    public String getStatus() { return status; }
    public void setStatus(String s) { status = s; }
    public Integer getPriority() { return priority; }
    public void setPriority(Integer p) { priority = p; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant t) { createdAt = t; }
    public Instant getCompletedAt() { return completedAt; }
    public void setCompletedAt(Instant t) { completedAt = t; }
}
