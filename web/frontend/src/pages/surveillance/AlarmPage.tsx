import React, { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Button, Space, Typography, message, Row, Col, Card, Statistic, Modal, Input, Empty, Badge } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { BellOutlined, ReloadOutlined, CheckCircleOutlined, AlertOutlined, WarningOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';

const { Title, Text } = Typography;

interface AlarmRecord {
  id: string; alarmType?: string; type?: string; severity: string;
  cameraId?: string; message?: string; description?: string;
  status: string; triggeredAt?: string; createdAt?: string; acknowledgedBy?: string;
}

interface AlarmStats { total: number; by_status: Record<string, number>; }

const severityColors: Record<string, string> = { CRITICAL: 'magenta', critical: 'magenta', HIGH: 'red', high: 'red', MEDIUM: 'orange', medium: 'gold', LOW: 'blue', low: 'blue' };
const statusLabels: Record<string, { color: string; text: string }> = {
  TRIGGERED: { color: 'red', text: '已触发' }, ACTIVE: { color: 'red', text: '活跃' },
  ACKNOWLEDGED: { color: 'orange', text: '已确认' }, RESOLVED: { color: 'green', text: '已解决' },
  DISMISSED: { color: 'default', text: '已忽略' }, pending: { color: 'red', text: '待处理' },
};

const AlarmPage: React.FC = () => {
  const [alarms, setAlarms] = useState<AlarmRecord[]>([]);
  const [stats, setStats] = useState<AlarmStats>({ total: 0, by_status: {} });
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [resolveModal, setResolveModal] = useState<{ open: boolean; id: string }>({ open: false, id: '' });
  const [resolveNote, setResolveNote] = useState('');

  const fetchAlarms = useCallback(async () => {
    setLoading(true);
    try {
      const [alarmData, statsData] = await Promise.all([
        apiGet<any>('/api/v1/alarms'),
        apiGet<AlarmStats>('/api/v1/alarms/stats'),
      ]);
      setAlarms(Array.isArray(alarmData) ? alarmData : []);
      if (statsData) setStats(statsData);
    } catch { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAlarms();
    if (!autoRefresh) return;
    const t = setInterval(fetchAlarms, 10000);
    return () => clearInterval(t);
  }, [autoRefresh, fetchAlarms]);

  const ackAlarm = async (id: string) => {
    try {
      await apiPost(`/api/v1/alarms/${id}/acknowledge`);
      message.success('告警已确认');
      fetchAlarms();
    } catch { message.error('确认失败'); }
  };

  const resolveAlarm = async () => {
    try {
      await apiPost(`/api/v1/alarms/${resolveModal.id}/resolve`, { note: resolveNote });
      message.success('告警已解决');
      setResolveModal({ open: false, id: '' }); setResolveNote('');
      fetchAlarms();
    } catch { message.error('解决失败'); }
  };

  const columns: ColumnsType<AlarmRecord> = [
    { title: 'ID', dataIndex: 'id', width: 80, render: (v: string) => <Text style={{ color: '#64748b', fontSize: 12 }}>{v?.substring(0, 8)}</Text> },
    {
      title: '级别', dataIndex: 'severity', width: 80,
      render: (v: string) => <Tag color={severityColors[v] || 'default'}>{v?.toUpperCase()}</Tag>,
      sorter: (a, b) => { const o = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']; return o.indexOf(a.severity?.toUpperCase() || '') - o.indexOf(b.severity?.toUpperCase() || ''); },
    },
    { title: '类型', dataIndex: 'type', width: 80, render: (v: string) => v || '—' },
    { title: '摄像头', dataIndex: 'cameraId', width: 90, render: (v: string) => <Tag>{v || '—'}</Tag> },
    { title: '描述', dataIndex: 'message', ellipsis: true, render: (v: string, r: AlarmRecord) => v || r.description || '—' },
    {
      title: '状态', dataIndex: 'status', width: 90,
      render: (v: string) => {
        const cfg = statusLabels[v] || { color: 'default', text: v };
        return <Badge status={cfg.color === 'red' ? 'error' : cfg.color === 'orange' ? 'processing' : cfg.color === 'green' ? 'success' : 'default'} text={cfg.text} />;
      },
    },
    {
      title: '时间', dataIndex: 'createdAt', width: 160, sorter: (a, b) => new Date(a.createdAt || '').getTime() - new Date(b.createdAt || '').getTime(),
      render: (v: string) => <Text style={{ color: '#a0a0a0', fontSize: 12 }}>{v ? new Date(v).toLocaleString() : '—'}</Text>,
    },
    {
      title: '操作', key: 'actions', width: 160,
      render: (_: any, r: AlarmRecord) => (
        <Space size="small">
          {r.status !== 'RESOLVED' && r.status !== 'DISMISSED' && (
            <>
              <Button size="small" type="link" icon={<CheckCircleOutlined />}
                onClick={() => ackAlarm(r.id)} disabled={r.status === 'ACKNOWLEDGED'}>确认</Button>
              <Button size="small" type="link" danger
                onClick={() => setResolveModal({ open: true, id: r.id })}>解决</Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  const activeCount = stats.by_status?.TRIGGERED || 0;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ color: '#e0e0e0', margin: 0 }}>
          <BellOutlined /> 智能布控告警
          {activeCount > 0 && <Badge count={activeCount} style={{ marginLeft: 8, backgroundColor: '#ff4d4f' }} />}
        </Title>
        <Space>
          <Button size="small" onClick={() => setAutoRefresh(!autoRefresh)} type={autoRefresh ? 'primary' : 'default'}>
            {autoRefresh ? '自动刷新中' : '手动刷新'}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchAlarms} loading={loading}>刷新</Button>
        </Space>
      </div>

      {/* Stats Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {[
          { title: '总告警', value: stats.total || alarms.length, icon: <AlertOutlined />, color: '#1677ff' },
          { title: '未处理', value: activeCount, icon: <ThunderboltOutlined />, color: '#ff4d4f' },
          { title: '已确认', value: stats.by_status?.ACKNOWLEDGED || 0, icon: <WarningOutlined />, color: '#faad14' },
          { title: '已解决', value: stats.by_status?.RESOLVED || 0, icon: <CheckCircleOutlined />, color: '#52c41a' },
        ].map(card => (
          <Col xs={24} sm={12} lg={6} key={card.title}>
            <Card hoverable style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
              bodyStyle={{ padding: '16px' }}>
              <Statistic title={<Text style={{ color: '#a0a0a0' }}>{card.title}</Text>}
                value={card.value} valueStyle={{ color: card.color, fontSize: 28, fontWeight: 700 }}
                prefix={card.icon} />
            </Card>
          </Col>
        ))}
      </Row>

      {/* Alarm Table */}
      <Card title={<span style={{ color: '#e0e0e0' }}>告警列表</span>} style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
        bodyStyle={{ padding: 0 }}>
        {alarms.length > 0 ? (
          <Table columns={columns} dataSource={alarms} rowKey="id" loading={loading}
            pagination={{ pageSize: 15, showSizeChanger: true, showTotal: (t: number) => `共 ${t} 条` }}
            style={{ background: 'transparent' }} size="small"
            rowClassName={(r: AlarmRecord) => r.severity === 'critical' ? 'alarm-row-critical' : ''} />
        ) : (
          <Empty description="暂无告警" style={{ padding: 40 }} image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      {/* Resolve Modal */}
      <Modal title="解决告警" open={resolveModal.open} onOk={resolveAlarm}
        onCancel={() => setResolveModal({ open: false, id: '' })} okText="确认解决">
        <Input.TextArea rows={3} placeholder="解决方案备注..." value={resolveNote}
          onChange={e => setResolveNote(e.target.value)} />
      </Modal>
    </div>
  );
};

export default AlarmPage;
