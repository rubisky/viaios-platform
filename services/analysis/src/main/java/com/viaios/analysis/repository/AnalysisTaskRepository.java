package com.viaios.analysis.repository;

import com.viaios.analysis.entity.AnalysisTask;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * Spring Data JPA repository for {@link AnalysisTask} entities.
 */
@Repository
public interface AnalysisTaskRepository extends JpaRepository<AnalysisTask, String> {

    /** Find all tasks for a specific camera, newest first. */
    List<AnalysisTask> findByCameraIdOrderByCreatedAtDesc(String cameraId);

    /** Find tasks by status (PENDING, RUNNING, COMPLETED, etc.). */
    List<AnalysisTask> findByStatus(String status);

    /** Find tasks by capability type. */
    List<AnalysisTask> findByCapability(String capability);

    /** Find tasks for a camera with a specific status. */
    List<AnalysisTask> findByCameraIdAndStatus(String cameraId, String status);

    /** Find the most recent tasks across all cameras. */
    List<AnalysisTask> findTop50ByOrderByCreatedAtDesc();

    /** Count running tasks for a specific camera. */
    long countByCameraIdAndStatus(String cameraId, String status);
}
