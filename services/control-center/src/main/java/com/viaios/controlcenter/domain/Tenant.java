package com.viaios.controlcenter.domain;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "tenants")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Tenant {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_name", unique = true, nullable = false, length = 64)
    private String tenantName;

    @Column(name = "display_name", length = 128)
    private String displayName;

    @Column(length = 32)
    @Builder.Default
    private String plan = "basic";

    @Column(name = "camera_limit")
    @Builder.Default
    private Integer cameraLimit = 100;

    @Column(name = "storage_limit_mb")
    @Builder.Default
    private Long storageLimitMb = 102400L;

    @Column(length = 20)
    @Builder.Default
    private String status = "ACTIVE";

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
