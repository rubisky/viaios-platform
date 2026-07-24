package com.viaios.caseservice.api;

import org.springframework.web.bind.annotation.*;
import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api/v1/trajectory")
public class TrajectoryController {

    static final List<Map<String, Object>> TRAJECTORIES = new ArrayList<>();
    static {
        addTraj("person-001", "cam-001", 121.4737, 31.2304, "2026-07-22T08:00:00Z");
        addTraj("person-001", "cam-002", 121.4740, 31.2310, "2026-07-22T08:02:00Z");
        addTraj("person-001", "cam-003", 121.4745, 31.2315, "2026-07-22T08:05:00Z");
        addTraj("vehicle-001", "cam-001", 121.4737, 31.2304, "2026-07-22T08:10:00Z");
        addTraj("vehicle-001", "cam-004", 121.4750, 31.2320, "2026-07-22T08:15:00Z");
        addTraj("vehicle-001", "cam-005", 121.4760, 31.2330, "2026-07-22T08:20:00Z");
    }

    static void addTraj(String targetId, String cameraId, double lng, double lat, String ts) {
        TRAJECTORIES.add(Map.of("id", UUID.randomUUID().toString().substring(0, 8),
            "targetId", targetId, "cameraId", cameraId,
            "longitude", lng, "latitude", lat, "timestamp", ts));
    }

    @GetMapping
    public Map<String, Object> query(@RequestParam(defaultValue = "") String targetId,
                                      @RequestParam(defaultValue = "") String cameraId) {
        List<Map<String, Object>> results = TRAJECTORIES.stream()
            .filter(t -> targetId.isEmpty() || targetId.equals(t.get("targetId")))
            .filter(t -> cameraId.isEmpty() || cameraId.equals(t.get("cameraId")))
            .toList();
        return Map.of("trajectory", results, "count", results.size());
    }

    @GetMapping("/search")
    public Map<String, Object> search(@RequestParam(defaultValue = "") String targetId) {
        if (targetId.isEmpty()) return Map.of("trajectory", TRAJECTORIES, "count", TRAJECTORIES.size());
        var points = TRAJECTORIES.stream().filter(t -> targetId.equals(t.get("targetId"))).toList();
        // Build trajectory path
        List<List<Double>> path = points.stream()
            .map(p -> List.of((Double) p.get("longitude"), (Double) p.get("latitude"))).toList();
        return Map.of("targetId", targetId, "path", path, "points", points.size(),
            "cameras", points.stream().map(p -> p.get("cameraId")).distinct().toList());
    }

    @GetMapping("/stats")
    public Map<String, Object> stats() {
        var targets = TRAJECTORIES.stream().map(t -> t.get("targetId")).distinct().toList();
        return Map.of("total_points", TRAJECTORIES.size(), "unique_targets", targets.size(),
            "targets", targets);
    }

    @PostMapping("/init-demo")
    public Map<String, Object> initDemo() {
        return Map.of("trajectories", TRAJECTORIES.size(), "targets",
            List.of("person-001", "vehicle-001"), "status", "ready");
    }
}
