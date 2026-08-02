// API routes for the video service.
package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/viaios/video/internal/decoder"
	"github.com/viaios/video/internal/stream"
)

// RegisterRoutes registers all API routes.
func RegisterRoutes(router *gin.Engine, streamMgr *stream.Manager, decoderSvc *decoder.Service) {
	// ── Stream Management ──────────────────────────────────────
	api := router.Group("/api/v1/video")
	{
		// List all streams
		api.GET("/streams", func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{
				"total":   len(streamMgr.ListStreams()),
				"streams": streamMgr.ListStreams(),
			})
		})

		// Get stream detail
		api.GET("/streams/:id", func(c *gin.Context) {
			s, err := streamMgr.GetStream(c.Param("id"))
			if err != nil {
				c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, s)
		})

		// Add a new stream
		api.POST("/streams", func(c *gin.Context) {
			var req stream.StreamRequest
			if err := c.ShouldBindJSON(&req); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
				return
			}
			if req.MaxFPS == 0 {
				req.MaxFPS = 25
			}
			if req.Resolution == "" {
				req.Resolution = "1920x1080"
			}
			s, err := streamMgr.AddStream(req)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusCreated, s)
		})

		// Remove a stream
		api.DELETE("/streams/:id", func(c *gin.Context) {
			if err := streamMgr.RemoveStream(c.Param("id")); err != nil {
				c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{"status": "removed"})
		})

		// Stream statistics
		api.GET("/stats", func(c *gin.Context) {
			c.JSON(http.StatusOK, streamMgr.Stats())
		})
	}

	// ── Decoder Management ─────────────────────────────────────
	dec := router.Group("/api/v1/video/decoder")
	{
		// List decode sessions
		dec.GET("/sessions", func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{
				"sessions": decoderSvc.ListSessions(),
				"stats":    decoderSvc.Stats(),
			})
		})

		// Start a decode session
		dec.POST("/sessions", func(c *gin.Context) {
			var req decoder.DecodeRequest
			if err := c.ShouldBindJSON(&req); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
				return
			}
			status, err := decoderSvc.Start(c.Request.Context(), req)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusCreated, status)
		})

		// Get decode session status
		dec.GET("/sessions/:id", func(c *gin.Context) {
			status, err := decoderSvc.Status(c.Param("id"))
			if err != nil {
				c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, status)
		})

		// Stop a decode session
		dec.DELETE("/sessions/:id", func(c *gin.Context) {
			if err := decoderSvc.Stop(c.Param("id")); err != nil {
				c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{"status": "stopped"})
		})
	}

	// ── RTSP Proxy ─────────────────────────────────────────────
	api.POST("/rtsp/proxy", func(c *gin.Context) {
		var req struct {
			SourceURI string `json:"source_uri" binding:"required"`
			MaxFPS    int    `json:"max_fps"`
		}
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		if req.MaxFPS == 0 {
			req.MaxFPS = 15
		}
		stream, err := streamMgr.AddStream(stream.StreamRequest{
			Name:      "rtsp-proxy",
			Type:      stream.StreamRTSP,
			SourceURI: req.SourceURI,
			MaxFPS:    req.MaxFPS,
		})
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusCreated, gin.H{
			"stream_id": stream.ID,
			"hls_url":   "/api/v1/video/hls/" + stream.ID + "/index.m3u8",
			"ws_url":    "ws://localhost:8093/api/v1/video/ws/" + stream.ID,
		})
	})
}
