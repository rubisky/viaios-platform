package com.viaios.gateway.filter;

import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.cloud.gateway.filter.ratelimit.RedisRateLimiter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Mono;

import java.util.Objects;

@Configuration
public class RateLimitConfig {

    /**
     * Key resolver that uses client IP address for rate limiting.
     * Falls back to "anonymous" if IP cannot be determined.
     */
    @Bean
    public KeyResolver ipKeyResolver() {
        return exchange -> {
            String ip = Objects.requireNonNull(
                    exchange.getRequest().getRemoteAddress()
            ).getAddress().getHostAddress();
            return Mono.just(ip);
        };
    }

    /**
     * Key resolver that uses the X-User-Id header for per-user rate limiting.
     * Falls back to IP-based limiting if the header is absent.
     */
    @Bean
    public KeyResolver userKeyResolver() {
        return exchange -> {
            String userId = exchange.getRequest().getHeaders().getFirst("X-User-Id");
            if (userId != null && !userId.isBlank()) {
                return Mono.just(userId);
            }
            // Fallback to IP
            String ip = Objects.requireNonNull(
                    exchange.getRequest().getRemoteAddress()
            ).getAddress().getHostAddress();
            return Mono.just(ip);
        };
    }

    /**
     * Key resolver that uses X-Tenant-Id for per-tenant rate limiting.
     */
    @Bean
    public KeyResolver tenantKeyResolver() {
        return exchange -> {
            String tenantId = exchange.getRequest().getHeaders().getFirst("X-Tenant-Id");
            if (tenantId != null && !tenantId.isBlank()) {
                return Mono.just(tenantId);
            }
            return Mono.just("default-tenant");
        };
    }

    /**
     * Default Redis rate limiter configuration.
     */
    @Bean
    public RedisRateLimiter defaultRateLimiter() {
        return new RedisRateLimiter(50, 100, 1);
    }
}
