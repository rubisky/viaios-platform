import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Typography, Tag, Spin } from 'antd';
import { VideoCameraOutlined, AlertOutlined, CloudServerOutlined, FileSearchOutlined, SafetyCertificateOutlined, RobotOutlined } from '@ant-design/icons';
import { checkAllServices, apiGet } from '../api/client';
import { DashboardCharts } from '../components/DashboardCharts';
import QuickActions from '../components/QuickActions';
import { useDashboardWebSocket } from '../hooks/useDashboardWebSocket';

const { Title, Paragraph } = Typography;

interface ServiceStats {
  cameras?: number; streaming?: number;
  alarms?: number; alarms_critical?: number;
  cases?: number; cases_open?: number;
  agents?: number; capabilities?: number; models?: number;
  entities?: number; relations?: number;
  workflows?: number; tasks?: number;
  onnx?: boolean;
}
interface SysMetrics { cpu_percent?: number; memory_percent?: number; disk_percent?: number; disk_free_gb?: number; }

const Dashboard: React.FC = () => {
  const [services, setServices] = useState<{ name: string; port: number; up: boolean }[]>([]);
  const [stats, setStats] = useState<ServiceStats>({});
  const [metrics, setMetrics] = useState<SysMetrics>({});
  const [loading, setLoading] = useState(true);

  const fetchAllStats = async () => {
    setLoading(true);
    const svc = await checkAllServices();
    setServices(svc);

    const s: ServiceStats = {};
    try { const r = await apiGet<any>('/api/v1/cameras/stats'); s.cameras = r.total; s.streaming = r.active_streams; } catch {}
    try { const r = await apiGet<any>('/api/v1/alarms/stats'); s.alarms = r.total; s.alarms_critical = r.by_status?.critical; } catch {}
    try { const r = await apiGet<any>('/api/v1/cases/stats'); s.cases = r.total; s.cases_open = r.open; } catch {}
    try { const r = await apiGet<any>('/api/v1/agents'); s.agents = Array.isArray(r) ? r.length : r?.agents?.length; } catch {}
    try { const r = await apiGet<any>('/api/v1/capabilities'); s.capabilities = r.capabilities?.length || 0; } catch {}
    try { const r = await apiGet<any>('/api/v1/capabilities/models'); s.models = Array.isArray(r) ? r.length : 0; } catch {}
    try { const r = await apiGet<any>('/api/v1/knowledge/entities'); s.entities = r.total; s.relations = r.relations; } catch {}
    try { const r = await apiGet<any>('/api/v1/workflows/stats'); s.workflows = r.total; } catch {}
    try { const r = await apiGet<any>('/api/v1/analysis/stats'); s.tasks = r.total; } catch {}
    try { const r = await apiGet<any>('/api/v1/capabilities/onnx-status'); s.onnx = r.onnx_available; } catch {}
    setStats(s);
    // Fetch system metrics from Python agent (direct)
    try { const m = await apiGet<SysMetrics>('/api/v1/system/metrics'); setMetrics(m); } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchAllStats(); const t = setInterval(fetchAllStats, 30000); return () => clearInterval(t); }, []);

  // WebSocket for real-time updates (non-blocking)
  useDashboardWebSocket({
    onAlarm: () => fetchAllStats(),
    onCameraChange: () => fetchAllStats(),
    onTaskComplete: () => fetchAllStats(),
  });

  const upCount = services.filter(s => s.up).length;

  const statCards = [
    { title: '系统服务', value: upCount, suffix: '/16', icon: <CloudServerOutlined style={{ fontSize: 32, color: upCount===16?'#52c41a':'#faad14' }} />, color: upCount===16?'#52c41a':'#faad14' },
    { title: '摄像头', value: stats.cameras ?? '-', suffix: stats.streaming ? ` ${stats.streaming}推流` : '', icon: <VideoCameraOutlined style={{ fontSize: 32, color: '#1677ff' }} />, color: '#1677ff' },
    { title: '告警', value: stats.alarms ?? '-', suffix: stats.alarms_critical ? ` ${stats.alarms_critical}严重` : '', icon: <AlertOutlined style={{ fontSize: 32, color: '#faad14' }} />, color: '#faad14' },
    { title: '案件', value: stats.cases ?? '-', suffix: stats.cases_open ? ` ${stats.cases_open}开放` : '', icon: <FileSearchOutlined style={{ fontSize: 32, color: '#52c41a' }} />, color: '#52c41a' },
    { title: 'Agent', value: stats.agents ?? '-', suffix: '就绪', icon: <RobotOutlined style={{ fontSize: 32, color: '#722ed1' }} />, color: '#722ed1' },
    { title: 'AI能力', value: stats.capabilities ?? '-', suffix: `${stats.models ?? '-'}模型`, icon: <SafetyCertificateOutlined style={{ fontSize: 32, color: '#13c2c2' }} />, color: '#13c2c2' },
    { title: 'AI引擎', value: stats.onnx ? 'ONNX' : 'Sim', suffix: stats.onnx ? '真实推理' : '模拟', icon: <RobotOutlined style={{ fontSize: 32, color: stats.onnx ? '#52c41a' : '#faad14' }} />, color: stats.onnx ? '#52c41a' : '#faad14' },
    { title: 'CPU', value: metrics.cpu_percent ?? '-', suffix: '%', icon: <CloudServerOutlined style={{ fontSize: 32, color: (metrics.cpu_percent||0) > 80 ? '#ff4d4f' : '#52c41a' }} />, color: (metrics.cpu_percent||0) > 80 ? '#ff4d4f' : '#52c41a' },
  ];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Title level={2} style={{ color: '#e0e0e0', marginBottom: 8 }}>VIAIOS 视频侦查总览</Title>
          <Tag color={upCount >= 16 ? 'green' : upCount >= 13 ? 'orange' : 'red'} style={{ fontSize: 10 }}>{upCount >= 16 ? '全部在线' : `${upCount}/16 在线`}</Tag>
        </div>
        <Paragraph style={{ color: '#a0a0a0', fontSize: 14 }}>
          服务在线: {upCount}/16 | 摄像头: {stats.cameras ?? '-'} | 告警: {stats.alarms ?? '-'} |
          案件: {stats.cases ?? '-'} | Agent: {stats.agents ?? '-'} | AI能力: {stats.capabilities ?? '-'}
        </Paragraph>
      </div>

      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          {statCards.map(card => (
            <Col xs={24} sm={12} lg={8} key={card.title}>
              <Card hoverable style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Statistic title={<span style={{ color: '#a0a0a0' }}>{card.title}</span>}
                    value={card.value} suffix={card.suffix}
                    valueStyle={{ color: card.color, fontSize: 28, fontWeight: 700 }} />
                  {card.icon}
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </Spin>

      <div style={{ marginTop: 16 }}>
        <QuickActions />
      </div>

      <div style={{ marginTop: 16 }}>
        <DashboardCharts />
      </div>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={14}>
          <Card title={<span style={{ color: '#e0e0e0' }}>服务健康状态</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {services.map(s => (
                <Tag key={s.port} color={s.up ? 'green' : 'red'} style={{ padding: '2px 10px', fontSize: 12 }}>
                  {s.name} {s.up ? '●' : '○'}
                </Tag>
              ))}
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title={<span style={{ color: '#e0e0e0' }}>平台数据</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[
                { label: '知识图谱实体', value: stats.entities ?? '-' },
                { label: '知识图谱关系', value: stats.relations ?? '-' },
                { label: '工作流执行', value: stats.workflows ?? '-' },
                { label: '分析任务', value: stats.tasks ?? '-' },
              ].map(item => (
                <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', color: '#e0e0e0' }}>
                  <span style={{ color: '#a0a0a0' }}>{item.label}</span>
                  <span style={{ fontWeight: 600 }}>{item.value}</span>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
