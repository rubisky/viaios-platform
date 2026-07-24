package com.viaios.agent.api;

import com.viaios.agent.core.LlmClient;
import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/v1/agents")
public class AgentController {
    private final LlmClient llm;
    private final Map<String, Map<String, Object>> executions = new LinkedHashMap<>();

    public AgentController(LlmClient l) { this.llm = l; }

    static final Map<String, Map<String, Object>> AGENTS = new LinkedHashMap<>();
    static {
        add("video-agent", "Video Agent", "builtin", "Video analysis specialist",
            List.of("video_search", "frame_extract", "object_detect", "tracking_api"));
        add("search-agent", "Search Agent", "builtin", "Multi-modal search specialist",
            List.of("milvus_search", "nlu_parse", "attribute_filter", "clip_embed"));
        add("case-agent", "Case Agent", "builtin", "Case analysis specialist",
            List.of("case_crud", "evidence_link", "graph_traverse", "timeline_build"));
        add("knowledge-agent", "Knowledge Agent", "builtin", "Knowledge graph specialist",
            List.of("cypher_query", "graphrag_search", "entity_resolve", "relation_extract"));
        add("report-agent", "Report Agent", "builtin", "Report generation specialist",
            List.of("template_render", "data_aggregate", "pdf_export", "chart_generate"));
        add("alarm-agent", "Alarm Agent", "builtin", "Alarm analysis specialist",
            List.of("alarm_evaluate", "rule_match", "notification_send", "auto_case_create"));
        add("analysis-agent", "Analysis Agent", "builtin", "Deep analysis specialist",
            List.of("trajectory_analyze", "pattern_mine", "risk_score", "anomaly_detect"));
        add("operation-agent", "Operation Agent", "builtin", "Operations specialist",
            List.of("health_check", "log_query", "metrics_dashboard", "auto_recovery"));
    }

    static void add(String id, String name, String type, String desc, List<String> tools) {
        Map<String, Object> a = new HashMap<>();
        a.put("id", id); a.put("name", name); a.put("type", type);
        a.put("description", desc); a.put("tools", tools); a.put("status", "ready");
        AGENTS.put(id, a);
    }

    // ====== Agent CRUD ======

    @GetMapping
    public List<Map<String, Object>> list() { return new ArrayList<>(AGENTS.values()); }

    @GetMapping("/{id}")
    public Map<String, Object> get(@PathVariable String id) {
        return AGENTS.getOrDefault(id, Map.of("error", "not_found"));
    }

    @PostMapping("/init-demo")
    public Map<String, Object> initDemo() {
        return Map.of("registered", AGENTS.keySet(), "count", AGENTS.size(), "status", "ready");
    }

    // ====== Agent Execution ======

    @PostMapping("/execute")
    public Map<String, Object> execute(@RequestBody Map<String, Object> req) {
        String intent = (String) req.getOrDefault("intent", "analyze data");
        String agentId = (String) req.getOrDefault("agent_id", "search-agent");
        String taskId = "exec-" + UUID.randomUUID().toString().substring(0, 8);

        Map<String, Object> execution = new LinkedHashMap<>();
        execution.put("task_id", taskId);
        execution.put("agent_id", agentId);
        execution.put("intent", intent);
        execution.put("status", "running");
        execution.put("started_at", System.currentTimeMillis());
        executions.put(taskId, execution);

        // LLM Planning
        List<Map<String, String>> msgs = new ArrayList<>();
        msgs.add(Map.of("role", "system", "content",
            "You are VIAIOS AI agent. Decompose user intent into executable agent plan."));
        msgs.add(Map.of("role", "user", "content", intent));

        LlmClient.LlmResponse plan = llm.chat(msgs, 500);
        List<Map<String, Object>> steps = parsePlan(plan.content, intent);

        execution.put("plan", steps);
        execution.put("plan_raw", plan.content);
        execution.put("llm_model", plan.model);
        execution.put("tokens_used", plan.tokensUsed);
        execution.put("latency_ms", plan.latencyMs);
        execution.put("status", "completed");
        execution.put("completed_at", System.currentTimeMillis());

        Map<String, Object> result = new LinkedHashMap<>(execution);
        result.put("plan_steps", steps.size());
        return result;
    }

    @GetMapping("/executions/{taskId}")
    public Map<String, Object> getExecution(@PathVariable String taskId) {
        return executions.getOrDefault(taskId, Map.of("error", "not_found"));
    }

    // ====== Agent Chat ======

    @PostMapping("/chat")
    public Map<String, Object> chat(@RequestBody Map<String, Object> req) {
        String query = (String) req.getOrDefault("query", "hello");
        String agentId = (String) req.getOrDefault("agent_id", "search-agent");
        Map<String, Object> agent = AGENTS.get(agentId);
        String systemPrompt = agent != null
            ? "You are " + agent.get("name") + ". " + agent.get("description")
            : "You are VIAIOS AI assistant.";

        List<Map<String, String>> msgs = new ArrayList<>();
        msgs.add(Map.of("role", "system", "content", systemPrompt));
        msgs.add(Map.of("role", "user", "content", query));

        LlmClient.LlmResponse resp = llm.chat(msgs, 800);
        Map<String, Object> result = new HashMap<>();
        result.put("agent_id", agentId); result.put("query", query);
        result.put("response", resp.content); result.put("model", resp.model);
        result.put("tokens_used", resp.tokensUsed); result.put("latency_ms", resp.latencyMs);
        return result;
    }

    @GetMapping("/stats")
    public Map<String, Object> stats() {
        return Map.of("total_agents", AGENTS.size(), "ready_agents", AGENTS.size(),
            "llm_model", "deepseek-chat", "llm_endpoint", "https://api.deepseek.com/v1",
            "total_executions", executions.size());
    }

    // ====== Helpers ======

    private List<Map<String, Object>> parsePlan(String planText, String intent) {
        List<Map<String, Object>> steps = new ArrayList<>();
        String[] agents = { "video", "search", "knowledge", "report", "alarm", "analysis", "case" };
        int stepNum = 1;
        for (String agent : agents) {
            if (planText.toLowerCase().contains(agent)) {
                Map<String, Object> step = new HashMap<>();
                step.put("step", stepNum++);
                step.put("agent", agent + "-agent");
                step.put("action", getActionForAgent(agent, intent));
                step.put("status", "pending");
                steps.add(step);
            }
        }
        if (steps.isEmpty()) {
            steps.add(Map.of("step", 1, "agent", "search-agent", "action", "Search: " + intent, "status", "pending"));
            steps.add(Map.of("step", 2, "agent", "video-agent", "action", "Video analysis", "status", "pending"));
            steps.add(Map.of("step", 3, "agent", "knowledge-agent", "action", "Knowledge query", "status", "pending"));
            steps.add(Map.of("step", 4, "agent", "report-agent", "action", "Generate report", "status", "pending"));
        }
        return steps;
    }

    private String getActionForAgent(String agent, String intent) {
        return Map.of(
            "video", "Analyze video: " + intent,
            "search", "Multi-modal search: " + intent,
            "knowledge", "Knowledge graph query: " + intent,
            "report", "Generate report for: " + intent,
            "alarm", "Evaluate alarm: " + intent,
            "analysis", "Deep analysis: " + intent,
            "case", "Case investigation: " + intent
        ).getOrDefault(agent, "Execute: " + intent);
    }
}
