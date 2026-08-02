/** Alarm Center — Real-time alarm monitoring dashboard */
import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Statistic, Row, Col, Select } from 'antd';
import { BellOutlined, CheckOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';

const sevColor: Record<string, string> = { CRITICAL: 'red', HIGH: 'orange', MEDIUM: 'gold', LOW: 'blue', INFO: 'default' };
const REFRESH = 8000;

const AlarmCenter: React.FC = () => {
  const [alarms, setAlarms] = useState<any[]>([]);
  const [rules, setRules] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');

  const fetch = async () => {
    setLoading(true);
    try {
      const [a, r, s] = await Promise.all([
        apiGet<any>(`/api/v1/surveillance/alarms${filter ? `?severity=${filter}` : ''}`),
        apiGet<any>('/api/v1/surveillance/rules'),
        apiGet<any>('/api/v1/surveillance/stats'),
      ]);
      setAlarms(a?.alarms || []); setRules(r?.rules || []); setStats(s || {});
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetch(); const t = setInterval(fetch, REFRESH); return () => clearInterval(t); }, [filter]);

  const ack = async (id: string) => { await apiPost(`/api/v1/surveillance/alarms/${id}/acknowledge`); fetch(); };
  const resolve = async (id: string) => { await apiPost(`/api/v1/surveillance/alarms/${id}/resolve`); fetch(); };

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <span style={{ color: '#e0e0e0', fontSize: 18 }}><BellOutlined /> Alarm Center</span>
        <Space>
          <Select style={{ width: 120 }} placeholder="Severity" allowClear onChange={(v: any) => setFilter(v || '')}
            options={['CRITICAL','HIGH','MEDIUM','LOW','INFO'].map(v=>({value:v,label:v}))} />
          <Button icon={<ReloadOutlined />} loading={loading} onClick={fetch}>Refresh</Button>
        </Space>
      </Space>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        {[{ title: 'Total', value: stats.total_alarms || 0, color: '#1677ff' },
          { title: 'Active', value: stats.active_alarms || 0, color: '#ff4d4f' },
          { title: 'Rules', value: rules.length, color: '#722ed1' },
          { title: 'Critical', value: stats.by_severity?.CRITICAL || 0, color: '#cf1322' },
        ].map(s => (
          <Col xs={12} sm={6} key={s.title}><Card size="small" style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
            <Statistic title={<span style={{ color: '#a0a0a0' }}>{s.title}</span>} value={s.value} valueStyle={{ color: s.color, fontSize: 20 }} />
          </Card></Col>
        ))}
      </Row>

      <Card title={<span style={{ color: '#e0e0e0' }}>Active Alarms</span>} style={{ background: '#16213e', borderColor: '#2a2a4a', marginBottom: 16 }}>
        <Table dataSource={alarms} loading={loading} rowKey="id" size="small"
          onRow={r => ({ style: { cursor: 'pointer' } })}
          columns={[
            { title: 'Time', dataIndex: 'triggered_at', width: 80, render: (v: string) => v?.slice(11,19) },
            { title: 'Rule', dataIndex: 'rule', render: (v: string) => <span style={{ color: '#e0e0e0' }}>{v}</span> },
            { title: 'Severity', dataIndex: 'severity', width: 90, render: (v: string) => <Tag color={sevColor[v]}>{v}</Tag> },
            { title: 'Status', dataIndex: 'status', width: 100, render: (v: string) => <Tag>{v}</Tag> },
            { title: 'Message', dataIndex: 'message', ellipsis: true },
            { title: 'Actions', width: 140, render: (_: any, r: any) => (
              <Space size="small">
                {r.status === 'TRIGGERED' && <Button size="small" icon={<CheckOutlined />} onClick={e => { e.stopPropagation(); ack(r.id); }}>Ack</Button>}
                <Button size="small" onClick={e => { e.stopPropagation(); resolve(r.id); }}>Resolve</Button>
              </Space>
            )},
          ]} />
      </Card>

      <Card title="Rules" size="small" style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
        <Table dataSource={rules} rowKey="id" size="small" pagination={false}
          columns={[
            { title: 'Name', dataIndex: 'name' }, { title: 'Severity', dataIndex: 'severity', render: (v: string) => <Tag color={sevColor[v]}>{v}</Tag> },
            { title: 'Cooldown', dataIndex: 'cooldown_s', render: (v: number) => `${v}s` },
            { title: 'Enabled', dataIndex: 'enabled', render: (v: boolean) => v ? <Tag color="green">Yes</Tag> : <Tag color="red">No</Tag> },
          ]} />
      </Card>
    </div>
  );
};

export default AlarmCenter;
