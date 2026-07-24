package com.viaios.videoaccess;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Video Access Gateway — VIAIOS video ingestion microservice.
 * <p>
 * Provides camera lifecycle management, stream control (start/stop),
 * and multi-protocol adaptation for GB/T 28181, RTSP, and ONVIF
 * cameras. Acts as the bridge between physical camera infrastructure
 * and the VIAIOS AI analysis pipeline.
 */
@SpringBootApplication
@EnableScheduling
public class VideoAccessApplication {

    public static void main(String[] args) {
        SpringApplication.run(VideoAccessApplication.class, args);
    }
}
