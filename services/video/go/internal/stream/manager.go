// Stream manager — manages RTSP, HLS, and WebRTC video streams.
package stream

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/viaios/video/internal/decoder"
	"go.uber.org/zap"
)

// StreamType represents the type of video stream.
type StreamType string

const (
	StreamRTSP    StreamType = "RTSP"
	StreamHLS     StreamType = "HLS"
	StreamWebRTC  StreamType = "WebRTC"
	StreamGB28181 StreamType = "GB28181"
	StreamFile    StreamType = "FILE"
)

// StreamStatus represents the status of a stream.
type StreamStatus string

const (
	StatusActive    StreamStatus = "ACTIVE"
	StatusPaused    StreamStatus = "PAUSED"
	StatusError     StreamStatus = "ERROR"
	StatusReconnecting StreamStatus = "RECONNECTING"
)

// Stream represents a video stream.
type Stream struct {
	ID           string       `json:"id"`
	Name         string       `json:"name"`
	Type         StreamType   `json:"type"`
	SourceURI    string       `json:"source_uri"`
	Status       StreamStatus `json:"status"`
	Codec        string       `json:"codec"`
	Resolution   string       `json:"resolution"`
	FPS          float64      `json:"fps"`
	BitrateKbps  int64        `json:"bitrate_kbps"`
	BytesTotal   int64        `json:"bytes_total"`
	PacketsTotal int64        `json:"packets_total"`
	Uptime       time.Duration `json:"uptime_seconds"`
	StartedAt    time.Time    `json:"started_at"`
	LastFrameAt  time.Time    `json:"last_frame_at"`
	Error        string       `json:"error,omitempty"`
	CameraID     string       `json:"camera_id,omitempty"`
	DecodeSession string      `json:"decode_session,omitempty"`
}

// Manager manages all video streams.
type Manager struct {
	logger   *zap.Logger
	decoder  *decoder.Service
	streams  map[string]*Stream
	mu       sync.RWMutex
}

// NewManager creates a new stream manager.
func NewManager(logger *zap.Logger, decoder *decoder.Service) *Manager {
	return &Manager{
		logger:  logger,
		decoder: decoder,
		streams: make(map[string]*Stream),
	}
}

// Run is the main manager loop.
func (m *Manager) Run(ctx context.Context) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			m.cleanupStaleStreams()
		}
	}
}

// AddStream starts streaming from a source.
func (m *Manager) AddStream(req StreamRequest) (*Stream, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	id := fmt.Sprintf("stream-%d", time.Now().UnixNano())
	stream := &Stream{
		ID:         id,
		Name:       req.Name,
		Type:       req.Type,
		SourceURI:  req.SourceURI,
		Status:     StatusActive,
		Resolution: req.Resolution,
		FPS:        float64(req.MaxFPS),
		StartedAt:  time.Now(),
		CameraID:   req.CameraID,
	}

	// Start decoding
	decReq := decoder.DecodeRequest{
		StreamID:   id,
		SourceURI:  req.SourceURI,
		MaxFPS:     req.MaxFPS,
		Resolution: req.Resolution,
		HWAccel:    req.HWAccel,
	}
	status, err := m.decoder.Start(context.Background(), decReq)
	if err != nil {
		stream.Status = StatusError
		stream.Error = err.Error()
	} else {
		stream.DecodeSession = status.SessionID
		stream.Codec = string(status.Codec)
	}

	m.streams[id] = stream
	m.logger.Info("Stream added",
		zap.String("id", id),
		zap.String("type", string(req.Type)),
		zap.String("uri", req.SourceURI))

	return stream, nil
}

// RemoveStream stops and removes a stream.
func (m *Manager) RemoveStream(id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	stream, ok := m.streams[id]
	if !ok {
		return fmt.Errorf("stream not found: %s", id)
	}

	if stream.DecodeSession != "" {
		m.decoder.Stop(stream.DecodeSession)
	}

	delete(m.streams, id)
	m.logger.Info("Stream removed", zap.String("id", id))
	return nil
}

// GetStream returns a stream by ID.
func (m *Manager) GetStream(id string) (*Stream, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	stream, ok := m.streams[id]
	if !ok {
		return nil, fmt.Errorf("stream not found: %s", id)
	}
	return stream, nil
}

// ListStreams returns all streams.
func (m *Manager) ListStreams() []*Stream {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var streams []*Stream
	for _, s := range m.streams {
		s.Uptime = time.Since(s.StartedAt)
		streams = append(streams, s)
	}
	return streams
}

// ActiveStreams returns the count of active streams.
func (m *Manager) ActiveStreams() int {
	m.mu.RLock()
	defer m.mu.RUnlock()

	count := 0
	for _, s := range m.streams {
		if s.Status == StatusActive {
			count++
		}
	}
	return count
}

// Stats returns stream manager statistics.
func (m *Manager) Stats() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var totalBytes int64
	byType := make(map[StreamType]int)
	byStatus := make(map[StreamStatus]int)

	for _, s := range m.streams {
		totalBytes += s.BytesTotal
		byType[s.Type]++
		byStatus[s.Status]++
	}

	return map[string]interface{}{
		"total_streams":   len(m.streams),
		"active_streams":  byStatus[StatusActive],
		"total_bytes":     totalBytes,
		"by_type":         byType,
		"by_status":       byStatus,
	}
}

// cleanupStaleStreams removes streams that haven't received frames recently.
func (m *Manager) cleanupStaleStreams() {
	m.mu.Lock()
	defer m.mu.Unlock()

	timeout := 5 * time.Minute
	for id, s := range m.streams {
		if s.Status == StatusActive && time.Since(s.LastFrameAt) > timeout {
			s.Status = StatusError
			s.Error = "stream timeout"
			m.logger.Warn("Stream timed out", zap.String("id", id))
		}
	}
}

// StreamRequest is a request to add a stream.
type StreamRequest struct {
	Name       string     `json:"name"`
	Type       StreamType `json:"type"`
	SourceURI  string     `json:"source_uri"`
	MaxFPS     int        `json:"max_fps"`
	Resolution string     `json:"resolution"`
	HWAccel    string     `json:"hw_accel"`
	CameraID   string     `json:"camera_id"`
}
