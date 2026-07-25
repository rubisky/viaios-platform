package com.viaios.agent.core;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Lightweight HTTP client for DeepSeek LLM API.
 * Falls back to simulated responses when API key is not configured.
 */
public class LlmClient {

    private final String apiKey;
    private final String baseUrl;
    private static final String DEFAULT_BASE_URL = "https://api.deepseek.com/v1";
    private static final String DEFAULT_MODEL = "deepseek-chat";

    public LlmClient() {
        this.apiKey = System.getenv("DEEPSEEK_API_KEY");
        this.baseUrl = DEFAULT_BASE_URL;
    }

    public LlmClient(String apiKey, String baseUrl) {
        this.apiKey = (apiKey != null && !apiKey.isEmpty()) ? apiKey : System.getenv("DEEPSEEK_API_KEY");
        this.baseUrl = (baseUrl != null && !baseUrl.isEmpty()) ? baseUrl : DEFAULT_BASE_URL;
    }

    public static class LlmResponse {
        public String content;
        public String model;
        public int tokensUsed;
        public long latencyMs;

        public LlmResponse(String content, String model, int tokensUsed, long latencyMs) {
            this.content = content;
            this.model = model;
            this.tokensUsed = tokensUsed;
            this.latencyMs = latencyMs;
        }
    }

    /**
     * Send chat completion request.
     *
     * @param messages  list of messages with "role" and "content" keys
     * @param maxTokens maximum completion tokens
     * @return LlmResponse with content, model, token count, and latency
     */
    public LlmResponse chat(List<Map<String, String>> messages, int maxTokens) {
        long start = System.currentTimeMillis();

        // Try real DeepSeek API if key is available
        if (apiKey != null && !apiKey.isEmpty()) {
            try {
                return callDeepSeekApi(messages, maxTokens, start);
            } catch (Exception e) {
                System.err.println("[LlmClient] DeepSeek API error: " + e.getMessage() + " — falling back to dev mode");
            }
        }

        // Dev mode: simulated response
        return simulatedResponse(messages, start);
    }

    private LlmResponse callDeepSeekApi(List<Map<String, String>> messages, int maxTokens, long start) throws Exception {
        URL url = URI.create(baseUrl + "/chat/completions").toURL();
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Authorization", "Bearer " + apiKey);
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(300000);
        conn.setDoOutput(true);

        // Build JSON request body
        String msgsJson = messages.stream()
            .map(m -> String.format("{\"role\":\"%s\",\"content\":\"%s\"}",
                escapeJson(m.get("role")), escapeJson(m.get("content"))))
            .collect(Collectors.joining(","));

        String body = String.format(
            "{\"model\":\"%s\",\"messages\":[%s],\"max_tokens\":%d,\"temperature\":0.7,\"stream\":false}",
            DEFAULT_MODEL, msgsJson, maxTokens);

        try (OutputStream os = conn.getOutputStream()) {
            os.write(body.getBytes(StandardCharsets.UTF_8));
        }

        int status = conn.getResponseCode();
        String responseBody;
        if (status == 200) {
            responseBody = readStream(conn.getInputStream());
        } else {
            String errBody = readStream(conn.getErrorStream());
            throw new IOException("HTTP " + status + ": " + errBody);
        }
        conn.disconnect();

        // Simple JSON parse (avoid heavy dependency)
        String content = extractJsonValue(responseBody, "\"content\":\"", "\"");
        String model = extractJsonValue(responseBody, "\"model\":\"", "\"");
        if (model.isEmpty()) model = DEFAULT_MODEL;

        int promptTokens = extractJsonInt(responseBody, "\"prompt_tokens\":", ",");
        int completionTokens = extractJsonInt(responseBody, "\"completion_tokens\":", ",");
        int totalTokens = extractJsonInt(responseBody, "\"total_tokens\":", "}");

        long latency = System.currentTimeMillis() - start;
        return new LlmResponse(content, model, totalTokens > 0 ? totalTokens : 100, latency);
    }

    private LlmResponse simulatedResponse(List<Map<String, String>> messages, long start) {
        String userMsg = "";
        for (Map<String, String> m : messages) {
            if ("user".equals(m.get("role"))) {
                userMsg = m.get("content");
                break;
            }
        }
        String response = "[DEV MODE] Simulated DeepSeek response.\n\n" +
            "Based on your query: \"" + truncate(userMsg, 200) + "\"\n\n" +
            "I would analyze this by:\n" +
            "1. Breaking down the task into steps\n" +
            "2. Identifying the relevant agents (search, video, knowledge)\n" +
            "3. Executing each step with proper tool calls\n" +
            "4. Aggregating results into a final answer\n\n" +
            "Note: Set DEEPSEEK_API_KEY environment variable for real AI responses.";

        long latency = System.currentTimeMillis() - start;
        return new LlmResponse(response, "deepseek-chat (simulated)", 150, latency);
    }

    // -- Simple JSON parsing helpers (no external dependencies) --

    private static String extractJsonValue(String json, String key, String terminator) {
        int start = json.indexOf(key);
        if (start < 0) return "";
        start += key.length();
        int end = json.indexOf(terminator, start);
        if (end < 0) return json.substring(start);
        return unescapeJson(json.substring(start, end));
    }

    private static int extractJsonInt(String json, String key, String terminator) {
        String val = extractJsonValue(json, key, terminator);
        try {
            return Integer.parseInt(val.trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private static String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }

    private static String unescapeJson(String s) {
        return s.replace("\\\"", "\"")
                .replace("\\n", "\n")
                .replace("\\r", "\r")
                .replace("\\t", "\t")
                .replace("\\\\", "\\");
    }

    private static String readStream(InputStream is) throws IOException {
        if (is == null) return "";
        try (BufferedReader r = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8))) {
            return r.lines().collect(Collectors.joining("\n"));
        }
    }

    private static String truncate(String s, int maxLen) {
        if (s == null) return "";
        return s.length() <= maxLen ? s : s.substring(0, maxLen) + "...";
    }
}
