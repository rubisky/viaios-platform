package com.viaios.workflowservice.repository;

import com.viaios.workflowservice.entity.WorkflowExecution;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface WorkflowExecutionRepository extends JpaRepository<WorkflowExecution, Long> {

    List<WorkflowExecution> findByStatusOrderByStartedAtDesc(String status);

    Page<WorkflowExecution> findByStatus(String status, Pageable pageable);

    List<WorkflowExecution> findByStatusIn(List<String> statuses);

    Page<WorkflowExecution> findAllByOrderByStartedAtDesc(Pageable pageable);

    long countByStatus(String status);
}
