package com.viaios.reportservice.controller;

import com.viaios.reportservice.entity.Report;
import com.viaios.reportservice.entity.Template;
import com.viaios.reportservice.repository.ReportRepository;
import com.viaios.reportservice.repository.TemplateRepository;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/reports")
public class ReportController {

    private static final Logger log = LoggerFactory.getLogger(ReportController.class);
    private final ReportRepository reportRepository;
    private final TemplateRepository templateRepository;

    public ReportController(ReportRepository reportRepository, TemplateRepository templateRepository) {
        this.reportRepository = reportRepository;
        this.templateRepository = templateRepository;
    }

    @PostMapping("/generate")
    public ResponseEntity<?> generateReport(@Valid @RequestBody GenerateReportRequest request) {
        log.info("Generating report for case: {}, format: {}", request.getCaseId(), request.getOutputFormat());

        if (request.getTemplateId() != null && !templateRepository.existsById(request.getTemplateId())) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(Map.of("error", "Template not found", "templateId", request.getTemplateId()));
        }

        Report report = new Report();
        report.setCaseId(request.getCaseId());
        report.setTemplateId(request.getTemplateId());
        report.setStatus("PROCESSING");
        report.setOutputFormat(request.getOutputFormat());

        Report saved = reportRepository.save(report);

        // Simulate async generation process
        String outputUrl = "/tmp/viaios/reports/" + saved.getId() + "_" + UUID.randomUUID().toString().substring(0, 8)
                + "." + request.getOutputFormat().toLowerCase();
        saved.setOutputUrl(outputUrl);
        saved.setStatus("COMPLETED");
        reportRepository.save(saved);

        log.info("Report {} generated at {}", saved.getId(), outputUrl);
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Report> getReport(@PathVariable Long id) {
        log.info("Fetching report: {}", id);
        return reportRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/download")
    public ResponseEntity<?> downloadReport(@PathVariable Long id) {
        log.info("Download request for report: {}", id);
        return reportRepository.findById(id)
                .map(report -> {
                    if (report.getOutputUrl() == null) {
                        return ResponseEntity.status(HttpStatus.CONFLICT)
                                .body((Object) Map.of("error", "Report not yet generated", "status", report.getStatus()));
                    }
                    return ResponseEntity.ok(Map.of(
                            "reportId", report.getId(),
                            "downloadUrl", report.getOutputUrl(),
                            "format", report.getOutputFormat(),
                            "status", report.getStatus(),
                            "message", "Download ready — stream from outputUrl"
                    ));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping
    public ResponseEntity<?> listReports(
            @RequestParam(required = false) Long caseId,
            @RequestParam(required = false) String status) {
        log.info("Listing reports - caseId: {}, status: {}", caseId, status);

        if (caseId != null) {
            return ResponseEntity.ok(reportRepository.findByCaseIdOrderByCreatedAtDesc(caseId));
        }
        if (status != null) {
            return ResponseEntity.ok(reportRepository.findByStatus(status));
        }
        return ResponseEntity.ok(reportRepository.findAll());
    }

    // --- Request DTO ---

    public static class GenerateReportRequest {
        @NotNull(message = "caseId is required")
        private Long caseId;

        private Long templateId;

        @NotNull(message = "outputFormat is required")
        private String outputFormat;

        public Long getCaseId() { return caseId; }
        public void setCaseId(Long caseId) { this.caseId = caseId; }
        public Long getTemplateId() { return templateId; }
        public void setTemplateId(Long templateId) { this.templateId = templateId; }
        public String getOutputFormat() { return outputFormat; }
        public void setOutputFormat(String outputFormat) { this.outputFormat = outputFormat; }
    }
}
