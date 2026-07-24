package com.viaios.workflowservice.repository;

import com.viaios.workflowservice.entity.WorkflowStep;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface WorkflowStepRepository extends JpaRepository<WorkflowStep, Long> {

    List<WorkflowStep> findByExecutionIdOrderByStartedAtAsc(Long executionId);

    Optional<WorkflowStep> findByExecutionIdAndStepId(Long executionId, String stepId);

    List<WorkflowStep> findByExecutionIdAndStatus(Long executionId, String status);

    long countByExecutionIdAndStatus(Long executionId, String status);

    void deleteByExecutionId(Long executionId);
}
