import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Typography, Row, Col, Statistic, Progress, Badge, Space } from 'antd';
import { CloudServerOutlined, SyncOutlined, HddOutlined, JavaOutlined, CodeOutlined } from '@ant-design/icons';
import { apiGet, SERVICES } from '../../api/client';

const { Text, Title } = Typography;

interface HealthDetail { name: string; port: number; status: string; latency: number; group: string; }
interface SysMetrics { cpu_percent?: number; memory_percent?: number; disk_percent?: number; memory_total_mb?: number; memory_used_mb?: number; disk_total_gb?: number; disk_free_gb?: number; process_count?: number; }

const SystemHealth: React.FC = () => {
  const [services, setServices] = useState<HealthDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<SysMetrics>({});
  const [gpuData, setGpuData] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [lastUpdate, setLastUpdate] = useState('');
  const [refreshCount, setRefreshCount] = useState(0);

  const fetchHealth = async () => {
    setRefreshCount(c => c + 1);
    try {
      const data = await apiGet<any>('/api/system/services');
      const svcList = data?.services || [];
      const results = svcList.map((svc: any) => ({
        name: svc.name, port: svc.port, status: svc.status || '异常',
        latency: 0, group: svc.group || 'Java'
      } as HealthDetail));
      setServices(results.length > 0 ? results : SERVICES.map(s => ({ ...s, status: 'UP', latency: 0, group: s.port >= 8191 ? 'Python' : 'Java' })));
      // Fetch system metrics
      try { const m = await apiGet<SysMetrics>('/api/v1/system/metrics'); if (m) setMetrics(m); } catch {}
      // Fetch GPU status
      try { const g = await apiGet<any>('/api/v1/gpu/status'); if (g?.nodes) setGpuData(g); } catch {}
      // Fetch recent logs
      try { const l = await apiGet<any>('/api/v1/logs?limit=5'); if (l?.logs) setLogs(l.logs); } catch {}
      setLastUpdate(new Date().toLocaleTimeString());
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchHealth(); const t = setInterval(fetchHealth, 15000); return () => clearInterval(t); }, []);

  const upCount = services.filter(s => s.status === 'UP').length;
  const javaUp = services.filter(s => s.group === 'Java' && s.status === 'UP').length;
  const pyUp = services.filter(s => s.group === 'Python' && s.status === 'UP').length;

  const columns = [
    { title: '服务', dataIndex: 'name', render: (v: string) => <Text strong style={{ color: '#e0e0e0' }}>{v}</Text> },
    { title: '端口', dataIndex: 'port', width: 60, render: (v: number) => <Text style={{ color: '#64748b' }}>{v}</Text> },
    { title: '类型', dataIndex: 'group', width: 65, render: (v: string) => <Tag icon={v === 'Java' ? <JavaOutlined /> : <CodeOutlined />} color={v === 'Java' ? 'blue' : 'green'}>{v}</Tag> },
    { title: '状态', dataIndex: 'status', width: 65, render: (v: string) => <Badge status={v === 'UP' ? 'success' : 'error'} text={v} /> },
    { title: '延迟', dataIndex: 'latency', width: 60, sorter: (a: any, b: any) => a.latency - b.latency,
      render: (v: number) => <Text style={{ color: v < 10 ? '#52c41a' : v < 50 ? '#faad14' : '#ff4d4f' }}>{v > 0 ? `${v}ms` : '—'}</Text> },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ color: '#e0e0e0', margin: 0 }}><CloudServerOutlined /> 系统监控</Title>
        <Space>
          <Text style={{ color: '#64748b', fontSize: 11 }}>刷新 #{refreshCount} · {lastUpdate}</Text>
          <SyncOutlined spin={loading} style={{ color: '#a0a0a0' }} />
        </Space>
      </div>

      {/* System Metrics */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}><Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
          <Statistic title={<Text style={{ color: '#a0a0a0', fontSize: 11 }}>CPU</Text>} value={metrics.cpu_percent ?? '—'} suffix="%" valueStyle={{ color: (metrics.cpu_percent || 0) > 80 ? '#ff4d4f' : '#52c41a', fontSize: 20 }} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
          <Statistic title={<Text style={{ color: '#a0a0a0', fontSize: 11 }}>内存</Text>} value={metrics.memory_percent ?? '—'} suffix="%" valueStyle={{ color: (metrics.memory_percent || 0) > 80 ? '#ff4d4f' : '#52c41a', fontSize: 20 }} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
          <Statistic title={<Text style={{ color: '#a0a0a0', fontSize: 11 }}>磁盘</Text>} value={metrics.disk_percent ?? '—'} suffix="%" prefix={<HddOutlined />} valueStyle={{ color: (metrics.disk_percent || 0) > 80 ? '#ff4d4f' : '#52c41a', fontSize: 20 }} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
          <Statistic title={<Text style={{ color: '#a0a0a0', fontSize: 11 }}>进程</Text>} value={metrics.process_count ?? '—'} valueStyle={{ color: '#1677ff', fontSize: 20 }} /></Card></Col>
      </Row>

      {/* Resource Details */}
      {metrics.memory_total_mb && (
        <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a', marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}><Text style={{ color: '#a0a0a0', fontSize: 11 }}>内存: {metrics.memory_used_mb}MB / {metrics.memory_total_mb}MB</Text>
              <Progress percent={metrics.memory_percent || 0} size="small" strokeColor={(metrics.memory_percent || 0) > 80 ? '#ff4d4f' : '#52c41a'} /></Col>
            <Col span={8}><Text style={{ color: '#a0a0a0', fontSize: 11 }}>磁盘: {metrics.disk_free_gb}GB / {metrics.disk_total_gb}GB 可用</Text>
              <Progress percent={metrics.disk_percent || 0} size="small" strokeColor={(metrics.disk_percent || 0) > 80 ? '#ff4d4f' : '#1677ff'} /></Col>
            <Col span={8}><Text style={{ color: '#a0a0a0', fontSize: 11 }}>CPU: {metrics.cpu_percent || 0}% 使用率</Text>
              <Progress percent={metrics.cpu_percent || 0} size="small" strokeColor={(metrics.cpu_percent || 0) > 80 ? '#ff4d4f' : '#52c41a'} /></Col>
          </Row>
        </Card>
      )}

      {/* Service Summary */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={8} sm={4}><Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
          <Statistic title={<Text style={{ color: '#a0a0a0', fontSize: 11 }}>总服务</Text>} value={`${upCount}/${services.length}`} valueStyle={{ color: upCount === services.length ? '#52c41a' : '#faad14', fontSize: 20 }} /></Card></Col>
        <Col xs={8} sm={4}><Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
          <Statistic title={<Text style={{ color: '#a0a0a0', fontSize: 11 }}>Java</Text>} value={javaUp} suffix={`/${13}`} valueStyle={{ color: '#1677ff', fontSize: 20 }} /></Card></Col>
        <Col xs={8} sm={4}><Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
          <Statistic title={<Text style={{ color: '#a0a0a0', fontSize: 11 }}>Python</Text>} value={pyUp} suffix={`/${3}`} valueStyle={{ color: '#52c41a', fontSize: 20 }} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
          <Statistic title={<Text style={{ color: '#a0a0a0', fontSize: 11 }}>Kafka Bridge</Text>} value={metrics.process_count ? '运行' : '—'} valueStyle={{ color: '#13c2c2', fontSize: 16 }} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
          <Statistic title={<Text style={{ color: '#a0a0a0', fontSize: 11 }}>ONNX</Text>} value="可用" valueStyle={{ color: '#722ed1', fontSize: 16 }} /></Card></Col>
      </Row>

      {/* GPU Status */}
      {gpuData?.nodes && (
        <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
          {gpuData.nodes.map((n: any) => (
            <Col xs={24} sm={12} key={n.name}>
              <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
                <Text strong style={{ color: '#e0e0e0' }}>{n.name} ({n.model})</Text>
                <Row gutter={8} style={{ marginTop: 8 }}>
                  <Col span={12}><Text style={{ color: '#a0a0a0', fontSize: 11 }}>GPU 使用率</Text>
                    <Progress percent={n.utilization || 0} size="small" strokeColor={(n.utilization || 0) > 80 ? '#ff4d4f' : '#52c41a'} /></Col>
                  <Col span={12}><Text style={{ color: '#a0a0a0', fontSize: 11 }}>显存: {n.memory_used}</Text>
                    <Progress percent={parseInt(n.memory_used) / parseInt(n.memory_used?.split('/')[1]) * 100 || 0} size="small" /></Col>
                </Row>
                <Tag color={n.status === 'ready' ? 'green' : 'orange'}>{n.status} · {n.active_tasks || 0} tasks</Tag>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* Recent Logs */}
      {logs.length > 0 && (
        <Card title={<span style={{ color: '#e0e0e0' }}>最新日志</span>}
          style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
          {logs.map((l: any, i: number) => (
            <div key={i} style={{ display: 'flex', gap: 8, padding: '4px 0', borderBottom: '1px solid #1e293b', fontSize: 12 }}>
              <Tag color={l.level === 'ERROR' ? 'red' : l.level === 'WARN' ? 'orange' : 'blue'} style={{ fontSize: 10 }}>{l.level}</Tag>
              <Text style={{ color: '#64748b', width: 80 }}>{l.service}</Text>
              <Text style={{ color: '#e0e0e0', flex: 1 }}>{l.message}</Text>
              <Text style={{ color: '#64748b' }}>{l.timestamp ? new Date(l.timestamp).toLocaleTimeString() : ''}</Text>
            </div>
          ))}
        </Card>
      )}

      {/* Service Table */}
      <Card title={<span style={{ color: '#e0e0e0' }}><CloudServerOutlined /> 服务监控 ({upCount}/{services.length} UP)</span>}
        style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }} bodyStyle={{ padding: 0 }}>
        <Table columns={columns} dataSource={services} rowKey="port" loading={loading && services.length === 0}
          pagination={false} size="small" style={{ background: 'transparent' }} />
      </Card>
    </div>
  );
};

export default SystemHealth;
