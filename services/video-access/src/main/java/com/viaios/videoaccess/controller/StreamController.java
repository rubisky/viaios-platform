package com.viaios.videoaccess.controller;

import com.viaios.videoaccess.repository.CameraRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Stream access controller for the Video Access Gateway.
 * <p>
 * Provides endpoints for retrieving live stream URLs and
 * on-demand snapshots (single-frame JPEG captures) from
 * registered cameras.
 */
@RestController
@RequestMapping("/api/v1/cameras")
@RequiredArgsConstructor
@Tag(name = "Stream Access", description = "Live stream and snapshot retrieval endpoints")
public class StreamController {

    private final CameraRepository cameraRepository;

    /**
     * Returns the live stream URL for the specified camera.
     * The URL can be an RTSP, WebRTC, or HLS endpoint depending
     * on the camera protocol and transcoding configuration.
     *
     * @param id camera UUID
     * @return {@code {"streamUrl":"rtsp://...","format":"RTSP","cameraId":"..."}}
     */
    @GetMapping("/{id}/stream")
    @Operation(summary = "Get stream URL", description = "Returns the live stream URL for the specified camera")
    public ResponseEntity<Map<String, String>> getStream(@PathVariable String id) {
        return cameraRepository.findById(id)
                .map(camera -> {
                    if (!"STREAMING".equals(camera.getStatus())) {
                        return ResponseEntity.ok(Map.of(
                                "cameraId", camera.getId(),
                                "status", camera.getStatus(),
                                "message", "Camera is not currently streaming"
                        ));
                    }
                    return ResponseEntity.ok(Map.of(
                            "cameraId", camera.getId(),
                            "streamUrl", camera.getStreamUrl() != null ? camera.getStreamUrl() : "",
                            "format", camera.getProtocol(),
                            "status", "STREAMING"
                    ));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Captures a single-frame snapshot (JPEG) from the camera.
     * The snapshot is returned as a base64-encoded image along
     * with capture timestamp and resolution metadata.
     *
     * @param id camera UUID
     * @return {@code {"cameraId":"...","timestamp":"...","format":"JPEG","resolution":"1920x1080","imageBase64":"..."}}
     */
    @GetMapping("/{id}/snapshot")
    @Operation(summary = "Capture snapshot", description = "Returns a single-frame JPEG snapshot from the camera as base64")
    public ResponseEntity<Map<String, String>> getSnapshot(@PathVariable String id) {
        return cameraRepository.findById(id)
                .map(camera -> {
                    // In production: connect to camera, grab one frame, encode as JPEG base64
                    return ResponseEntity.ok(Map.of(
                            "cameraId", camera.getId(),
                            "timestamp", java.time.Instant.now().toString(),
                            "format", "JPEG",
                            "resolution", camera.getResolution(),
                            "imageBase64", "/9j/4AAQSkZJRg...placeholder..."
                    ));
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
