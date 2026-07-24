package com.viaios.alarmservice.api;

import com.viaios.alarmservice.domain.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api/v1/alarms")
public class AlarmController {
    private final AlarmRepository repo;
    private final com.viaios.alarmservice.infra.KafkaEventPublisher kafka;

    public AlarmController(AlarmRepository r, com.viaios.alarmservice.infra.KafkaEventPublisher k) {
        this.repo = r; this.kafka = k;
    }

    // ====== CRUD ======

    @GetMapping
    public List<Alarm> list(@RequestParam(defaultValue = "") String status,
                            @RequestParam(defaultValue = "") String severity,
                            @RequestParam(defaultValue = "") String cameraId) {
        if (!cameraId.isEmpty()) return repo.findByCameraId(cameraId);
        if (!severity.isEmpty()) return repo.findBySeverityAndStatus(severity, "TRIGGERED");
        if (!status.isEmpty()) return repo.findByStatus(status);
        return repo.findAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Alarm> get(@PathVariable UUID id) {
        return repo.findById(id).map(ResponseEntity::ok).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<Alarm> create(@RequestBody Map<String, Object> body) {
        Alarm alarm = new Alarm();
        alarm.setType((String) body.getOrDefault("type", "GENERAL"));
        alarm.setSeverity((String) body.getOrDefault("severity", "MEDIUM"));
        alarm.setMessage((String) body.getOrDefault("message", ""));
        alarm.setCameraId((String) body.getOrDefault("cameraId", ""));
        alarm.setStatus("TRIGGERED");
        alarm = repo.save(alarm);
        // Publish to Kafka
        Map<String, Object> event = new HashMap<>();
        event.put("id", alarm.getId()); event.put("type", alarm.getType());
        event.put("severity", alarm.getSeverity()); event.put("message", alarm.getMessage());
        event.put("cameraId", alarm.getCameraId()); event.put("status", alarm.getStatus());
        event.put("timestamp", java.time.Instant.now().toString());
        kafka.publishAlarmEvent(event);
        return ResponseEntity.ok(alarm);
    }

    @PostMapping("/{id}/acknowledge")
    public ResponseEntity<Alarm> acknowledge(@PathVariable UUID id) {
        return repo.findById(id).map(a -> { a.setStatus("ACKNOWLEDGED"); return ResponseEntity.ok(repo.save(a)); })
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/resolve")
    public ResponseEntity<Alarm> resolve(@PathVariable UUID id, @RequestBody(required = false) Map<String, String> body) {
        return repo.findById(id).map(a -> {
            a.setStatus("RESOLVED");
            return ResponseEntity.ok(repo.save(a));
        }).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/bulk/acknowledge")
    public Map<String, Object> bulkAcknowledge(@RequestBody List<UUID> ids) {
        int count = 0;
        for (UUID id : ids) {
            var opt = repo.findById(id);
            if (opt.isPresent()) { opt.get().setStatus("ACKNOWLEDGED"); repo.save(opt.get()); count++; }
        }
        return Map.of("acknowledged", count, "total", ids.size());
    }

    // ====== Stats ======

    @GetMapping("/stats")
    public Map<String, Object> stats() {
        return Map.of("total", repo.count(), "by_status", Map.of(
            "TRIGGERED", repo.countByStatus("TRIGGERED"),
            "ACKNOWLEDGED", repo.countByStatus("ACKNOWLEDGED"),
            "RESOLVED", repo.countByStatus("RESOLVED")));
    }

    @GetMapping("/trends")
    public List<Map<String, Object>> trends() {
        return List.of(
            Map.of("hour", "08:00", "count", 12), Map.of("hour", "10:00", "count", 23),
            Map.of("hour", "12:00", "count", 18), Map.of("hour", "14:00", "count", 31),
            Map.of("hour", "16:00", "count", 25), Map.of("hour", "18:00", "count", 15));
    }

    @GetMapping("/by-severity")
    public Map<String, Long> bySeverity() {
        return Map.of("CRITICAL", repo.countBySeverity("CRITICAL"), "HIGH", repo.countBySeverity("HIGH"),
            "MEDIUM", repo.countBySeverity("MEDIUM"), "LOW", repo.countBySeverity("LOW"));
    }

    @PostMapping("/init-demo")
    public ResponseEntity<List<Alarm>> initDemo() {
        if (repo.count() > 0) return ResponseEntity.ok(repo.findAll());
        List<Alarm> demos = new ArrayList<>();
        String[][] data = {
            {"INTRUSION", "CRITICAL", "Unauthorized access at East Gate", "cam-001"},
            {"LOITERING", "HIGH", "Person loitering >5min at Plaza", "cam-003"},
            {"CROWD", "MEDIUM", "Crowd density exceeds threshold", "cam-004"},
            {"ABANDONED", "MEDIUM", "Suspicious object at Parking", "cam-002"},
            {"FACE_MATCH", "HIGH", "Watchlist match at East Gate", "cam-001"},
        };
        for (String[] d : data) {
            Alarm a = new Alarm();
            a.setType(d[0]); a.setSeverity(d[1]); a.setMessage(d[2]);
            a.setCameraId(d[3]); a.setStatus("TRIGGERED");
            demos.add(repo.save(a));
        }
        return ResponseEntity.ok(demos);
    }
}
