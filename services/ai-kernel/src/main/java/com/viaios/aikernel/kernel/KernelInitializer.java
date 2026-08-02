package com.viaios.aikernel.kernel;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Initializes the AI Kernel with pre-configured capabilities and models.
 * Runs on application startup to ensure the kernel is ready to serve
 * capability-based routing immediately.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class KernelInitializer {

    private final ModelManager modelManager;
    private final CapabilityManager capabilityManager;

    /** The 15 VIAIOS Vision Capability domains. */
    private static final List<CapabilityDef> CAPABILITIES = List.of(
        new CapabilityDef("detection",       "Object Detection",       "DETECTION",   "Detect and localize objects in images/video"),
        new CapabilityDef("tracking",        "Object Tracking",        "TRACKING",    "Track objects across video frames"),
        new CapabilityDef("segmentation",    "Image Segmentation",     "SEGMENTATION","Pixel-level semantic/instance segmentation"),
        new CapabilityDef("ocr",             "Optical Character Rec",  "OCR",         "Recognize text in images"),
        new CapabilityDef("face_detection",  "Face Detection",         "FACE",        "Detect faces in images"),
        new CapabilityDef("face_recognition","Face Recognition",       "FACE",        "Recognize and verify face identity"),
        new CapabilityDef("body_analysis",   "Human Body Analysis",    "BODY",        "Analyze human body attributes"),
        new CapabilityDef("vehicle_recog",   "Vehicle Recognition",    "VEHICLE",     "Recognize vehicle type/plate/color"),
        new CapabilityDef("bike_recog",      "Non-Motor Vehicle Rec",  "BIKE",        "Recognize bicycles/e-bikes"),
        new CapabilityDef("gait_recog",      "Gait Recognition",       "GAIT",        "Recognize person by walking pattern"),
        new CapabilityDef("pose_estimation", "Pose Estimation",        "POSE",        "Estimate human body keypoints"),
        new CapabilityDef("behavior_analysis","Behavior Analysis",     "BEHAVIOR",    "Analyze human behavior patterns"),
        new CapabilityDef("person_reid",     "Person Re-Identification","REID",       "Cross-camera person re-identification"),
        new CapabilityDef("embedding",       "Feature Embedding",      "EMBEDDING",   "Extract visual feature embeddings"),
        new CapabilityDef("vlm",             "Vision-Language Model",  "VLM",         "Multimodal vision-language understanding"),
        new CapabilityDef("visual_reasoning","Visual Reasoning",       "REASONING",   "Logical reasoning over visual inputs")
    );

    /** Pre-configured models to register on startup. */
    private static final List<ModelDef> DEFAULT_MODELS = List.of(
        new ModelDef("yolov8n",     "v8.2", "ONNX",    "detection",          "[1,3,640,640]",  "[1,84,8400]",   "FP16", 2048),
        new ModelDef("yolov8s",     "v8.2", "ONNX",    "detection",          "[1,3,640,640]",  "[1,84,8400]",   "FP16", 4096),
        new ModelDef("yolov8n-pose","v8.2", "ONNX",    "pose_estimation",    "[1,3,640,640]",  "[1,17,3]",      "FP16", 2048),
        new ModelDef("arcface_r100","v2.1", "ONNX",    "face_recognition",   "[1,3,112,112]",  "[1,512]",       "FP32", 4096),
        new ModelDef("resnet50_reid","v1.0","ONNX",    "person_reid",        "[1,3,256,128]",  "[1,2048]",      "FP32", 3072),
        new ModelDef("vehicle_reid","v1.0", "ONNX",    "vehicle_recog",      "[1,3,256,256]",  "[1,512]",       "FP32", 2048),
        new ModelDef("clip-vit-b-32","v1.0","ONNX",    "vlm",                "[1,3,224,224]",  "[1,512]",       "FP32", 6144),
        new ModelDef("mobilenet_v3", "v1.0", "ONNX",    "embedding",          "[1,3,224,224]",  "[1,1280]",      "FP16", 1024),
        new ModelDef("2d106det",     "v1.0", "ONNX",    "face_detection",     "[1,3,192,192]",  "[1,106,2]",     "FP16", 1024),
        new ModelDef("det_10g",      "v3.0", "TENSORRT","detection",          "[1,3,640,640]",  "[1,84,8400]",   "INT8", 1024)
    );

    @PostConstruct
    public void initialize() {
        log.info("══════════════════════════════════════════");
        log.info("  VIAIOS AI Kernel 4.0 — Initializing");
        log.info("══════════════════════════════════════════");

        // Register all 16 capability domains
        int capCount = 0;
        for (CapabilityDef def : CAPABILITIES) {
            try {
                capabilityManager.register(new CapabilityRegistration(
                    def.domain, def.displayName, def.category, def.description,
                    "{}", "{}", Map.of("version", "4.0")
                ));
                capCount++;
            } catch (Exception e) {
                log.warn("Capability {} already registered, skipping", def.domain);
            }
        }
        log.info("  ✓ {} capability domains registered", capCount);

        // Register default models
        int modelCount = 0;
        Map<UUID, String> modelTasks = new java.util.HashMap<>();
        for (ModelDef def : DEFAULT_MODELS) {
            try {
                ModelDescriptor m = modelManager.register(new ModelRegistrationRequest(
                    def.name, def.version, def.runtime, def.task,
                    "/opt/viaios/models/" + def.name + ".onnx",
                    def.inputShape, def.outputShape, def.precision,
                    def.gpuMemoryMb, Map.of("source", "pre-installed")
                ));
                modelManager.validate(m.id());
                modelTasks.put(m.id(), def.task);
                modelCount++;
            } catch (Exception e) {
                log.warn("Model {} already registered, skipping", def.name);
            }
        }
        log.info("  ✓ {} models registered and validated", modelCount);

        // Bind models to capabilities
        int bindCount = 0;
        var caps = capabilityManager.listCapabilities();
        for (var cap : caps.capabilities()) {
            for (var entry : modelTasks.entrySet()) {
                // Bind model if its task matches the capability domain
                if (cap.domain().equals(entry.getValue()) ||
                    cap.domain().contains(entry.getValue()) ||
                    entry.getValue().contains(cap.domain())) {
                    try {
                        capabilityManager.bindModel(cap.id(), entry.getKey(),
                            new BindingConfig(100, Map.of(), false, 100));
                        bindCount++;
                        break; // bind one default model per capability
                    } catch (Exception e) {
                        // skip already bound
                    }
                }
            }
        }
        log.info("  ✓ {} model→capability bindings created", bindCount);

        // Summary
        var models = modelManager.list(ModelFilter.all());
        log.info("══════════════════════════════════════════");
        log.info("  Kernel Ready: {} capabilities, {} models, {} bindings",
            capCount, models.total(), bindCount);
        log.info("  API: /api/v1/kernel/health");
        log.info("══════════════════════════════════════════");
    }

    // ── Helper types ──────────────────────────────────────────────

    private record CapabilityDef(
        String domain, String displayName, String category, String description
    ) {}

    private record ModelDef(
        String name, String version, String runtime, String task,
        String inputShape, String outputShape, String precision, int gpuMemoryMb
    ) {}
}
