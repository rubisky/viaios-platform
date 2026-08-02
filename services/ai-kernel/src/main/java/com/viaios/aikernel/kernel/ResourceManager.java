package com.viaios.aikernel.kernel;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

/**
 * Resource Manager — unified AI compute resource scheduling.
 *
 * <p>Manages GPU, NPU, CPU, and memory resources across the cluster.
 * Provides scheduling, allocation, and monitoring for heterogeneous
 * compute environments (NVIDIA CUDA, Huawei Ascend NPU, Rockchip RK3588).
 *
 * <p>Scheduling strategy: bin-packing with anti-affinity for HA workloads,
 * priority-based preemption for critical inference tasks.
 */
public interface ResourceManager {

    // ── Cluster Overview ──────────────────────────────────────────

    /** Get cluster-wide resource snapshot. */
    ClusterResources getClusterResources();

    /** List all compute nodes with current utilization. */
    List<ComputeNode> listNodes(NodeFilter filter);

    /** Get detailed node info including running workloads. */
    ComputeNode getNode(String nodeName);

    // ── Allocation ────────────────────────────────────────────────

    /** Request resource allocation for a workload.
     *  Returns immediately with GRANTED, QUEUED, or DENIED status. */
    AllocationResult allocate(AllocationRequest request);

    /** Release an allocation back to the pool. */
    void release(UUID allocationId);

    /** Preempt a lower-priority allocation for a critical workload. */
    AllocationResult preempt(UUID allocationId, String reason);

    // ── Workload Management ───────────────────────────────────────

    /** Get all active workloads on a node. */
    List<WorkloadInfo> getWorkloads(String nodeName);

    /** Migrate a workload to another node. */
    CompletableFuture<AllocationResult> migrate(UUID allocationId, String targetNode);

    // ── GPU Inventory ─────────────────────────────────────────────

    /** List all available GPU devices with capabilities. */
    List<GpuDevice> listGpuDevices();

    /** Get GPU device details (temperature, power, memory, processes). */
    GpuDevice getGpuDevice(String deviceId);

    // ── Scheduling Policy ─────────────────────────────────────────

    /** Get current scheduling policy. */
    SchedulingPolicy getPolicy();

    /** Update scheduling policy (e.g., bin-packing → spread). */
    void updatePolicy(SchedulingPolicy policy);
}

// ── Domain types ──────────────────────────────────────────────────

record ClusterResources(
    int totalNodes,
    int healthyNodes,
    int totalGpus,
    int allocatedGpus,
    int availableGpus,
    long totalMemoryMb,
    long allocatedMemoryMb,
    long availableMemoryMb,
    int totalCpuCores,
    double avgGpuUtilization,
    double avgMemoryUtilization,
    int queuedWorkloads,
    int runningWorkloads,
    LocalDateTime snapshotAt
) {}

record ComputeNode(
    String nodeName,
    String hostIp,
    String nodeType,       // GPU_SERVER, NPU_DEVICE, CPU_ONLY, EDGE_JETSON, EDGE_ASCEND
    String gpuModel,       // A100, H100, Ascend 910, RK3588 NPU
    int totalGpus,
    int availableGpus,
    long totalMemoryMb,
    long availableMemoryMb,
    int totalCpuCores,
    double cpuUtilization,
    double gpuUtilization,
    double memoryUtilization,
    String status,         // HEALTHY, DEGRADED, OFFLINE, MAINTENANCE
    List<WorkloadInfo> activeWorkloads,
    Map<String, String> labels,
    LocalDateTime lastHeartbeat
) {}

record NodeFilter(
    String nodeType,
    String gpuModel,
    String status,
    int minAvailableGpus,
    int limit
) {
    public static NodeFilter all() { return new NodeFilter(null, null, null, 0, 50); }
}

record AllocationRequest(
    String workloadId,
    String workloadType,    // INFERENCE, TRAINING, BATCH
    int gpuCount,
    long memoryMb,
    int cpuCores,
    String preferredNode,   // or null for auto-schedule
    String gpuModel,        // or null for any
    int priority,           // 0=low, 100=critical
    long maxDurationSeconds, // 0 = no limit
    Map<String, String> constraints
) {}

record AllocationResult(
    UUID allocationId,
    String status,          // GRANTED, QUEUED, DENIED
    String assignedNode,
    int allocatedGpus,
    long allocatedMemoryMb,
    String reason,          // detail for DENIED or QUEUED
    LocalDateTime createdAt,
    LocalDateTime expiresAt
) {}

record WorkloadInfo(
    UUID allocationId,
    String workloadId,
    String workloadType,
    String status,          // RUNNING, PAUSED, MIGRATING, COMPLETED, FAILED
    int gpuCount,
    long memoryMb,
    double gpuUtilization,
    long uptimeSeconds,
    LocalDateTime startedAt
) {}

record GpuDevice(
    String deviceId,
    String nodeName,
    String gpuModel,
    String uuid,
    int memoryTotalMb,
    int memoryUsedMb,
    int memoryFreeMb,
    double utilization,
    int temperatureC,
    double powerWatts,
    double powerLimitWatts,
    List<String> processes,  // process names using this GPU
    String driverVersion,
    String cudaVersion
) {}

enum SchedulingStrategy { BIN_PACK, SPREAD, RANDOM, PRIORITY_BASED }

record SchedulingPolicy(
    SchedulingStrategy strategy,
    boolean preemptionEnabled,
    int maxQueuedPerWorkload,
    int defaultPriority,
    Map<String, Object> overrides  // per-workload-type overrides
) {}
