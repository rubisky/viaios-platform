package com.viaios.caseservice.api;

import com.viaios.caseservice.domain.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api/v1/cases")
public class CaseController {
    private final CaseRepository caseRepo;
    private final EvidenceRepository evidenceRepo;

    public CaseController(CaseRepository cr, EvidenceRepository er) {
        this.caseRepo = cr; this.evidenceRepo = er;
    }

    // ====== Case CRUD ======

    @GetMapping
    public List<CaseEntity> list(@RequestParam(defaultValue = "") String status,
                                  @RequestParam(defaultValue = "") String priority) {
        if (!status.isEmpty()) return caseRepo.findByStatus(status);
        if (!priority.isEmpty()) return caseRepo.findByStatusAndPriority(status, priority);
        return caseRepo.findAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<CaseEntity> get(@PathVariable UUID id) {
        return caseRepo.findById(id).map(ResponseEntity::ok).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<CaseEntity> create(@RequestBody Map<String, Object> body) {
        CaseEntity c = new CaseEntity();
        c.setTitle((String) body.getOrDefault("title", "New Case"));
        c.setDescription((String) body.getOrDefault("description", ""));
        c.setStatus((String) body.getOrDefault("status", "NEW"));
        c.setPriority((String) body.getOrDefault("priority", "P2"));
        c.setCreatedAt(Instant.now());
        return ResponseEntity.ok(caseRepo.save(c));
    }

    @PutMapping("/{id}")
    public ResponseEntity<CaseEntity> update(@PathVariable UUID id, @RequestBody CaseEntity updates) {
        return caseRepo.findById(id).map(c -> {
            if (updates.getTitle() != null) c.setTitle(updates.getTitle());
            if (updates.getStatus() != null) c.setStatus(updates.getStatus());
            if (updates.getPriority() != null) c.setPriority(updates.getPriority());
            return ResponseEntity.ok(caseRepo.save(c));
        }).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/close")
    public ResponseEntity<CaseEntity> close(@PathVariable UUID id) {
        return caseRepo.findById(id).map(c -> {
            c.setStatus("CLOSED"); return ResponseEntity.ok(caseRepo.save(c));
        }).orElse(ResponseEntity.notFound().build());
    }

    // ====== Evidence ======

    @GetMapping("/{caseId}/evidence")
    public ResponseEntity<List<Evidence>> listEvidence(@PathVariable UUID caseId) {
        return ResponseEntity.ok(evidenceRepo.findByCaseId(caseId));
    }

    @PostMapping("/{caseId}/evidence")
    public ResponseEntity<Evidence> addEvidence(@PathVariable UUID caseId, @RequestBody Map<String, Object> body) {
        if (!caseRepo.existsById(caseId)) return ResponseEntity.notFound().build();
        Evidence e = new Evidence();
        e.setCaseId(caseId);
        e.setType((String) body.getOrDefault("type", "IMAGE"));
        e.setTitle((String) body.getOrDefault("title", "Evidence"));
        e.setUrl((String) body.getOrDefault("url", ""));
        e.setSource((String) body.getOrDefault("source", ""));
        e.setCreatedAt(Instant.now());
        return ResponseEntity.ok(evidenceRepo.save(e));
    }

    // ====== Stats ======

    @GetMapping("/stats")
    public Map<String, Object> stats() {
        return Map.of("total", caseRepo.count(), "open", caseRepo.countByStatus("OPEN"),
            "in_progress", caseRepo.countByStatus("IN_PROGRESS"), "closed", caseRepo.countByStatus("CLOSED"));
    }

    @PostMapping("/init-demo")
    public ResponseEntity<List<CaseEntity>> initDemo() {
        if (caseRepo.count() > 0) return ResponseEntity.ok(caseRepo.findAll());
        List<CaseEntity> demos = new ArrayList<>();
        String[][] data = {
            {"Theft Case #2024-001", "OPEN", "P0", "East District theft investigation"},
            {"Traffic Accident #2024-015", "IN_PROGRESS", "P1", "South Station hit and run"},
            {"Missing Person #2024-008", "OPEN", "P1", "Missing elderly at West Plaza"},
            {"Fraud Case #2024-022", "CLOSED", "P2", "Online fraud investigation"},
            {"Vandalism #2024-030", "IN_PROGRESS", "P2", "Park property damage"},
        };
        for (String[] d : data) {
            CaseEntity c = new CaseEntity();
            c.setTitle(d[0]); c.setStatus(d[1]); c.setPriority(d[2]);
            c.setDescription(d[3]); c.setCreatedAt(Instant.now());
            demos.add(caseRepo.save(c));
        }
        return ResponseEntity.ok(demos);
    }
}
