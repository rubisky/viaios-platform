/**
 * CesiumTrajectory — 3D Globe trajectory visualization
 * Uses CesiumJS for real 3D terrain rendering with camera fly-to animation.
 */
import React, { useEffect, useRef, useState } from 'react';
import { Card, Button, Space, Slider, Select, Tag, Spin } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, AimOutlined, SwapOutlined, GlobalOutlined } from '@ant-design/icons';
import * as Cesium from 'cesium';

// ── Types ─────────────────────────────────────────────────────────

interface TrajectoryPoint {
  id: string; targetId: string; cameraId?: string; cameraName?: string;
  longitude: number; latitude: number; altitude?: number; timestamp: string; label?: string;
}

interface TrajectoryTrack { targetId: string; color: string; points: TrajectoryPoint[]; }

interface Props { tracks: TrajectoryTrack[]; height?: string; }

const TRACK_COLORS = ['#FF6B6B','#4ECDC4','#45B7D1','#96CEB4','#FFEAA7','#DDA0DD'];

const CesiumTrajectory: React.FC<Props> = ({ tracks, height = '600px' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const [ready, setReady] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [, setCurrentIdx] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [selectedTrack, setSelectedTrack] = useState<string | null>(null);
  const [showAllTracks, setShowAllTracks] = useState(true);

  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return;
    const viewer = new Cesium.Viewer(containerRef.current, {
      animation: false, timeline: false, fullscreenButton: false,
      homeButton: true, sceneModePicker: true, navigationHelpButton: false,
      geocoder: false, baseLayerPicker: false,
      imageryProvider: new Cesium.UrlTemplateImageryProvider({
        url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', maximumLevel: 18,
      }),
    });
    viewer.scene.globe.enableLighting = true;
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(121.4737, 31.2304, 5000),
      orientation: { heading: 0, pitch: -0.5, roll: 0 }, duration: 2,
    });
    viewerRef.current = viewer;
    setReady(true);
    return () => { if (!viewer.isDestroyed()) viewer.destroy(); };
  }, []);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !ready) return;
    viewer.entities.removeAll();

    const visibleTracks = selectedTrack
      ? tracks.filter(t => t.targetId === selectedTrack)
      : showAllTracks ? tracks : [];

    visibleTracks.forEach((track, i) => {
      const color = track.color || TRACK_COLORS[i % TRACK_COLORS.length];
      if (track.points.length > 1) {
        viewer.entities.add({
          polyline: {
            positions: Cesium.Cartesian3.fromDegreesArray(
              track.points.flatMap(p => [p.longitude, p.latitude])),
            width: 3, clampToGround: true,
            material: Cesium.Color.fromCssColorString(color).withAlpha(0.7),
          },
        });
      }
      track.points.forEach((point, j) => {
        viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, point.altitude || 0),
          point: { pixelSize: 6, color: Cesium.Color.fromCssColorString(color), outlineColor: Cesium.Color.WHITE, outlineWidth: 1 },
          label: { text: point.cameraName || `P${j+1}`, font: '12px sans-serif', fillColor: Cesium.Color.WHITE,
            showBackground: true, backgroundColor: Cesium.Color.BLACK.withAlpha(0.7),
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM, pixelOffset: new Cesium.Cartesian2(0, -10) },
        });
      });
    });
  }, [tracks, ready, selectedTrack, showAllTracks]);

  useEffect(() => {
    if (!playing) return;
    const allPoints = tracks.flatMap(t => t.points);
    if (!allPoints.length) return;
    const timer = setInterval(() => {
      setCurrentIdx(prev => {
        const next = prev + 1;
        if (next >= allPoints.length) { setPlaying(false); return 0; }
        const pt = allPoints[next];
        viewerRef.current?.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(pt.longitude, pt.latitude, 500), duration: 0.5,
        });
        return next;
      });
    }, 1000 / speed);
    return () => clearInterval(timer);
  }, [playing, speed, tracks]);

  return (
    <Card
      title={<Space><GlobalOutlined /><span>3D 轨迹回放</span>{tracks.length > 0 && <Tag color="blue">{tracks.length} 条轨迹</Tag>}</Space>}
      extra={<Space>
        <Select size="small" style={{ width: 130 }} placeholder="选择目标" allowClear value={selectedTrack}
          onChange={(v: any) => { setSelectedTrack(v); setShowAllTracks(!v); }}
          options={tracks.map(t => ({ label: t.targetId, value: t.targetId }))} />
        <Button size="small" icon={<SwapOutlined />} onClick={() => setShowAllTracks(!showAllTracks)}>{showAllTracks ? '全部' : '单选'}</Button>
        <Button size="small" type="primary" icon={playing ? <PauseCircleOutlined /> : <PlayCircleOutlined />} onClick={() => setPlaying(!playing)}>{playing ? '暂停' : '播放'}</Button>
        <Button size="small" icon={<AimOutlined />} onClick={() => viewerRef.current?.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(121.4737, 31.2304, 10000), duration: 2 })}>复位</Button>
        <Slider style={{ width: 100 }} min={0.5} max={5} step={0.5} value={speed} onChange={setSpeed} tooltip={{ formatter: (v?: number) => `${v}x` }} />
      </Space>}
      styles={{ body: { padding: 0 } }}>
      <div ref={containerRef} style={{ width: '100%', height, background: '#1a1a2e', borderRadius: '0 0 8px 8px' }}>
        {!ready && <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#888' }}><Spin tip="加载 3D 引擎..." /></div>}
      </div>
    </Card>
  );
};

export default CesiumTrajectory;
