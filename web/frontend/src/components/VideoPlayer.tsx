import { useEffect, useRef, useState, useCallback, useImperativeHandle, forwardRef } from 'react';
import { Button, Space, Slider, Spin, Typography } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, ExpandOutlined, CompressOutlined, CameraOutlined, SoundOutlined, ReloadOutlined } from '@ant-design/icons';
import Hls from 'hls.js';

const { Text } = Typography;

interface AnalysisBox { x: number; y: number; w: number; h: number; label: string; confidence: number; }

export interface VideoPlayerProps {
  streamUrl?: string;
  poster?: string;
  analysisBoxes?: AnalysisBox[];
  onSnapshot?: (dataUrl: string) => void;
  autoPlay?: boolean;
  muted?: boolean;
  height?: number;
}

export interface VideoPlayerRef {
  pause: () => void;
  play: () => void;
  takeSnapshot: () => string | null;
}

const VideoPlayer = forwardRef<VideoPlayerRef, VideoPlayerProps>(({
  streamUrl, poster, analysisBoxes = [], onSnapshot, autoPlay = true, muted = true, height = 500,
}, ref) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [volume, setVolume] = useState(muted ? 0 : 1);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const animFrameRef = useRef<number>();

  // Initialize HLS
  useEffect(() => {
    if (!streamUrl || !videoRef.current) return;
    setLoading(true); setError(null);
    const video = videoRef.current;

    if (Hls.isSupported()) {
      const hls = new Hls({ enableWorker: false, lowLatencyMode: true });
      hls.loadSource(streamUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setLoading(false);
        if (autoPlay) video.play().catch(() => { });
      });
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) { setError('视频流加载失败'); setLoading(false); }
      });
      return () => { hls.destroy(); };
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = streamUrl;
      video.addEventListener('loadedmetadata', () => setLoading(false));
      if (autoPlay) video.play().catch(() => { });
      return () => { video.src = ''; };
    } else {
      setError('浏览器不支持 HLS 播放');
      setLoading(false);
    }
  }, [streamUrl, autoPlay]);

  // Video event handlers
  const onPlay = useCallback(() => setPlaying(true), []);
  const onPause = useCallback(() => setPlaying(false), []);
  const onTimeUpdate = useCallback(() => { if (videoRef.current) setCurrentTime(videoRef.current.currentTime); }, []);
 const onLoadedMetadata = useCallback(() => { if (videoRef.current) setDuration(videoRef.current.duration); }, []);

  useEffect(() => {
    const v = videoRef.current; if (!v) return;
    v.addEventListener('play', onPlay); v.addEventListener('pause', onPause);
    v.addEventListener('timeupdate', onTimeUpdate); v.addEventListener('loadedmetadata', onLoadedMetadata);
    return () => { v.removeEventListener('play', onPlay); v.removeEventListener('pause', onPause); v.removeEventListener('timeupdate', onTimeUpdate); v.removeEventListener('loadedmetadata', onLoadedMetadata); };
  }, [onPlay, onPause, onTimeUpdate, onLoadedMetadata]);

  // Analysis overlay animation
  useEffect(() => {
    if (!canvasRef.current || !videoRef.current) return;
    const ctx = canvasRef.current.getContext('2d'); if (!ctx) return;
    const draw = () => {
      ctx.clearRect(0, 0, canvasRef.current!.width, canvasRef.current!.height);
      analysisBoxes.forEach(box => {
        ctx.strokeStyle = box.confidence > 0.9 ? '#52c41a' : box.confidence > 0.7 ? '#faad14' : '#ff4d4f';
        ctx.lineWidth = 2;
        ctx.strokeRect(box.x, box.y, box.w, box.h);
        ctx.fillStyle = ctx.strokeStyle + '22'; ctx.fillRect(box.x, box.y, box.w, box.h);
        ctx.fillStyle = '#fff'; ctx.font = '11px sans-serif';
        ctx.fillText(`${box.label} ${Math.round(box.confidence * 100)}%`, box.x + 2, box.y - 4);
      });
      animFrameRef.current = requestAnimationFrame(draw);
    };
    animFrameRef.current = requestAnimationFrame(draw);
    return () => { if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current); };
  }, [analysisBoxes]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const v = videoRef.current; if (!v) return;
      if (e.key === ' ') { e.preventDefault(); v.paused ? v.play() : v.pause(); }
      if (e.key === 'f') toggleFullscreen();
      if (e.key === 'm') { const newVol = v.muted ? 1 : 0; v.muted = !v.muted; setVolume(newVol); }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  const togglePlay = () => { const v = videoRef.current; if (!v) return; v.paused ? v.play() : v.pause(); };
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) { containerRef.current.requestFullscreen(); setFullscreen(true); }
    else { document.exitFullscreen(); setFullscreen(false); }
  };
  const handleVolumeChange = (v: number) => { setVolume(v); if (videoRef.current) { videoRef.current.volume = v; videoRef.current.muted = v === 0; } };
  const handleSeek = (val: number) => { if (videoRef.current) { videoRef.current.currentTime = val; setCurrentTime(val); } };

  const takeSnapshot = useCallback(() => {
    if (!videoRef.current) return null;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth; canvas.height = videoRef.current.videoHeight;
    canvas.getContext('2d')?.drawImage(videoRef.current, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    onSnapshot?.(dataUrl); return dataUrl;
  }, [onSnapshot]);

  useImperativeHandle(ref, () => ({
    pause: () => videoRef.current?.pause(),
    play: () => videoRef.current?.play(),
    takeSnapshot,
  }), [takeSnapshot]);

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${Math.floor(s % 60).toString().padStart(2, '0')}`;

  return (
    <div ref={containerRef} style={{ position: 'relative', background: '#000', borderRadius: 8, overflow: 'hidden', height }}>
      {loading && <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2 }}><Spin size="large" /></div>}
      {error && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', zIndex: 2, color: '#fff' }}>
          <Text style={{ color: '#f87171' }}>{error}</Text>
          <Button icon={<ReloadOutlined />} onClick={() => { setError(null); setLoading(true); if (videoRef.current) videoRef.current.load(); }} style={{ marginTop: 8 }}>重试</Button>
        </div>
      )}
      <video ref={videoRef} style={{ width: '100%', height: '100%', objectFit: 'contain' }} muted={muted} playsInline poster={poster} />
      <canvas ref={canvasRef} style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }} />
      {/* Controls */}
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, background: 'linear-gradient(transparent, rgba(0,0,0,0.8))', padding: '32px 12px 8px', opacity: playing ? 0 : 1, transition: 'opacity 0.3s' }}
        onMouseEnter={e => (e.currentTarget.style.opacity = '1')} onMouseLeave={e => playing && (e.currentTarget.style.opacity = '0')}>
        <Slider min={0} max={duration || 100} value={currentTime} onChange={handleSeek} style={{ margin: 0 }} tooltip={{ formatter: (v) => formatTime(v || 0) }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
          <Space size="small">
            <Button type="text" size="small" icon={playing ? <PauseCircleOutlined /> : <PlayCircleOutlined />} onClick={togglePlay} style={{ color: '#fff' }} />
            <Button type="text" size="small" icon={<CameraOutlined />} onClick={takeSnapshot} style={{ color: '#fff' }} />
            <Button type="text" size="small" icon={<SoundOutlined />} style={{ color: '#fff' }} onClick={() => handleVolumeChange(volume > 0 ? 0 : 1)} />
            <Slider min={0} max={1} step={0.1} value={volume} onChange={handleVolumeChange} style={{ width: 60 }} />
            <Text style={{ color: '#fff', fontSize: 12 }}>{formatTime(currentTime)} / {formatTime(duration)}</Text>
          </Space>
          <Button type="text" size="small" icon={fullscreen ? <CompressOutlined /> : <ExpandOutlined />} onClick={toggleFullscreen} style={{ color: '#fff' }} />
        </div>
      </div>
    </div>
  );
});

export default VideoPlayer;
