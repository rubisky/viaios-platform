package com.viaios.aikernel.kernel;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class ResourceManagerImpl implements ResourceManager {

    private final Map<String, ComputeNode> nodes = new ConcurrentHashMap<>();
    private final Map<UUID, AllocationResult> allocations = new ConcurrentHashMap<>();
    private SchedulingPolicy policy = new SchedulingPolicy(
        SchedulingStrategy.PRIORITY_BASED, true, 10, 50, Map.of()
    );

    public ResourceManagerImpl() {
        // Register simulated GPU nodes
        registerSimulatedNodes();
    }

    private void registerSimulatedNodes() {
        var now = LocalDateTime.now();
        nodes.put("gpu-node-01", new ComputeNode(
            "gpu-node-01", "10.0.1.11", "GPU_SERVER", "NVIDIA A100",
            4, 2, 327680L, 245760L, 64, 45.0, 50.0, 25.0,
            "HEALTHY", List.of(), Map.of("zone", "us-east-1a"), now
        ));
        nodes.put("gpu-node-02", new ComputeNode(
            "gpu-node-02", "10.0.1.12", "GPU_SERVER", "NVIDIA A100",
            4, 3, 327680L, 262144L, 64, 30.0, 25.0, 20.0,
            "HEALTHY", List.of(), Map.of("zone", "us-east-1a"), now
        ));
        nodes.put("edge-jetson-01", new ComputeNode(
            "edge-jetson-01", "192.168.2.101", "EDGE_JETSON", "Jetson Orin",
            1, 0, 32768L, 16384L, 12, 60.0, 100.0, 50.0,
            "HEALTHY", List.of(), Map.of("zone", "edge-gate-a"), now
        ));
        log.info("ResourceManager initialized with {} nodes", nodes.size());
    }

    @Override
    public ClusterResources getClusterResources() {
        var now = LocalDateTime.now();
        int totalGpus = nodes.values().stream().mapToInt(ComputeNode::totalGpus).sum();
        int availGpus = nodes.values().stream().mapToInt(ComputeNode::availableGpus).sum();
        long totalMem = nodes.values().stream().mapToLong(ComputeNode::totalMemoryMb).sum();
        long availMem = nodes.values().stream().mapToLong(ComputeNode::availableMemoryMb).sum();

        return new ClusterResources(
            nodes.size(), (int) nodes.values().stream().filter(n -> "HEALTHY".equals(n.status())).count(),
            totalGpus, totalGpus - availGpus, availGpus,
            totalMem, totalMem - availMem, availMem,
            nodes.values().stream().mapToInt(ComputeNode::totalCpuCores).sum(),
            nodes.values().stream().mapToDouble(ComputeNode::gpuUtilization).average().orElse(0),
            nodes.values().stream().mapToDouble(ComputeNode::memoryUtilization).average().orElse(0),
            0, allocations.size(), now
        );
    }

    @Override
    public List<ComputeNode> listNodes(NodeFilter filter) {
        var stream = nodes.values().stream();
        if (filter.nodeType() != null) stream = stream.filter(n -> filter.nodeType().equals(n.nodeType()));
        if (filter.gpuModel() != null) stream = stream.filter(n -> filter.gpuModel().equals(n.gpuModel()));
        if (filter.status() != null) stream = stream.filter(n -> filter.status().equals(n.status()));
        if (filter.minAvailableGpus() > 0) stream = stream.filter(n -> n.availableGpus() >= filter.minAvailableGpus());
        return stream.limit(filter.limit() > 0 ? filter.limit() : 50).toList();
    }

    @Override
    public ComputeNode getNode(String nodeName) {
        ComputeNode n = nodes.get(nodeName);
        if (n == null) throw new NoSuchElementException("Node not found: " + nodeName);
        return n;
    }

    @Override
    public AllocationResult allocate(AllocationRequest request) {
        // Find best-fit node
        ComputeNode best = nodes.values().stream()
            .filter(n -> "HEALTHY".equals(n.status()))
            .filter(n -> n.availableGpus() >= request.gpuCount())
            .filter(n -> n.availableMemoryMb() >= request.memoryMb())
            .filter(n -> request.gpuModel() == null || request.gpuModel().equals(n.gpuModel()))
            .min(Comparator.comparingInt(ComputeNode::availableGpus)) // bin-pack
            .orElse(null);

        if (best == null) {
            log.warn("No available node for workload {}: need {} GPU/{}MB",
                request.workloadId(), request.gpuCount(), request.memoryMb());
            return new AllocationResult(
                null, "QUEUED", null, 0, 0,
                "No node with sufficient resources", LocalDateTime.now(), null
            );
        }

        UUID id = UUID.randomUUID();
        var now = LocalDateTime.now();
        var result = new AllocationResult(
            id, "GRANTED", best.nodeName(),
            request.gpuCount(), request.memoryMb(),
            "Allocated on " + best.nodeName(), now,
            request.maxDurationSeconds() > 0 ? now.plusSeconds(request.maxDurationSeconds()) : null
        );

        allocations.put(id, result);

        // Update node availability
        nodes.put(best.nodeName(), new ComputeNode(
            best.nodeName(), best.hostIp(), best.nodeType(), best.gpuModel(),
            best.totalGpus(), best.availableGpus() - request.gpuCount(),
            best.totalMemoryMb(), best.availableMemoryMb() - request.memoryMb(),
            best.totalCpuCores(), best.cpuUtilization(), best.gpuUtilization(),
            best.memoryUtilization(), best.status(), best.activeWorkloads(),
            best.labels(), best.lastHeartbeat()
        ));

        log.info("Allocated {} GPU/{}MB on {} for workload {}",
            request.gpuCount(), request.memoryMb(), best.nodeName(), request.workloadId());
        return result;
    }

    @Override
    public void release(UUID allocationId) {
        allocations.remove(allocationId);
        log.info("Released allocation {}", allocationId);
    }

    @Override
    public AllocationResult preempt(UUID allocationId, String reason) {
        AllocationResult existing = allocations.get(allocationId);
        if (existing == null) throw new NoSuchElementException("Allocation not found: " + allocationId);

        allocations.remove(allocationId);
        log.warn("Preempted allocation {}: {}", allocationId, reason);
        return new AllocationResult(
            null, "PREEMPTED", null, 0, 0, reason, LocalDateTime.now(), null
        );
    }

    @Override
    public List<WorkloadInfo> getWorkloads(String nodeName) {
        ComputeNode n = nodes.get(nodeName);
        return n != null ? n.activeWorkloads() : List.of();
    }

    @Override
    public CompletableFuture<AllocationResult> migrate(UUID allocationId, String targetNode) {
        return CompletableFuture.supplyAsync(() -> {
            release(allocationId);
            return allocate(new AllocationRequest(
                allocationId.toString(), "INFERENCE", 1, 4096L, 2,
                targetNode, null, 50, 0, Map.of()
            ));
        });
    }

    @Override
    public List<GpuDevice> listGpuDevices() {
        return List.of(
            new GpuDevice("gpu-0", "gpu-node-01", "NVIDIA A100",
                "GPU-abc123", 81920, 40960, 40960,
                50.0, 65, 250.0, 400.0,
                List.of("triton-server", "onnx-runtime"),
                "535.154.05", "12.2"),
            new GpuDevice("gpu-1", "gpu-node-01", "NVIDIA A100",
                "GPU-abc124", 81920, 20480, 61440,
                25.0, 58, 180.0, 400.0,
                List.of("vllm-worker"),
                "535.154.05", "12.2")
        );
    }

    @Override public GpuDevice getGpuDevice(String deviceId) {
        return listGpuDevices().stream().filter(d -> d.deviceId().equals(deviceId))
            .findFirst().orElseThrow(() -> new NoSuchElementException("GPU not found: " + deviceId));
    }

    @Override public SchedulingPolicy getPolicy() { return policy; }

    @Override
    public void updatePolicy(SchedulingPolicy newPolicy) {
        this.policy = newPolicy;
        log.info("Scheduling policy updated: {}", newPolicy.strategy());
    }
}
