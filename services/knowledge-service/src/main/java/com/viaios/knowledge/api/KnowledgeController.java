package com.viaios.knowledge.api;

import org.springframework.web.bind.annotation.*;
import java.util.*;
import java.time.Instant;

@RestController
@RequestMapping("/api/v1/knowledge")
public class KnowledgeController {

    static final List<Map<String, Object>> ENTITIES = new ArrayList<>();
    static final List<Map<String, Object>> RELATIONS = new ArrayList<>();
    static {
        addEntity("person-001", "Person", "Suspect A", Map.of("gender", "male", "age", "35"));
        addEntity("person-002", "Person", "Companion B", Map.of("gender", "male", "age", "28"));
        addEntity("person-003", "Person", "Witness C", Map.of("gender", "female", "age", "42"));
        addEntity("vehicle-001", "Vehicle", "Plate A12345", Map.of("brand", "Toyota", "color", "white"));
        addEntity("vehicle-002", "Vehicle", "Plate B67890", Map.of("brand", "Honda", "color", "black"));
        addEntity("camera-001", "Camera", "Gate A", Map.of("location", "East Entrance", "zone", "A"));
        addEntity("camera-002", "Camera", "Gate B", Map.of("location", "West Parking", "zone", "B"));
        addEntity("case-001", "Case", "Theft Case #2024-001", Map.of("status", "INVESTIGATING"));
        addRelation("rel-001", "person-001", "vehicle-001", "DRIVES");
        addRelation("rel-002", "person-001", "person-002", "ACCOMPANIED_BY");
        addRelation("rel-003", "person-001", "camera-001", "APPEARED_AT");
        addRelation("rel-004", "vehicle-001", "camera-002", "APPEARED_AT");
        addRelation("rel-005", "person-001", "case-001", "INVOLVED_IN");
    }

    static void addEntity(String id, String type, String name, Map<String, String> props) {
        Map<String, Object> e = new LinkedHashMap<>();
        e.put("id", id); e.put("type", type); e.put("name", name);
        e.put("properties", props); e.put("created_at", Instant.now().toString());
        ENTITIES.add(e);
    }

    static void addRelation(String id, String from, String to, String type) {
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("id", id); r.put("from_id", from); r.put("to_id", to);
        r.put("type", type); r.put("created_at", Instant.now().toString());
        RELATIONS.add(r);
    }

    // ====== Entity CRUD ======

    @GetMapping("/entities")
    public Map<String, Object> listEntities(@RequestParam(defaultValue = "") String type) {
        List<Map<String, Object>> filtered = type.isEmpty() ? ENTITIES
            : ENTITIES.stream().filter(e -> type.equals(e.get("type"))).toList();
        return Map.of("entities", filtered, "total", filtered.size());
    }

    @GetMapping("/entities/{id}")
    public Map<String, Object> getEntity(@PathVariable String id) {
        return ENTITIES.stream().filter(e -> id.equals(e.get("id"))).findFirst()
            .orElse(Map.of("error", "not_found"));
    }

    @PostMapping("/entities")
    public Map<String, Object> createEntity(@RequestBody Map<String, Object> body) {
        String id = "entity-" + UUID.randomUUID().toString().substring(0, 8);
        Map<String, Object> e = new LinkedHashMap<>(body);
        e.put("id", id);
        e.put("created_at", Instant.now().toString());
        ENTITIES.add(e);
        return e;
    }

    // ====== Relations ======

    @GetMapping("/relations")
    public Map<String, Object> listRelations(@RequestParam(defaultValue = "") String entityId) {
        List<Map<String, Object>> filtered = entityId.isEmpty() ? RELATIONS
            : RELATIONS.stream().filter(r -> entityId.equals(r.get("from_id")) || entityId.equals(r.get("to_id"))).toList();
        return Map.of("relations", filtered, "total", filtered.size());
    }

    @PostMapping("/relations")
    public Map<String, Object> createRelation(@RequestBody Map<String, Object> body) {
        String id = "rel-" + UUID.randomUUID().toString().substring(0, 8);
        Map<String, Object> r = new LinkedHashMap<>(body);
        r.put("id", id);
        r.put("created_at", Instant.now().toString());
        RELATIONS.add(r);
        return r;
    }

    // ====== Graph Query ======

    @GetMapping("/graph")
    public Map<String, Object> getGraph(@RequestParam(defaultValue = "") String entityId) {
        List<Map<String, Object>> nodes = new ArrayList<>();
        List<Map<String, Object>> edges = new ArrayList<>();
        Set<String> included = new HashSet<>();

        if (!entityId.isEmpty()) {
            // 1-hop subgraph
            included.add(entityId);
            for (var r : RELATIONS) {
                if (entityId.equals(r.get("from_id"))) {
                    included.add((String) r.get("to_id"));
                    edges.add(Map.of("from", r.get("from_id"), "to", r.get("to_id"), "type", r.get("type")));
                } else if (entityId.equals(r.get("to_id"))) {
                    included.add((String) r.get("from_id"));
                    edges.add(Map.of("from", r.get("from_id"), "to", r.get("to_id"), "type", r.get("type")));
                }
            }
            for (var e : ENTITIES) {
                if (included.contains(e.get("id"))) nodes.add(e);
            }
        } else {
            nodes.addAll(ENTITIES);
            for (var r : RELATIONS) edges.add(Map.of("from", r.get("from_id"), "to", r.get("to_id"), "type", r.get("type")));
        }
        return Map.of("nodes", nodes, "edges", edges);
    }

    // ====== GraphRAG ======

    @PostMapping("/graphrag")
    public Map<String, Object> graphRAG(@RequestBody Map<String, Object> body) {
        String query = (String) body.getOrDefault("query", "");
        // Simulate GraphRAG: keyword match on entities + relations
        List<Map<String, Object>> matchedEntities = new ArrayList<>();
        List<Map<String, Object>> matchedRelations = new ArrayList<>();
        for (var e : ENTITIES) {
            if (e.toString().toLowerCase().contains(query.toLowerCase())) matchedEntities.add(e);
        }
        // Get related entities via 1-hop
        Set<String> relatedIds = new HashSet<>();
        for (var e : matchedEntities) {
            String eid = (String) e.get("id");
            for (var r : RELATIONS) {
                if (eid.equals(r.get("from_id"))) relatedIds.add((String) r.get("to_id"));
                if (eid.equals(r.get("to_id"))) relatedIds.add((String) r.get("from_id"));
            }
        }
        List<Map<String, Object>> related = ENTITIES.stream()
            .filter(e -> relatedIds.contains(e.get("id"))).toList();

        return Map.of("query", query, "matched_entities", matchedEntities,
            "related_entities", related, "graph_results", matchedEntities.size() + related.size());
    }

    // ====== Stats ======

    @GetMapping("/stats")
    public Map<String, Object> stats() {
        return Map.of("total_entities", ENTITIES.size(), "total_relations", RELATIONS.size(),
            "entity_types", List.of("Person", "Vehicle", "Camera", "Case", "Location"),
            "relation_types", List.of("DRIVES", "ACCOMPANIED_BY", "APPEARED_AT", "INVOLVED_IN"));
    }

    @PostMapping("/init-demo")
    public Map<String, Object> initDemo() {
        return Map.of("entities", ENTITIES.size(), "relations", RELATIONS.size(),
            "entity_types", List.of("Person", "Vehicle", "Camera", "Case"),
            "relation_types", List.of("DRIVES", "ACCOMPANIED_BY", "APPEARED_AT", "INVOLVED_IN"),
            "status", "ready");
    }
}
