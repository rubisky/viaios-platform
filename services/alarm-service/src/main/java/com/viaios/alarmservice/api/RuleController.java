package com.viaios.alarmservice.api;

import org.springframework.web.bind.annotation.*;
import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api/v1/alarms/rules")
public class RuleController {

    static final List<Map<String, Object>> RULES = new ArrayList<>(List.of(
        createRule("rule-001", "Intrusion Detection", "intrusion", "CRITICAL", true,
            Map.of("zones", List.of("Zone-A", "Zone-B"))),
        createRule("rule-002", "Speed Alert", "speed", "HIGH", true,
            Map.of("maxSpeedKmh", 120)),
        createRule("rule-003", "Crowd Density", "crowd", "MEDIUM", false,
            Map.of("maxDensity", 50)),
        createRule("rule-004", "Face Match", "face_match", "CRITICAL", true,
            Map.of("watchlist", List.of("person-001", "person-002"), "minConfidence", 0.85)),
        createRule("rule-005", "Abandoned Object", "abandoned", "MEDIUM", true,
            Map.of("minDurationSec", 30)),
        createRule("rule-006", "Line Crossing", "line_cross", "HIGH", true,
            Map.of("lineId", "line-A1", "direction", "bidirectional"))
    ));

    static Map<String, Object> createRule(String id, String name, String type, String severity, boolean enabled, Map<String, Object> condition) {
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("id", id); r.put("name", name); r.put("type", type);
        r.put("severity", severity); r.put("enabled", enabled);
        r.put("condition", condition); r.put("createdAt", Instant.now().toString());
        r.put("triggerCount", 0); r.put("lastTriggered", null);
        return r;
    }

    @GetMapping
    public List<Map<String, Object>> list(@RequestParam(defaultValue = "") String type,
                                           @RequestParam(defaultValue = "") String enabled) {
        return RULES.stream()
            .filter(r -> type.isEmpty() || type.equals(r.get("type")))
            .filter(r -> enabled.isEmpty() || String.valueOf(r.get("enabled")).equals(enabled))
            .toList();
    }

    @GetMapping("/{id}")
    public Map<String, Object> get(@PathVariable String id) {
        return RULES.stream().filter(r -> id.equals(r.get("id"))).findFirst()
            .orElse(Map.of("error", "not_found"));
    }

    @PostMapping
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        Map<String, Object> rule = new LinkedHashMap<>(body);
        rule.put("id", "rule-" + UUID.randomUUID().toString().substring(0, 8));
        rule.put("createdAt", Instant.now().toString());
        rule.putIfAbsent("enabled", true);
        rule.putIfAbsent("triggerCount", 0);
        rule.putIfAbsent("lastTriggered", null);
        RULES.add(rule);
        return rule;
    }

    @PutMapping("/{id}")
    public Map<String, Object> update(@PathVariable String id, @RequestBody Map<String, Object> body) {
        for (var r : RULES) {
            if (id.equals(r.get("id"))) {
                r.putAll(body);
                return r;
            }
        }
        return Map.of("error", "not_found");
    }

    @PutMapping("/{id}/toggle")
    public Map<String, Object> toggle(@PathVariable String id) {
        for (var r : RULES) {
            if (id.equals(r.get("id"))) {
                r.put("enabled", !(Boolean) r.get("enabled"));
                return r;
            }
        }
        return Map.of("error", "not_found");
    }

    @DeleteMapping("/{id}")
    public Map<String, Object> delete(@PathVariable String id) {
        RULES.removeIf(r -> id.equals(r.get("id")));
        return Map.of("deleted", id);
    }

    // ====== Rule Evaluation ======

    @PostMapping("/evaluate")
    public Map<String, Object> evaluate(@RequestBody Map<String, Object> event) {
        List<Map<String, Object>> matched = new ArrayList<>();
        String eventType = (String) event.getOrDefault("type", "");
        Map<String, Object> eventData = (Map<String, Object>) event.getOrDefault("data", Map.of());

        for (var rule : RULES) {
            if (!(Boolean) rule.get("enabled")) continue;
            if (!eventType.isEmpty() && !eventType.equals(rule.get("type"))) continue;

            Map<String, Object> condition = (Map<String, Object>) rule.get("condition");
            if (evaluateCondition(condition, eventData)) {
                rule.put("triggerCount", ((Integer) rule.getOrDefault("triggerCount", 0)) + 1);
                rule.put("lastTriggered", Instant.now().toString());
                matched.add(Map.of("ruleId", rule.get("id"), "ruleName", rule.get("name"),
                    "severity", rule.get("severity"), "triggered", true));
            }
        }
        return Map.of("event", eventType, "matched_rules", matched.size(), "rules", matched);
    }

    private boolean evaluateCondition(Map<String, Object> condition, Map<String, Object> data) {
        if (condition == null || condition.isEmpty()) return true;
        for (var entry : condition.entrySet()) {
            String key = entry.getKey();
            Object expected = entry.getValue();
            Object actual = data.get(key);
            if (actual == null) return false;
            if (expected instanceof Number && actual instanceof Number) {
                if (((Number) actual).doubleValue() > ((Number) expected).doubleValue()) return true;
            } else if (expected instanceof List && actual instanceof String) {
                if (((List<?>) expected).contains(actual)) return true;
            }
        }
        return !condition.containsKey("maxSpeedKmh") && !condition.containsKey("maxDensity")
            && !condition.containsKey("minDurationSec");
    }

    @GetMapping("/stats")
    public Map<String, Object> stats() {
        long enabled = RULES.stream().filter(r -> (Boolean) r.get("enabled")).count();
        int totalTriggers = RULES.stream().mapToInt(r -> (Integer) r.getOrDefault("triggerCount", 0)).sum();
        return Map.of("total", RULES.size(), "enabled", enabled, "total_triggers", totalTriggers);
    }
}
