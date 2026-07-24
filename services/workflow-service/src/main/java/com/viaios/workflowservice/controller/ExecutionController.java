package com.viaios.workflowservice.controller;

import com.viaios.workflowservice.entity.WorkflowExecution;
import com.viaios.workflowservice.entity.WorkflowStep;
import com.viaios.workflowservice.repository.WorkflowExecutionRepository;
import com.viaios.workflowservice.repository.WorkflowStepRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/workflows/{executionId}/steps")
public class ExecutionController {

    private static final Logger log = LoggerFactory.getLogger(ExecutionController.class);
    private final WorkflowExecutionRepository executionRepository;
    private final WorkflowStepRepository stepRepository;

    public ExecutionController(WorkflowExecutionRepository executionRepository, WorkflowStepRepository stepRepository) {
        this.executionRepository = executionRepository;
        this.stepRepository = stepRepository;
    }

    @GetMapping
    public ResponseEntity<?> getSteps(@PathVariable Long executionId) {
        log.info("Fetching steps for execution: {}", executionId);
        return executionRepository.findById(executionId)
                .map(exec -> {
                    List<WorkflowStep> steps = stepRepository.findByExecutionIdOrderByStartedAtAsc(executionId);

                    Map<String, Object> response = new HashMap<>();
                    response.put("executionId", executionId);
                    response.put("status", exec.getStatus());
                    response.put("totalSteps", steps.size());
                    response.put("steps", steps);
                    return ResponseEntity.ok(response);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{stepId}/result")
    public ResponseEntity<?> getStepResult(@PathVariable Long executionId, @PathVariable String stepId) {
        log.info("Fetching result for execution: {}, step: {}", executionId, stepId);

        if (!executionRepository.existsById(executionId)) {
            return ResponseEntity.notFound().build();
        }

        return stepRepository.findByExecutionIdAndStepId(executionId, stepId)
                .map(step -> {
                    Map<String, Object> result = new HashMap<>();
                    result.put("executionId", executionId);
                    result.put("stepId", step.getStepId());
                    result.put("stepName", step.getStepName());
                    result.put("status", step.getStatus());
                    result.put("output", step.getOutput());
                    result.put("error", step.getError());
                    result.put("retryCount", step.getRetryCount());
                    result.put("startedAt", step.getStartedAt());
                    result.put("completedAt", step.getCompletedAt());
                    return ResponseEntity.ok(result);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/status")
    public ResponseEntity<?> getStepStatuses(@PathVariable Long executionId) {
        log.info("Fetching step status summary for execution: {}", executionId);

        if (!executionRepository.existsById(executionId)) {
            return ResponseEntity.notFound().build();
        }

        List<WorkflowStep> steps = stepRepository.findByExecutionIdOrderByStartedAtAsc(executionId);
        long pending = steps.stream().filter(s -> "PENDING".equals(s.getStatus())).count();
        long running = steps.stream().filter(s -> "RUNNING".equals(s.getStatus())).count();
        long completed = steps.stream().filter(s -> "COMPLETED".equals(s.getStatus())).count();
        long failed = steps.stream().filter(s -> "FAILED".equals(s.getStatus())).count();
        long cancelled = steps.stream().filter(s -> "CANCELLED".equals(s.getStatus())).count();

        Map<String, Object> summary = new HashMap<>();
        summary.put("executionId", executionId);
        summary.put("totalSteps", steps.size());
        summary.put("pending", pending);
        summary.put("running", running);
        summary.put("completed", completed);
        summary.put("failed", failed);
        summary.put("cancelled", cancelled);
        return ResponseEntity.ok(summary);
    }
}
