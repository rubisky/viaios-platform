package com.viaios.controlcenter.config;

import com.viaios.controlcenter.domain.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;

@Component
@RequiredArgsConstructor
@Slf4j
public class DataInitializer implements CommandLineRunner {

    private final UserRepository userRepository;
    private final RoleRepository roleRepository;
    private final PermissionRepository permissionRepository;
    private final TenantRepository tenantRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    @Transactional
    public void run(String... args) {
        if (userRepository.count() > 0) {
            log.info("Data already initialized, skipping seed");
            return;
        }
        log.info("Seeding initial data...");

        // Create default tenant
        Tenant tenant = tenantRepository.save(Tenant.builder()
                .tenantName("default")
                .displayName("Default Tenant")
                .plan("enterprise")
                .build());

        // Create admin role
        Role adminRole = roleRepository.save(Role.builder()
                .roleName("ADMIN")
                .displayName("Administrator")
                .description("Full system access")
                .tenantId(tenant.getId())
                .build());

        // Create operator role
        Role operatorRole = roleRepository.save(Role.builder()
                .roleName("OPERATOR")
                .displayName("Operator")
                .description("Daily operations")
                .tenantId(tenant.getId())
                .build());

        // Create viewer role
        roleRepository.save(Role.builder()
                .roleName("VIEWER")
                .displayName("Viewer")
                .description("Read-only access")
                .tenantId(tenant.getId())
                .build());

        // Create permissions
        String[][] permDefs = {
            {"cameras:read", "cameras", "read", "View cameras"},
            {"cameras:write", "cameras", "write", "Add/edit cameras"},
            {"cameras:delete", "cameras", "delete", "Delete cameras"},
            {"search:execute", "search", "execute", "Execute searches"},
            {"cases:read", "cases", "read", "View cases"},
            {"cases:write", "cases", "write", "Create/edit cases"},
            {"alarms:read", "alarms", "read", "View alarms"},
            {"alarms:acknowledge", "alarms", "acknowledge", "Acknowledge alarms"},
            {"alarms:resolve", "alarms", "resolve", "Resolve alarms"},
            {"reports:generate", "reports", "generate", "Generate reports"},
            {"admin:users", "admin", "users", "Manage users"},
            {"admin:roles", "admin", "roles", "Manage roles"},
            {"admin:tenants", "admin", "tenants", "Manage tenants"},
            {"admin:system", "admin", "system", "System configuration"},
        };

        List<Permission> allPerms = new ArrayList<>();
        for (String[] def : permDefs) {
            allPerms.add(permissionRepository.save(Permission.builder()
                    .permissionCode(def[0])
                    .resourceType(def[1])
                    .action(def[2])
                    .description(def[3])
                    .build()));
        }

        // Assign all permissions to admin role
        adminRole.setPermissions(new HashSet<>(allPerms));
        roleRepository.save(adminRole);

        // Assign basic permissions to operator
        Set<Permission> operatorPerms = new HashSet<>();
        for (Permission p : allPerms) {
            String code = p.getPermissionCode();
            if (!code.startsWith("admin:")) {
                operatorPerms.add(p);
            }
        }
        operatorRole.setPermissions(operatorPerms);
        roleRepository.save(operatorRole);

        // Create admin user
        User admin = User.builder()
                .username("admin")
                .passwordHash(passwordEncoder.encode("viaios-admin-2024"))
                .displayName("System Admin")
                .email("admin@viaios.com")
                .tenantId(tenant.getId())
                .roles(new HashSet<>(List.of(adminRole)))
                .build();
        userRepository.save(admin);

        log.info("Seed data created: 1 tenant, 3 roles, {} permissions, 1 admin user", allPerms.size());
    }
}
