package com.viaios.gateway.filter;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.UUID;

/**
 * Global filter that adds correlation ID and structured request/response logging.
 * <p>
 * The correlation ID is propagated via the X-Correlation-Id header. If the incoming
 * request already has one, it is reused; otherwise a new UUIDv7-like ID is generated.
 * Every request/response pair is logged as a single structured JSON line containing
 * method, path, status, latency, client IP, user agent, and the correlation ID.
 */
@Component
public class GatewayLoggingFilter implements GlobalFilter, Ordered {

    private static final Logger log = LoggerFactory.getLogger(GatewayLoggingFilter.class);
    private static final String CORRELATION_ID_HEADER = "X-Correlation-Id";
    private static final String CORRELATION_ID_MDC = "correlationId";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        long startNanos = System.nanoTime();

        // Extract or generate correlation ID
        String correlationId = extractOrGenerateCorrelationId(exchange.getRequest());

        // Inject into MDC for downstream log context
        MDC.put(CORRELATION_ID_MDC, correlationId);

        // Add correlation ID to response headers
        exchange.getResponse().getHeaders().add(CORRELATION_ID_HEADER, correlationId);

        // Add to request headers for downstream propagation
        ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                .header(CORRELATION_ID_HEADER, correlationId)
                .build();
        ServerWebExchange mutatedExchange = exchange.mutate().request(mutatedRequest).build();

        return chain.filter(mutatedExchange)
                .doOnSuccess(v -> logResponse(exchange, startNanos, correlationId))
                .doOnError(e -> {
                    log.error("Request failed: correlationId={} error={}",
                            correlationId, e.getMessage());
                    logResponse(exchange, startNanos, correlationId);
                })
                .doFinally(signalType -> MDC.remove(CORRELATION_ID_MDC));
    }

    private String extractOrGenerateCorrelationId(ServerHttpRequest request) {
        String existingId = request.getHeaders().getFirst(CORRELATION_ID_HEADER);
        if (existingId != null && !existingId.isBlank()) {
            return existingId;
        }
        // Generate a short ID: timestamp prefix + random suffix
        return Instant.now().toEpochMilli() + "-" + UUID.randomUUID().toString().substring(0, 8);
    }

    private void logResponse(ServerWebExchange exchange, long startNanos, String correlationId) {
        ServerHttpResponse response = exchange.getResponse();
        ServerHttpRequest request = exchange.getRequest();

        Integer statusCode = response.getStatusCode() != null
                ? response.getStatusCode().value() : null;

        long latencyMs = (System.nanoTime() - startNanos) / 1_000_000;

        String clientIp = request.getHeaders().getFirst("X-Forwarded-For");
        if (clientIp == null || clientIp.isBlank()) {
            clientIp = request.getRemoteAddress() != null
                    ? request.getRemoteAddress().getAddress().getHostAddress()
                    : "unknown";
        }
        // Only use the first IP if X-Forwarded-For contains multiple
        if (clientIp != null && clientIp.contains(",")) {
            clientIp = clientIp.split(",")[0].trim();
        }

        String userId = request.getHeaders().getFirst("X-User-Id");
        String userAgent = request.getHeaders().getFirst("User-Agent");

        // Structured JSON log line
        log.info("{\"type\":\"gateway_request\"," +
                        "\"correlationId\":\"{}\"," +
                        "\"timestamp\":\"{}\"," +
                        "\"method\":\"{}\"," +
                        "\"path\":\"{}\"," +
                        "\"query\":\"{}\"," +
                        "\"status\":{}," +
                        "\"latencyMs\":{}," +
                        "\"clientIp\":\"{}\"," +
                        "\"userId\":\"{}\"," +
                        "\"userAgent\":\"{}\"}",
                correlationId,
                Instant.now().toString(),
                request.getMethod().name(),
                request.getURI().getPath(),
                request.getURI().getQuery() != null ? request.getURI().getQuery() : "",
                statusCode,
                latencyMs,
                clientIp != null ? clientIp : "unknown",
                userId != null ? userId : "anonymous",
                userAgent != null ? userAgent.replace("\"", "'") : "unknown");
    }

    @Override
    public int getOrder() {
        // Run early (after security/auth filters) but before most business filters
        return Ordered.HIGHEST_PRECEDENCE + 20;
    }
}
