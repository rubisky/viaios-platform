package com.viaios.gateway.filter;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Timer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Custom Prometheus metrics for the API Gateway.
 * <p>
 * Exposes counters and timers that are scraped by Prometheus
 * at /actuator/prometheus.
 */
@Configuration
public class MetricsConfig {

    @Bean
    public Counter authFailures(MeterRegistry registry) {
        return Counter.builder("viaios.gateway.auth.failures")
                .description("Number of failed authentication attempts at the gateway")
                .tag("gateway", "api-gateway")
                .register(registry);
    }

    @Bean
    public Counter rateLimitHits(MeterRegistry registry) {
        return Counter.builder("viaios.gateway.ratelimit.hits")
                .description("Number of requests blocked by rate limiting")
                .tag("gateway", "api-gateway")
                .register(registry);
    }

    @Bean
    public Timer requestLatency(MeterRegistry registry) {
        return Timer.builder("viaios.gateway.request.latency")
                .description("Request latency through the API gateway")
                .tag("gateway", "api-gateway")
                .publishPercentiles(0.5, 0.95, 0.99)
                .register(registry);
    }

    @Bean
    public Counter requestsByRoute(MeterRegistry registry) {
        return Counter.builder("viaios.gateway.requests.total")
                .description("Total requests through the API gateway by route and status")
                .tag("gateway", "api-gateway")
                .register(registry);
    }
}
