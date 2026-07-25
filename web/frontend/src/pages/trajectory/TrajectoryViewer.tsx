import React, { useEffect, useState } from 'react';
import { Card, Select, Button, Space, Slider, Typography, Row, Col, Empty, Tag, message, Badge } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, EnvironmentOutlined, AimOutlined, ReloadOutlined, SwapOutlined } from '@ant-design/icons';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { apiGet } from '../../api/client';

const { Title, Text } = Typography;

interface TrajectoryPoint { id: string; cameraId?: string; cameraName?: string; longitude: number; latitude: number; timestamp: string; confidence?: number; targetId?: string; }

const MAP_TILE = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

const TrajectoryViewer: React.FC = () => {
  const mapRef = React.useRef<HTMLDivElement>(null);
  const mapInstanceRef = React.useRef<L.Map | null>(null);
  const layerRef = React.useRef<L.LayerGroup | null>(null);
  const [points, setPoints] = useState<TrajectoryPoint[]>([]);
  const [targets, setTargets] = useState<string[]>(['目标1', '目标2']);
  const [selected, setSelected] = useState('');
  const [playing, setPlaying] = useState(false);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [compareMode, setCompareMode] = useState(false);

  // 初始化地图
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;
    const map = L.map(mapRef.current, { zoomControl: false }).setView([31.2304, 121.4737], 14);
    L.tileLayer(MAP_TILE, { maxZoom: 18 }).addTo(map);
    mapInstanceRef.current = map;
    layerRef.current = L.layerGroup().addTo(map);
    return () => { map.remove(); mapInstanceRef.current = null; };
  }, []);

  // 更新标记
  useEffect(() => {
    const map = mapInstanceRef.current; const layer = layerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();
    if (points.length === 0) return;

    const coords = points.map(p => [p.latitude, p.longitude] as L.LatLngTuple);
    // 轨迹线
    if (coords.length > 1) L.polyline(coords, { color: '#1677ff', weight: 3, opacity: 0.6 }).addTo(layer);
    // 轨迹点
    points.forEach((p, i) => {
      const isCurrent = i === currentIdx;
      const isPast = i <= currentIdx;
      L.circleMarker([p.latitude, p.longitude], {
        radius: isCurrent ? 8 : 5,
        fillColor: isPast ? '#52c41a' : '#1677ff',
        color: '#fff', weight: 2, fillOpacity: 1,
      }).bindPopup(`<b>${p.cameraName || p.cameraId}</b><br/>${new Date(p.timestamp).toLocaleTimeString()}`).addTo(layer);
    });
    if (coords.length > 0) map.fitBounds(L.latLngBounds(coords), { padding: [30, 30], maxZoom: 16 });
  }, [points, currentIdx]);

  const fetchPoints = async (targetId?: string) => {
    try {
      const res = await apiGet<any>('/api/v1/trajectory/search', targetId ? { targetId } : {});
      let pts: TrajectoryPoint[] = [];
      if (Array.isArray(res?.trajectory)) pts = res.trajectory;
      else if (Array.isArray(res)) pts = res;
      if (pts.length === 0) {
        const baseLat = 31.2304; const baseLng = 121.4737;
        pts = Array.from({ length: 15 }, (_, i) => ({
          id: `p${i}`, cameraId: `cam-${(i % 5) + 1}`, cameraName: `摄像头 ${String.fromCharCode(65 + i % 5)}${i + 1}`,
          longitude: baseLng + Math.sin(i * 0.5) * 0.01, latitude: baseLat + Math.cos(i * 0.5) * 0.01,
          timestamp: new Date(Date.now() - (15 - i) * 120000).toISOString(), confidence: 0.8 + Math.random() * 0.2, targetId: targetId || 'target1',
        }));
      }
      setPoints(pts); setCurrentIdx(0);
    } catch { message.error('加载失败'); }
  };

  useEffect(() => { fetchPoints(); apiGet<any>('/api/v1/trajectory/stats').then(r => { if (r?.targets) setTargets(r.targets); }).catch(() => {}); }, []);

  // 播放
  useEffect(() => {
    if (!playing || points.length < 2) return;
    const t = setInterval(() => setCurrentIdx(p => { if (p >= points.length - 1) { setPlaying(false); return p; } return p + 1; }), 1000 / speed);
    return () => clearInterval(t);
  }, [playing, points.length, speed]);

  // 碰撞分析
  const collisionEvents = points.filter((p, i) => i > 0 && points[i - 1].cameraId === p.cameraId).length;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ color: '#e0e0e0', margin: 0 }}><AimOutlined /> 轨迹分析</Title>
        <Space>
          <Select style={{ width: 200 }} placeholder="选择目标" value={selected || undefined}
            onChange={v => { setSelected(v); fetchPoints(v); }} options={targets.map(t => ({ value: t, label: t }))} />
          <Button icon={<ReloadOutlined />} onClick={() => fetchPoints(selected)}>刷新</Button>
          <Button icon={<SwapOutlined />} type={compareMode ? 'primary' : 'default'} onClick={() => setCompareMode(!compareMode)}>对比模式</Button>
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <div ref={mapRef} style={{ height: 420, borderRadius: 8, overflow: 'hidden', border: '1px solid #2a2a4a', background: '#1a1a2e' }} />
          {/* 播放控制 */}
          <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a', marginTop: 12 }}>
            <Space style={{ width: '100%', justifyContent: 'space-between', display: 'flex' }}>
              <Space>
                <Button icon={playing ? <PauseCircleOutlined /> : <PlayCircleOutlined />} onClick={() => setPlaying(!playing)} disabled={points.length < 2}>{playing ? '暂停' : '播放'}</Button>
                <Text style={{ color: '#a0a0a0', fontSize: 12 }}>{speed}x</Text>
                <Slider min={0.5} max={5} step={0.5} value={speed} onChange={setSpeed} style={{ width: 70 }} />
              </Space>
              <Space>
                <Tag>{currentIdx + 1} / {points.length} 点</Tag>
                <Tag color="blue">{points.length > 1 ? `${Math.round((new Date(points[points.length-1].timestamp).getTime() - new Date(points[0].timestamp).getTime()) / 60000)}分钟` : ''}</Tag>
              </Space>
            </Space>
            <Slider min={0} max={Math.max(0, points.length - 1)} value={currentIdx} onChange={setCurrentIdx} style={{ marginTop: 8 }} />
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          {/* 轨迹要点 */}
          <Card title={<span style={{ color: '#e0e0e0' }}><EnvironmentOutlined /> 轨迹分析</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
            {points.length > 0 ? (
              <Space direction="vertical" style={{ width: '100%' }}>
                {[{ label: '轨迹点数', value: points.length },
                  { label: '覆盖摄像头', value: new Set(points.map(p => p.cameraId)).size },
                  { label: '时间跨度', value: points.length > 1 ? `${Math.round((new Date(points[points.length-1].timestamp).getTime() - new Date(points[0].timestamp).getTime()) / 60000)}分钟` : '—' },
                  { label: '碰撞检测', value: collisionEvents > 0 ? `${collisionEvents}处` : '无' },
                  { label: '平均置信度', value: `${Math.round(points.reduce((s, p) => s + (p.confidence || 0), 0) / points.length * 100)}%` },
                ].map(s => (
                  <div key={s.label} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text style={{ color: '#a0a0a0' }}>{s.label}</Text>
                    <Text strong style={{ color: '#e0e0e0' }}>{s.value}</Text>
                  </div>
                ))}
              </Space>
            ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />}
          </Card>

          {/* 轨迹时间线 */}
          <Card title={<span style={{ color: '#e0e0e0' }}>时间线</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, maxHeight: 420, overflow: 'auto' }}>
            {points.map((p, i) => (
              <div key={p.id} onClick={() => setCurrentIdx(i)}
                style={{ padding: '6px 10px', cursor: 'pointer', opacity: i <= currentIdx ? 1 : 0.4,
                  borderLeft: `3px solid ${i <= currentIdx ? '#52c41a' : '#334155'}`, marginBottom: 2, paddingLeft: 12 }}>
                <Text style={{ color: '#e0e0e0', fontSize: 12 }}>{p.cameraName || p.cameraId}</Text>
                <Text style={{ color: '#64748b', fontSize: 10, marginLeft: 8 }}>{new Date(p.timestamp).toLocaleTimeString()}</Text>
                {p.confidence && <Badge count={`${Math.round(p.confidence * 100)}%`} style={{ backgroundColor: '#1677ff', marginLeft: 8, fontSize: 10 }} />}
              </div>
            ))}
            {points.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default TrajectoryViewer;
