package com.viaios.caseservice.repository;

import com.viaios.caseservice.entity.Case;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface CaseRepository extends JpaRepository<Case, Long> {

    Page<Case> findByStatus(String status, Pageable pageable);

    Page<Case> findByCreatedBy(String createdBy, Pageable pageable);

    Page<Case> findByAssignedTo(String assignedTo, Pageable pageable);

    List<Case> findByStatusIn(List<String> statuses);

    Page<Case> findByStatusAndPriority(String status, String priority, Pageable pageable);

    long countByStatus(String status);
}
