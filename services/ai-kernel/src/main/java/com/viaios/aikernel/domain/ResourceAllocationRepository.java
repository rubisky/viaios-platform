package com.viaios.aikernel.repository;

import com.viaios.aikernel.entity.ResourceAllocation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Spring Data JPA repository for {@link ResourceAllocation} entities.
 */
@Repository
public interface ResourceAllocationRepository extends JpaRepository<ResourceAllocation, String> {

    /** Find all allocations for a specific workload. */
    List<ResourceAllocation> findByWorkloadId(String workloadId);

    /** Find allocations on a specific compute node. */
    List<ResourceAllocation> findByNodeName(String nodeName);

    /** Find allocations by status (PENDING, GRANTED, ACTIVE, etc.). */
    List<ResourceAllocation> findByStatus(String status);

    /** Find the active allocation for a particular workload. */
    Optional<ResourceAllocation> findByWorkloadIdAndStatus(String workloadId, String status);

    /** Sum of GPU count used on a node (for scheduling decisions). */
    long countByNodeNameAndStatus(String nodeName, String status);
}
