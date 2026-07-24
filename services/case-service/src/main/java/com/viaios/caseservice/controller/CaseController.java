package com.viaios.caseservice.controller;

import com.viaios.caseservice.entity.Case;
import com.viaios.caseservice.repository.CaseRepository;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
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
@RequestMapping("/api/v1/cases")
public class CaseController {

    private static final Logger log = LoggerFactory.getLogger(CaseController.class);
    private final CaseRepository caseRepository;

    public CaseController(CaseRepository caseRepository) {
        this.caseRepository = caseRepository;
    }

    @PostMapping
    public ResponseEntity<Case> createCase(@Valid @RequestBody CreateCaseRequest request) {
        log.info("Creating new case: {}", request.getTitle());

        Case c = new Case();
        c.setTitle(request.getTitle());
        c.setDescription(request.getDescription());
        c.setStatus("OPEN");
        c.setPriority(request.getPriority() != null ? request.getPriority() : "MEDIUM");
        c.setCreatedBy(request.getCreatedBy());
        c.setAssignedTo(request.getAssignedTo());

        Case saved = caseRepository.save(c);
        log.info("Case created with id: {}", saved.getId());
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    @GetMapping
    public ResponseEntity<Page<Case>> listCases(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String priority,
            @RequestParam(required = false) String createdBy,
            @RequestParam(required = false) String assignedTo,
            Pageable pageable) {
        log.info("Listing cases with filters - status: {}, priority: {}", status, priority);

        Page<Case> page;
        if (status != null && priority != null) {
            page = caseRepository.findByStatusAndPriority(status, priority, pageable);
        } else if (status != null) {
            page = caseRepository.findByStatus(status, pageable);
        } else if (createdBy != null) {
            page = caseRepository.findByCreatedBy(createdBy, pageable);
        } else if (assignedTo != null) {
            page = caseRepository.findByAssignedTo(assignedTo, pageable);
        } else {
            page = caseRepository.findAll(pageable);
        }
        return ResponseEntity.ok(page);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Case> getCase(@PathVariable Long id) {
        log.info("Fetching case: {}", id);
        return caseRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PutMapping("/{id}")
    public ResponseEntity<Case> updateCase(@PathVariable Long id, @Valid @RequestBody UpdateCaseRequest request) {
        log.info("Updating case: {}", id);
        return caseRepository.findById(id)
                .map(c -> {
                    if (request.getTitle() != null) c.setTitle(request.getTitle());
                    if (request.getDescription() != null) c.setDescription(request.getDescription());
                    if (request.getPriority() != null) c.setPriority(request.getPriority());
                    if (request.getAssignedTo() != null) c.setAssignedTo(request.getAssignedTo());
                    if (request.getTimeline() != null) c.setTimeline(request.getTimeline());
                    Case updated = caseRepository.save(c);
                    return ResponseEntity.ok(updated);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/close")
    public ResponseEntity<Case> closeCase(@PathVariable Long id, @RequestBody(required = false) Map<String, String> body) {
        log.info("Closing case: {}", id);
        return caseRepository.findById(id)
                .map(c -> {
                    if (!"OPEN".equals(c.getStatus()) && !"IN_PROGRESS".equals(c.getStatus())) {
                        throw new IllegalStateException("Case is already " + c.getStatus());
                    }
                    c.setStatus("CLOSED");
                    Case closed = caseRepository.save(c);
                    return ResponseEntity.ok(closed);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    // --- Request DTOs ---

    public static class CreateCaseRequest {
        @NotBlank(message = "Title is required")
        @Size(max = 200, message = "Title must not exceed 200 characters")
        private String title;

        private String description;

        @NotBlank(message = "createdBy is required")
        private String createdBy;

        private String assignedTo;

        private String priority;

        public String getTitle() { return title; }
        public void setTitle(String title) { this.title = title; }
        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }
        public String getCreatedBy() { return createdBy; }
        public void setCreatedBy(String createdBy) { this.createdBy = createdBy; }
        public String getAssignedTo() { return assignedTo; }
        public void setAssignedTo(String assignedTo) { this.assignedTo = assignedTo; }
        public String getPriority() { return priority; }
        public void setPriority(String priority) { this.priority = priority; }
    }

    public static class UpdateCaseRequest {
        private String title;
        private String description;
        private String priority;
        private String assignedTo;
        private String timeline;

        public String getTitle() { return title; }
        public void setTitle(String title) { this.title = title; }
        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }
        public String getPriority() { return priority; }
        public void setPriority(String priority) { this.priority = priority; }
        public String getAssignedTo() { return assignedTo; }
        public void setAssignedTo(String assignedTo) { this.assignedTo = assignedTo; }
        public String getTimeline() { return timeline; }
        public void setTimeline(String timeline) { this.timeline = timeline; }
    }
}
