package com.viaios.aikernel.domain;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "model_registry")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ModelInfo {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, length = 128)
    private String name;

    @Column(length = 32)
    private String version;

    @Column(length = 64)
    private String runtime;  // TENSORRT, ONNX, TRITON, TORCHSERVE, VLLM, CUSTOM

    @Column(length = 64)
    private String task;     // detection, face_recognition, reid, ocr, llm, embedding

    @Column(length = 32)
    @Builder.Default
    private String status = "REGISTERED";

    @Column(name = "registry_path", length = 512)
    private String registryPath;

    @Column(name = "model_path", length = 512)
    private String modelPath;

    @Column(name = "input_shape", length = 128)
    private String inputShape;

    @Column(name = "output_shape", length = 128)
    private String outputShape;

    @Column(length = 16)
    private String precision;  // FP32, FP16, INT8

    @Column(name = "gpu_memory_mb")
    private Integer gpuMemoryMb;

    @Column(name = "avg_latency_ms")
    private Integer avgLatencyMs;

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
