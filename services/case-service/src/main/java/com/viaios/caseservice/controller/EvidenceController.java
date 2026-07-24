package com.viaios.caseservice.controller;

import com.viaios.caseservice.entity.Case;
import com.viaios.caseservice.entity.Evidence;
import com.viaios.caseservice.repository.CaseRepository;
import com.viaios.caseservice.repository.EvidenceRepository;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/cases/{caseId}/evidence")
public class EvidenceController {

    private static final Logger log = LoggerFactory.getLogger(EvidenceController.class);
    private final EvidenceRepository evidenceRepository;
    private final CaseRepository caseRepository;

    public EvidenceController(EvidenceRepository evidenceRepository, CaseRepository caseRepository) {
        this.evidenceRepository = evidenceRepository;
        this.caseRepository = caseRepository;
    }

    @PostMapping
    public ResponseEntity<?> addEvidence(@PathVariable Long caseId, @Valid @RequestBody AddEvidenceRequest request) {
        log.info("Adding evidence to case: {}", caseId);

        if (!caseRepository.existsById(caseId)) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(Map.of("error", "Case not found", "caseId", caseId));
        }

        Evidence evidence = new Evidence();
        evidence.setCaseId(caseId);
        evidence.setType(request.getType());
        evidence.setUrl(request.getUrl());
        evidence.setSource(request.getSource());
        evidence.setHash(request.getHash());
        evidence.setReliabilityScore(request.getReliabilityScore());

        Evidence saved = evidenceRepository.save(evidence);
        log.info("Evidence {} added to case {}", saved.getId(), caseId);
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    @GetMapping
    public ResponseEntity<List<Evidence>> listEvidence(
            @PathVariable Long caseId,
            @RequestParam(required = false) String type) {
        log.info("Listing evidence for case: {}", caseId);

        if (!caseRepository.existsById(caseId)) {
            return ResponseEntity.notFound().build();
        }

        List<Evidence> evidence;
        if (type != null && !type.isBlank()) {
            evidence = evidenceRepository.findByCaseIdAndType(caseId, type);
        } else {
            evidence = evidenceRepository.findByCaseIdOrderByCreatedAtDesc(caseId);
        }
        return ResponseEntity.ok(evidence);
    }

    @GetMapping("/{evidenceId}")
    public ResponseEntity<Evidence> getEvidence(@PathVariable Long caseId, @PathVariable("evidenceId") Long evidenceId) {
        log.info("Fetching evidence {} for case {}", evidenceId, caseId);
        return evidenceRepository.findById(evidenceId)
                .filter(e -> e.getCaseId().equals(caseId))
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{evidenceId}")
    public ResponseEntity<Map<String, Object>> deleteEvidence(
            @PathVariable Long caseId, @PathVariable("evidenceId") Long evidenceId) {
        log.info("Deleting evidence {} from case {}", evidenceId, caseId);

        return evidenceRepository.findById(evidenceId)
                .filter(e -> e.getCaseId().equals(caseId))
                .map(e -> {
                    evidenceRepository.delete(e);
                    return ResponseEntity.ok(Map.of(
                            "message", "Evidence deleted",
                            "evidenceId", evidenceId,
                            "caseId", caseId
                    ));
                })
                .orElse(ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of(
                        "error", "Evidence not found for this case",
                        "evidenceId", evidenceId,
                        "caseId", caseId
                )));
    }

    // --- Request DTO ---

    public static class AddEvidenceRequest {
        @NotBlank(message = "Type is required")
        private String type;

        @NotBlank(message = "URL is required")
        private String url;

        private String source;

        private String hash;

        @NotNull(message = "reliabilityScore is required")
        private Double reliabilityScore;

        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
        public String getUrl() { return url; }
        public void setUrl(String url) { this.url = url; }
        public String getSource() { return source; }
        public void setSource(String source) { this.source = source; }
        public String getHash() { return hash; }
        public void setHash(String hash) { this.hash = hash; }
        public Double getReliabilityScore() { return reliabilityScore; }
        public void setReliabilityScore(Double reliabilityScore) { this.reliabilityScore = reliabilityScore; }
    }
}
