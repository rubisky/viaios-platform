package com.viaios.videoaccess.config;

import com.viaios.videoaccess.domain.*;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import java.time.Instant;

@Configuration
public class DataInitializer {
    @Bean
    CommandLineRunner initCameras(CameraRepository repo) {
        return args -> {
            if (repo.count() == 0) {
                String[][] data = {
                    {"East Gate", "East Entrance", "rtsp://192.168.1.101:554/stream1", "RTSP"},
                    {"West Gate", "West Entrance", "rtsp://192.168.1.102:554/stream1", "RTSP"},
                    {"South Plaza", "South Plaza", "rtsp://192.168.1.103:554/stream1", "RTSP"},
                    {"Parking Lot", "B1 Parking", "rtsp://192.168.2.101:554/stream1", "RTSP"},
                    {"Lobby Main", "Lobby Main", "rtsp://192.168.3.101:554/stream1", "RTSP"},
                };
                for (String[] d : data) {
                    Camera cam = new Camera();
                    cam.setName(d[0]); cam.setLocation(d[1]);
                    cam.setStreamUrl(d[2]); cam.setProtocol(d[3]);
                    cam.setStatus("ONLINE"); cam.setCreatedAt(Instant.now());
                    repo.save(cam);
                }
            }
        };
    }
}
