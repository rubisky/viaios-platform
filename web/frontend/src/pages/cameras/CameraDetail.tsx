import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Tag, Button, Typography, Spin, Row, Col, Space, Empty, message, Badge, Progress } from 'antd';
import { ArrowLeftOutlined, PlayCircleOutlined, PauseCircleOutlined, CameraOutlined, AlertOutlined, VideoCameraOutlined, CaretUpOutlined, CaretDownOutlined, CaretLeftOutlined, CaretRightOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';
import VideoPlayer from '../../components/VideoPlayer';

const { Title, Text } = Typography;

interface Camera { id: string; name: string; location?: string; protocol?: string;
  ipAddress?: string; streamUrl?: string; status: string; resolution?: string; fps?: number; }
interface SnapshotItem { image_url: string; timestamp: string; camera_name?: string; }
interface DetectionEvent { time: string; type: string; label: string; confidence: number; }

const CameraDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [camera, setCamera] = useState<Camera | null>(null);
  const [loading, setLoading] = useState(true);
  const [streaming, setStreaming] = useState(false);
  const [snapshots, setSnapshots] = useState<SnapshotItem[]>([]);
  const [detections, setDetections] = useState<DetectionEvent[]>([]);
  const [recording, setRecording] = useState(false);
  const [recordTime, setRecordTime] = useState(0);
  const [cpuUsage] = useState(12);

  const fetchCamera = useCallback(async () => {
    if (!id) return;
    try { setCamera(await apiGet<Camera>(`/api/v1/cameras/${id}`)); } catch {}
    setLoading(false);
  }, [id]);

  const fetchSnapshots = async () => {
    if (!id) return;
    try { const r = await apiGet<any>(`/api/v1/video/snapshots/${id}`); setSnapshots(Array.isArray(r?.snapshots) ? r.snapshots : []); } catch {}
  };

  useEffect(() => { fetchCamera(); fetchSnapshots(); }, [id]);

  // 模拟AI检测事件
  useEffect(() => {
    if (!streaming) return;
    const types = [{ type: '人员', label: '人员检测' }, { type: '车辆', label: '车辆检测' }, { type: '行为', label: '异常行为' }];
    const t = setInterval(() => {
      const d = types[Math.floor(Math.random() * 3)];
      setDetections(prev => [{ time: new Date().toLocaleTimeString(), ...d, confidence: Math.round(Math.random() * 20 + 80) }, ...prev].slice(0, 20));
    }, 3000);
    return () => clearInterval(t);
  }, [streaming]);

  // 录像计时
  useEffect(() => {
    if (!recording) return;
    const t = setInterval(() => setRecordTime(prev => prev + 1), 1000);
    return () => clearInterval(t);
  }, [recording]);

  const startStream = () => setStreaming(true);
  const stopStream = () => { setStreaming(false); setRecording(false); setRecordTime(0); };

  const takeSnapshot = async () => {
    if (!id) return;
    try {
      const r = await apiPost<any>(`/api/v1/video/snapshot/${id}`);
      setSnapshots(prev => [{ image_url: r?.image_url || `/snapshots/${id}.jpg`, timestamp: r?.timestamp || new Date().toISOString() }, ...prev].slice(0, 40));
      message.success('截图已保存');
    } catch { message.error('截图失败'); }
  };

  const toggleRecording = () => setRecording(!recording);

  const ptzCmd = (cmd: string) => message.info(`PTZ: ${cmd}`);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!camera) return <Empty description="摄像头不存在" />;

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cameras')}>返回列表</Button>
          <Title level={3} style={{ color: '#e0e0e0', margin: 0 }}><VideoCameraOutlined /> {camera.name}</Title>
          <Badge status={camera.status === 'online' ? 'processing' : 'error'} text={camera.status === 'online' ? '在线' : '离线'} />
        </Space>
        <Text style={{ color: '#a0a0a0' }}>{camera.location} · {camera.protocol?.toUpperCase()} · {camera.resolution}</Text>
      </div>

      <Row gutter={[16, 16]}>
        {/* 主视频区 */}
        <Col xs={24} lg={16}>
          <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }} bodyStyle={{ padding: 0 }}>
            {!streaming ? (
              <div style={{ textAlign: 'center', padding: 80, color: '#64748b' }}>
                <PlayCircleOutlined style={{ fontSize: 48 }} />
                <p style={{ marginTop: 12 }}>点击下方按钮开始实时监控</p>
                <Button type="primary" size="large" icon={<PlayCircleOutlined />} onClick={startStream}>开始推流</Button>
              </div>
            ) : (
              <div style={{ position: 'relative' }}>
                <VideoPlayer streamUrl="/live/placeholder.m3u8" autoPlay muted height={420}
                  analysisBoxes={[
                    { x: 50, y: 80, w: 100, h: 140, label: '人员', confidence: 0.95 },
                    { x: 180, y: 100, w: 70, h: 90, label: '车辆', confidence: 0.88 },
                  ]} />
                {/* 状态覆盖层 */}
                <div style={{ position: 'absolute', top: 8, left: 8, right: 8, display: 'flex', justifyContent: 'space-between' }}>
                  <Space>
                    <Badge status="processing" />
                    <Text style={{ color: '#52c41a', fontSize: 11, background: 'rgba(0,0,0,0.5)', padding: '2px 8px', borderRadius: 4 }}>LIVE</Text>
                    <Text style={{ color: '#fff', fontSize: 11, background: 'rgba(0,0,0,0.5)', padding: '2px 8px', borderRadius: 4 }}>{camera.fps}fps</Text>
                  </Space>
                  {recording && (
                    <Space>
                      <Badge status="error" />
                      <Text style={{ color: '#ff4d4f', fontSize: 11, background: 'rgba(0,0,0,0.5)', padding: '2px 8px', borderRadius: 4 }}>
                        REC {Math.floor(recordTime/60)}:{String(recordTime%60).padStart(2,'0')}
                      </Text>
                    </Space>
                  )}
                </div>
              </div>
            )}
          </Card>

          {/* 控制栏 */}
          <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginTop: 12 }}>
            <Row gutter={16} align="middle">
              <Col span={8}>
                <Space>
                  <Button size="small" danger={streaming} icon={streaming ? <PauseCircleOutlined /> : <PlayCircleOutlined />} onClick={streaming ? stopStream : startStream}>
                    {streaming ? '停止' : '推流'}
                  </Button>
                  <Button size="small" icon={<CameraOutlined />} onClick={takeSnapshot} disabled={!streaming}>截图</Button>
                  <Button size="small" danger={recording} icon={<Badge status="error" />} onClick={toggleRecording} disabled={!streaming}>
                    {recording ? '停止录像' : '录像'}
                  </Button>
                </Space>
              </Col>
              <Col span={8}>
                {/* PTZ */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 2, width: 120 }}>
                  <div /><Button size="small" icon={<CaretUpOutlined />} disabled={!streaming} onClick={() => ptzCmd('上')} /><div />
                  <Button size="small" icon={<CaretLeftOutlined />} disabled={!streaming} onClick={() => ptzCmd('左')} />
                  <Button size="small" disabled={!streaming} onClick={() => ptzCmd('归位')}>归</Button>
                  <Button size="small" icon={<CaretRightOutlined />} disabled={!streaming} onClick={() => ptzCmd('右')} />
                  <div /><Button size="small" icon={<CaretDownOutlined />} disabled={!streaming} onClick={() => ptzCmd('下')} /><div />
                </div>
              </Col>
              <Col span={8}>
                <Text style={{ color: '#a0a0a0', fontSize: 11, display: 'block' }}>设备信息</Text>
                <Text style={{ color: '#e0e0e0', fontSize: 12 }}>{camera.protocol?.toUpperCase()} · {camera.ipAddress || '—'}</Text>
                <Text style={{ color: '#e0e0e0', fontSize: 12 }}>{camera.resolution} @ {camera.fps}fps</Text>
                <Text style={{ color: '#64748b', fontSize: 11 }}>CPU: <Progress percent={cpuUsage} size="small" style={{ width: 60, display: 'inline-block' }} /></Text>
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 右侧面板 */}
        <Col xs={24} lg={8}>
          {/* AI检测 */}
          <Card title={<span style={{ color: '#e0e0e0' }}><AlertOutlined /> AI实时检测</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
            {streaming && detections.length > 0 ? detections.slice(0, 8).map((d, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #1e293b' }}>
                <Space size={4}>
                  <Tag color={d.type === '人员' ? 'blue' : d.type === '车辆' ? 'green' : 'orange'} style={{ fontSize: 10 }}>{d.label}</Tag>
                  <Text style={{ color: '#64748b', fontSize: 10 }}>{d.time}</Text>
                </Space>
                <Tag color={d.confidence > 90 ? 'green' : 'orange'} style={{ fontSize: 10 }}>{d.confidence}%</Tag>
              </div>
            )) : <Empty description={streaming ? '等待检测...' : '启动推流后显示'} image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </Card>

          {/* 截图库 */}
          <Card title={<span style={{ color: '#e0e0e0' }}><CameraOutlined /> 截图 ({snapshots.length})</span>}
            extra={<Button size="small" icon={<CameraOutlined />} onClick={takeSnapshot} disabled={!streaming}>截图</Button>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            {snapshots.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 4 }}>
                {snapshots.slice(0, 12).map((s, i) => (
                  <div key={i} style={{ aspectRatio: '16/9', background: '#1a1a2e', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
                    <CameraOutlined style={{ fontSize: 16, color: '#64748b' }} />
                    <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, background: 'rgba(0,0,0,0.6)', padding: '1px 4px', fontSize: 8, color: '#a0a0a0', textAlign: 'center' }}>
                      {new Date(s.timestamp).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit', second:'2-digit' })}
                    </div>
                  </div>
                ))}
              </div>
            ) : <Empty description="暂无截图" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default CameraDetail;
