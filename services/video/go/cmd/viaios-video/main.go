// viaios-video: High-performance video processing service (P2-3)
// Handles video decoding, structuring, RTSP/HLS streaming, GB28181 ingestion.
// Port: 8093 | Language: Go | Tier: Access
package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/viaios/video/internal/api"
	"github.com/viaios/video/internal/decoder"
	"github.com/viaios/video/internal/stream"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

var (
	Version   = "4.0.0"
	BuildTime = "2026-08-02"
)

func main() {
	// Logger
	cfg := zap.NewProductionConfig()
	cfg.EncoderConfig.TimeKey = "timestamp"
	cfg.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
	logger, _ := cfg.Build()
	defer logger.Sync()
	zap.ReplaceGlobals(logger)

	logger.Info("VIAIOS Video Service starting",
		zap.String("version", Version),
		zap.String("build", BuildTime))

	// Core components
	decoderSvc := decoder.NewService(logger)
	streamMgr := stream.NewManager(logger, decoderSvc)

	// Start stream manager
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go streamMgr.Run(ctx)

	// HTTP server
	router := gin.New()
	router.Use(gin.LoggerWithWriter(os.Stdout), gin.Recovery())

	// Health
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":  "UP",
			"service": "viaios-video",
			"version": Version,
			"streams": streamMgr.ActiveStreams(),
			"uptime":  time.Now().Unix(),
		})
	})
	router.GET("/actuator/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "UP"})
	})

	// Metrics
	router.GET("/actuator/prometheus", gin.WrapH(promhttp.Handler()))

	// API routes
	api.RegisterRoutes(router, streamMgr, decoderSvc)

	// Server
	port := getEnv("VIDEO_PORT", "8093")
	srv := &http.Server{
		Addr:         ":" + port,
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 60 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Graceful shutdown
	go func() {
		quit := make(chan os.Signal, 1)
		signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
		<-quit
		logger.Info("Shutting down...")
		cancel()
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		srv.Shutdown(ctx)
	}()

	logger.Info("Listening", zap.String("port", port))
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		logger.Fatal("Server failed", zap.Error(err))
	}
}

func getEnv(key, defaultVal string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultVal
}
