package com.viaios.analysis.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Analysis pipeline configuration controller.
 * <p>
 * Pipelines are reusable analysis workflows that chain together
 * multiple capabilities (e.g. object detection followed by tracking)
 * and can be submitted as a single task. This controller manages
 * pipeline definitions.
 */
@RestController
@RequestMapping("/api/v1/analysis/pipelines")
@Tag(name = "Analysis Pipelines", description = "Define and manage reusable analysis pipeline workflows")
public class PipelineController {

    /**
     * Lists all registered analysis pipelines.
     * Each pipeline defines a sequence of capability steps with
     * their respective parameters.
     *
     * @return list of pipeline definitions
     */
    @GetMapping
    @Operation(summary = "List pipelines", description = "Returns all registered analysis pipeline definitions")
    public ResponseEntity<List<Map<String, Object>>> listPipelines() {
        Map<String, Object> samplePipeline = Map.of(
                "id", UUID.randomUUID().toString(),
                "name", "Intrusion Detection Pipeline",
                "description", "Detect persons → track movement → check zone violation",
                "steps", List.of(
                        Map.of("order", 1, "capability", "OBJECT_DETECTION", "params", Map.of("modelId", "yolo-v8", "classes", List.of("person"))),
                        Map.of("order", 2, "capability", "INTRUSION_DETECTION", "params", Map.of("zones", List.of(Map.of("id", "zone-1", "polygon", List.of(List.of(0, 0), List.of(100, 0), List.of(100, 100), List.of(0, 100))))))
                ),
                "createdAt", java.time.Instant.now().toString()
        );
        return ResponseEntity.ok(List.of(samplePipeline));
    }

    /**
     * Creates a new analysis pipeline definition.
     * Pipelines are reusable templates that can be referenced
     * when submitting analysis tasks.
     *
     * @param body {@code {"name":"...","description":"...","steps":[...]}}
     * @return the created pipeline with server-assigned UUID
     */
    @PostMapping
    @Operation(summary = "Create pipeline", description = "Defines a new reusable analysis pipeline workflow")
    public ResponseEntity<Map<String, Object>> createPipeline(@RequestBody Map<String, Object> body) {
        Map<String, Object> pipeline = Map.of(
                "id", UUID.randomUUID().toString(),
                "name", body.getOrDefault("name", "Unnamed Pipeline"),
                "description", body.getOrDefault("description", ""),
                "steps", body.getOrDefault("steps", List.of()),
                "createdAt", java.time.Instant.now().toString()
        );
        // In production: persist to pipelines table or configuration store
        return ResponseEntity.status(HttpStatus.CREATED).body(pipeline);
    }
}
