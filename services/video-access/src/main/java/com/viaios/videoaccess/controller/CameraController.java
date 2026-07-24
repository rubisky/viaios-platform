package com.viaios.videoaccess.controller;

import com.viaios.videoaccess.entity.Camera;
import com.viaios.videoaccess.repository.CameraRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Camera lifecycle controller for the Video Access Gateway.
 * <p>
 * Full CRUD for camera registrations plus start/stop stream control.
 * Cameras must be registered before they can be streamed or analysed.
 */
@RestController
@RequestMapping("/api/v1/cameras")
@RequiredArgsConstructor
@Tag(name = "Camera Management", description = "CRUD operations and stream control for cameras")
public class CameraController {

    private final CameraRepository cameraRepository;

    /** Lists all registered cameras, optionally filtered by status. */
    @GetMapping
    @Operation(summary = "List cameras", description = "Returns all cameras, optionally filtered by status or protocol")
    public ResponseEntity<List<Camera>> listCameras(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String protocol) {
        if (status != null && !status.isBlank()) {
            return ResponseEntity.ok(cameraRepository.findByStatus(status));
        }
        if (protocol != null && !protocol.isBlank()) {
            return ResponseEntity.ok(cameraRepository.findByProtocol(protocol));
        }
        return ResponseEntity.ok(cameraRepository.findAll());
    }

    /** Retrieves a single camera by its UUID. */
    @GetMapping("/{id}")
    @Operation(summary = "Get camera by ID", description = "Returns the camera with the specified UUID")
    public ResponseEntity<Camera> getCamera(@PathVariable String id) {
        return cameraRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /** Registers a new camera in the platform. */
    @PostMapping
    @Operation(summary = "Register camera", description = "Registers a new camera with its location, stream URL, and protocol")
    public ResponseEntity<Camera> createCamera(@RequestBody Camera camera) {
        Camera saved = cameraRepository.save(camera);
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    /** Updates a camera's mutable fields (name, location, stream URL, etc.). */
    @PutMapping("/{id}")
    @Operation(summary = "Update camera", description = "Updates the mutable fields of an existing camera registration")
    public ResponseEntity<Camera> updateCamera(@PathVariable String id, @RequestBody Camera updates) {
        return cameraRepository.findById(id)
                .map(existing -> {
                    existing.setName(updates.getName());
                    existing.setLocation(updates.getLocation());
                    existing.setStreamUrl(updates.getStreamUrl());
                    existing.setProtocol(updates.getProtocol());
                    existing.setFps(updates.getFps());
                    existing.setResolution(updates.getResolution());
                    return ResponseEntity.ok(cameraRepository.save(existing));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /** Deletes a camera registration. Any active stream is stopped first. */
    @DeleteMapping("/{id}")
    @Operation(summary = "Delete camera", description = "Removes a camera registration after stopping any active stream")
    public ResponseEntity<Void> deleteCamera(@PathVariable String id) {
        return cameraRepository.findById(id)
                .map(camera -> {
                    camera.setStatus("OFFLINE");
                    cameraRepository.save(camera);
                    cameraRepository.delete(camera);
                    return ResponseEntity.<Void>noContent().build();
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /** Starts video ingestion from this camera. The camera transitions to STREAMING. */
    @PostMapping("/{id}/start")
    @Operation(summary = "Start stream", description = "Begins video ingestion from the specified camera")
    public ResponseEntity<Map<String, String>> startCamera(@PathVariable String id) {
        return cameraRepository.findById(id)
                .map(camera -> {
                    camera.setStatus("STREAMING");
                    cameraRepository.save(camera);
                    return ResponseEntity.ok(Map.of(
                            "cameraId", camera.getId(),
                            "status", "STREAMING",
                            "message", "Stream started successfully"
                    ));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /** Stops video ingestion from this camera. The camera transitions to ONLINE. */
    @PostMapping("/{id}/stop")
    @Operation(summary = "Stop stream", description = "Stops video ingestion from the specified camera")
    public ResponseEntity<Map<String, String>> stopCamera(@PathVariable String id) {
        return cameraRepository.findById(id)
                .map(camera -> {
                    camera.setStatus("ONLINE");
                    cameraRepository.save(camera);
                    return ResponseEntity.ok(Map.of(
                            "cameraId", camera.getId(),
                            "status", "ONLINE",
                            "message", "Stream stopped successfully"
                    ));
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
