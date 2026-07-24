package com.viaios.agent.api;

import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/v1/agents")
public class OrchestrateController {

    // Multi-Agent orchestration: chain multiple agents
    @PostMapping("/orchestrate")
    public Map<String, Object> orchestrate(@RequestBody Map<String, Object> body) {
        String intent = (String) body.getOrDefault("intent", "analyze and report");
        List<Map<String, String>> agentChain = parseChain(body);

        List<Map<String, Object>> results = new ArrayList<>();
        Map<String, Object> context = new LinkedHashMap<>();
        context.put("intent", intent);

        for (Map<String, String> step : agentChain) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("agent", step.get("agent"));
            result.put("action", step.get("action"));
            result.put("status", "completed");
            result.put("output", simulateOutput(step.get("agent"), intent));
            result.put("latency_ms", new Random().nextInt(500) + 50);
            results.add(result);

            // Pass context to next agent
            context.put(step.get("agent") + "_done", true);
        }

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("orchestration_id", "orch-" + UUID.randomUUID().toString().substring(0, 8));
        response.put("intent", intent);
        response.put("pipeline", agentChain);
        response.put("results", results);
        response.put("total_steps", results.size());
        response.put("status", "completed");
        response.put("summary", generateSummary(results));
        return response;
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, String>> parseChain(Map<String, Object> body) {
        if (body.containsKey("pipeline")) {
            return (List<Map<String, String>>) body.get("pipeline");
        }
        // Default pipeline: search -> video -> knowledge -> report
        return List.of(
            Map.of("agent", "search-agent", "action", "Multi-modal search"),
            Map.of("agent", "video-agent", "action", "Video analysis"),
            Map.of("agent", "knowledge-agent", "action", "Knowledge graph query"),
            Map.of("agent", "report-agent", "action", "Generate report")
        );
    }

    private String simulateOutput(String agent, String intent) {
        return Map.of(
            "search-agent", "Found 12 matching results for: " + intent,
            "video-agent", "Analyzed 5 video clips, 3 persons detected",
            "knowledge-agent", "Graph query returned 8 related entities",
            "report-agent", "Report generated with 4 sections",
            "case-agent", "Case timeline constructed with 6 events",
            "alarm-agent", "2 alarms evaluated, 0 triggered",
            "analysis-agent", "Trajectory analysis complete, risk score: 0.3"
        ).getOrDefault(agent, "Task completed");
    }

    private String generateSummary(List<Map<String, Object>> results) {
        return "Multi-agent pipeline completed " + results.size() +
            " steps. " + results.stream().filter(r -> "completed".equals(r.get("status"))).count() +
            " agents succeeded.";
    }
}
