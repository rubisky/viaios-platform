package com.viaios.analysis.api;

import com.viaios.analysis.domain.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api/v1/analysis")
public class AnalysisController {
    private final AnalysisTaskRepository repo;
    private final Map<String, String> pipelines = new LinkedHashMap<>();

    public AnalysisController(AnalysisTaskRepository r) { this.repo = r; }

    @PostMapping("/submit")
    public ResponseEntity<AnalysisTask> submit(@RequestBody Map<String, Object> body) {
        AnalysisTask task = new AnalysisTask();
        task.setCameraId((String) body.getOrDefault("cameraId", ""));
        task.setCapability((String) body.getOrDefault("capability", "detection"));
        task.setStatus("PENDING");
        task.setPriority(((Number) body.getOrDefault("priority", 5)).intValue());
        task.setCreatedAt(Instant.now());
        task = repo.save(task);

        // Simulate async processing
        final UUID taskId = task.getId();
        new Thread(() -> {
            try { Thread.sleep(2000); } catch (Exception e) {}
            repo.findById(taskId).ifPresent(t -> {
                t.setStatus("COMPLETED");
                t.setCompletedAt(Instant.now());
                Map<String, Object> result = new HashMap<>();
                result.put("detections", List.of(
                    Map.of("class", "person", "confidence", 0.95, "bbox", List.of(100, 150, 300, 400)),
                    Map.of("class", "car", "confidence", 0.88, "bbox", List.of(50, 200, 250, 350))
                ));
                result.put("processed_frames", 120);
                result.put("duration_ms", 2340);
                t.setResult(result.toString());
                repo.save(t);
            });
        }).start();

        return ResponseEntity.ok(task);
    }

    @GetMapping("/{id}/status")
    public ResponseEntity<Map<String, Object>> status(@PathVariable UUID id) {
        return repo.findById(id).map(t -> {
            Map<String, Object> m = new HashMap<>();
            m.put("taskId", t.getId()); m.put("status", t.getStatus());
            m.put("capability", t.getCapability()); m.put("createdAt", t.getCreatedAt());
            m.put("completedAt", t.getCompletedAt());
            return ResponseEntity.ok(m);
        }).orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/result")
    public ResponseEntity<Map<String, Object>> result(@PathVariable UUID id) {
        return repo.findById(id).map(t -> {
            if (!"COMPLETED".equals(t.getStatus()))
                return ResponseEntity.ok((Map<String, Object>) (Map) Map.of("status", t.getStatus(), "message", "Task not completed yet"));
            return ResponseEntity.ok((Map<String, Object>) (Map) Map.of("taskId", t.getId(), "status", t.getStatus(),
                "result", t.getResult(), "completedAt", t.getCompletedAt()));
        }).orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/history")
    public List<AnalysisTask> history(@RequestParam(defaultValue = "") String cameraId,
                                       @RequestParam(defaultValue = "") String status) {
        if (!cameraId.isEmpty()) return repo.findByCameraId(cameraId);
        if (!status.isEmpty()) return repo.findByStatus(status);
        return repo.findAll();
    }

    @GetMapping("/stats")
    public Map<String, Object> stats() {
        return Map.of("total", repo.count(), "completed", repo.countByStatus("COMPLETED"),
            "pending", repo.countByStatus("PENDING"), "failed", repo.countByStatus("FAILED"));
    }

    @PostMapping("/init-demo")
    public ResponseEntity<List<AnalysisTask>> initDemo() {
        List<AnalysisTask> tasks = new ArrayList<>();
        String[][] data = {
            {"cam-001", "detection", "COMPLETED"},
            {"cam-001", "face_recognition", "COMPLETED"},
            {"cam-002", "vehicle_recognition", "RUNNING"},
            {"cam-003", "detection", "COMPLETED"},
            {"cam-003", "tracking", "PENDING"},
        };
        for (String[] d : data) {
            AnalysisTask t = new AnalysisTask();
            t.setCameraId(d[0]); t.setCapability(d[1]); t.setStatus(d[2]);
            t.setPriority(5); t.setCreatedAt(Instant.now());
            if ("COMPLETED".equals(d[2])) t.setCompletedAt(Instant.now());
            tasks.add(repo.save(t));
        }
        return ResponseEntity.ok(tasks);
    }

    @PostMapping("/pipelines")
    public Map<String, Object> createPipeline(@RequestBody Map<String, Object> body) {
        String name = (String) body.getOrDefault("name", "default-pipeline");
        pipelines.put(name, body.toString());
        return Map.of("name", name, "status", "created");
    }

    @GetMapping("/pipelines")
    public Map<String, Object> listPipelines() {
        return Map.of("pipelines", pipelines.keySet());
    }
}
