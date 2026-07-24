package com.viaios.videoaccess.repository;

import com.viaios.videoaccess.entity.Camera;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * Spring Data JPA repository for {@link Camera} entities.
 */
@Repository
public interface CameraRepository extends JpaRepository<Camera, String> {

    /** Find cameras by operational status. */
    List<Camera> findByStatus(String status);

    /** Find cameras using a specific protocol. */
    List<Camera> findByProtocol(String protocol);

    /** Find cameras whose name contains the given substring (case-insensitive). */
    List<Camera> findByNameContainingIgnoreCase(String name);

    /** Count cameras that are currently streaming. */
    long countByStatus(String status);
}
