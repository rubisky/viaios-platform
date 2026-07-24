package com.viaios.capability.api;

import com.viaios.capability.inference.TritonClient;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/v1/capabilities")
public class CapabilityController {
    private final TritonClient triton;
    public CapabilityController(TritonClient t) { this.triton = t; }

    private static final List<Map<String, Object>> CAPS = new ArrayList<>();
    static {
        addCap("detection", "vision", "Object Detection", "yolov8x", 15);
        addCap("tracking", "vision", "Object Tracking", "bytetrack", 10);
        addCap("ocr", "vision", "OCR", "paddleocr", 45);
        addCap("face_detect", "face", "Face Detection", "retinaface", 12);
        addCap("face_recognize", "face", "Face Recognition", "arcface", 18);
        addCap("body_analyze", "body", "Body Analysis", "resnet101", 8);
        addCap("vehicle_detect", "vehicle", "Vehicle Detection", "yolov8x", 15);
        addCap("plate_recognize", "vehicle", "Plate Recognition", "lprnet", 8);
        addCap("reid", "search", "Person ReID", "osnet", 25);
        addCap("embedding", "feature", "Feature Embedding", "clip-vit", 12);
        addCap("vlm", "llm", "Vision Language Model", "qwen-vl", 500);
        addCap("reasoning", "llm", "Visual Reasoning", "gpt-4o", 1000);
    }

    private static void addCap(String n, String c, String d, String m, int s) {
        Map<String, Object> cap = new HashMap<>();
        cap.put("name", n); cap.put("category", c); cap.put("description", d);
        cap.put("default_model", m); cap.put("sla_ms", s); cap.put("status", "active");
        CAPS.add(cap);
    }

    @GetMapping
    public List<Map<String, Object>> list() { return CAPS; }

    @GetMapping("/{name}")
    public ResponseEntity<Map<String, Object>> get(@PathVariable String name) {
        return CAPS.stream().filter(c -> name.equals(c.get("name"))).findFirst()
            .map(ResponseEntity::ok).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/init-demo")
    public Map<String, Object> initDemo() {
        return Map.of("capabilities", CAPS.size(), "types", List.of("vision", "face", "body", "vehicle", "search", "feature", "llm"), "status", "ready");
    }

    @PostMapping("/infer")
    public Map<String, Object> infer(@RequestBody Map<String, Object> req) {
        String capName = (String) req.getOrDefault("capability", "detection");
        Map<String, Object> cap = CAPS.stream().filter(c -> capName.equals(c.get("name"))).findFirst()
            .orElse(CAPS.get(0));

        // Simulate inference (production: call Triton via triton.infer)
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("capability", cap.get("name"));
        result.put("model", cap.get("default_model"));
        result.put("status", "completed");
        result.put("latency_ms", cap.get("sla_ms"));
        result.put("results", simulateResults((String) cap.get("name")));
        return result;
    }

    private List<Map<String, Object>> simulateResults(String capName) {
        if (capName.contains("detect"))
            return List.of(Map.of("class", "person", "confidence", 0.95, "bbox", List.of(100, 150, 300, 400)));
        if (capName.contains("face"))
            return List.of(Map.of("identity", "person_001", "confidence", 0.93));
        if (capName.contains("ocr"))
            return List.of(Map.of("text", "VIAIOS", "confidence", 0.99));
        if (capName.contains("reid"))
            return List.of(Map.of("match_id", "cam3_person_42", "similarity", 0.89));
        return List.of(Map.of("result", "ok", "confidence", 0.90));
    }

    @GetMapping("/models")
    public List<Map<String, Object>> listModels() {
        return List.of(
            Map.of("name", "yolov8x", "framework", "TensorRT", "task", "detection", "status", "ACTIVE"),
            Map.of("name", "arcface", "framework", "TensorRT", "task", "face_recognition", "status", "ACTIVE"),
            Map.of("name", "bytetrack", "framework", "TensorRT", "task", "tracking", "status", "ACTIVE"),
            Map.of("name", "paddleocr", "framework", "ONNX", "task", "ocr", "status", "ACTIVE"),
            Map.of("name", "clip-vit", "framework", "ONNX", "task", "embedding", "status", "ACTIVE")
        );
    }
}
