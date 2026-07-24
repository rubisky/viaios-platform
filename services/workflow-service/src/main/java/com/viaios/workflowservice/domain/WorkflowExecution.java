package com.viaios.workflowservice.domain;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "workflow_executions")
public class WorkflowExecution {
    @Id @GeneratedValue
    private UUID id;

    @Column(name = "workflow_name")
    private String workflowName;

    @Column(columnDefinition = "TEXT")
    private String definition;

    @Column(columnDefinition = "TEXT")
    private String result;

    private String status = "PENDING";

    @Column(name = "started_at")
    private Instant startedAt = Instant.now();

    @Column(name = "completed_at")
    private Instant completedAt;

    public WorkflowExecution() {}

    public UUID getId() { return id; }
    public String getWorkflowName() { return workflowName; }
    public void setWorkflowName(String n) { workflowName = n; }
    public String getDefinition() { return definition; }
    public void setDefinition(String d) { definition = d; }
    public String getResult() { return result; }
    public void setResult(String r) { result = r; }
    public String getStatus() { return status; }
    public void setStatus(String s) { status = s; }
    public Instant getStartedAt() { return startedAt; }
    public void setStartedAt(Instant t) { startedAt = t; }
    public Instant getCompletedAt() { return completedAt; }
    public void setCompletedAt(Instant t) { completedAt = t; }
}
