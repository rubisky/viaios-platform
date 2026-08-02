package com.viaios.aikernel.kernel;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

/**
 * Model Manager — full lifecycle management for AI models.
 *
 * <p>Lifecycle state machine:
 * <pre>
 *   REGISTERED → VALIDATING → VALIDATED → DEPLOYING → ACTIVE
 *                                                    ↓
 *                                              FAILED / ROLLING_BACK → RETIRED
 * </pre>
 *
 * <p>This is NOT a CRUD wrapper. The Model Manager orchestrates real
 * deployment workflows across compute nodes, validates model integrity,
 * manages version history, and provides hot-swap capability.
 */
public interface ModelManager {

    // ── Registration ──────────────────────────────────────────────

    /** Register a new model. Returns the model descriptor with assigned ID. */
    ModelDescriptor register(ModelRegistrationRequest request);

    /** Validate model integrity (checksum, input/output shape compatibility). */
    ValidationResult validate(UUID modelId);

    // ── Deployment ────────────────────────────────────────────────

    /** Deploy a validated model to target runtime(s). */
    DeploymentStatus deploy(UUID modelId, DeploymentTarget target);

    /** Rollback to a previous version. */
    DeploymentStatus rollback(UUID modelId, String targetVersion);

    /** Hot-swap: deploy new version alongside old, cut over traffic atomically. */
    DeploymentStatus hotSwap(UUID modelId, ModelRegistrationRequest newVersion);

    // ── Runtime operations ────────────────────────────────────────

    /** Run inference on a deployed model. */
    CompletableFuture<InferenceResult> infer(UUID modelId, Map<String, Object> inputs);

    /** Get current model metrics (latency, throughput, error rate). */
    ModelMetrics getMetrics(UUID modelId);

    // ── Lifecycle ─────────────────────────────────────────────────

    /** Pause a model (stop accepting inference but keep warm). */
    void pause(UUID modelId);

    /** Resume a paused model. */
    void resume(UUID modelId);

    /** Retire a model (graceful shutdown, archive metadata). */
    void retire(UUID modelId);

    // ── Query ─────────────────────────────────────────────────────

    /** List all registered models, optionally filtered. */
    ModelList list(ModelFilter filter);

    /** Get full model descriptor including version history. */
    ModelDescriptor get(UUID modelId);

    /** Get deployment history for a model. */
    DeploymentHistory getHistory(UUID modelId);
}

// ── Domain types ──────────────────────────────────────────────────

record ModelRegistrationRequest(
    String name,
    String version,
    String runtime,       // TENSORRT, ONNX, TRITON, TORCHSERVE, VLLM
    String task,          // detection, face_recognition, reid, ocr, llm, embedding, segmentation, tracking
    String modelPath,     // registry path or S3/MinIO URL
    String inputShape,    // e.g. "[1,3,640,640]"
    String outputShape,   // e.g. "[1,84,8400]"
    String precision,     // FP32, FP16, INT8
    Integer gpuMemoryMb,
    Map<String, String> labels
) {}

record ModelDescriptor(
    UUID id,
    String name,
    String version,
    String runtime,
    String task,
    String status,
    String modelPath,
    String inputShape,
    String outputShape,
    String precision,
    Integer gpuMemoryMb,
    Integer avgLatencyMs,
    Double throughputRps,
    Map<String, String> labels,
    LocalDateTime createdAt,
    LocalDateTime updatedAt,
    LocalDateTime deployedAt
) {}

enum ValidationStatus { PASSED, FAILED, PENDING }

record ValidationResult(
    UUID modelId,
    ValidationStatus status,
    String checksum,
    boolean shapeCompatible,
    boolean runtimeCompatible,
    String errorMessage
) {}

record DeploymentTarget(
    String nodeName,       // target compute node, or null for auto-schedule
    int instanceCount,     // number of replicas
    int gpuCount,          // GPUs per instance
    int memoryMb,          // memory per instance
    boolean canary         // deploy as canary first
) {}

record DeploymentStatus(
    UUID modelId,
    String status,         // DEPLOYING, ACTIVE, FAILED, ROLLING_BACK, RETIRED
    int readyReplicas,
    int targetReplicas,
    String currentNode,
    LocalDateTime startedAt,
    LocalDateTime completedAt
) {}

record InferenceResult(
    UUID modelId,
    String modelName,
    String status,         // completed, failed, timeout
    Object outputs,
    long latencyMs,
    String traceId
) {}

record ModelMetrics(
    UUID modelId,
    long totalInferences,
    double avgLatencyMs,
    double p95LatencyMs,
    double p99LatencyMs,
    double throughputRps,
    double errorRate,
    int activeReplicas,
    double gpuUtilization
) {}

record ModelFilter(
    String name,
    String task,
    String runtime,
    String status,
    int limit,
    int offset
) {
    public ModelFilter {
        if (limit <= 0) limit = 50;
        if (offset < 0) offset = 0;
    }

    public static ModelFilter all() { return new ModelFilter(null, null, null, null, 50, 0); }
}

record ModelList(
    java.util.List<ModelDescriptor> models,
    int total,
    int limit,
    int offset
) {}

record DeploymentHistory(
    UUID modelId,
    java.util.List<DeploymentStatus> entries
) {}
