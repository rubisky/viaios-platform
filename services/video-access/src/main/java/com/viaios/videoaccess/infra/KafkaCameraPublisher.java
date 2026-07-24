package com.viaios.videoaccess.infra;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class KafkaCameraPublisher {
    private static final Logger log = LoggerFactory.getLogger(KafkaCameraPublisher.class);
    private final KafkaTemplate<String, String> kafka;
    private final ObjectMapper mapper = new ObjectMapper();

    public KafkaCameraPublisher(KafkaTemplate<String, String> k) { this.kafka = k; }

    public void publishCameraEvent(String eventType, Map<String, Object> data) {
        try {
            data.put("event_type", eventType);
            data.put("timestamp", System.currentTimeMillis());
            String json = mapper.writeValueAsString(data);
            kafka.send("viaios.video.frames", json);
            log.info("Camera event published: {} camera={}", eventType, data.get("cameraId"));
        } catch (Exception e) {
            log.error("Failed to publish camera event", e);
        }
    }
}
