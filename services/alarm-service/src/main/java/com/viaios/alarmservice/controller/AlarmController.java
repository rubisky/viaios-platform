package com.viaios.alarmservice.controller;

import com.viaios.alarmservice.entity.Alarm;
import com.viaios.alarmservice.repository.AlarmRepository;
import com.viaios.alarmservice.repository.RuleRepository;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/alarms")
public class AlarmController {

    private static final Logger log = LoggerFactory.getLogger(AlarmController.class);
    private final AlarmRepository alarmRepository;
    private final RuleRepository ruleRepository;

    public AlarmController(AlarmRepository alarmRepository, RuleRepository ruleRepository) {
        this.alarmRepository = alarmRepository;
        this.ruleRepository = ruleRepository;
    }

    @PostMapping
    public ResponseEntity<?> createAlarm(@Valid @RequestBody CreateAlarmRequest request) {
        log.info("Creating alarm for camera: {}, type: {}", request.getCameraId(), request.getType());

        if (!ruleRepository.existsById(request.getRuleId())) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(Map.of("error", "Rule not found", "ruleId", request.getRuleId()));
        }

        Alarm alarm = new Alarm();
        alarm.setRuleId(request.getRuleId());
        alarm.setCameraId(request.getCameraId());
        alarm.setType(request.getType());
        alarm.setSeverity(request.getSeverity() != null ? request.getSeverity() : "MEDIUM");
        alarm.setSnapshotUrl(request.getSnapshotUrl());
        alarm.setStatus("ACTIVE");

        Alarm saved = alarmRepository.save(alarm);
        log.info("Alarm created with id: {}", saved.getId());
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    @GetMapping
    public ResponseEntity<Page<Alarm>> listAlarms(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String severity,
            @RequestParam(required = false) String cameraId,
            @RequestParam(required = false) Long ruleId,
            Pageable pageable) {
        log.info("Listing alarms - status: {}, severity: {}", status, severity);

        Page<Alarm> page;
        if (status != null && severity != null) {
            page = alarmRepository.findByStatusAndSeverity(status, severity, pageable);
        } else if (status != null) {
            page = alarmRepository.findByStatus(status, pageable);
        } else if (cameraId != null) {
            page = alarmRepository.findByCameraId(cameraId, pageable);
        } else if (ruleId != null) {
            page = alarmRepository.findByRuleId(ruleId, pageable);
        } else {
            page = alarmRepository.findAll(pageable);
        }
        return ResponseEntity.ok(page);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Alarm> getAlarm(@PathVariable Long id) {
        log.info("Fetching alarm: {}", id);
        return alarmRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/acknowledge")
    public ResponseEntity<Alarm> acknowledgeAlarm(@PathVariable Long id, @Valid @RequestBody AcknowledgeRequest request) {
        log.info("Acknowledging alarm: {} by user: {}", id, request.getAcknowledgedBy());
        return alarmRepository.findById(id)
                .map(alarm -> {
                    if (!"ACTIVE".equals(alarm.getStatus())) {
                        throw new IllegalStateException("Only ACTIVE alarms can be acknowledged, current status: " + alarm.getStatus());
                    }
                    alarm.setStatus("ACKNOWLEDGED");
                    alarm.setAcknowledgedBy(request.getAcknowledgedBy());
                    Alarm saved = alarmRepository.save(alarm);
                    log.info("Alarm {} acknowledged", id);
                    return ResponseEntity.ok(saved);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/resolve")
    public ResponseEntity<Alarm> resolveAlarm(@PathVariable Long id, @RequestBody(required = false) Map<String, String> body) {
        log.info("Resolving alarm: {}", id);
        return alarmRepository.findById(id)
                .map(alarm -> {
                    if ("RESOLVED".equals(alarm.getStatus())) {
                        throw new IllegalStateException("Alarm is already RESOLVED");
                    }
                    alarm.setStatus("RESOLVED");
                    alarm.setResolvedAt(LocalDateTime.now());
                    Alarm saved = alarmRepository.save(alarm);
                    log.info("Alarm {} resolved", id);
                    return ResponseEntity.ok(saved);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        long active = alarmRepository.countByStatus("ACTIVE");
        long acknowledged = alarmRepository.countByStatus("ACKNOWLEDGED");
        long resolved = alarmRepository.countByStatus("RESOLVED");
        return ResponseEntity.ok(Map.of(
                "active", active,
                "acknowledged", acknowledged,
                "resolved", resolved,
                "total", active + acknowledged + resolved
        ));
    }

    // --- Request DTOs ---

    public static class CreateAlarmRequest {
        @NotNull(message = "ruleId is required")
        private Long ruleId;

        @NotBlank(message = "cameraId is required")
        private String cameraId;

        @NotBlank(message = "type is required")
        private String type;

        private String severity;

        private String snapshotUrl;

        public Long getRuleId() { return ruleId; }
        public void setRuleId(Long ruleId) { this.ruleId = ruleId; }
        public String getCameraId() { return cameraId; }
        public void setCameraId(String cameraId) { this.cameraId = cameraId; }
        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
        public String getSeverity() { return severity; }
        public void setSeverity(String severity) { this.severity = severity; }
        public String getSnapshotUrl() { return snapshotUrl; }
        public void setSnapshotUrl(String snapshotUrl) { this.snapshotUrl = snapshotUrl; }
    }

    public static class AcknowledgeRequest {
        @NotBlank(message = "acknowledgedBy is required")
        private String acknowledgedBy;

        public String getAcknowledgedBy() { return acknowledgedBy; }
        public void setAcknowledgedBy(String acknowledgedBy) { this.acknowledgedBy = acknowledgedBy; }
    }
}
