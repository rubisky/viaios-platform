package com.viaios.aikernel;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * AI Kernel — VIAIOS AI orchestration microservice.
 * <p>
 * Manages the full lifecycle of AI workloads: resource scheduling
 * (GPU, memory, nodes), model registry, agent management, and the
 * internal event bus used for cross-service communication.
 */
@SpringBootApplication
@EnableScheduling
public class AiKernelApplication {

    public static void main(String[] args) {
        SpringApplication.run(AiKernelApplication.class, args);
    }
}
