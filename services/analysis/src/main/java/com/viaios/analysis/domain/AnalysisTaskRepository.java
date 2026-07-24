package com.viaios.analysis.domain;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.UUID;

public interface AnalysisTaskRepository extends JpaRepository<AnalysisTask, UUID> {
    List<AnalysisTask> findByCameraId(String cameraId);
    List<AnalysisTask> findByStatus(String status);
    long countByStatus(String status);
}
