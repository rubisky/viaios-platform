package com.viaios.videoaccess.domain;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.UUID;

public interface CameraRepository extends JpaRepository<Camera, UUID> {
    List<Camera> findByStatus(String status);
    List<Camera> findByProtocol(String protocol);
    long countByStatus(String status);
}
