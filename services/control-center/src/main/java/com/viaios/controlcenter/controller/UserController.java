package com.viaios.controlcenter.controller;

import com.viaios.controlcenter.domain.User;
import com.viaios.controlcenter.domain.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/admin/users")
@RequiredArgsConstructor
public class UserController {

    private final UserRepository userRepository;

    @GetMapping
    public ResponseEntity<List<User>> listUsers(@RequestParam(required = false) UUID tenantId) {
        List<User> users;
        if (tenantId != null) {
            users = userRepository.findByTenantId(tenantId);
        } else {
            users = userRepository.findAll();
        }
        return ResponseEntity.ok(users);
    }

    @GetMapping("/{id}")
    public ResponseEntity<User> getUser(@PathVariable UUID id) {
        return userRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<User> createUser(@RequestBody User user) {
        if (user.getTenantId() != null && userRepository.existsByTenantIdAndUsername(user.getTenantId(), user.getUsername())) {
            return ResponseEntity.status(HttpStatus.CONFLICT).build();
        }
        User saved = userRepository.save(user);
        return ResponseEntity.status(HttpStatus.CREATED).body(saved);
    }

    @PutMapping("/{id}")
    public ResponseEntity<User> updateUser(@PathVariable UUID id, @RequestBody User updates) {
        return userRepository.findById(id)
                .map(existing -> {
                    if (updates.getEmail() != null) existing.setEmail(updates.getEmail());
                    if (updates.getStatus() != null) existing.setStatus(updates.getStatus());
                    return ResponseEntity.ok(userRepository.save(existing));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteUser(@PathVariable UUID id) {
        var userOpt = userRepository.findById(id);
        if (userOpt.isPresent()) {
            var user = userOpt.get();
            user.setStatus("DELETED");
            userRepository.save(user);
            return ResponseEntity.noContent().build();
        }
        return ResponseEntity.notFound().build();
    }
}
