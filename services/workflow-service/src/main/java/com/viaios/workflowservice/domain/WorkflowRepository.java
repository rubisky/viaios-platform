package com.viaios.workflowservice.domain;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.UUID;

public interface WorkflowRepository extends JpaRepository<WorkflowExecution, UUID> {
    List<WorkflowExecution> findByStatus(String status);
    long countByStatus(String status);
    List<WorkflowExecution> findAllByOrderByStartedAtDesc();
}
