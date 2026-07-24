package com.viaios.videoaccess.api;

import com.viaios.videoaccess.domain.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api/v1/cameras")
public class CameraController {
    private final CameraRepository repo;
    private final com.viaios.videoaccess.infra.KafkaCameraPublisher kafka;
    private final Map<String, String> activeStreams = new HashMap<>();

    public CameraController(CameraRepository r, com.viaios.videoaccess.infra.KafkaCameraPublisher k) {
        this.repo = r; this.kafka = k;
    }

    // ====== CRUD ======

    @GetMapping
    public List<Camera> list(@RequestParam(defaultValue = "") String status,
                             @RequestParam(defaultValue = "") String protocol) {
        if (!status.isEmpty()) return repo.findByStatus(status);
        if (!protocol.isEmpty()) return repo.findByProtocol(protocol);
        return repo.findAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Camera> get(@PathVariable UUID id) {
        return repo.findById(id).map(ResponseEntity::ok).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<Camera> create(@RequestBody Camera cam) {
        if (cam.getStatus() == null) cam.setStatus("OFFLINE");
        cam.setCreatedAt(Instant.now());
        return ResponseEntity.ok(repo.save(cam));
    }

    @PutMapping("/{id}")
    public ResponseEntity<Camera> update(@PathVariable UUID id, @RequestBody Camera cam) {
        return repo.findById(id).map(c -> {
            if (cam.getName() != null) c.setName(cam.getName());
            if (cam.getLocation() != null) c.setLocation(cam.getLocation());
            if (cam.getStreamUrl() != null) c.setStreamUrl(cam.getStreamUrl());
            if (cam.getProtocol() != null) c.setProtocol(cam.getProtocol());
            if (cam.getStatus() != null) c.setStatus(cam.getStatus());
            if (cam.getResolution() != null) c.setResolution(cam.getResolution());
            if (cam.getFps() != null) c.setFps(cam.getFps());
            c.setLastSeenAt(Instant.now());
            return ResponseEntity.ok(repo.save(c));
        }).orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable UUID id) {
        if (repo.existsById(id)) { activeStreams.remove(id.toString()); repo.deleteById(id); return ResponseEntity.ok().build(); }
        return ResponseEntity.notFound().build();
    }

    // ====== Stream Control ======

    @PostMapping("/{id}/start")
    public ResponseEntity<Map<String, Object>> startStream(@PathVariable UUID id) {
        return repo.findById(id).map(c -> {
            c.setStatus("STREAMING");
            c.setLastSeenAt(Instant.now());
            repo.save(c);
            String streamUrl = "/live/" + id.toString().substring(0, 8) + "/index.m3u8";
            activeStreams.put(id.toString(), streamUrl);
            return ResponseEntity.ok((Map<String, Object>) (Map) Map.of("status", "streaming", "stream_url", streamUrl,
                "protocol", "HLS", "started_at", Instant.now().toString()));
        }).orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/stop")
    public ResponseEntity<Map<String, Object>> stopStream(@PathVariable UUID id) {
        return repo.findById(id).map(c -> {
            c.setStatus("ONLINE");
            c.setLastSeenAt(Instant.now());
            repo.save(c);
            activeStreams.remove(id.toString());
            return ResponseEntity.ok((Map<String, Object>) (Map) Map.of("status", "stopped"));
        }).orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/stream")
    public ResponseEntity<Map<String, Object>> getStreamUrl(@PathVariable UUID id) {
        String url = activeStreams.get(id.toString());
        if (url == null) return ResponseEntity.ok((Map<String, Object>) (Map) Map.of("stream_url", "/live/placeholder.m3u8", "status", "inactive"));
        return ResponseEntity.ok((Map<String, Object>) (Map) Map.of("stream_url", url, "status", "active"));
    }

    // ====== Snapshot ======

    @GetMapping("/{id}/snapshot")
    public ResponseEntity<Map<String, Object>> snapshot(@PathVariable UUID id) {
        return repo.findById(id).map(c -> {
            c.setLastSeenAt(Instant.now());
            repo.save(c);
            return ResponseEntity.ok((Map<String, Object>) (Map) Map.of("camera_id", id.toString(), "timestamp", Instant.now().toString(),
                "image_url", "/snapshots/cam_" + id.toString().substring(0, 8) + ".jpg",
                "resolution", c.getResolution() != null ? c.getResolution() : "1920x1080",
                "format", "JPEG"));
        }).orElse(ResponseEntity.notFound().build());
    }

    // ====== PTZ Control ======

    @PostMapping("/{id}/ptz")
    public ResponseEntity<Map<String, Object>> ptz(@PathVariable UUID id, @RequestBody Map<String, Object> cmd) {
        return repo.findById(id).map(c -> ResponseEntity.ok(Map.of(
            "camera_id", id.toString(), "pan", cmd.getOrDefault("pan", 0),
            "tilt", cmd.getOrDefault("tilt", 0), "zoom", cmd.getOrDefault("zoom", 1.0),
            "status", "executed"))).orElse(ResponseEntity.notFound().build());
    }

    // ====== Health & Stats ======

    @GetMapping("/stats")
    public Map<String, Object> stats() {
        return Map.of("total", repo.count(), "online", repo.countByStatus("ONLINE"),
            "streaming", repo.countByStatus("STREAMING"), "offline", repo.countByStatus("OFFLINE"),
            "active_streams", activeStreams.size());
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        return Map.of("total_cameras", repo.count(), "online", repo.countByStatus("ONLINE"),
            "active_streams", activeStreams.size(), "status", "operational");
    }

    @PostMapping("/init-demo")
    public ResponseEntity<List<Camera>> initDemo() {
        if (repo.count() > 0) return ResponseEntity.ok(repo.findAll());
        List<Camera> demos = new ArrayList<>();
        String[][] data = {
            {"East Gate", "East Entrance", "RTSP", "192.168.1.101", "1920x1080", "25"},
            {"West Parking", "West Parking Lot", "RTSP", "192.168.1.102", "1920x1080", "25"},
            {"South Plaza", "South Plaza", "ONVIF", "192.168.1.103", "2560x1440", "30"},
            {"Lobby Main", "Main Lobby", "RTSP", "192.168.1.104", "1920x1080", "15"},
            {"Loading Dock", "Loading Area", "GB28181", "192.168.1.105", "1280x720", "20"},
        };
        for (String[] d : data) {
            Camera cam = new Camera();
            cam.setName(d[0]); cam.setLocation(d[1]); cam.setProtocol(d[2]);
            cam.setIpAddress(d[3]); cam.setResolution(d[4]); cam.setFps(Integer.parseInt(d[5]));
            cam.setStatus("ONLINE"); cam.setCreatedAt(Instant.now()); cam.setLastSeenAt(Instant.now());
            demos.add(repo.save(cam));
        }
        return ResponseEntity.ok(demos);
    }
}
