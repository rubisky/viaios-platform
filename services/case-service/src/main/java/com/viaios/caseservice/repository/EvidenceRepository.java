package com.viaios.caseservice.repository;

import com.viaios.caseservice.entity.Evidence;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface EvidenceRepository extends JpaRepository<Evidence, Long> {

    List<Evidence> findByCaseIdOrderByCreatedAtDesc(Long caseId);

    List<Evidence> findByCaseIdAndType(Long caseId, String type);

    List<Evidence> findByHash(String hash);

    void deleteByCaseId(Long caseId);

    long countByCaseId(Long caseId);
}
