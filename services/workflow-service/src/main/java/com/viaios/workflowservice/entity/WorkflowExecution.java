package com.viaios.workflowservice.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "workflow_executions")
public class WorkflowExecution {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "workflow_def", columnDefinition = "jsonb", nullable = false)
    private String workflowDef;

    @Column(nullable = false, length = 20)
    private String status;

    @Column(name = "current_step", length = 128)
    private String currentStep;

    @Column(columnDefinition = "jsonb")
    private String result;

    @Column(columnDefinition = "jsonb")
    private String error;

    @Column(name = "started_at", nullable = false, updatable = false)
    private LocalDateTime startedAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @PrePersist
    protected void onCreate() {
        this.startedAt = LocalDateTime.now();
    }

    public WorkflowExecution() {
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getWorkflowDef() { return workflowDef; }
    public void setWorkflowDef(String workflowDef) { this.workflowDef = workflowDef; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public String getCurrentStep() { return currentStep; }
    public void setCurrentStep(String currentStep) { this.currentStep = currentStep; }

    public String getResult() { return result; }
    public void setResult(String result) { this.result = result; }

    public String getError() { return error; }
    public void setError(String error) { this.error = error; }

    public LocalDateTime getStartedAt() { return startedAt; }
    public void setStartedAt(LocalDateTime startedAt) { this.startedAt = startedAt; }

    public LocalDateTime getCompletedAt() { return completedAt; }
    public void setCompletedAt(LocalDateTime completedAt) { this.completedAt = completedAt; }
}
