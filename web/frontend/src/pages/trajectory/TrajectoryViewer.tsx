import React, { useEffect, useState, lazy, Suspense } from 'react';
import { Card, Select, Button, Space, Slider, Typography, Row, Col, Empty, Tag, message, Spin } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, EnvironmentOutlined, AimOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiGet } from '../../api/client';

const { Title, Text } = Typography;

const CesiumTrajectory = lazy(() => import('../../components/CesiumTrajectory'));

interface TrajectoryPoint { id: string; cameraId?: string; cameraName?: string; longitude: number; latitude: number; altitude?: number; timestamp: string; confidence?: number; targetId?: string; }

const TRACK_COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'];

const TrajectoryViewer: React.FC = () => {
  const [points, setPoints] = useState<TrajectoryPoint[]>([]);
  const [targets, setTargets] = useState<string[]>(['目标1', '目标2']);
  const [selected, setSelected] = useState('');
  const [playing, setPlaying] = useState(false);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [view3D, setView3D] = useState(true);

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
          altitude: 10 + Math.random() * 50,
          timestamp: new Date(Date.now() - (15 - i) * 120000).toISOString(), confidence: 0.8 + Math.random() * 0.2, targetId: targetId || 'target1',
        }));
      }
      setPoints(pts); setCurrentIdx(0);
    } catch { message.error('加载失败'); }
  };

  useEffect(() => { fetchPoints(); apiGet<any>('/api/v1/trajectory/stats').then(r => { if (r?.targets) setTargets(r.targets); }).catch(() => {}); }, []);

  const collisionEvents = points.filter((p, i) => i > 0 && points[i - 1].cameraId === p.cameraId).length;
  const tracks = [{
    targetId: selected || 'target1',
    color: TRACK_COLORS[0],
    points: points as any[],
  }] as any[];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Title level={3} style={{ color: '#e0e0e0', margin: 0 }}><AimOutlined /> 轨迹分析</Title>
        <Space wrap>
          <Button size="small" type={view3D ? 'primary' : 'default'} onClick={() => setView3D(!view3D)}>
            {view3D ? '3D 地球' : '2D 地图'}
          </Button>
          <Select style={{ width: 150 }} placeholder="选择目标" value={selected || undefined}
            onChange={v => { setSelected(v); fetchPoints(v); }} options={targets.map(t => ({ value: t, label: t }))} />
          <Button icon={<ReloadOutlined />} onClick={() => fetchPoints(selected)}>刷新</Button>
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Suspense fallback={<div style={{ height: 450, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#1a1a2e', borderRadius: 8 }}><Spin tip="加载 3D 引擎..." /></div>}>
            {view3D ? (
              <CesiumTrajectory tracks={tracks} height="450px" />
            ) : (
              <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', height: 450 }}>
                <Empty description="2D 地图模式 — 请在 3D 模式下查看" />
              </Card>
            )}
          </Suspense>
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
          <Card title={<span style={{ color: '#e0e0e0' }}><EnvironmentOutlined /> 轨迹分析</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
            {points.length > 0 ? (
              <Space direction="vertical" style={{ width: '100%' }}>
                {[{ label: '轨迹点数', value: points.length },
                  { label: '覆盖摄像头', value: new Set(points.map(p => p.cameraId)).size },
                  { label: '时间跨度', value: points.length > 1 ? `${Math.round((new Date(points[points.length-1].timestamp).getTime() - new Date(points[0].timestamp).getTime()) / 60000)}分钟` : '—' },
                  { label: '碰撞检测', value: collisionEvents > 0 ? `${collisionEvents}处` : '无' },
                  { label: '平均置信度', value: `${Math.round(points.reduce((s, p) => s + (p.confidence || 0), 0) / points.length * 100)}%` },
                  { label: '视图模式', value: view3D ? 'Cesium 3D' : 'Leaflet 2D' },
                ].map(s => (
                  <div key={s.label} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text style={{ color: '#a0a0a0' }}>{s.label}</Text>
                    <Text strong style={{ color: '#e0e0e0' }}>{s.value}</Text>
                  </div>
                ))}
              </Space>
            ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />}
          </Card>

          <Card title={<span style={{ color: '#e0e0e0' }}>时间线</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, maxHeight: 420, overflow: 'auto' }}>
            {points.map((p, i) => (
              <div key={p.id} onClick={() => setCurrentIdx(i)}
                style={{ padding: '6px 10px', cursor: 'pointer', opacity: i <= currentIdx ? 1 : 0.4,
                  borderLeft: `3px solid ${i <= currentIdx ? '#52c41a' : '#334155'}`, marginBottom: 2, paddingLeft: 12 }}>
                <Text style={{ color: '#e0e0e0', fontSize: 12 }}>{p.cameraName || p.cameraId}</Text>
                <Text style={{ color: '#64748b', fontSize: 10, marginLeft: 8 }}>{new Date(p.timestamp).toLocaleTimeString()}</Text>
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
