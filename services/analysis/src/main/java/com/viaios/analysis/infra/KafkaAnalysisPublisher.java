package com.viaios.analysis.infra;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import java.util.Map;

@Service
public class KafkaAnalysisPublisher {
    private static final Logger log = LoggerFactory.getLogger(KafkaAnalysisPublisher.class);
    private final KafkaTemplate<String, String> kafka;
    private final ObjectMapper mapper = new ObjectMapper();

    public KafkaAnalysisPublisher(KafkaTemplate<String, String> k) { this.kafka = k; }

    public void publishTaskEvent(String eventType, Map<String, Object> data) {
        try {
            data.put("event", eventType);
            String json = mapper.writeValueAsString(data);
            kafka.send("viaios.analysis.tasks", json);
            log.info("Analysis event: {} task={}", eventType, data.get("taskId"));
        } catch (Exception e) { log.error("Publish failed", e); }
    }
}
