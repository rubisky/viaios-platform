package com.viaios.reportservice.repository;

import com.viaios.reportservice.entity.Report;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ReportRepository extends JpaRepository<Report, Long> {

    List<Report> findByCaseIdOrderByCreatedAtDesc(Long caseId);

    Page<Report> findByCaseId(Long caseId, Pageable pageable);

    List<Report> findByStatus(String status);

    Page<Report> findByStatusOrderByCreatedAtDesc(String status, Pageable pageable);

    List<Report> findByCaseIdAndTemplateId(Long caseId, Long templateId);
}
