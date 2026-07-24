package com.viaios.capability.api;

import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/v1/capabilities")
public class PipelineController {

    @PostMapping("/pipeline/analyze")
    public Map<String, Object> analyzeVideo(@RequestBody Map<String, Object> body) {
        String cameraId = (String) body.getOrDefault("cameraId", "cam-001");
        String pipeline = (String) body.getOrDefault("pipeline", "detect→track→reid");

        List<Map<String, Object>> steps = new ArrayList<>();
        Map<String, Object> context = new LinkedHashMap<>();
        context.put("cameraId", cameraId);
        long startTime = System.currentTimeMillis();

        // Step 1: Detection
        Map<String, Object> detect = new LinkedHashMap<>();
        detect.put("step", 1); detect.put("capability", "detection");
        detect.put("status", "completed");
        detect.put("latency_ms", 45);
        detect.put("output", Map.of("objects_detected", 15, "classes", List.of("person","car","bicycle")));
        steps.add(detect);
        context.put("detections", 15);

        // Step 2: Tracking (if in pipeline)
        if (pipeline.contains("track")) {
            Map<String, Object> track = new LinkedHashMap<>();
            track.put("step", 2); track.put("capability", "tracking");
            track.put("status", "completed");
            track.put("latency_ms", 32);
            track.put("output", Map.of("tracks_created", 12, "avg_track_length", 45));
            steps.add(track);
            context.put("tracks", 12);
        }

        // Step 3: Face Recognition (if in pipeline)
        if (pipeline.contains("face")) {
            Map<String, Object> face = new LinkedHashMap<>();
            face.put("step", 3); face.put("capability", "face_recognize");
            face.put("status", "completed");
            face.put("latency_ms", 28);
            face.put("output", Map.of("faces_detected", 8, "identities_matched", 5));
            steps.add(face);
            context.put("faces_matched", 5);
        }

        // Step 4: ReID (if in pipeline)
        if (pipeline.contains("reid")) {
            Map<String, Object> reid = new LinkedHashMap<>();
            reid.put("step", steps.size() + 1); reid.put("capability", "reid");
            reid.put("status", "completed");
            reid.put("latency_ms", 55);
            reid.put("output", Map.of("cross_camera_matches", 3, "gallery_size", 1000));
            steps.add(reid);
            context.put("reid_matches", 3);
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("pipeline_id", "pipe-" + UUID.randomUUID().toString().substring(0, 8));
        result.put("cameraId", cameraId);
        result.put("pipeline", pipeline);
        result.put("steps", steps);
        result.put("total_steps", steps.size());
        result.put("total_latency_ms", System.currentTimeMillis() - startTime);
        result.put("context", context);
        result.put("status", "completed");
        return result;
    }

    @GetMapping("/pipeline/templates")
    public List<Map<String, Object>> templates() {
        return List.of(
            Map.of("name", "full-analysis", "pipeline", "detect→track→reid→face",
                "description", "Complete video analysis: detect objects, track them, re-identify across cameras, recognize faces"),
            Map.of("name", "quick-detect", "pipeline", "detect",
                "description", "Fast object detection only"),
            Map.of("name", "person-search", "pipeline", "detect→reid",
                "description", "Detect persons and search across camera network"),
            Map.of("name", "vehicle-track", "pipeline", "detect→track→plate_recognize",
                "description", "Vehicle detection, tracking and plate recognition"),
            Map.of("name", "face-verify", "pipeline", "face_detect→face_recognize",
                "description", "Face detection and identity verification")
        );
    }
}
