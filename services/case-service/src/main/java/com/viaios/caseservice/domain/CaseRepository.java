package com.viaios.caseservice.domain;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.UUID;

public interface CaseRepository extends JpaRepository<CaseEntity, UUID> {
    List<CaseEntity> findByStatus(String status);
    List<CaseEntity> findByStatusAndPriority(String status, String priority);
    long countByStatus(String status);
}
