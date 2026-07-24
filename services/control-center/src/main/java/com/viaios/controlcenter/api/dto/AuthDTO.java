package com.viaios.controlcenter.api.dto;

/**
 * DTOs for authentication endpoints.
 * Uses Java 21 records for clean data transfer objects.
 */
public class AuthDTO {

    public record LoginRequest(String username, String password) {}

    public record RegisterRequest(String username, String password, String email) {}

    public record RefreshRequest(String refreshToken) {}

    public record TokenResponse(
            String accessToken,
            String refreshToken,
            String username,
            String role) {}
}
