package com.viaios.search.controller;

import com.viaios.search.entity.SearchHistory;
import com.viaios.search.repository.SearchHistoryRepository;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/v1/search")
public class SearchController {

    private static final Logger log = LoggerFactory.getLogger(SearchController.class);
    private final SearchHistoryRepository searchHistoryRepository;

    public SearchController(SearchHistoryRepository searchHistoryRepository) {
        this.searchHistoryRepository = searchHistoryRepository;
    }

    @PostMapping("/image")
    public ResponseEntity<Map<String, Object>> searchByImage(@Valid @RequestBody ImageSearchRequest request) {
        long start = System.currentTimeMillis();
        log.info("Image search requested by user: {}", request.getUserId());

        // Simulated vector search via Milvus
        List<Map<String, Object>> results = simulateSearchResults("image", request.getImageUrl());

        long latency = System.currentTimeMillis() - start;
        persistHistory(request.getUserId(), "image", buildQueryJson(request), results.size(), latency);

        Map<String, Object> response = new HashMap<>();
        response.put("queryType", "image");
        response.put("results", results);
        response.put("totalHits", results.size());
        response.put("latencyMs", latency);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/text")
    public ResponseEntity<Map<String, Object>> searchByText(@Valid @RequestBody TextSearchRequest request) {
        long start = System.currentTimeMillis();
        log.info("Text search requested by user: {}", request.getUserId());

        List<Map<String, Object>> results = simulateSearchResults("text", request.getQuery());

        long latency = System.currentTimeMillis() - start;
        persistHistory(request.getUserId(), "text", buildQueryJson(request), results.size(), latency);

        Map<String, Object> response = new HashMap<>();
        response.put("queryType", "text");
        response.put("results", results);
        response.put("totalHits", results.size());
        response.put("latencyMs", latency);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/attribute")
    public ResponseEntity<Map<String, Object>> searchByAttribute(@Valid @RequestBody AttributeSearchRequest request) {
        long start = System.currentTimeMillis();
        log.info("Attribute search requested by user: {}", request.getUserId());

        List<Map<String, Object>> results = simulateSearchResults("attribute", request.getAttributes().toString());

        long latency = System.currentTimeMillis() - start;
        persistHistory(request.getUserId(), "attribute", buildQueryJson(request), results.size(), latency);

        Map<String, Object> response = new HashMap<>();
        response.put("queryType", "attribute");
        response.put("results", results);
        response.put("totalHits", results.size());
        response.put("latencyMs", latency);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/composite")
    public ResponseEntity<Map<String, Object>> searchByComposite(@Valid @RequestBody CompositeSearchRequest request) {
        long start = System.currentTimeMillis();
        log.info("Composite search requested by user: {}", request.getUserId());

        List<Map<String, Object>> results = simulateSearchResults("composite", "multi-modal");

        long latency = System.currentTimeMillis() - start;
        persistHistory(request.getUserId(), "composite", buildQueryJson(request), results.size(), latency);

        Map<String, Object> response = new HashMap<>();
        response.put("queryType", "composite");
        response.put("results", results);
        response.put("totalHits", results.size());
        response.put("latencyMs", latency);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/history")
    public ResponseEntity<Page<SearchHistory>> getHistory(
            @RequestParam String userId,
            @RequestParam(required = false) String queryType,
            Pageable pageable) {
        Page<SearchHistory> page;
        if (queryType != null && !queryType.isBlank()) {
            page = searchHistoryRepository.findByUserIdAndQueryType(userId, queryType, pageable);
        } else {
            page = searchHistoryRepository.findByUserId(userId, pageable);
        }
        return ResponseEntity.ok(page);
    }

    private void persistHistory(String userId, String queryType, String queryJson, int resultCount, long latencyMs) {
        try {
            SearchHistory history = new SearchHistory(userId, queryType, queryJson, resultCount, latencyMs);
            searchHistoryRepository.save(history);
        } catch (Exception e) {
            log.error("Failed to persist search history", e);
        }
    }

    private String buildQueryJson(Object request) {
        // Simplified JSON serialization of the request object
        return request.toString();
    }

    private List<Map<String, Object>> simulateSearchResults(String type, String query) {
        List<Map<String, Object>> results = new ArrayList<>();
        for (int i = 0; i < 5; i++) {
            Map<String, Object> item = new HashMap<>();
            item.put("id", "target-" + (i + 1));
            item.put("score", 0.95 - (i * 0.05));
            item.put("type", type);
            item.put("label", "Match " + (i + 1) + " for: " + query);
            results.add(item);
        }
        return results;
    }

    // --- Request DTOs ---

    public static class ImageSearchRequest {
        @NotBlank(message = "userId is required")
        private String userId;
        @NotBlank(message = "imageUrl is required")
        private String imageUrl;
        private Integer topK = 20;
        private Double threshold = 0.7;

        public String getUserId() { return userId; }
        public void setUserId(String userId) { this.userId = userId; }
        public String getImageUrl() { return imageUrl; }
        public void setImageUrl(String imageUrl) { this.imageUrl = imageUrl; }
        public Integer getTopK() { return topK; }
        public void setTopK(Integer topK) { this.topK = topK; }
        public Double getThreshold() { return threshold; }
        public void setThreshold(Double threshold) { this.threshold = threshold; }

        @Override
        public String toString() {
            return "{\"userId\":\"" + userId + "\",\"imageUrl\":\"" + imageUrl + "\",\"topK\":" + topK + ",\"threshold\":" + threshold + "}";
        }
    }

    public static class TextSearchRequest {
        @NotBlank(message = "userId is required")
        private String userId;
        @NotBlank(message = "query is required")
        private String query;
        private Integer topK = 20;
        private Double threshold = 0.7;

        public String getUserId() { return userId; }
        public void setUserId(String userId) { this.userId = userId; }
        public String getQuery() { return query; }
        public void setQuery(String query) { this.query = query; }
        public Integer getTopK() { return topK; }
        public void setTopK(Integer topK) { this.topK = topK; }
        public Double getThreshold() { return threshold; }
        public void setThreshold(Double threshold) { this.threshold = threshold; }

        @Override
        public String toString() {
            return "{\"userId\":\"" + userId + "\",\"query\":\"" + query + "\",\"topK\":" + topK + ",\"threshold\":" + threshold + "}";
        }
    }

    public static class AttributeSearchRequest {
        @NotBlank(message = "userId is required")
        private String userId;
        private Map<String, Object> attributes = new HashMap<>();
        private Integer topK = 20;

        public String getUserId() { return userId; }
        public void setUserId(String userId) { this.userId = userId; }
        public Map<String, Object> getAttributes() { return attributes; }
        public void setAttributes(Map<String, Object> attributes) { this.attributes = attributes; }
        public Integer getTopK() { return topK; }
        public void setTopK(Integer topK) { this.topK = topK; }

        @Override
        public String toString() {
            return "{\"userId\":\"" + userId + "\",\"attributes\":" + attributes + ",\"topK\":" + topK + "}";
        }
    }

    public static class CompositeSearchRequest {
        @NotBlank(message = "userId is required")
        private String userId;
        private String imageUrl;
        private String textQuery;
        private Map<String, Object> attributes = new HashMap<>();
        private Integer topK = 20;
        private Double threshold = 0.7;

        public String getUserId() { return userId; }
        public void setUserId(String userId) { this.userId = userId; }
        public String getImageUrl() { return imageUrl; }
        public void setImageUrl(String imageUrl) { this.imageUrl = imageUrl; }
        public String getTextQuery() { return textQuery; }
        public void setTextQuery(String textQuery) { this.textQuery = textQuery; }
        public Map<String, Object> getAttributes() { return attributes; }
        public void setAttributes(Map<String, Object> attributes) { this.attributes = attributes; }
        public Integer getTopK() { return topK; }
        public void setTopK(Integer topK) { this.topK = topK; }
        public Double getThreshold() { return threshold; }
        public void setThreshold(Double threshold) { this.threshold = threshold; }

        @Override
        public String toString() {
            return "{\"userId\":\"" + userId + "\",\"imageUrl\":\"" + imageUrl + "\",\"textQuery\":\"" + textQuery + "\",\"attributes\":" + attributes + ",\"topK\":" + topK + ",\"threshold\":" + threshold + "}";
        }
    }
}
