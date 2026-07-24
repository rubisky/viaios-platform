package com.viaios.controlcenter.config;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Custom Prometheus metrics for the Control Center.
 */
@Configuration
public class MetricsConfig {

    @Bean
    public Counter loginAttempts(MeterRegistry registry) {
        return Counter.builder("viaios.auth.login.attempts")
                .description("Total login attempts by outcome")
                .tag("service", "control-center")
                .register(registry);
    }

    @Bean
    public Counter userCreations(MeterRegistry registry) {
        return Counter.builder("viaios.admin.users.created")
                .description("Total user accounts created")
                .tag("service", "control-center")
                .register(registry);
    }

    @Bean
    public Counter tenantOperations(MeterRegistry registry) {
        return Counter.builder("viaios.admin.tenants.operations")
                .description("Tenant CRUD operations count")
                .tag("service", "control-center")
                .register(registry);
    }
}
