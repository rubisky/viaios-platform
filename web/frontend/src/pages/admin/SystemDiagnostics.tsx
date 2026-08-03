/** System Diagnostics — Real-time health monitoring dashboard (P2-5) */
import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Row, Col, Statistic, Timeline, Badge } from 'antd';
import { ReloadOutlined, DashboardOutlined, ThunderboltOutlined, ApiOutlined } from '@ant-design/icons';
import { apiGet } from '../../api/client';

interface ServiceStatus { name: string; port: number; status: string; group: string; }
interface MeshStats { total_endpoints: number; healthy_endpoints: number; open_circuits: number; total_requests: number; }
interface KernelHealth { kernel: string; totalManagers: number; managers: Record<string, {status: string}>; }

const REFRESH = 10000;

const SystemDiagnostics: React.FC = () => {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [mesh, setMesh] = useState<MeshStats | null>(null);
  const [kernel, setKernel] = useState<KernelHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<{time: string; up: number; total: number}[]>([]);

  const fetch = async () => {
    setLoading(true);
    try {
      const [svc, msh, krn] = await Promise.all([
        apiGet<any>('/api/system/services'),
        apiGet<any>('/api/v1/mesh/stats').catch(() => null),
        apiGet<any>('/api/v1/kernel/health'),
      ]);
      setServices(svc?.services || []);
      setMesh(msh);
      setKernel(krn);
      const up = (svc?.services || []).filter((s: ServiceStatus) => s.status === 'UP').length;
      setHistory(prev => [...prev.slice(-30), { time: new Date().toLocaleTimeString(), up, total: (svc?.services || []).length }]);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetch(); const t = setInterval(fetch, REFRESH); return () => clearInterval(t); }, []);

  const upCount = services.filter(s => s.status === 'UP').length;
  const downCount = services.length - upCount;

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <span style={{ color: '#e0e0e0', fontSize: 18 }}><DashboardOutlined /> System Diagnostics</span>
        <Space>
          <Tag color={downCount === 0 ? 'green' : 'red'}>{downCount === 0 ? '正常' : `${downCount} DOWN`}</Tag>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={fetch}>Refresh ({REFRESH/1000}s)</Button>
        </Space>
      </Space>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        {[{ title: '服务数', value: `${upCount}/${services.length}`, color: downCount ? '#ff4d4f' : '#52c41a' },
          { title: '网格端点', value: mesh?.total_endpoints || 0, color: '#1677ff' },
          { title: '内核管理器', value: kernel?.totalManagers || 0, color: '#722ed1' },
          { title: '断路数', value: mesh?.open_circuits || 0, color: mesh?.open_circuits ? '#faad14' : '#52c41a' },
        ].map(s => (
          <Col xs={12} sm={6} key={s.title}>
            <Card size="small" style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
              <Statistic title={<span style={{ color: '#a0a0a0' }}>{s.title}</span>} value={s.value} valueStyle={{ color: s.color, fontSize: 22 }} />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={16}>
        <Col xs={24} lg={14}>
          <Card title={<span style={{ color: '#e0e0e0' }}><ApiOutlined /> Services</span>} size="small"
            style={{ background: '#16213e', borderColor: '#2a2a4a', marginBottom: 16 }}>
            <Table dataSource={services} loading={loading} rowKey="port" size="small" pagination={false}
              columns={[
                { title: '名称', dataIndex: 'name', render: (v: string) => <span style={{ color: '#e0e0e0' }}>{v}</span> },
                { title: '端口', dataIndex: 'port', width: 60 },
                { title: '分组', dataIndex: 'group', width: 70, render: (v: string) => <Tag>{v}</Tag> },
                { title: '状态', dataIndex: 'status', width: 80,
                  render: (v: string) => <Badge status={v === 'UP' ? 'success' : 'error'} text={v} /> },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title={<span style={{ color: '#e0e0e0' }}><ThunderboltOutlined /> Health Timeline</span>} size="small"
            style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
            <Timeline items={history.slice(-10).map(h => ({
              color: h.up === h.total ? 'green' : 'red',
              children: <span style={{ color: '#a0a0a0', fontSize: 12 }}>{h.time} — {h.up}/{h.total} UP</span>,
            }))} />
          </Card>
          {kernel && (
            <Card title="Kernel Managers" size="small" style={{ background: '#16213e', borderColor: '#2a2a4a', marginTop: 16 }}>
              {Object.entries(kernel.managers || {}).map(([name]) => (
                <div key={name} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                  <span style={{ color: '#a0a0a0' }}>{name}</span>
                  <Badge status="success" text="UP" />
                </div>
              ))}
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
};

export default SystemDiagnostics;
