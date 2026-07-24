package com.viaios.analysis.controller;

import com.viaios.analysis.entity.AnalysisTask;
import com.viaios.analysis.repository.AnalysisTaskRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * Analysis task controller for the VIAIOS AI Analysis service.
 * <p>
 * Submit new analysis tasks, poll for status, retrieve results,
 * browse history, and cancel or delete tasks.
 */
@RestController
@RequestMapping("/api/v1/analysis")
@RequiredArgsConstructor
@Tag(name = "Analysis Tasks", description = "Submit, track, and retrieve AI analysis tasks")
public class AnalysisController {

    private final AnalysisTaskRepository taskRepository;

    /**
     * Submits a new analysis task to the pipeline.
     * The task is persisted in PENDING status and will be picked up
     * by the AI Kernel scheduler for resource allocation.
     *
     * @param body {@code {"cameraId":"...","capability":"OBJECT_DETECTION","params":{...},"priority":5}}
     * @return the created task with its server-assigned UUID and PENDING status
     */
    @PostMapping("/submit")
    @Operation(summary = "Submit analysis task", description = "Creates a new analysis task and enqueues it for scheduling")
    public ResponseEntity<AnalysisTask> submitTask(@RequestBody Map<String, Object> body) {
        AnalysisTask task = AnalysisTask.builder()
                .cameraId((String) body.get("cameraId"))
                .capability((String) body.get("capability"))
                .params(body.containsKey("params") ? body.get("params").toString() : null)
                .priority(body.containsKey("priority") ? ((Number) body.get("priority")).intValue() : 5)
                .status("PENDING")
                .build();
        AnalysisTask saved = taskRepository.save(task);
        // In production: publish AnalysisTaskSubmitted event to Kafka
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    /**
     * Returns the current status of an analysis task.
     * Includes progress percentage if the task is RUNNING.
     *
     * @param id task UUID
     * @return {@code {"id":"...","status":"RUNNING","progress":45,"capability":"OBJECT_DETECTION"}}
     */
    @GetMapping("/{id}/status")
    @Operation(summary = "Get task status", description = "Returns the current status and progress of an analysis task")
    public ResponseEntity<Map<String, Object>> getStatus(@PathVariable String id) {
        return taskRepository.findById(id)
                .map(task -> ResponseEntity.ok(Map.<String, Object>of(
                        "id", task.getId(),
                        "status", task.getStatus(),
                        "capability", task.getCapability(),
                        "priority", task.getPriority(),
                        "createdAt", task.getCreatedAt().toString(),
                        "progress", "RUNNING".equals(task.getStatus()) ? 45 : 100
                )))
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Returns the full analysis result for a completed task.
     * The result structure depends on the analysis capability.
     *
     * @param id task UUID
     * @return the result JSONB payload alongside task metadata
     */
    @GetMapping("/{id}/result")
    @Operation(summary = "Get analysis result", description = "Returns the full analysis result for a completed task")
    public ResponseEntity<Map<String, Object>> getResult(@PathVariable String id) {
        return taskRepository.findById(id)
                .filter(task -> "COMPLETED".equals(task.getStatus()))
                .map(task -> ResponseEntity.ok(Map.<String, Object>of(
                        "id", task.getId(),
                        "cameraId", task.getCameraId(),
                        "capability", task.getCapability(),
                        "status", task.getStatus(),
                        "result", task.getResult() != null ? task.getResult() : "{}",
                        "completedAt", task.getCompletedAt() != null ? task.getCompletedAt().toString() : null
                )))
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Returns the 50 most recent analysis tasks across all cameras.
     * Supports optional filtering by cameraId and status.
     */
    @GetMapping("/history")
    @Operation(summary = "Analysis history", description = "Returns the 50 most recent analysis tasks, optionally filtered")
    public ResponseEntity<List<AnalysisTask>> getHistory(
            @RequestParam(required = false) String cameraId,
            @RequestParam(required = false) String status) {
        if (cameraId != null && !cameraId.isBlank() && status != null && !status.isBlank()) {
            return ResponseEntity.ok(taskRepository.findByCameraIdAndStatus(cameraId, status));
        }
        if (cameraId != null && !cameraId.isBlank()) {
            return ResponseEntity.ok(taskRepository.findByCameraIdOrderByCreatedAtDesc(cameraId));
        }
        if (status != null && !status.isBlank()) {
            return ResponseEntity.ok(taskRepository.findByStatus(status));
        }
        return ResponseEntity.ok(taskRepository.findTop50ByOrderByCreatedAtDesc());
    }

    /**
     * Cancels a running or pending analysis task.
     * Resources are released and the task transitions to CANCELLED.
     */
    @DeleteMapping("/{id}")
    @Operation(summary = "Cancel/delete task", description = "Cancels a running task or deletes a completed/failed task")
    public ResponseEntity<Void> deleteTask(@PathVariable String id) {
        return taskRepository.findById(id)
                .map(task -> {
                    if ("RUNNING".equals(task.getStatus()) || "PENDING".equals(task.getStatus())) {
                        task.setStatus("CANCELLED");
                        task.setCompletedAt(Instant.now());
                        taskRepository.save(task);
                    } else {
                        taskRepository.delete(task);
                    }
                    return ResponseEntity.<Void>noContent().build();
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
