package com.viaios.controlcenter.controller;

import com.viaios.controlcenter.domain.Tenant;
import com.viaios.controlcenter.domain.TenantRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/admin/tenants")
@RequiredArgsConstructor
public class TenantController {

    private final TenantRepository tenantRepository;

    @GetMapping
    public ResponseEntity<List<Tenant>> listTenants(@RequestParam(required = false) String status) {
        List<Tenant> tenants;
        if (status != null && !status.isBlank()) {
            tenants = tenantRepository.findByStatus(status);
        } else {
            tenants = tenantRepository.findAll();
        }
        return ResponseEntity.ok(tenants);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Tenant> getTenant(@PathVariable UUID id) {
        return tenantRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<Tenant> createTenant(@RequestBody Tenant tenant) {
        if (tenantRepository.existsByTenantName(tenant.getTenantName())) {
            return ResponseEntity.status(HttpStatus.CONFLICT).build();
        }
        Tenant saved = tenantRepository.save(tenant);
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Tenant> updateTenant(@PathVariable UUID id, @RequestBody Tenant updates) {
        return tenantRepository.findById(id)
                .map(existing -> {
                    if (updates.getTenantName() != null) existing.setTenantName(updates.getTenantName());
                    if (updates.getPlan() != null) existing.setPlan(updates.getPlan());
                    if (updates.getStatus() != null) existing.setStatus(updates.getStatus());
                    return ResponseEntity.ok(tenantRepository.save(existing));
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
