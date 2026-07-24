import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Tag, Button, Typography, Spin, message, Row, Col, Space, Divider, Progress, Empty } from 'antd';
import { ArrowLeftOutlined, PlayCircleOutlined, PauseCircleOutlined, CameraOutlined, ReloadOutlined, AlertOutlined, ControlOutlined, AimOutlined } from '@ant-design/icons';
import { apiGet } from '../../api/client';
import VideoPlayer from '../../components/VideoPlayer';

const { Title, Text } = Typography;

interface Camera {
  id: string; name: string; location?: string; protocol?: string;
  ipAddress?: string; streamUrl?: string;
  status: string; resolution?: string; fps?: number;
}

interface AnalysisEvent {
  timestamp: string; type: string; label: string; confidence: number; bbox?: number[];
}

interface Snapshot {
  image_url: string; timestamp: string; resolution: string;
}

const CameraDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [camera, setCamera] = useState<Camera | null>(null);
  const [loading, setLoading] = useState(true);
  const [streaming, setStreaming] = useState(false);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [events, setEvents] = useState<AnalysisEvent[]>([]);
  const [cpuUsage, setCpuUsage] = useState(0);

  const fetchCamera = useCallback(async () => {
    if (!id) return;
    try {
      const cam = await apiGet<Camera>(`/api/v1/cameras/${id}`);
      setCamera(cam);
    } catch { message.error('加载摄像头失败'); }
    setLoading(false);
  }, [id]);

  useEffect(() => { fetchCamera(); }, [fetchCamera]);

  // Fetch AI analysis events
  const fetchAnalysis = async () => {
    if (!id) return;
    try {
      const r = await apiGet<any>(`/api/v1/analysis/events?camera_id=${id}`);
      setEvents(Array.isArray(r) ? r : r?.events || []);
    } catch { /* analysis not available */ }
  };

  // Fetch snapshots
  const fetchSnapshots = async () => {
    if (!id) return;
    try {
      const r = await apiGet<any>(`/api/v1/cameras/${id}/snapshots`);
      setSnapshots(Array.isArray(r) ? r : r?.snapshots || []);
    } catch { /* no snapshots yet */ }
  };

  useEffect(() => { fetchAnalysis(); fetchSnapshots(); }, [id]);

  const startStream = () => setStreaming(true);
  const stopStream = () => setStreaming(false);

  const takeSnapshot = async () => {
    if (!id) return;
    try {
      const r = await apiGet<any>(`/api/v1/cameras/${id}/snapshot`);
      setSnapshots(prev => [{ image_url: r?.image_url || `/snapshots/cam_${id}.jpg`, timestamp: r?.timestamp || new Date().toISOString(), resolution: r?.resolution || camera?.resolution || '1920x1080' }, ...prev]);
      message.success('截图已保存');
    } catch { message.error('截图失败'); }
  };

  // Simulate CPU usage for demo
  useEffect(() => {
    if (streaming) {
      const t = setInterval(() => setCpuUsage(Math.floor(Math.random() * 30 + 15)), 2000);
      return () => clearInterval(t);
    }
    setCpuUsage(0);
  }, [streaming]);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!camera) return <Empty description="摄像头不存在" />;

  const statusColor = camera.status === 'online' ? 'green' : camera.status === 'offline' ? 'red' : 'orange';

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cameras')}>返回</Button>
          <Title level={3} style={{ color: '#e0e0e0', margin: 0 }}>{camera.name}</Title>
          <Tag color={statusColor}>{camera.status === 'online' ? '在线' : camera.status}</Tag>
        </Space>
        <Space>
          <Text style={{ color: '#a0a0a0' }}>{camera.location}</Text>
          <Text style={{ color: '#64748b' }}>{camera.protocol?.toUpperCase()} | {camera.resolution} | {camera.fps}fps</Text>
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        {/* Video Player */}
        <Col xs={24} lg={16}>
          <Card
            title={<span style={{ color: '#e0e0e0' }}>实时视频</span>}
            extra={
              <Space>
                {!streaming ? (
                  <Button type="primary" icon={<PlayCircleOutlined />} onClick={startStream}>开始推流</Button>
                ) : (
                  <Button danger icon={<PauseCircleOutlined />} onClick={stopStream}>停止</Button>
                )}
                <Button icon={<CameraOutlined />} onClick={takeSnapshot} disabled={!streaming}>截图</Button>
                <Button icon={<ReloadOutlined />} onClick={fetchCamera}>刷新</Button>
              </Space>
            }
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
            bodyStyle={{ padding: 0 }}
          >
            <div style={{ position: 'relative', background: '#000', minHeight: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {!streaming ? (
                <div style={{ textAlign: 'center', color: '#64748b', padding: 40 }}>
                  <PlayCircleOutlined style={{ fontSize: 48 }} />
                  <p>点击"开始推流"查看实时视频</p>
                </div>
              ) : (
                <VideoPlayer
                  streamUrl="/live/placeholder.m3u8"
                  autoPlay
                  muted
                  analysisBoxes={[
                    { x: 50, y: 80, w: 120, h: 150, label: 'Person', confidence: 0.95 },
                    { x: 200, y: 100, w: 80, h: 100, label: 'Vehicle', confidence: 0.88 },
                  ]}
                  onSnapshot={(url) => setSnapshots(prev => [{ image_url: url, timestamp: new Date().toISOString(), resolution: camera.resolution || '1920x1080' }, ...prev])}
                />
              )}
              {/* AI detection overlay */}
              {streaming && events.length > 0 && (
                <div style={{ position: 'absolute', top: 8, right: 8, background: 'rgba(0,0,0,0.6)', padding: '4px 12px', borderRadius: 4, fontSize: 11, color: '#faad14' }}>
                  <AlertOutlined /> AI 检测中
                </div>
              )}
            </div>
            {/* Stream stats */}
            {streaming && (
              <div style={{ padding: '8px 16px', background: '#0f0f23', display: 'flex', gap: 24, fontSize: 12, color: '#a0a0a0' }}>
                <span>CPU: <Progress percent={cpuUsage} size="small" style={{ width: 80 }} strokeColor="#52c41a" /></span>
                <span>带宽: {(Math.random() * 4 + 1).toFixed(1)} Mbps</span>
                <span>延迟: {(Math.random() * 200 + 50).toFixed(0)}ms</span>
                <span>丢包: {(Math.random() * 0.5).toFixed(1)}%</span>
              </div>
            )}
          </Card>
        </Col>

        {/* Sidebar: Camera Info + Controls */}
        <Col xs={24} lg={8}>
          {/* Camera Info */}
          <Card title={<span style={{ color: '#e0e0e0' }}>设备信息</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
            <Descriptions column={1} size="small" labelStyle={{ color: '#a0a0a0' }} contentStyle={{ color: '#e0e0e0' }}>
              <Descriptions.Item label="ID">{camera.id}</Descriptions.Item>
              <Descriptions.Item label="协议">{camera.protocol?.toUpperCase()}</Descriptions.Item>
              <Descriptions.Item label="IP 地址">{camera.ipAddress || '—'}</Descriptions.Item>
              <Descriptions.Item label="分辨率">{camera.resolution || '—'}</Descriptions.Item>
              <Descriptions.Item label="帧率">{camera.fps ? `${camera.fps} fps` : '—'}</Descriptions.Item>
              <Descriptions.Item label="推流地址">{camera.streamUrl || '—'}</Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={statusColor}>{camera.status === 'online' ? '在线' : camera.status}</Tag></Descriptions.Item>
            </Descriptions>
          </Card>

          {/* PTZ Controls */}
          <Card title={<span style={{ color: '#e0e0e0' }}><ControlOutlined /> 云台控制</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, textAlign: 'center' }}>
              <div />
              <Button icon={<AimOutlined style={{ transform: 'rotate(-90deg)' }} />} disabled={!streaming}>上</Button>
              <div />
              <Button icon={<AimOutlined style={{ transform: 'rotate(180deg)' }} />} disabled={!streaming}>左</Button>
              <Button disabled={!streaming}>归位</Button>
              <Button icon={<AimOutlined />} disabled={!streaming}>右</Button>
              <div />
              <Button icon={<AimOutlined style={{ transform: 'rotate(90deg)' }} />} disabled={!streaming}>下</Button>
              <div />
            </div>
            <Divider style={{ margin: '12px 0', borderColor: '#2a2a4a' }} />
            <Space>
              <Button size="small" disabled={!streaming}>放大</Button>
              <Button size="small" disabled={!streaming}>缩小</Button>
              <Button size="small" disabled={!streaming}>聚焦</Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Tabs: Analysis Timeline + Snapshots */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title={<span style={{ color: '#e0e0e0' }}><AlertOutlined /> AI 分析结果</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            {events.length > 0 ? events.map((e, i) => (
              <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid #2a2a4a', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Tag color={e.confidence > 0.9 ? 'green' : e.confidence > 0.7 ? 'orange' : 'red'}>{e.label}</Tag>
                  <Text style={{ color: '#a0a0a0', fontSize: 12 }}>{e.type}</Text>
                </div>
                <Space>
                  <Text style={{ color: '#64748b', fontSize: 11 }}>{new Date(e.timestamp).toLocaleTimeString()}</Text>
                  <Tag>{`${(e.confidence * 100).toFixed(0)}%`}</Tag>
                </Space>
              </div>
            )) : (
              <Empty description="暂无AI分析结果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title={<span style={{ color: '#e0e0e0' }}><CameraOutlined /> 截图库</span>}
            extra={<Button size="small" icon={<CameraOutlined />} onClick={takeSnapshot} disabled={!streaming}>截图</Button>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            {snapshots.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 8 }}>
                {snapshots.map((s, i) => (
                  <div key={i} style={{ position: 'relative', borderRadius: 4, overflow: 'hidden', border: '1px solid #2a2a4a' }}>
                    <img src={s.image_url} alt={`截图 ${i + 1}`} style={{ width: '100%', height: 80, objectFit: 'cover', background: '#000' }}
                      onError={(e) => { (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22160%22 height=%2290%22><rect fill=%22%23333%22 width=%22160%22 height=%2290%22/><text fill=%22%23666%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 font-size=%2212%22>预览</text></svg>'; }} />
                    <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, background: 'rgba(0,0,0,0.6)', padding: '2px 4px', fontSize: 9, color: '#a0a0a0', textAlign: 'center' }}>
                      {new Date(s.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <Empty description="暂无截图" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default CameraDetail;
