package com.viaios.gateway;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.*;

@RestController
public class HealthController {

    @GetMapping("/api/v1/health")
    public Map<String, Object> health() {
        Map<String, Object> status = new LinkedHashMap<>();
        status.put("service", "VIAIOS Gateway 4.0.0");
        status.put("status", "UP");
        status.put("timestamp", System.currentTimeMillis());
        Map<String, Integer> svcs = new LinkedHashMap<>();
        svcs.put("control-center", 8081); svcs.put("ai-kernel", 8082);
        svcs.put("video-access", 8083); svcs.put("analysis", 8084);
        svcs.put("search", 8085); svcs.put("case-service", 8086);
        svcs.put("report-service", 8087); svcs.put("alarm-service", 8088);
        svcs.put("workflow-service", 8089); svcs.put("agent-service", 8091);
        svcs.put("capability-service", 8092); svcs.put("knowledge-service", 8093);
        status.put("services", svcs);
        return status;
    }
}
