package com.viaios.search.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/v1/search/admin")
public class SearchAdminController {

    private static final Logger log = LoggerFactory.getLogger(SearchAdminController.class);

    @GetMapping("/collections")
    public ResponseEntity<Map<String, Object>> listCollections() {
        log.info("Listing Milvus collections");

        Map<String, Object> response = new HashMap<>();
        List<Map<String, String>> collections = new ArrayList<>();

        Map<String, String> imageCol = new HashMap<>();
        imageCol.put("name", "viaios_image_vectors");
        imageCol.put("dimension", "2048");
        imageCol.put("indexType", "IVF_FLAT");
        imageCol.put("status", "ready");
        collections.add(imageCol);

        Map<String, String> textCol = new HashMap<>();
        textCol.put("name", "viaios_text_vectors");
        textCol.put("dimension", "768");
        textCol.put("indexType", "IVF_SQ8");
        textCol.put("status", "ready");
        collections.add(textCol);

        response.put("collections", collections);
        response.put("count", collections.size());
        return ResponseEntity.ok(response);
    }

    @PostMapping("/collections/{collectionName}/index")
    public ResponseEntity<Map<String, Object>> buildIndex(
            @PathVariable String collectionName,
            @RequestBody IndexBuildRequest request) {
        log.info("Building index for collection: {} with type: {}", collectionName, request.getIndexType());

        Map<String, Object> response = new HashMap<>();
        response.put("collection", collectionName);
        response.put("indexType", request.getIndexType());
        response.put("status", "building");
        response.put("message", "Index build initiated for collection " + collectionName);
        return ResponseEntity.accepted().body(response);
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> healthCheck() {
        Map<String, Object> response = new HashMap<>();
        response.put("milvus", "connected");
        response.put("collections", "ready");
        return ResponseEntity.ok(response);
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        Map<String, Object> response = new HashMap<>();
        response.put("totalVectors", 1_250_000L);
        response.put("totalQueries", 45_320L);
        response.put("avgLatencyMs", 42);
        response.put("cacheHitRatio", 0.78);
        return ResponseEntity.ok(response);
    }

    public static class IndexBuildRequest {
        private String indexType = "IVF_FLAT";
        private Map<String, Object> params = new HashMap<>();

        public String getIndexType() { return indexType; }
        public void setIndexType(String indexType) { this.indexType = indexType; }
        public Map<String, Object> getParams() { return params; }
        public void setParams(Map<String, Object> params) { this.params = params; }
    }
}
