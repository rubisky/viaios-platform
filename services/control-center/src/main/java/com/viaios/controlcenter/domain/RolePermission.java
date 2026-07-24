package com.viaios.controlcenter.domain;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

/**
 * Associates a permission string with a role.
 * Example: role "Camera Operator" → permission "camera:read".
 */
@Entity
@Table(name = "role_permissions")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class RolePermission {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", length = 36, nullable = false, updatable = false)
    private String id;

    /** The role this permission belongs to. */
    @Column(name = "role_id", length = 36, nullable = false)
    private String roleId;

    /**
     * Permission string in format {@code resource:action},
     * e.g. {@code "camera:read"}, {@code "user:write"}.
     */
    @Column(name = "permission", length = 128, nullable = false)
    private String permission;

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();
}
