package com.viaios.alarmservice.infra;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class KafkaEventPublisher {
    private static final Logger log = LoggerFactory.getLogger(KafkaEventPublisher.class);
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper mapper = new ObjectMapper();

    public KafkaEventPublisher(KafkaTemplate<String, String> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    public void publishAlarmEvent(Map<String, Object> alarmData) {
        try {
            String json = mapper.writeValueAsString(alarmData);
            kafkaTemplate.send("viaios.alarm.events", json);
            log.info("Alarm event published: {}", alarmData.get("id"));
        } catch (Exception e) {
            log.error("Failed to publish alarm event", e);
        }
    }

    public void publishNotification(Map<String, Object> notification) {
        try {
            String json = mapper.writeValueAsString(notification);
            kafkaTemplate.send("viaios.alarm.notifications", json);
        } catch (Exception e) {
            log.error("Failed to publish notification", e);
        }
    }
}
