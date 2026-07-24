package com.viaios.videoaccess.domain;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "cameras")
public class Camera {
    @Id
    @GeneratedValue
    private UUID id;

    @Column(nullable = false)
    private String name;

    private String location;

    @Column(name = "stream_url")
    private String streamUrl;

    private String protocol = "RTSP";

    private String status = "OFFLINE";

    private Integer fps = 15;

    private String resolution = "1920x1080";

    @Column(name = "ip_address")
    private String ipAddress;

    @Column(name = "created_at")
    private Instant createdAt = Instant.now();

    @Column(name = "last_seen_at")
    private Instant lastSeenAt;

    public Camera() {}

    // Getters and Setters
    public UUID getId() { return id; }
    public String getName() { return name; }
    public void setName(String n) { name = n; }
    public String getLocation() { return location; }
    public void setLocation(String l) { location = l; }
    public String getStreamUrl() { return streamUrl; }
    public void setStreamUrl(String u) { streamUrl = u; }
    public String getProtocol() { return protocol; }
    public void setProtocol(String p) { protocol = p; }
    public String getStatus() { return status; }
    public void setStatus(String s) { status = s; }
    public Integer getFps() { return fps; }
    public void setFps(Integer f) { fps = f; }
    public String getResolution() { return resolution; }
    public void setResolution(String r) { resolution = r; }
    public String getIpAddress() { return ipAddress; }
    public void setIpAddress(String ip) { ipAddress = ip; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant t) { createdAt = t; }
    public Instant getLastSeenAt() { return lastSeenAt; }
    public void setLastSeenAt(Instant t) { lastSeenAt = t; }
}
