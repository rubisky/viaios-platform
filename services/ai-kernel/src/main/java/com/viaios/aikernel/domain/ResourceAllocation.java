package com.viaios.aikernel.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

/**
 * Tracks a GPU/memory resource allocation for a workload.
 * <p>
 * The kernel scheduler creates an allocation when it reserves
 * compute resources on a specific node for an analysis task
 * or inference workload.
 */
@Entity
@Table(name = "resource_allocations")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ResourceAllocation {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", length = 36, nullable = false, updatable = false)
    private String id;

    /** The workload or analysis task this allocation serves. */
    @Column(name = "workload_id", length = 36, nullable = false)
    private String workloadId;

    /** Number of GPU devices allocated. */
    @Column(name = "gpu_count", nullable = false)
    @Builder.Default
    private int gpuCount = 1;

    /** Reserved memory in megabytes. */
    @Column(name = "memory_mb", nullable = false)
    private int memoryMb;

    /** The compute node where resources were reserved. */
    @Column(name = "node_name", length = 255)
    private String nodeName;

    /**
     * Allocation status: PENDING, GRANTED, ACTIVE, RELEASED, FAILED.
     */
    @Column(name = "status", length = 32, nullable = false)
    @Builder.Default
    private String status = "PENDING";

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();
}
