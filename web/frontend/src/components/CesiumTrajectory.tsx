/**
 * CesiumTrajectory — 3D Globe trajectory visualization (P1-5)
 *
 * Replaces 2D Leaflet map with Cesium 3D globe.
 * Falls back gracefully if cesium package is not installed.
 *
 * Install: npm install cesium (optional — falls back to 2D indicator)
 */
import React, { useEffect, useRef, useState } from 'react';
import { Card, Button, Space, Slider, Select, Tag, Spin } from 'antd';
import {
  PlayCircleOutlined, PauseCircleOutlined, AimOutlined,
  SwapOutlined, GlobalOutlined,
} from '@ant-design/icons';

// ── Types ─────────────────────────────────────────────────────────

interface TrajectoryPoint {
  id: string;
  targetId: string;
  cameraId?: string;
  cameraName?: string;
  longitude: number;
  latitude: number;
  altitude?: number;
  timestamp: string;
  confidence?: number;
  label?: string;
}

interface TrajectoryTrack {
  targetId: string;
  color: string;
  points: TrajectoryPoint[];
}

interface Props {
  tracks: TrajectoryTrack[];
  height?: string;
}

const TRACK_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
];

const DEFAULT_VIEW = { longitude: 121.4737, latitude: 31.2304, height: 5000 };

// ── Component ──────────────────────────────────────────────────────

const CesiumTrajectory: React.FC<Props> = ({ tracks, height = '600px' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);
  const [loaded, setLoaded] = useState(false);
  const [cesiumAvailable, setCesiumAvailable] = useState(false);
  const [, setPlaying] = useState(false);
  const [currentIdx] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [selectedTrack, setSelectedTrack] = useState<string | null>(null);
  const [showAllTracks, setShowAllTracks] = useState(true);

  // Helper to dynamically import cesium (bypasses Rollup analysis)
  const loadCesium = (): Promise<any> => {
    return new Function('return import("cesium")')();
  };

  // ── Initialize Cesium ─────────────────────────────────────────

  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return;

    loadCesium().then((Cesium: any) => {
      if (!containerRef.current) return;

      try {
        const viewer = new Cesium.Viewer(containerRef.current, {
          animation: false,
          timeline: false,
          fullscreenButton: false,
          homeButton: true,
          sceneModePicker: true,
          navigationHelpButton: false,
          geocoder: false,
          baseLayerPicker: false,
          imageryProvider: new Cesium.UrlTemplateImageryProvider({
            url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            maximumLevel: 18,
          }),
        });

        viewer.scene.globe.enableLighting = true;
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(
            DEFAULT_VIEW.longitude, DEFAULT_VIEW.latitude, DEFAULT_VIEW.height
          ),
          orientation: { heading: 0, pitch: -0.5, roll: 0 },
          duration: 2,
        });

        viewerRef.current = viewer;
        setCesiumAvailable(true);
        setLoaded(true);
      } catch (e) {
        console.warn('Cesium init failed, using fallback', e);
        setLoaded(true);
      }
    }).catch(() => {
      console.info('Cesium not installed — using 2D fallback');
      setLoaded(true);
    });

    return () => {
      if (viewerRef.current && !viewerRef.current.isDestroyed?.()) {
        viewerRef.current.destroy?.();
        viewerRef.current = null;
      }
    };
  }, []);

  // ── Render Tracks ─────────────────────────────────────────────

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !cesiumAvailable) return;

    loadCesium().then((Cesium: any) => {
      if (!viewer || viewer.isDestroyed?.()) return;
      viewer.entities?.removeAll();

      const visibleTracks = selectedTrack
        ? tracks.filter(t => t.targetId === selectedTrack)
        : showAllTracks ? tracks : [];

      visibleTracks.forEach((track: TrajectoryTrack, trackIdx: number) => {
        const color = track.color || TRACK_COLORS[trackIdx % TRACK_COLORS.length];

        if (track.points.length > 1) {
          viewer.entities?.add({
            polyline: {
              positions: Cesium.Cartesian3.fromDegreesArray(
                track.points.flatMap((p: TrajectoryPoint) => [p.longitude, p.latitude])
              ),
              width: 3,
              material: Cesium.Color.fromCssColorString(color)?.withAlpha(0.7),
              clampToGround: true,
            },
          });
        }

        track.points.forEach((point: TrajectoryPoint, i: number) => {
          viewer.entities?.add({
            position: Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, point.altitude || 0),
            point: {
              pixelSize: 6,
              color: Cesium.Color.fromCssColorString(color),
              outlineColor: Cesium.Color.WHITE,
              outlineWidth: 1,
            },
            label: {
              text: point.cameraName || `P${i + 1}`,
              font: '12px sans-serif',
              fillColor: Cesium.Color.WHITE,
              showBackground: true,
              backgroundColor: Cesium.Color.BLACK?.withAlpha(0.7),
              verticalOrigin: Cesium.VerticalOrigin?.BOTTOM,
              pixelOffset: new Cesium.Cartesian2(0, -10),
            },
          });
        });
      });

      if (visibleTracks.length > 0) {
        const allPoints = visibleTracks.flatMap((t: TrajectoryTrack) => t.points);
        viewer.camera?.flyTo({
          destination: Cesium.Rectangle.fromDegrees(
            Math.min(...allPoints.map((p: TrajectoryPoint) => p.longitude)) - 0.01,
            Math.min(...allPoints.map((p: TrajectoryPoint) => p.latitude)) - 0.01,
            Math.max(...allPoints.map((p: TrajectoryPoint) => p.longitude)) + 0.01,
            Math.max(...allPoints.map((p: TrajectoryPoint) => p.latitude)) + 0.01,
          ),
          duration: 1.5,
        });
      }
    });
  }, [tracks, cesiumAvailable, selectedTrack, showAllTracks, currentIdx]);

  // ── Render ────────────────────────────────────────────────────

  return (
    <Card
      title={
        <Space>
          <GlobalOutlined />
          <span>3D 轨迹回放</span>
          {tracks.length > 0 && <Tag color="blue">{tracks.length} 条轨迹</Tag>}
          {!cesiumAvailable && loaded && <Tag color="orange">2D 模式</Tag>}
        </Space>
      }
      extra={
        <Space>
          <Select
            size="small" style={{ width: 130 }} placeholder="选择目标" allowClear
            value={selectedTrack}
            onChange={(v: any) => { setSelectedTrack(v); setShowAllTracks(!v); }}
            options={tracks.map(t => ({ label: t.targetId, value: t.targetId }))}
          />
          <Button size="small" icon={<SwapOutlined />}
            onClick={() => setShowAllTracks(!showAllTracks)}>
            {showAllTracks ? '全部' : '单选'}
          </Button>
          <Button size="small" type="primary"
            icon={false ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() => setPlaying((p: boolean) => !p)}>
            {false ? '暂停' : '播放'}
          </Button>
          <Button size="small" icon={<AimOutlined />}
            onClick={() => {
              const v = viewerRef.current;
              if (v && !v.isDestroyed?.()) {
                import('cesium').then((C: any) => {
                  v.camera?.flyTo({
                    destination: C.Cartesian3.fromDegrees(
                      DEFAULT_VIEW.longitude, DEFAULT_VIEW.latitude, 10000
                    ),
                    duration: 2,
                  });
                });
              }
            }}>
            复位
          </Button>
          <Slider style={{ width: 100, margin: '0 8px' }}
            min={0.5} max={5} step={0.5} value={speed}
            onChange={(v: number) => setSpeed(v)}
            tooltip={{ formatter: (v?: number) => `${v}x` }}
          />
        </Space>
      }
      styles={{ body: { padding: 0 } }}
    >
      <div ref={containerRef} style={{
        width: '100%', height, background: '#1a1a2e',
        borderRadius: '0 0 8px 8px',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {!loaded && (
          <Spin tip="加载 Cesium 3D 引擎..." />
        )}
        {loaded && !cesiumAvailable && (
          <span style={{ color: '#888' }}>
            3D 地球组件需要安装 cesium 依赖: npm install cesium
          </span>
        )}
      </div>
    </Card>
  );
};

export default CesiumTrajectory;
