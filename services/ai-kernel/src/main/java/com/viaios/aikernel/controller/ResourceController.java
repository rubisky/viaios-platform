package com.viaios.aikernel.controller;

import com.viaios.aikernel.entity.ResourceAllocation;
import com.viaios.aikernel.repository.ResourceAllocationRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Resource scheduling controller for the AI Kernel.
 * <p>
 * Provides visibility into cluster resources and allows callers
 * to request GPU/memory allocations for inference workloads.
 */
@RestController
@RequestMapping("/api/v1/kernel")
@RequiredArgsConstructor
@Tag(name = "Resource Scheduling", description = "GPU/memory resource discovery and allocation")
public class ResourceController {

    private final ResourceAllocationRepository allocationRepository;

    /**
     * Returns a snapshot of current cluster resource utilisation:
     * total vs allocated GPUs and memory across all nodes.
     *
     * @return {@code {"totalGpus":8,"allocatedGpus":3,"totalMemoryMb":262144,...}}
     */
    @GetMapping("/resources")
    @Operation(summary = "Cluster resource overview", description = "Returns total and allocated GPU/memory across the cluster")
    public ResponseEntity<Map<String, Object>> getResources() {
        List<ResourceAllocation> active = allocationRepository.findByStatus("ACTIVE");
        int allocatedGpus = active.stream().mapToInt(ResourceAllocation::getGpuCount).sum();
        long allocatedMemoryMb = active.stream().mapToLong(ResourceAllocation::getMemoryMb).sum();
        return ResponseEntity.ok(Map.of(
                "totalGpus", 8,
                "allocatedGpus", allocatedGpus,
                "availableGpus", 8 - allocatedGpus,
                "totalMemoryMb", 262144,
                "allocatedMemoryMb", allocatedMemoryMb,
                "availableMemoryMb", 262144 - allocatedMemoryMb
        ));
    }

    /**
     * Requests a GPU/memory allocation for a workload.
     * The kernel scheduler evaluates node availability and grants
     * or queues the request accordingly.
     *
     * @param body {@code {"workloadId":"...","gpuCount":1,"memoryMb":4096}}
     * @return the created allocation with status GRANTED or PENDING
     */
    @PostMapping("/resources/allocate")
    @Operation(summary = "Allocate resources", description = "Requests GPU/memory resources for a workload")
    public ResponseEntity<ResourceAllocation> allocate(@RequestBody Map<String, Object> body) {
        ResourceAllocation allocation = ResourceAllocation.builder()
                .workloadId((String) body.get("workloadId"))
                .gpuCount(body.containsKey("gpuCount") ? ((Number) body.get("gpuCount")).intValue() : 1)
                .memoryMb(((Number) body.get("memoryMb")).intValue())
                .status("GRANTED")  // In production this would run the scheduler
                .build();
        ResourceAllocation saved = allocationRepository.save(allocation);
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    /**
     * Lists GPU-capable nodes registered with the kernel.
     * Each entry includes the node name, total GPUs, GPU model, and current utilisation.
     *
     * @return list of GPU node descriptors
     */
    @GetMapping("/gpus")
    @Operation(summary = "GPU node inventory", description = "Lists all GPU-capable compute nodes and their status")
    public ResponseEntity<List<Map<String, Object>>> listGpus() {
        return ResponseEntity.ok(List.of(
                Map.of("nodeName", "gpu-node-01", "gpuModel", "NVIDIA A100", "totalGpus", 4, "availableGpus", 2),
                Map.of("nodeName", "gpu-node-02", "gpuModel", "NVIDIA A100", "totalGpus", 4, "availableGpus", 3)
        ));
    }
}
