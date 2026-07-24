package com.viaios.reportservice.api;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api/v1/reports")
public class ReportController {

    static final List<Map<String, Object>> REPORTS = new ArrayList<>();
    static final List<Map<String, Object>> TEMPLATES = new ArrayList<>();
    static {
        addTpl("tpl-001", "Case Analysis Report", "case_analysis", List.of("Summary", "Evidence", "Timeline", "Conclusion"));
        addTpl("tpl-002", "Weekly Summary", "weekly", List.of("Overview", "Statistics", "Alarms", "Recommendations"));
        addTpl("tpl-003", "Evidence Report", "evidence_report", List.of("Case Info", "Evidence List", "Chain of Custody"));
    }

    static void addTpl(String id, String name, String type, List<String> sections) {
        TEMPLATES.add(Map.of("id", id, "name", name, "type", type, "sections", sections));
    }

    @GetMapping
    public List<Map<String, Object>> list() { return REPORTS; }

    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> get(@PathVariable String id) {
        return REPORTS.stream().filter(r -> id.equals(r.get("id"))).findFirst()
            .map(ResponseEntity::ok).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/generate")
    public Map<String, Object> generate(@RequestBody Map<String, Object> body) {
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("id", "rpt-" + UUID.randomUUID().toString().substring(0, 8));
        r.put("title", body.getOrDefault("title", "Report"));
        r.put("type", body.getOrDefault("type", "case_analysis"));
        r.put("caseId", body.getOrDefault("caseId", ""));
        r.put("templateId", body.getOrDefault("templateId", "tpl-001"));
        r.put("outputFormat", body.getOrDefault("outputFormat", "PDF"));
        r.put("status", "PENDING");
        r.put("createdAt", Instant.now().toString());
        REPORTS.add(0, r);
        // Simulate async generation
        new Thread(() -> {
            try { Thread.sleep(3000); } catch (Exception e) {}
            r.put("status", "COMPLETED");
            r.put("outputUrl", "/reports/" + r.get("id") + ".pdf");
        }).start();
        return r;
    }

    @GetMapping("/{id}/download")
    public Map<String, Object> download(@PathVariable String id) {
        return Map.of("reportId", id, "downloadUrl", "/api/v1/reports/" + id + "/download", "format", "PDF");
    }

    @GetMapping("/templates")
    public List<Map<String, Object>> templates() { return TEMPLATES; }

    @PostMapping("/init-demo")
    public Map<String, Object> initDemo() {
        if (REPORTS.isEmpty()) {
            String[][] data = {
                {"Weekly Report W28", "weekly", "COMPLETED", "PDF"},
                {"Case Analysis #001", "case_analysis", "COMPLETED", "DOCX"},
                {"Evidence Report #003", "evidence_report", "COMPLETED", "PDF"},
                {"Monthly Summary", "monthly", "GENERATING", "PDF"},
            };
            for (String[] d : data) {
                Map<String, Object> r = new LinkedHashMap<>();
                r.put("id", "rpt-" + UUID.randomUUID().toString().substring(0, 8));
                r.put("title", d[0]); r.put("type", d[1]); r.put("status", d[2]);
                r.put("outputFormat", d[3]); r.put("createdAt", Instant.now().toString());
                REPORTS.add(r);
            }
        }
        return Map.of("reports", REPORTS.size(), "templates", TEMPLATES.size(), "status", "ready");
    }
}
