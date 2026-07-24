package com.viaios.alarmservice.domain;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.UUID;

public interface AlarmRepository extends JpaRepository<Alarm, UUID> {
    List<Alarm> findByStatus(String status);
    List<Alarm> findByStatusOrderByCreatedAtDesc(String status);
    List<Alarm> findByCameraId(String cameraId);
    List<Alarm> findBySeverityAndStatus(String severity, String status);
    long countByStatus(String status);
    long countBySeverity(String severity);
}
