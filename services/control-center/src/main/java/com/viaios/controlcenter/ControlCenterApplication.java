package com.viaios.controlcenter;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Control Center — VIAIOS Control Plane microservice.
 * <p>
 * Manages users, tenants, roles, permissions, licenses, configuration,
 * and audit logging. This is the administrative backbone of the VIAIOS
 * platform, enforcing multi-tenancy and role-based access control.
 */
@SpringBootApplication
@EnableScheduling
public class ControlCenterApplication {

    public static void main(String[] args) {
        SpringApplication.run(ControlCenterApplication.class, args);
    }
}
