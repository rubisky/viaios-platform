package com.viaios.analysis.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

/**
 * Represents an AI analysis task submitted to the pipeline.
 * <p>
 * Each task is associated with a camera and a specific analysis
 * capability (e.g. object detection). The {@code params} JSONB
 * column holds capability-specific configuration, and the
 * {@code result} JSONB column stores the analysis output once
 * the task completes.
 */
@Entity
@Table(name = "analysis_tasks")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AnalysisTask {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", length = 36, nullable = false, updatable = false)
    private String id;

    /** The camera that provides the video source for this analysis. */
    @Column(name = "camera_id", length = 36, nullable = false)
    private String cameraId;

    /**
     * Analysis capability: OBJECT_DETECTION, FACIAL_RECOGNITION,
     * LICENSE_PLATE, INTRUSION_DETECTION, CROWD_ESTIMATION, CUSTOM.
     */
    @Column(name = "capability", length = 64, nullable = false)
    private String capability;

    /**
     * Capability-specific parameters stored as JSONB.
     * e.g. {@code {"modelId":"uuid","confidence":0.8,"roi":[...]}}
     */
    @Column(name = "params", columnDefinition = "jsonb")
    private String params;

    /**
     * Task lifecycle status: PENDING, QUEUED, SCHEDULED, RUNNING,
     * COMPLETED, FAILED, CANCELLED.
     */
    @Column(name = "status", length = 32, nullable = false)
    @Builder.Default
    private String status = "PENDING";

    /** Execution priority: 1 (lowest) to 10 (highest). */
    @Column(name = "priority")
    @Builder.Default
    private int priority = 5;

    /**
     * Analysis output stored as JSONB.
     * Structure depends on the capability, e.g. detections array
     * with bounding boxes, confidence scores, and class labels.
     */
    @Column(name = "result", columnDefinition = "jsonb")
    private String result;

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

    /** When the task reached a terminal state (COMPLETED, FAILED, CANCELLED). */
    @Column(name = "completed_at")
    private Instant completedAt;
}
