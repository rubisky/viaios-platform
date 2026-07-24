package com.viaios.workflowservice.api;

import com.viaios.workflowservice.domain.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api/v1/workflows")
public class WorkflowController {
    private final WorkflowRepository repo;
    private final Map<String, List<Map<String, Object>>> stepStore = new LinkedHashMap<>();

    public WorkflowController(WorkflowRepository r) { this.repo = r; }

    @GetMapping
    public List<WorkflowExecution> list(@RequestParam(defaultValue = "") String status) {
        if (!status.isEmpty()) return repo.findByStatus(status);
        return repo.findAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<WorkflowExecution> get(@PathVariable UUID id) {
        return repo.findById(id).map(ResponseEntity::ok).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/execute")
    public ResponseEntity<Map<String, Object>> execute(@RequestBody Map<String, Object> req) {
        String name = (String) req.getOrDefault("workflow", "video-analysis");
        String def = (String) req.getOrDefault("definition", "detection->tracking->embedding->report");

        WorkflowExecution w = new WorkflowExecution();
        w.setWorkflowName(name);
        w.setDefinition(def);
        w.setStatus("RUNNING");
        w.setStartedAt(Instant.now());
        w = repo.save(w);

        // Parse DAG steps
        List<Map<String, Object>> steps = new ArrayList<>();
        String[] stepNames = def.split("->");
        for (int i = 0; i < stepNames.length; i++) {
            Map<String, Object> step = new LinkedHashMap<>();
            step.put("step", i + 1);
            step.put("name", stepNames[i].trim());
            step.put("status", "PENDING");
            step.put("retry", 0);
            steps.add(step);
        }
        stepStore.put(w.getId().toString(), steps);

        // Simulate async execution
        final UUID wfId = w.getId();
        new Thread(() -> {
            List<Map<String, Object>> ss = stepStore.get(wfId.toString());
            for (Map<String, Object> step : ss) {
                step.put("status", "RUNNING");
                try { Thread.sleep(500); } catch (Exception e) {}
                step.put("status", "COMPLETED");
            }
            repo.findById(wfId).ifPresent(wf -> {
                wf.setStatus("COMPLETED");
                wf.setCompletedAt(Instant.now());
                wf.setResult("{\"steps_completed\":" + ss.size() + ",\"objects_detected\":15}");
                repo.save(wf);
            });
        }).start();

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("workflowId", w.getId());
        result.put("name", name);
        result.put("status", "RUNNING");
        result.put("steps", steps);
        result.put("startedAt", w.getStartedAt());
        return ResponseEntity.ok(result);
    }

    @GetMapping("/{id}/steps")
    public ResponseEntity<List<Map<String, Object>>> steps(@PathVariable UUID id) {
        List<Map<String, Object>> steps = stepStore.get(id.toString());
        return ResponseEntity.ok(steps != null ? steps : List.of());
    }

    @PostMapping("/{id}/cancel")
    public ResponseEntity<Map<String, Object>> cancel(@PathVariable UUID id) {
        return repo.findById(id).map(w -> {
            w.setStatus("CANCELLED");
            w.setCompletedAt(Instant.now());
            repo.save(w);
            return ResponseEntity.ok((Map<String, Object>) (Map) Map.of("status", "cancelled", "workflowId", id));
        }).orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/stats")
    public Map<String, Object> stats() {
        return Map.of("total", repo.count(), "completed", repo.countByStatus("COMPLETED"),
            "running", repo.countByStatus("RUNNING"), "failed", repo.countByStatus("FAILED"));
    }

    @GetMapping("/history")
    public List<WorkflowExecution> history() { return repo.findAllByOrderByStartedAtDesc(); }

    @PostMapping("/init-demo")
    public ResponseEntity<List<WorkflowExecution>> initDemo() {
        if (repo.count() > 0) return ResponseEntity.ok(repo.findAll());
        List<WorkflowExecution> demos = new ArrayList<>();
        String[][] data = {
            {"video-analysis", "detection->tracking->embedding->report", "COMPLETED"},
            {"face-recognition", "face_detect->face_recognize->alert", "COMPLETED"},
            {"vehicle-tracking", "vehicle_detect->plate_recognize->search", "RUNNING"},
        };
        for (String[] d : data) {
            WorkflowExecution w = new WorkflowExecution();
            w.setWorkflowName(d[0]); w.setDefinition(d[1]); w.setStatus(d[2]);
            w.setStartedAt(Instant.now());
            if ("COMPLETED".equals(d[2])) w.setCompletedAt(Instant.now());
            demos.add(repo.save(w));
        }
        return ResponseEntity.ok(demos);
    }
}
