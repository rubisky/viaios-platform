import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Typography, Row, Col, Statistic, Spin } from 'antd';
import { CloudServerOutlined, CheckCircleOutlined, CloseCircleOutlined, SyncOutlined, DatabaseOutlined, HddOutlined } from '@ant-design/icons';
import { apiGet, SERVICES } from '../../api/client';

const { Text } = Typography;

interface HealthDetail { name: string; port: number; status: string; latency: number; uptime: string; }

const SystemHealth: React.FC = () => {
  const [services, setServices] = useState<HealthDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [diskInfo, setDiskInfo] = useState<{ total: number; free: number; usedPercent: number }>({ total: 0, free: 0, usedPercent: 0 });

  const fetchHealth = async () => {
    setLoading(true);
    try {
      // Check all services
      const results = await Promise.all(
        SERVICES.map(async (s) => {
          const start = performance.now();
          try {
            const res = await apiGet<any>('/actuator/health');
            const latency = Math.round(performance.now() - start);
            const status = res?.status || 'UNKNOWN';
            // Parse disk info from gateway health
            if (s.port === 8080 && res?.components?.diskSpace) {
              const ds = res.components.diskSpace.details;
              setDiskInfo({ total: Math.round(ds.total / 1e9), free: Math.round(ds.free / 1e9), usedPercent: Math.round((1 - ds.free / ds.total) * 100) });
            }
            return { ...s, status, latency, uptime: '—' };
          } catch {
            return { ...s, status: 'DOWN', latency: 0, uptime: '—' };
          }
        })
      );
      setServices(results);
    } catch { }
    setLoading(false);
  };

  useEffect(() => { fetchHealth(); const t = setInterval(fetchHealth, 30000); return () => clearInterval(t); }, []);

  const upCount = services.filter(s => s.status === 'UP').length;

  const columns = [
    { title: '服务', dataIndex: 'name', key: 'name', render: (v: string) => <Text strong style={{ color: '#e0e0e0' }}>{v}</Text> },
    { title: '端口', dataIndex: 'port', key: 'port', width: 70, render: (v: number) => <Text style={{ color: '#64748b' }}>{v}</Text> },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: string) => <Tag icon={v === 'UP' ? <CheckCircleOutlined /> : <CloseCircleOutlined />} color={v === 'UP' ? 'green' : 'red'}>{v}</Tag>,
    },
    {
      title: '延迟', dataIndex: 'latency', key: 'latency', width: 80, sorter: (a: any, b: any) => a.latency - b.latency,
      render: (v: number) => <Text style={{ color: v < 10 ? '#52c41a' : v < 50 ? '#faad14' : '#ff4d4f' }}>{v > 0 ? `${v}ms` : '—'}</Text>,
    },
  ];

  if (loading && services.length === 0) return <Spin size="large" style={{ display: 'block', margin: 40 }} />;

  return (
    <div>
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>服务状态</Text>}
              value={upCount} suffix={`/ ${services.length}`}
              valueStyle={{ color: upCount === services.length ? '#52c41a' : '#faad14', fontSize: 22 }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>磁盘总量</Text>}
              value={diskInfo.total} suffix="GB" prefix={<HddOutlined />}
              valueStyle={{ color: '#1677ff', fontSize: 22 }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>磁盘可用</Text>}
              value={diskInfo.free} suffix="GB"
              valueStyle={{ color: '#52c41a', fontSize: 22 }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>磁盘使用率</Text>}
              value={diskInfo.usedPercent} suffix="%" prefix={<DatabaseOutlined />}
              valueStyle={{ color: diskInfo.usedPercent > 80 ? '#ff4d4f' : '#52c41a', fontSize: 22 }} />
          </Card>
        </Col>
      </Row>

      <Card title={<span style={{ color: '#e0e0e0' }}><CloudServerOutlined /> 服务监控</span>}
        extra={<SyncOutlined spin={loading} style={{ color: '#a0a0a0' }} />}
        style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
        bodyStyle={{ padding: 0 }}>
        <Table columns={columns} dataSource={services} rowKey="port" loading={loading && services.length === 0}
          pagination={false} size="small" style={{ background: 'transparent' }} />
      </Card>
    </div>
  );
};

export default SystemHealth;
