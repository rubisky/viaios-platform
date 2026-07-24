package com.viaios.controlcenter.controller;

import com.viaios.controlcenter.domain.*;
import com.viaios.controlcenter.domain.*;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.*;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/v1/admin")
@RequiredArgsConstructor
public class AdminController {

    private final UserRepository userRepository;
    private final RoleRepository roleRepository;
    private final PermissionRepository permissionRepository;
    private final TenantRepository tenantRepository;
    private final PasswordEncoder passwordEncoder;

    // ==================== User Management ====================

    @GetMapping("/users")
    public ResponseEntity<Map<String, Object>> listUsers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String search,
            @RequestParam(required = false) String status) {

        Pageable pageable = PageRequest.of(page, size, Sort.by("createdAt").descending());
        Page<User> users;
        if (search != null && !search.isEmpty()) {
            users = userRepository.findByUsernameContainingIgnoreCase(search, pageable);
        } else {
            users = userRepository.findAll(pageable);
        }
        return ResponseEntity.ok(Map.of(
            "data", users.getContent(),
            "total", users.getTotalElements(),
            "page", page,
            "size", size
        ));
    }

    @GetMapping("/users/{id}")
    public ResponseEntity<User> getUser(@PathVariable UUID id) {
        return userRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/users")
    public ResponseEntity<User> createUser(@RequestBody CreateUserRequest req) {
        if (userRepository.existsByUsername(req.username)) {
            return ResponseEntity.badRequest().build();
        }
        User user = User.builder()
                .username(req.username)
                .passwordHash(passwordEncoder.encode(req.password))
                .displayName(req.displayName)
                .email(req.email)
                .phone(req.phone)
                .status("ACTIVE")
                .build();
        return ResponseEntity.ok(userRepository.save(user));
    }

    @PutMapping("/users/{id}")
    public ResponseEntity<User> updateUser(@PathVariable UUID id, @RequestBody UpdateUserRequest req) {
        return userRepository.findById(id).map(user -> {
            if (req.displayName != null) user.setDisplayName(req.displayName);
            if (req.email != null) user.setEmail(req.email);
            if (req.phone != null) user.setPhone(req.phone);
            if (req.status != null) user.setStatus(req.status);
            return ResponseEntity.ok(userRepository.save(user));
        }).orElse(ResponseEntity.notFound().build());
    }

    @PatchMapping("/users/{id}/status")
    public ResponseEntity<User> toggleUserStatus(@PathVariable UUID id, @RequestBody Map<String, String> body) {
        return userRepository.findById(id).map(user -> {
            user.setStatus(body.getOrDefault("status", user.getStatus()));
            return ResponseEntity.ok(userRepository.save(user));
        }).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/users/{id}/roles")
    public ResponseEntity<User> assignRoles(@PathVariable UUID id, @RequestBody List<UUID> roleIds) {
        return userRepository.findById(id).map(user -> {
            List<Role> roles = roleRepository.findAllById(roleIds);
            user.setRoles(new HashSet<>(roles));
            return ResponseEntity.ok(userRepository.save(user));
        }).orElse(ResponseEntity.notFound().build());
    }

    // ==================== Role Management ====================

    @GetMapping("/roles")
    public ResponseEntity<List<Role>> listRoles() {
        return ResponseEntity.ok(roleRepository.findAll());
    }

    @PostMapping("/roles")
    public ResponseEntity<Role> createRole(@RequestBody Map<String, String> body) {
        Role role = Role.builder()
                .roleName(body.get("roleName"))
                .displayName(body.getOrDefault("displayName", body.get("roleName")))
                .description(body.getOrDefault("description", ""))
                .build();
        return ResponseEntity.ok(roleRepository.save(role));
    }

    @PutMapping("/roles/{id}")
    public ResponseEntity<Role> updateRole(@PathVariable UUID id, @RequestBody Map<String, String> body) {
        return roleRepository.findById(id).map(role -> {
            if (body.containsKey("displayName")) role.setDisplayName(body.get("displayName"));
            if (body.containsKey("description")) role.setDescription(body.get("description"));
            return ResponseEntity.ok(roleRepository.save(role));
        }).orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/roles/{id}")
    public ResponseEntity<Void> deleteRole(@PathVariable UUID id) {
        roleRepository.deleteById(id);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/roles/{id}/permissions")
    public ResponseEntity<Role> assignPermissions(@PathVariable UUID id, @RequestBody List<UUID> permIds) {
        return roleRepository.findById(id).map(role -> {
            List<Permission> perms = permissionRepository.findAllById(permIds);
            role.setPermissions(new HashSet<>(perms));
            return ResponseEntity.ok(roleRepository.save(role));
        }).orElse(ResponseEntity.notFound().build());
    }

    // ==================== Permission Management ====================

    @GetMapping("/permissions")
    public ResponseEntity<Map<String, List<Permission>>> listPermissions() {
        List<Permission> all = permissionRepository.findAll();
        Map<String, List<Permission>> grouped = new LinkedHashMap<>();
        for (Permission p : all) {
            String resource = p.getResourceType() != null ? p.getResourceType() : "other";
            grouped.computeIfAbsent(resource, k -> new ArrayList<>()).add(p);
        }
        return ResponseEntity.ok(grouped);
    }

    // ==================== Tenant Management ====================

    @GetMapping("/tenants")
    public ResponseEntity<List<Tenant>> listTenants() {
        return ResponseEntity.ok(tenantRepository.findAll());
    }

    @PostMapping("/tenants")
    public ResponseEntity<Tenant> createTenant(@RequestBody Map<String, String> body) {
        Tenant tenant = Tenant.builder()
                .tenantName(body.get("tenantName"))
                .displayName(body.getOrDefault("displayName", body.get("tenantName")))
                .plan(body.getOrDefault("plan", "basic"))
                .build();
        return ResponseEntity.ok(tenantRepository.save(tenant));
    }

    @PutMapping("/tenants/{id}")
    public ResponseEntity<Tenant> updateTenant(@PathVariable UUID id, @RequestBody Map<String, String> body) {
        return tenantRepository.findById(id).map(tenant -> {
            if (body.containsKey("displayName")) tenant.setDisplayName(body.get("displayName"));
            if (body.containsKey("plan")) tenant.setPlan(body.get("plan"));
            if (body.containsKey("status")) tenant.setStatus(body.get("status"));
            return ResponseEntity.ok(tenantRepository.save(tenant));
        }).orElse(ResponseEntity.notFound().build());
    }

    // ==================== DTOs ====================

    public static class CreateUserRequest {
        public String username;
        public String password;
        public String displayName;
        public String email;
        public String phone;
    }

    public static class UpdateUserRequest {
        public String displayName;
        public String email;
        public String phone;
        public String status;
    }
}
