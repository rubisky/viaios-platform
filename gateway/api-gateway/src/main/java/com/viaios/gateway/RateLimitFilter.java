package com.viaios.gateway;

import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class RateLimitFilter implements GlobalFilter, Ordered {

    private final Map<String, TokenBucket> buckets = new ConcurrentHashMap<>();
    private static final int DEFAULT_RATE = 100;  // requests per minute
    private static final int AUTH_RATE = 300;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();
        if (path.startsWith("/actuator") || path.startsWith("/api/v1/health")) {
            return chain.filter(exchange);
        }

        String clientIp = exchange.getRequest().getRemoteAddress() != null
            ? exchange.getRequest().getRemoteAddress().getHostString()
            : "unknown";

        String userId = exchange.getRequest().getHeaders().getFirst("X-User-Id");
        String key = userId != null ? "user:" + userId : "ip:" + clientIp;
        int rate = userId != null ? AUTH_RATE : DEFAULT_RATE;

        TokenBucket bucket = buckets.computeIfAbsent(key, k -> new TokenBucket(rate));
        if (!bucket.tryConsume()) {
            exchange.getResponse().setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
            exchange.getResponse().getHeaders().set("Retry-After", "60");
            return exchange.getResponse().setComplete();
        }

        return chain.filter(exchange);
    }

    @Override
    public int getOrder() { return -200; }

    static class TokenBucket {
        private final int capacity;
        private double tokens;
        private long lastRefill;

        TokenBucket(int rate) {
            this.capacity = rate;
            this.tokens = rate;
            this.lastRefill = System.currentTimeMillis();
        }

        synchronized boolean tryConsume() {
            refill();
            if (tokens >= 1) { tokens--; return true; }
            return false;
        }

        private void refill() {
            long now = System.currentTimeMillis();
            double elapsed = (now - lastRefill) / 1000.0;
            tokens = Math.min(capacity, tokens + elapsed * capacity / 60.0);
            lastRefill = now;
        }
    }
}
