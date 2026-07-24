package com.viaios.agent.api;

import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/v1/agents/framework")
public class AgentFrameworkController {

    // ====== Planner ======
    private final Map<String, Object> memoryStore = new LinkedHashMap<>();

    @PostMapping("/planner")
    public Map<String, Object> plan(@RequestBody Map<String, Object> body) {
        String goal = (String) body.getOrDefault("goal", "analyze video");
        List<String> capabilities = parseCapabilities(body);

        List<Map<String, Object>> steps = new ArrayList<>();
        int stepNum = 1;
        for (String cap : capabilities) {
            Map<String, Object> step = new LinkedHashMap<>();
            step.put("step", stepNum++);
            step.put("capability", cap);
            step.put("action", getAction(cap, goal));
            step.put("estimated_ms", estimateLatency(cap));
            step.put("depends_on", stepNum > 2 ? List.of(stepNum - 2) : List.of());
            steps.add(step);
        }

        return Map.of("plan_id", "plan-" + UUID.randomUUID().toString().substring(0, 8),
            "goal", goal, "steps", steps, "total_steps", steps.size(),
            "estimated_total_ms", steps.stream().mapToInt(s -> (int) s.get("estimated_ms")).sum());
    }

    private List<String> parseCapabilities(Map<String, Object> body) {
        if (body.containsKey("capabilities")) {
            @SuppressWarnings("unchecked")
            var list = (List<String>) body.get("capabilities");
            return list;
        }
        return List.of("detection", "tracking", "reid", "face_recognize", "report");
    }

    private String getAction(String cap, String goal) {
        return Map.of("detection", "Detect objects in: " + goal,
            "tracking", "Track detected objects", "reid", "Cross-camera re-identification",
            "face_recognize", "Recognize faces", "ocr", "Extract text",
            "report", "Generate analysis report").getOrDefault(cap, "Execute: " + goal);
    }

    private int estimateLatency(String cap) {
        return Map.of("detection", 45, "tracking", 32, "reid", 55,
            "face_recognize", 28, "ocr", 60, "report", 500).getOrDefault(cap, 100);
    }

    // ====== Memory ======

    @PostMapping("/memory")
    public Map<String, Object> store(@RequestBody Map<String, Object> body) {
        String key = (String) body.getOrDefault("key", UUID.randomUUID().toString().substring(0, 8));
        Object value = body.getOrDefault("value", body);
        String type = (String) body.getOrDefault("type", "fact");
        memoryStore.put(key, Map.of("value", value, "type", type, "timestamp", System.currentTimeMillis()));
        return Map.of("key", key, "stored", true, "total_memories", memoryStore.size());
    }

    @GetMapping("/memory/{key}")
    public Map<String, Object> retrieve(@PathVariable String key) {
        return memoryStore.containsKey(key)
            ? Map.of("key", key, "found", true, "data", memoryStore.get(key))
            : Map.of("key", key, "found", false);
    }

    @GetMapping("/memory")
    public Map<String, Object> listMemory(@RequestParam(defaultValue = "") String type) {
        var filtered = new LinkedHashMap<String, Object>();
        for (var entry : memoryStore.entrySet()) {
            @SuppressWarnings("unchecked")
            Map<String, Object> val = (Map<String, Object>) entry.getValue();
            if (type.isEmpty() || type.equals(val.get("type"))) {
                filtered.put(entry.getKey(), entry.getValue());
            }
        }
        return Map.of("count", filtered.size(), "memories", filtered);
    }

    @DeleteMapping("/memory/{key}")
    public Map<String, Object> forget(@PathVariable String key) {
        memoryStore.remove(key);
        return Map.of("key", key, "deleted", true);
    }

    // ====== Reasoner ======

    @PostMapping("/reasoner")
    public Map<String, Object> reason(@RequestBody Map<String, Object> body) {
        String question = (String) body.getOrDefault("question", "What happened?");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> evidence = (List<Map<String, Object>>) body.getOrDefault("evidence", List.of());

        // Simulated reasoning chain
        List<Map<String, Object>> chain = new ArrayList<>();
        chain.add(Map.of("step", 1, "type", "observation", "content", "Analyzing " + evidence.size() + " evidence items"));
        chain.add(Map.of("step", 2, "type", "hypothesis", "content", "Generating hypotheses based on patterns"));
        chain.add(Map.of("step", 3, "type", "evaluation", "content", "Evaluating hypotheses against evidence"));
        chain.add(Map.of("step", 4, "type", "conclusion", "content", "Pattern detected: multiple correlated events"));

        return Map.of("reasoning_id", "reason-" + UUID.randomUUID().toString().substring(0, 8),
            "question", question, "chain", chain, "confidence", 0.85,
            "conclusion", "Based on " + evidence.size() + " evidence items, multiple correlated events detected with 85% confidence");
    }

    @GetMapping("/framework/status")
    public Map<String, Object> status() {
        return Map.of(
            "planner", "active", "memory", Map.of("entries", memoryStore.size(), "backend", "in-memory"),
            "reasoner", "active", "evaluator", "active", "governance", "basic",
            "framework_version", "2.0.0");
    }
}
