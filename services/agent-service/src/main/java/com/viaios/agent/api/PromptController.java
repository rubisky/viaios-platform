package com.viaios.agent.api;

import org.springframework.web.bind.annotation.*;
import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api/v1/prompts")
public class PromptController {

    static final List<Map<String, Object>> TEMPLATES = new ArrayList<>();
    static {
        add("video-analysis", "Analyze the following video scene: {{scene_description}}. Identify all objects, persons, and vehicles. Output JSON with detections, confidence scores, and bounding boxes.");
        add("case-report", "You are a forensic analyst. Review the following case evidence: {{evidence_summary}}. Generate a structured report with: 1) Case Summary 2) Key Findings 3) Evidence Analysis 4) Recommendations.");
        add("alarm-evaluate", "Evaluate the following alarm event: type={{alarm_type}}, severity={{severity}}, camera={{camera_id}}, description={{description}}. Determine if this is a true positive or false positive. Explain your reasoning.");
        add("knowledge-query", "Given the knowledge graph with entities: {{entity_list}}, answer the question: {{question}}. Use graph traversal to find relationships.");
        add("search-query", "A user is searching for: {{query}}. Generate an optimized multi-modal search plan using image, text, and attribute modalities. Include query expansion and re-ranking strategy.");
        add("trajectory-analyze", "Analyze trajectory points: {{trajectory_data}}. Identify patterns, anomalies, and predict next likely positions. Output path analysis with confidence scores.");
    }

    static void add(String name, String template) {
        TEMPLATES.add(new LinkedHashMap<>(Map.of(
            "id", "tpl-" + UUID.randomUUID().toString().substring(0, 8),
            "name", name, "template", template,
            "variables", extractVars(template),
            "version", "1.0.0",
            "createdAt", Instant.now().toString()
        )));
    }

    static List<String> extractVars(String template) {
        List<String> vars = new ArrayList<>();
        int start = 0;
        while ((start = template.indexOf("{{", start)) >= 0) {
            int end = template.indexOf("}}", start);
            if (end > start) vars.add(template.substring(start + 2, end).trim());
            start = end + 2;
        }
        return vars;
    }

    @GetMapping
    public List<Map<String, Object>> list() { return TEMPLATES; }

    @GetMapping("/{name}")
    public Map<String, Object> get(@PathVariable String name) {
        return TEMPLATES.stream().filter(t -> name.equals(t.get("name"))).findFirst()
            .orElse(Map.of("error", "not_found"));
    }

    @PostMapping
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        String name = (String) body.get("name");
        String template = (String) body.get("template");
        Map<String, Object> t = new LinkedHashMap<>();
        t.put("id", "tpl-" + UUID.randomUUID().toString().substring(0, 8));
        t.put("name", name); t.put("template", template);
        t.put("variables", extractVars(template));
        t.put("version", "1.0.0"); t.put("createdAt", Instant.now().toString());
        TEMPLATES.add(t);
        return t;
    }

    @PostMapping("/render")
    public Map<String, Object> render(@RequestBody Map<String, Object> body) {
        String name = (String) body.get("name");
        @SuppressWarnings("unchecked")
        Map<String, String> vars = (Map<String, String>) body.getOrDefault("variables", Map.of());

        var tpl = TEMPLATES.stream().filter(t -> name.equals(t.get("name"))).findFirst();
        if (tpl.isEmpty()) return Map.of("error", "template not found");

        String rendered = (String) tpl.get().get("template");
        for (var entry : vars.entrySet()) {
            rendered = rendered.replace("{{" + entry.getKey() + "}}", entry.getValue());
        }
        return Map.of("name", name, "rendered", rendered, "variables", vars);
    }
}
