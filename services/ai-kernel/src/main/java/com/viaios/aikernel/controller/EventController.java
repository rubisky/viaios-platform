package com.viaios.aikernel.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Internal event bus controller for the AI Kernel.
 * <p>
 * Provides a synchronous HTTP API for publishing and consuming
 * domain events. In production this is backed by Kafka for
 * durability and broad fan-out, but the HTTP API is retained
 * for debugging and low-latency intra-kernel communication.
 */
@RestController
@RequestMapping("/api/v1/kernel/events")
@Tag(name = "Event Bus", description = "Publish and inspect kernel domain events")
public class EventController {

    /**
     * Returns the most recent events (last 50) from the event log.
     * Supports optional {@code type} filtering.
     *
     * @param type optional event type filter (e.g. "ModelDeployed")
     * @return list of event envelopes
     */
    @GetMapping
    @Operation(summary = "List recent events", description = "Returns the last 50 events, optionally filtered by type")
    public ResponseEntity<List<Map<String, Object>>> listEvents(@RequestParam(required = false) String type) {
        // In production: query from Kafka compacted topic or event store
        Map<String, Object> sampleEvent = Map.of(
                "id", UUID.randomUUID().toString(),
                "type", type != null ? type : "ModelDeployed",
                "source", "ai-kernel",
                "timestamp", Instant.now().toString(),
                "payload", Map.of("modelId", "uuid-1234", "version", "1.0.0")
        );
        return ResponseEntity.ok(List.of(sampleEvent));
    }

    /**
     * Publishes a domain event onto the event bus.
     * The event is persisted to Kafka and fanned out to all
     * interested consumers.
     *
     * @param body {@code {"type":"ModelDeployed","payload":{...},"source":"ai-kernel"}}
     * @return the published event envelope with server-assigned id and timestamp
     */
    @PostMapping("/publish")
    @Operation(summary = "Publish event", description = "Publishes a domain event to the Kafka-backed event bus")
    public ResponseEntity<Map<String, Object>> publishEvent(@RequestBody Map<String, Object> body) {
        Map<String, Object> envelope = Map.of(
                "id", UUID.randomUUID().toString(),
                "type", body.getOrDefault("type", "UnknownEvent"),
                "source", body.getOrDefault("source", "ai-kernel"),
                "timestamp", Instant.now().toString(),
                "payload", body.getOrDefault("payload", Map.of())
        );
        // In production: send to KafkaTemplate with proper partitioning
        return ResponseEntity.status(HttpStatus.CREATED).body(envelope);
    }
}
