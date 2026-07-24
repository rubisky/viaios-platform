package com.viaios.alarmservice.config;

import com.viaios.alarmservice.domain.*;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DataInitializer {
    @Bean
    CommandLineRunner initAlarms(AlarmRepository repo) {
        return args -> {
            if (repo.count() == 0) {
                String[][] data = {
                    {"INTRUSION", "CRITICAL", "Unauthorized access at East Gate", "cam-001"},
                    {"LOITERING", "HIGH", "Person loitering at Plaza", "cam-002"},
                    {"CROWD", "MEDIUM", "Crowd threshold exceeded", "cam-003"},
                };
                for (String[] d : data) {
                    Alarm a = new Alarm();
                    a.setType(d[0]); a.setSeverity(d[1]);
                    a.setMessage(d[2]); a.setCameraId(d[3]);
                    a.setStatus("TRIGGERED");
                    repo.save(a);
                }
            }
        };
    }
}
