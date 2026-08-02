package com.viaios.aikernel.kernel;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Capability Manager — the heart of "Capability First" architecture.
 *
 * <p>Business applications call <b>Capabilities</b>, not specific models.
 * The Capability Manager maintains the mapping between abstract capabilities
 * and concrete model implementations, enabling hot-swap of models without
 * any business code changes.
 *
 * <p>Example: A case system calls {@code /api/v1/capability/face/detect},
 * the Capability Manager routes to the current best face detection model
 * (e.g., YOLOv8-Face v3.2 on GPU node 02), completely transparent to the caller.
 *
 * <p>Core capabilities (15 domains):
 * <pre>
 *   DETECTION | TRACKING | SEGMENTATION | OCR | FACE | BODY | VEHICLE |
 *   BIKE | GAIT | POSE | BEHAVIOR | REID | EMBEDDING | VLM | REASONING
 * </pre>
 */
public interface CapabilityManager {

    // ── Capability Registration ───────────────────────────────────

    /** Register a new capability domain (e.g., "face_detection"). */
    CapabilityDescriptor register(CapabilityRegistration request);

    /** Bind a model to a capability (the key decoupling mechanism). */
    CapabilityBinding bindModel(UUID capabilityId, UUID modelId, BindingConfig config);

    /** Unbind a model from a capability. */
    void unbindModel(UUID capabilityId, UUID modelId);

    // ── Routing (the core value) ──────────────────────────────────

    /** Resolve a capability call to the best model instance.
     *  Accounts for: model version, load, latency, canary rules, A/B test groups. */
    RoutingDecision route(String capabilityDomain, RoutingContext context);

    /** Get all available models for a capability, sorted by preference. */
    List<CapabilityBinding> getBindings(String capabilityDomain);

    // ── Version & Release Management ──────────────────────────────

    /** Promote a model version (canary → stable, stable → default). */
    void promoteVersion(UUID capabilityId, UUID modelId, ReleaseChannel channel);

    /** Create an A/B test between two model versions. */
    ABTest createABTest(UUID capabilityId, UUID modelA, UUID modelB, ABTestConfig config);

    /** Conclude an A/B test and select the winner. */
    ABTestResult concludeABTest(String testId, String winnerModelId);

    // ── Discovery ─────────────────────────────────────────────────

    /** List all registered capabilities. */
    CapabilityCatalog listCapabilities();

    /** Get capability details including all bound models and their metrics. */
    CapabilityDetail getCapability(String capabilityDomain);

    /** Discover capabilities by task type. */
    List<CapabilityDescriptor> findByTask(String taskType);
}

// ── Domain types ──────────────────────────────────────────────────

record CapabilityRegistration(
    String domain,         // e.g. "face_detection", "person_reid"
    String displayName,    // e.g. "Face Detection"
    String category,       // DETECTION, TRACKING, FACE, BODY, VEHICLE, etc.
    String description,
    String inputSchema,    // JSON Schema for input
    String outputSchema,   // JSON Schema for output
    Map<String, String> metadata
) {}

record CapabilityDescriptor(
    UUID id,
    String domain,
    String displayName,
    String category,
    String description,
    String inputSchema,
    String outputSchema,
    String status,         // ACTIVE, DEPRECATED, DISABLED
    int bindingCount,
    LocalDateTime createdAt,
    Map<String, String> metadata
) {}

record CapabilityBinding(
    UUID id,
    UUID capabilityId,
    UUID modelId,
    String modelName,
    String modelVersion,
    ReleaseChannel channel,   // DEFAULT, STABLE, CANARY, EXPERIMENTAL
    int weight,               // traffic weight (0-100)
    BindingConfig config,
    LocalDateTime boundAt
) {}

record BindingConfig(
    int weight,               // traffic allocation percentage
    Map<String, String> conditions,  // routing conditions (e.g., "region=us-east")
    boolean fallback,         // use as fallback if primary fails
    int priority              // higher = preferred
) {
    public BindingConfig {
        if (weight < 0 || weight > 100) throw new IllegalArgumentException("weight must be 0-100");
        if (priority < 0) throw new IllegalArgumentException("priority must be >= 0");
    }
}

enum ReleaseChannel { DEFAULT, STABLE, CANARY, EXPERIMENTAL }

record RoutingContext(
    String callerService,
    String userId,
    String tenantId,
    Map<String, String> headers,
    Map<String, Object> params
) {}

record RoutingDecision(
    UUID modelId,
    String nodeName,
    String endpoint,
    ReleaseChannel channel,
    String reason,         // why this model was chosen
    boolean fallback
) {}

record ABTestConfig(
    String name,
    int trafficSplit,      // percentage to model B (0-100)
    int durationMinutes,
    String successMetric,  // e.g. "p95_latency", "accuracy"
    double minImprovement  // minimum improvement to declare winner
) {}

record ABTest(
    String id,
    UUID capabilityId,
    UUID modelAId,
    UUID modelBId,
    ABTestConfig config,
    String status,         // RUNNING, COMPLETED, CANCELLED
    LocalDateTime startedAt,
    LocalDateTime endsAt
) {}

record ABTestResult(
    String testId,
    String winnerModelId,
    Map<String, Double> metricsA,
    Map<String, Double> metricsB,
    String recommendation,
    boolean autoApplied
) {}

record CapabilityCatalog(
    List<CapabilityDescriptor> capabilities,
    int total,
    Map<String, Integer> byCategory  // category → count
) {}

record CapabilityDetail(
    CapabilityDescriptor descriptor,
    List<CapabilityBinding> bindings,
    List<ABTest> activeTests,
    Map<String, Object> aggregateMetrics
) {}
