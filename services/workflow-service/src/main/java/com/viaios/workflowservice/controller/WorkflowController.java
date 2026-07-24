package com.viaios.workflowservice.controller;

import com.viaios.workflowservice.entity.WorkflowExecution;
import com.viaios.workflowservice.entity.WorkflowStep;
import com.viaios.workflowservice.repository.WorkflowExecutionRepository;
import com.viaios.workflowservice.repository.WorkflowStepRepository;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/workflows")
public class WorkflowController {

    private static final Logger log = LoggerFactory.getLogger(WorkflowController.class);
    private final WorkflowExecutionRepository executionRepository;
    private final WorkflowStepRepository stepRepository;

    public WorkflowController(WorkflowExecutionRepository executionRepository, WorkflowStepRepository stepRepository) {
        this.executionRepository = executionRepository;
        this.stepRepository = stepRepository;
    }

    @PostMapping("/execute")
    public ResponseEntity<WorkflowExecution> executeWorkflow(@Valid @RequestBody ExecuteWorkflowRequest request) {
        log.info("Executing workflow: {}", request.getWorkflowName());

        WorkflowExecution execution = new WorkflowExecution();
        execution.setWorkflowDef(request.getWorkflowDef());
        execution.setStatus("RUNNING");
        execution.setCurrentStep("step-0");

        WorkflowExecution saved = executionRepository.save(execution);

        // Simulate DAG step creation from the workflow definition
        List<Map<String, Object>> simulatedSteps = parseSteps(request.getWorkflowDef());
        for (int i = 0; i < simulatedSteps.size(); i++) {
            Map<String, Object> stepDef = simulatedSteps.get(i);
            WorkflowStep step = new WorkflowStep();
            step.setExecutionId(saved.getId());
            step.setStepId("step-" + i);
            step.setStepName((String) stepDef.getOrDefault("name", "step-" + i));
            step.setStatus(i == 0 ? "RUNNING" : "PENDING");
            step.setInput("{}");
            step.setRetryCount(0);
            step.setStartedAt(i == 0 ? LocalDateTime.now() : null);
            stepRepository.save(step);
        }

        // Simulate async completion
        saved.setStatus("COMPLETED");
        saved.setCurrentStep("step-" + (simulatedSteps.size() - 1));
        saved.setResult("{\"message\":\"Workflow completed successfully\"}");
        saved.setCompletedAt(LocalDateTime.now());
        WorkflowExecution completed = executionRepository.save(saved);

        log.info("Workflow {} executed with id: {}", request.getWorkflowName(), completed.getId());
        return ResponseEntity.status(HttpStatus.CREATED).body(completed);
    }

    @GetMapping("/{id}/status")
    public ResponseEntity<Map<String, Object>> getWorkflowStatus(@PathVariable Long id) {
        log.info("Fetching workflow status: {}", id);
        return executionRepository.findById(id)
                .map(exec -> {
                    long totalSteps = stepRepository.countByExecutionIdAndStatus(id, null);
                    long completedSteps = stepRepository.countByExecutionIdAndStatus(id, "COMPLETED");
                    long failedSteps = stepRepository.countByExecutionIdAndStatus(id, "FAILED");

                    Map<String, Object> status = new HashMap<>();
                    status.put("executionId", exec.getId());
                    status.put("status", exec.getStatus());
                    status.put("currentStep", exec.getCurrentStep());
                    status.put("totalSteps", totalSteps);
                    status.put("completedSteps", completedSteps);
                    status.put("failedSteps", failedSteps);
                    status.put("startedAt", exec.getStartedAt());
                    status.put("completedAt", exec.getCompletedAt());
                    if (exec.getError() != null) {
                        status.put("error", exec.getError());
                    }
                    return ResponseEntity.ok(status);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/cancel")
    public ResponseEntity<WorkflowExecution> cancelWorkflow(@PathVariable Long id) {
        log.info("Cancelling workflow: {}", id);
        return executionRepository.findById(id)
                .map(exec -> {
                    if ("COMPLETED".equals(exec.getStatus()) || "CANCELLED".equals(exec.getStatus())) {
                        throw new IllegalStateException("Workflow is already " + exec.getStatus());
                    }
                    exec.setStatus("CANCELLED");
                    exec.setCompletedAt(LocalDateTime.now());
                    WorkflowExecution cancelled = executionRepository.save(exec);

                    // Cancel all pending/running steps
                    List<WorkflowStep> steps = stepRepository.findByExecutionIdOrderByStartedAtAsc(id);
                    for (WorkflowStep step : steps) {
                        if ("PENDING".equals(step.getStatus()) || "RUNNING".equals(step.getStatus())) {
                            step.setStatus("CANCELLED");
                            step.setCompletedAt(LocalDateTime.now());
                            stepRepository.save(step);
                        }
                    }

                    log.info("Workflow {} cancelled", id);
                    return ResponseEntity.ok(cancelled);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/history")
    public ResponseEntity<Page<WorkflowExecution>> getHistory(
            @RequestParam(required = false) String status,
            Pageable pageable) {
        log.info("Fetching workflow history - status: {}", status);
        Page<WorkflowExecution> page;
        if (status != null && !status.isBlank()) {
            page = executionRepository.findByStatus(status, pageable);
        } else {
            page = executionRepository.findAllByOrderByStartedAtDesc(pageable);
        }
        return ResponseEntity.ok(page);
    }

    private List<Map<String, Object>> parseSteps(String workflowDef) {
        // Simplified DSL step parser — extracts step names from JSON workflow definition
        List<Map<String, Object>> steps = new ArrayList<>();
        try {
            // Simulate parsing — in production this would interpret the DSL
            for (int i = 0; i < 3; i++) {
                Map<String, Object> step = new HashMap<>();
                step.put("name", "Step-" + (i + 1));
                step.put("order", i);
                steps.add(step);
            }
        } catch (Exception e) {
            log.error("Failed to parse workflow definition", e);
        }
        return steps;
    }

    // --- Request DTO ---

    public static class ExecuteWorkflowRequest {
        @NotBlank(message = "workflowDef is required")
        private String workflowDef;

        private String workflowName;

        public String getWorkflowDef() { return workflowDef; }
        public void setWorkflowDef(String workflowDef) { this.workflowDef = workflowDef; }
        public String getWorkflowName() { return workflowName; }
        public void setWorkflowName(String workflowName) { this.workflowName = workflowName; }
    }
}
