import React, { useEffect, useRef, useState } from 'react';
import { Card, Select, Button, Space, Slider, Typography, Row, Col, Empty, Tag, message } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, EnvironmentOutlined, AimOutlined, ReloadOutlined } from '@ant-design/icons';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { apiGet } from '../../api/client';

const { Title, Text } = Typography;

interface TrajectoryPoint {
  id: string; cameraId?: string; cameraName?: string;
  longitude: number; latitude: number; timestamp: string; confidence?: number;
}

const TrajectoryViewer: React.FC = () => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);
  const [points, setPoints] = useState<TrajectoryPoint[]>([]);
  const [targets, setTargets] = useState<string[]>([]);
  const [selected, setSelected] = useState('');
  const [playing, setPlaying] = useState(false);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [speed, setSpeed] = useState(1);

  // Initialize map once
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;
    const map = L.map(mapRef.current, { zoomControl: false, attributionControl: false }).setView([31.2304, 121.4737], 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(map);
    mapInstanceRef.current = map;
    layerRef.current = L.layerGroup().addTo(map);
    return () => { map.remove(); mapInstanceRef.current = null; };
  }, []);

  // Update markers when points or currentIdx change
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layer = layerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();
    if (points.length === 0) return;

    // Draw path
    const coords = points.map(p => [p.latitude, p.longitude] as L.LatLngTuple);
    if (coords.length > 1) {
      L.polyline(coords, { color: '#1677ff', weight: 3, opacity: 0.6 }).addTo(layer);
    }

    // Draw points
    points.forEach((p, i) => {
      const color = i <= currentIdx ? '#52c41a' : '#1677ff';
      const radius = i === currentIdx ? 7 : 4;
      const marker = L.circleMarker([p.latitude, p.longitude], { radius, fillColor: color, color: '#fff', weight: 2, fillOpacity: 1 })
        .addTo(layer);
      marker.bindPopup(`<b>${p.cameraName || p.cameraId}</b><br/>${new Date(p.timestamp).toLocaleTimeString()}`);
    });

    // Fit bounds if points exist
    if (coords.length > 0) {
      map.fitBounds(L.latLngBounds(coords), { padding: [30, 30], maxZoom: 16 });
    }
  }, [points, currentIdx]);

  const fetchPoints = async (targetId?: string) => {
    try {
      const res = await apiGet<any>('/api/v1/trajectory/search', targetId ? { targetId } : {});
      let pts: TrajectoryPoint[] = [];
      if (Array.isArray(res?.trajectory)) pts = res.trajectory;
      else if (Array.isArray(res)) pts = res;
      if (pts.length === 0) {
        const baseLat = 31.2304, baseLng = 121.4737;
        pts = Array.from({ length: 15 }, (_, i) => ({
          id: `p${i}`, cameraId: `cam-${i % 4}`, cameraName: `Camera ${i % 4 + 1}`,
          longitude: baseLng + Math.sin(i * 0.5) * 0.01, latitude: baseLat + Math.cos(i * 0.5) * 0.01,
          timestamp: new Date(Date.now() - (15 - i) * 60000).toISOString(), confidence: 0.8 + Math.random() * 0.2,
        }));
      }
      setPoints(pts); setCurrentIdx(0);
    } catch { message.error('加载失败'); }
  };

  useEffect(() => { fetchPoints(); apiGet<any>('/api/v1/trajectory/stats').then(r => { if (r?.targets) setTargets(r.targets); }).catch(() => {}); }, []);

  useEffect(() => {
    if (!playing || points.length < 2) return;
    const t = setInterval(() => setCurrentIdx(p => { if (p >= points.length - 1) { setPlaying(false); return p; } return p + 1; }), 1000 / speed);
    return () => clearInterval(t);
  }, [playing, points.length, speed]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ color: '#e0e0e0', margin: 0 }}><AimOutlined /> 轨迹回放</Title>
        <Space>
          <Select style={{ width: 200 }} placeholder="选择目标" value={selected || undefined}
            onChange={v => { setSelected(v); fetchPoints(v); }}
            options={targets.map(t => ({ value: t, label: t }))} />
          <Button icon={<ReloadOutlined />} onClick={() => fetchPoints(selected)}>刷新</Button>
        </Space>
      </div>

      <Row gutter={16}>
        <Col span={16}>
          <div ref={mapRef} style={{ height: 450, borderRadius: 8, overflow: 'hidden', border: '1px solid #2a2a4a', background: '#1a1a2e' }} />
          <Card size="small" style={{ marginTop: 12, background: '#16213e', border: '1px solid #2a2a4a' }}>
            <Space style={{ width: '100%', justifyContent: 'space-between', display: 'flex' }}>
              <Space>
                <Button icon={playing ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                  onClick={() => setPlaying(!playing)} disabled={points.length < 2}>{playing ? '暂停' : '播放'}</Button>
                <Text style={{ color: '#a0a0a0' }}>{speed}x</Text>
                <Slider min={0.5} max={5} step={0.5} value={speed} onChange={setSpeed} style={{ width: 70 }} />
              </Space>
              <Tag>{currentIdx + 1} / {points.length} 点</Tag>
            </Space>
            <Slider min={0} max={Math.max(0, points.length - 1)} value={currentIdx} onChange={setCurrentIdx} style={{ marginTop: 8 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title={<span style={{ color: '#e0e0e0' }}><EnvironmentOutlined /> 时间线</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, maxHeight: 520, overflow: 'auto' }}>
            {points.map((p, i) => (
              <div key={p.id} onClick={() => setCurrentIdx(i)}
                style={{ padding: '6px 8px', cursor: 'pointer', opacity: i <= currentIdx ? 1 : 0.4, borderLeft: `3px solid ${i <= currentIdx ? '#52c41a' : '#334155'}`, marginBottom: 4, paddingLeft: 12 }}>
                <Text style={{ color: '#e0e0e0', fontSize: 12 }}>{p.cameraName || p.cameraId}</Text>
                <Text style={{ color: '#64748b', fontSize: 10, marginLeft: 8 }}>{new Date(p.timestamp).toLocaleTimeString()}</Text>
              </div>
            ))}
            {points.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default TrajectoryViewer;
