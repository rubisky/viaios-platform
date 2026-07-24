package com.viaios.controlcenter.service;

import com.viaios.controlcenter.api.dto.AuthDTO.*;
import com.viaios.controlcenter.domain.*;
import com.viaios.controlcenter.infra.JwtUtil;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
public class AuthService {
    private final UserRepository userRepo;
    private final JwtUtil jwtUtil;
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

    public AuthService(UserRepository r, JwtUtil j) { userRepo = r; jwtUtil = j; }

    @Transactional
    public TokenResponse register(RegisterRequest req) {
        if (userRepo.existsByUsername(req.username()))
            throw new RuntimeException("Username already exists");
        User u = User.builder()
                .username(req.username())
                .email(req.email())
                .passwordHash(encoder.encode(req.password()))
                .displayName(req.username())
                .status("ACTIVE")
                .build();
        u = userRepo.save(u);
        String mainRole = u.getRoles() != null && !u.getRoles().isEmpty()
                ? u.getRoles().iterator().next().getRoleName() : "USER";
        return new TokenResponse(
            jwtUtil.generateAccessToken(u.getId(), u.getUsername(), mainRole),
            jwtUtil.generateRefreshToken(u.getId()), u.getUsername(), mainRole);
    }

    public TokenResponse login(LoginRequest req) {
        User u = userRepo.findByUsername(req.username())
            .orElseThrow(() -> new RuntimeException("Invalid credentials"));
        if (!encoder.matches(req.password(), u.getPasswordHash()))
            throw new RuntimeException("Invalid credentials");
        String mainRole = u.getRoles() != null && !u.getRoles().isEmpty()
                ? u.getRoles().iterator().next().getRoleName() : "USER";
        return new TokenResponse(
            jwtUtil.generateAccessToken(u.getId(), u.getUsername(), mainRole),
            jwtUtil.generateRefreshToken(u.getId()), u.getUsername(), mainRole);
    }

    public TokenResponse refresh(RefreshRequest req) {
        var claims = jwtUtil.validateToken(req.refreshToken());
        UUID userId = UUID.fromString(claims.getSubject());
        User u = userRepo.findById(userId)
            .orElseThrow(() -> new RuntimeException("User not found"));
        String mainRole = u.getRoles() != null && !u.getRoles().isEmpty()
                ? u.getRoles().iterator().next().getRoleName() : "USER";
        return new TokenResponse(
            jwtUtil.generateAccessToken(u.getId(), u.getUsername(), mainRole),
            null, u.getUsername(), mainRole);
    }
}
