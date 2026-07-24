package com.viaios.controlcenter.infra;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import java.util.concurrent.TimeUnit;

@Service
public class TokenBlacklistService {
    private final StringRedisTemplate redis;

    public TokenBlacklistService(StringRedisTemplate r) { this.redis = r; }

    public void blacklist(String token, long expireSeconds) {
        redis.opsForValue().set("blacklist:" + token, "1", expireSeconds, TimeUnit.SECONDS);
    }

    public boolean isBlacklisted(String token) {
        return Boolean.TRUE.equals(redis.hasKey("blacklist:" + token));
    }

    public void cacheUser(String userId, String username, String role) {
        redis.opsForHash().putAll("user:" + userId, java.util.Map.of(
            "username", username, "role", role, "cached_at", String.valueOf(System.currentTimeMillis())
        ));
        redis.expire("user:" + userId, 30, TimeUnit.MINUTES);
    }

    public java.util.Map<Object, Object> getUserCache(String userId) {
        return redis.opsForHash().entries("user:" + userId);
    }
}
