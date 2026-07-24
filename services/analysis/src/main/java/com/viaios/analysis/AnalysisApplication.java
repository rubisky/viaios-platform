package com.viaios.analysis;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * AI Analysis — VIAIOS video analysis microservice.
 * <p>
 * Accepts analysis task submissions, dispatches them to the AI Kernel
 * for GPU scheduling, tracks progress through the pipeline, and serves
 * results (detections, classifications, annotations) back to callers.
 * Supports multiple analysis capabilities: object detection, facial
 * recognition, license plate recognition, and custom models.
 */
@SpringBootApplication
@EnableScheduling
public class AnalysisApplication {

    public static void main(String[] args) {
        SpringApplication.run(AnalysisApplication.class, args);
    }
}
