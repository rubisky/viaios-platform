package com.viaios.alarmservice.infra;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class AlarmEventConsumer {
    private static final Logger log = LoggerFactory.getLogger(AlarmEventConsumer.class);
    private final ObjectMapper mapper = new ObjectMapper();

    @KafkaListener(topics = "viaios.alarm.events", groupId = "alarm-service")
    public void consumeAlarmEvent(String message) {
        try {
            Map<String, Object> event = mapper.readValue(message, Map.class);
            String type = (String) event.get("type");
            String severity = (String) event.get("severity");
            String alarmId = (String) event.get("id");

            log.info("Alarm event received: id={} type={} severity={}", alarmId, type, severity);

            // Rule evaluation
            if ("CRITICAL".equals(severity) || "HIGH".equals(severity)) {
                log.warn("HIGH PRIORITY ALARM: {} - {}", type, event.get("message"));
                // Trigger notification
                triggerNotification(event);
            }
        } catch (Exception e) {
            log.error("Failed to process alarm event", e);
        }
    }

    @KafkaListener(topics = "viaios.alarm.notifications", groupId = "alarm-service")
    public void consumeNotification(String message) {
        try {
            Map<String, Object> notification = mapper.readValue(message, Map.class);
            log.info("Notification received: {}", notification.get("type"));
        } catch (Exception e) {
            log.error("Notification parse error", e);
        }
    }

    private void triggerNotification(Map<String, Object> alarm) {
        log.info("NOTIFICATION: Alarm {} ({}): {}",
            alarm.get("id"), alarm.get("type"), alarm.get("message"));
        // In production: send email/SMS/webhook
    }
}
