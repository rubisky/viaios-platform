package com.viaios.alarmservice.repository;

import com.viaios.alarmservice.entity.Alarm;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface AlarmRepository extends JpaRepository<Alarm, Long> {

    Page<Alarm> findByStatus(String status, Pageable pageable);

    List<Alarm> findByCameraIdAndStatus(String cameraId, String status);

    Page<Alarm> findByCameraId(String cameraId, Pageable pageable);

    Page<Alarm> findByRuleId(Long ruleId, Pageable pageable);

    List<Alarm> findBySeverityAndStatus(String severity, String status);

    Page<Alarm> findByStatusAndSeverity(String status, String severity, Pageable pageable);

    List<Alarm> findByStatusIn(List<String> statuses);

    long countByStatus(String status);

    List<Alarm> findByCreatedAtBeforeAndStatus(LocalDateTime since, String status);
}
