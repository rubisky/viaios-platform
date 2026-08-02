// Video decoder service — FFmpeg-based decoding with hardware acceleration.
package decoder

import (
	"context"
	"fmt"
	"sync"
	"time"

	"go.uber.org/zap"
)

// Codec represents a video codec type.
type Codec string

const (
	CodecH264 Codec = "h264"
	CodecH265 Codec = "h265"
	CodecMJPEG Codec = "mjpeg"
)

// DecodeRequest is a request to decode a video stream.
type DecodeRequest struct {
	StreamID    string `json:"stream_id"`
	SourceURI   string `json:"source_uri"`   // rtsp://, file://, gb28181://
	OutputDir   string `json:"output_dir"`
	MaxFPS      int    `json:"max_fps"`
	Resolution  string `json:"resolution"`   // "1920x1080" or "" for source
	Duration    int    `json:"duration_sec"` // 0 = indefinite
	HWAccel     string `json:"hw_accel"`     // cuda, vaapi, none
}

// DecodeStatus is the status of a decoding session.
type DecodeStatus struct {
	SessionID     string    `json:"session_id"`
	StreamID      string    `json:"stream_id"`
	Codec         Codec     `json:"codec"`
	Resolution    string    `json:"resolution"`
	FPS           float64   `json:"fps"`
	FramesTotal   int64     `json:"frames_total"`
	FramesDropped int64     `json:"frames_dropped"`
	BitrateKbps   int64     `json:"bitrate_kbps"`
	Running       bool      `json:"running"`
	StartedAt     time.Time `json:"started_at"`
	Error         string    `json:"error,omitempty"`
}

// VideoFrame represents a decoded video frame.
type VideoFrame struct {
	SessionID  string    `json:"session_id"`
	FrameIndex int64     `json:"frame_index"`
	Timestamp  time.Time `json:"timestamp"`
	Width      int       `json:"width"`
	Height     int       `json:"height"`
	Format     string    `json:"format"` // yuv420p, rgb24, bgra
	Data       []byte    `json:"data,omitempty"`
	KeyFrame   bool      `json:"keyframe"`
	Size       int64     `json:"size_bytes"`
}

// Service handles video decoding operations.
type Service struct {
	logger   *zap.Logger
	sessions map[string]*decodeSession
	mu       sync.RWMutex
}

type decodeSession struct {
	status   DecodeStatus
	cancel   context.CancelFunc
	frameCh  chan *VideoFrame
}

// NewService creates a new decoder service.
func NewService(logger *zap.Logger) *Service {
	return &Service{
		logger:   logger,
		sessions: make(map[string]*decodeSession),
	}
}

// Start begins decoding a video source.
func (s *Service) Start(ctx context.Context, req DecodeRequest) (*DecodeStatus, error) {
	sessionID := fmt.Sprintf("dec-%d", time.Now().UnixNano())

	sessionCtx, cancel := context.WithCancel(ctx)

	session := &decodeSession{
		status: DecodeStatus{
			SessionID:  sessionID,
			StreamID:   req.StreamID,
			Resolution: req.Resolution,
			Running:    true,
			StartedAt:  time.Now(),
		},
		cancel:  cancel,
		frameCh: make(chan *VideoFrame, 100),
	}

	s.mu.Lock()
	s.sessions[sessionID] = session
	s.mu.Unlock()

	go s.decodeLoop(sessionCtx, req, session)

	s.logger.Info("Decode session started",
		zap.String("session_id", sessionID),
		zap.String("uri", req.SourceURI),
		zap.String("codec", string(session.status.Codec)))

	return &session.status, nil
}

// Stop terminates a decoding session.
func (s *Service) Stop(sessionID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	session, ok := s.sessions[sessionID]
	if !ok {
		return fmt.Errorf("session not found: %s", sessionID)
	}

	session.cancel()
	session.status.Running = false
	return nil
}

// Status returns the status of a decoding session.
func (s *Service) Status(sessionID string) (*DecodeStatus, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	session, ok := s.sessions[sessionID]
	if !ok {
		return nil, fmt.Errorf("session not found: %s", sessionID)
	}

	status := session.status
	return &status, nil
}

// ListSessions returns all active decoding sessions.
func (s *Service) ListSessions() []DecodeStatus {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var statuses []DecodeStatus
	for _, session := range s.sessions {
		statuses = append(statuses, session.status)
	}
	return statuses
}

// Stats returns decoder service statistics.
func (s *Service) Stats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var totalFrames, totalDropped int64
	for _, session := range s.sessions {
		totalFrames += session.status.FramesTotal
		totalDropped += session.status.FramesDropped
	}

	return map[string]interface{}{
		"active_sessions": len(s.sessions),
		"total_frames":    totalFrames,
		"dropped_frames":  totalDropped,
	}
}

// decodeLoop is the main decoding loop (runs in a goroutine).
func (s *Service) decodeLoop(ctx context.Context, req DecodeRequest, session *decodeSession) {
	defer s.logger.Info("Decode session ended", zap.String("session_id", session.status.SessionID))

	// In production: use FFmpeg CGO bindings or exec ffmpeg process
	// For now: simulate frame generation
	fps := float64(req.MaxFPS)
	if fps <= 0 {
		fps = 25.0
	}

	resolution := req.Resolution
	if resolution == "" {
		resolution = "1920x1080"
	}

	ticker := time.NewTicker(time.Duration(1000.0/fps) * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			session.status.FramesTotal++
			// Simulate frame processing
			_ = resolution // used for frame sizing
		}
	}
}
