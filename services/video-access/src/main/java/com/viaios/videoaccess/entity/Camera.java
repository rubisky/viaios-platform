package com.viaios.videoaccess.entity;

import jakarta.persistence.*;
import lombok.*;
import org.locationtech.jts.geom.Point;

import java.time.Instant;

/**
 * Represents a registered camera in the VIAIOS platform.
 * <p>
 * Each camera stores its geographic location as a PostGIS {@code POINT},
 * its stream URL, the protocol used for communication, and its
 * current operational status. The camera is the primary data source
 * for the video analysis pipeline.
 */
@Entity
@Table(name = "cameras")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Camera {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", length = 36, nullable = false, updatable = false)
    private String id;

    /** Human-readable camera name, e.g. "Main Entrance - East". */
    @Column(name = "name", length = 255, nullable = false)
    private String name;

    /**
     * Geographic location as a PostGIS POINT (longitude, latitude).
     * Mapped via Hibernate Spatial.
     */
    @Column(name = "location", columnDefinition = "geometry(Point,4326)")
    private Point location;

    /**
     * RTSP or GB/T 28181 stream URL used to pull video frames.
     */
    @Column(name = "stream_url", length = 1024)
    private String streamUrl;

    /**
     * Communication protocol: RTSP, GB28181, ONVIF, RTMP, HLS.
     */
    @Column(name = "protocol", length = 32, nullable = false)
    @Builder.Default
    private String protocol = "RTSP";

    /**
     * Operational status: ONLINE, OFFLINE, STREAMING, ERROR.
     */
    @Column(name = "status", length = 32, nullable = false)
    @Builder.Default
    private String status = "OFFLINE";

    /** Target frames per second for video ingestion. */
    @Column(name = "fps")
    @Builder.Default
    private int fps = 25;

    /** Stream resolution as WIDTHxHEIGHT, e.g. "1920x1080". */
    @Column(name = "resolution", length = 20)
    @Builder.Default
    private String resolution = "1920x1080";

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();
}
