package com.viaios.gateway.filter;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.List;

@Component
public class AuthFilter implements GlobalFilter, Ordered {

    private static final Logger log = LoggerFactory.getLogger(AuthFilter.class);

    private static final List<String> PUBLIC_PATHS = List.of(
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/token/refresh",
            "/health",
            "/actuator"
    );

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();

        // Allow public paths without authentication
        if (isPublicPath(path)) {
            return chain.filter(exchange);
        }

        String authHeader = exchange.getRequest().getHeaders().getFirst(HttpHeaders.AUTHORIZATION);

        if (!StringUtils.hasText(authHeader) || !authHeader.startsWith("Bearer ")) {
            // For development, inject default headers if no token
            log.debug("No Bearer token on path: {}, injecting dev defaults", path);
            ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                    .header("X-User-Id", "dev-user")
                    .header("X-Tenant-Id", "dev-tenant")
                    .header("X-User-Role", "developer")
                    .build();
            return chain.filter(exchange.mutate().request(mutatedRequest).build());
        }

        String token = authHeader.substring(7);
        try {
            String[] parts = decodeJwt(token);
            String userId = parts.length > 0 ? parts[0] : "unknown";
            String tenantId = parts.length > 1 ? parts[1] : "default";
            String role = parts.length > 2 ? parts[2] : "user";

            log.debug("JWT decoded: userId={}, tenantId={}, role={}", userId, tenantId, role);

            ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                    .header("X-User-Id", userId)
                    .header("X-Tenant-Id", tenantId)
                    .header("X-User-Role", role)
                    .build();

            return chain.filter(exchange.mutate().request(mutatedRequest).build());

        } catch (Exception e) {
            log.warn("Invalid JWT token: {}", e.getMessage());
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }
    }

    private boolean isPublicPath(String path) {
        return PUBLIC_PATHS.stream().anyMatch(path::startsWith);
    }

    private String[] decodeJwt(String token) {
        // Decode JWT payload without verification (gateway validates via OAuth2 resource server)
        // Format: header.payload.signature
        String[] chunks = token.split("\\.");
        if (chunks.length < 2) {
            throw new IllegalArgumentException("Invalid JWT format");
        }

        byte[] decoded = Base64.getUrlDecoder().decode(chunks[1]);
        String payload = new String(decoded, StandardCharsets.UTF_8);

        // Simple JSON field extraction (production: use a proper JSON parser)
        String sub = extractJsonField(payload, "sub");
        String tenantId = extractJsonField(payload, "tenant_id");
        String role = extractJsonField(payload, "role");

        return new String[]{
                sub != null ? sub : "unknown",
                tenantId != null ? tenantId : "default",
                role != null ? role : "user"
        };
    }

    private String extractJsonField(String json, String fieldName) {
        String searchKey = "\"" + fieldName + "\"";
        int keyIndex = json.indexOf(searchKey);
        if (keyIndex < 0) {
            return null;
        }
        int colonIndex = json.indexOf(":", keyIndex);
        if (colonIndex < 0) {
            return null;
        }
        int valueStart = colonIndex + 1;
        while (valueStart < json.length() && (json.charAt(valueStart) == ' ' || json.charAt(valueStart) == '"')) {
            valueStart++;
        }
        int valueEnd = valueStart;
        while (valueEnd < json.length() && json.charAt(valueEnd) != '"' && json.charAt(valueEnd) != ',' && json.charAt(valueEnd) != '}') {
            valueEnd++;
        }
        if (valueEnd > valueStart) {
            return json.substring(valueStart, valueEnd);
        }
        return null;
    }

    @Override
    public int getOrder() {
        return -100;
    }
}
