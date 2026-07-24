package com.viaios.capability.api;

import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/v1/capabilities")
public class CapabilitySchemaController {

    private static final List<Map<String, Object>> SCHEMAS = new ArrayList<>();
    static {
        // 15 Capability Schemas with I/O definitions
        add("detection", "Object Detection", "vision",
            List.of(Map.of("name","image","type","image","required",true,"desc","Input image frame")),
            List.of(Map.of("name","detections","type","array","desc","List of detected objects with class,confidence,bbox")));
        add("tracking", "Object Tracking", "vision",
            List.of(Map.of("name","detections","type","array","required",true), Map.of("name","frame_id","type","string")),
            List.of(Map.of("name","tracks","type","array","desc","Tracked objects with track_id,bbox,velocity")));
        add("segmentation", "Image Segmentation", "vision",
            List.of(Map.of("name","image","type","image","required",true)),
            List.of(Map.of("name","masks","type","array","desc","Pixel-wise segmentation masks")));
        add("face_detect", "Face Detection", "face",
            List.of(Map.of("name","image","type","image","required",true)),
            List.of(Map.of("name","faces","type","array","desc","Face bounding boxes with landmarks")));
        add("face_recognize", "Face Recognition", "face",
            List.of(Map.of("name","face_image","type","image","required",true)),
            List.of(Map.of("name","identity","type","object","desc","Identity with name,confidence,embedding")));
        add("body_analyze", "Body Analysis", "body",
            List.of(Map.of("name","image","type","image","required",true)),
            List.of(Map.of("name","attributes","type","object","desc","Gender,age,clothing color,height")));
        add("vehicle_detect", "Vehicle Detection", "vehicle",
            List.of(Map.of("name","image","type","image","required",true)),
            List.of(Map.of("name","vehicles","type","array","desc","Vehicle type,color,bbox")));
        add("plate_recognize", "Plate Recognition", "vehicle",
            List.of(Map.of("name","vehicle_image","type","image","required",true)),
            List.of(Map.of("name","plate","type","object","desc","Plate number,confidence,bbox")));
        add("reid", "Person Re-Identification", "search",
            List.of(Map.of("name","query_image","type","image","required",true), Map.of("name","gallery_ids","type","array")),
            List.of(Map.of("name","matches","type","array","desc","Ranked matches with person_id,similarity")));
        add("embedding", "Feature Embedding", "feature",
            List.of(Map.of("name","image","type","image","required",true), Map.of("name","model","type","string")),
            List.of(Map.of("name","embedding","type","array","desc","Feature vector (512-dim for CLIP)")));
        add("ocr", "Optical Character Recognition", "vision",
            List.of(Map.of("name","image","type","image","required",true)),
            List.of(Map.of("name","text","type","string","desc","Recognized text with confidence per character")));
        add("pose", "Pose Estimation", "body",
            List.of(Map.of("name","image","type","image","required",true)),
            List.of(Map.of("name","keypoints","type","array","desc","17 keypoints with x,y,confidence")));
        add("behavior", "Behavior Analysis", "behavior",
            List.of(Map.of("name","track_data","type","array","required",true), Map.of("name","duration_s","type","number")),
            List.of(Map.of("name","behaviors","type","array","desc","Detected behaviors: loitering,fighting,falling")));
        add("vlm", "Vision Language Model", "llm",
            List.of(Map.of("name","image","type","image","required",true), Map.of("name","prompt","type","string")),
            List.of(Map.of("name","response","type","string","desc","LLM response about the image")));
        add("reasoning", "Visual Reasoning", "llm",
            List.of(Map.of("name","scene_data","type","object","required",true), Map.of("name","question","type","string")),
            List.of(Map.of("name","answer","type","string"), Map.of("name","reasoning","type","string")));
    }

    static void add(String name, String desc, String category, List<Map<String,Object>> inputs, List<Map<String,Object>> outputs) {
        SCHEMAS.add(Map.of("name", name, "description", desc, "category", category,
            "inputs", inputs, "outputs", outputs, "status", "DEFINED"));
    }

    @GetMapping("/schemas")
    public List<Map<String, Object>> listSchemas() { return SCHEMAS; }

    @GetMapping("/schemas/{name}")
    public Map<String, Object> getSchema(@PathVariable String name) {
        return SCHEMAS.stream().filter(s -> name.equals(s.get("name"))).findFirst()
            .orElse(Map.of("error", "not_found"));
    }

    @GetMapping("/schemas/summary")
    public Map<String, Object> summary() {
        var categories = new LinkedHashMap<String, Integer>();
        for (var s : SCHEMAS) {
            String cat = (String) s.get("category");
            categories.merge(cat, 1, Integer::sum);
        }
        return Map.of("total_schemas", SCHEMAS.size(), "by_category", categories,
            "categories", List.of("vision","face","body","vehicle","search","feature","behavior","llm"));
    }
}
