package com.viaios.search.api;
import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/v1/search")
public class SearchController {

    @PostMapping("/image")
    public Map<String, Object> byImage(@RequestBody Map<String, Object> req) {
        String url = (String) req.getOrDefault("image_url", "");
        return Map.of("query_type", "image", "query", url, "results", mockResults(6),
            "total", 6, "latency_ms", 45, "engine", "Milvus-ANN");
    }

    @PostMapping("/text")
    public Map<String, Object> byText(@RequestBody Map<String, Object> req) {
        String query = (String) req.getOrDefault("query", "");
        return Map.of("query_type", "text", "query", query,
            "results", mockResults(query.contains("person") ? 5 : 3),
            "total", query.contains("person") ? 5 : 3,
            "latency_ms", 32, "engine", "CLIP-CrossModal");
    }

    @PostMapping("/attribute")
    public Map<String, Object> byAttr(@RequestBody Map<String, Object> req) {
        return Map.of("query_type", "attribute", "results", mockResults(4), "total", 4, "latency_ms", 28);
    }

    @PostMapping("/composite")
    public Map<String, Object> composite(@RequestBody Map<String, Object> req) {
        return Map.of("query_type", "composite", "results", mockResults(3), "total", 3,
            "latency_ms", 67, "sub_engines", List.of("Milvus", "CLIP"));
    }

    @GetMapping("/history")
    public List<Map<String, Object>> history(@RequestParam(defaultValue = "") String userId) {
        return List.of(
            Map.of("id", 1, "query_type", "image", "query", "person_001.jpg", "result_count", 6, "latency_ms", 45),
            Map.of("id", 2, "query_type", "text", "query", "person in red coat", "result_count", 3, "latency_ms", 32)
        );
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        return Map.of("milvus", Map.of("status", "connected", "host", "localhost:19530", "collections", 2),
            "clip_model", "clip-vit-large", "index_type", "IVF_FLAT", "status", "operational");
    }

    @PostMapping("/init-demo")
    public Map<String, Object> initDemo() {
        return Map.of("engines", List.of("Milvus-ANN", "CLIP-CrossModal", "Attribute-Filter"),
            "collections", List.of("person_embeddings", "vehicle_features"), "status", "ready");
    }

    @GetMapping("/collections")
    public List<Map<String, Object>> collections() {
        return List.of(
            Map.of("name", "person_embeddings", "dimension", 512, "index", "IVF_FLAT", "count", 100000),
            Map.of("name", "vehicle_features", "dimension", 256, "index", "IVF_FLAT", "count", 50000)
        );
    }

    private List<Map<String, Object>> mockResults(int n) {
        List<Map<String, Object>> results = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            results.add(Map.of("id", "result-" + (i + 1),
                "score", Math.round((0.98 - i * 0.05) * 100) / 100.0,
                "url", "/snapshots/result_" + (i + 1) + ".jpg",
                "metadata", Map.of("camera", "cam-" + ((i % 3) + 1), "timestamp", "2026-07-22T10:00:0" + i)));
        }
        return results;
    }
}
