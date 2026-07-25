import React, { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Button, Space, Typography, message, Row, Col, Card, Statistic, Modal, Input, Badge, Tabs, Switch, Select, Empty } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { BellOutlined, ReloadOutlined, CheckCircleOutlined, AlertOutlined, WarningOutlined, ThunderboltOutlined, SettingOutlined, DownloadOutlined, FilterOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';

const { Title, Text } = Typography;

interface AlarmRecord { id: string; type?: string; severity: string; cameraId?: string; camera?: string; message?: string; location?: string; status: string; triggeredAt?: string; createdAt?: string; }
interface AlarmStats { total: number; by_status: Record<string, number>; }

const severityColors: Record<string, string> = { CRITICAL: 'magenta', HIGH: 'red', MEDIUM: 'orange', LOW: 'blue' };
const statusLabels: Record<string, { color: string; text: string }> = {
  TRIGGERED: { color: 'red', text: '已触发' }, ACKNOWLEDGED: { color: 'orange', text: '已确认' },
  RESOLVED: { color: 'green', text: '已解决' }, DISMISSED: { color: 'default', text: '已忽略' },
};

const AlarmPage: React.FC = () => {
  const [alarms, setAlarms] = useState<AlarmRecord[]>([]);
  const [stats, setStats] = useState<AlarmStats>({ total: 0, by_status: {} });
  const [rules, setRules] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [resolveModal, setResolveModal] = useState<{ open: boolean; id: string }>({ open: false, id: '' });
  const [resolveNote, setResolveNote] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [activeTab, setActiveTab] = useState('alarms');
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [newSinceLastRefresh, setNewSinceLastRefresh] = useState(0);

  const fetchAlarms = useCallback(async () => {
    setLoading(true);
    try {
      const [alarmData, statsData, rulesData] = await Promise.all([
        apiGet<any>('/api/v1/alarms'),
        apiGet<AlarmStats>('/api/v1/alarms/stats'),
        apiGet<any>('/api/v1/alarms/rules'),
      ]);
      setAlarms(Array.isArray(alarmData) ? alarmData : []);
      if (statsData) setStats(statsData);
      if (Array.isArray(rulesData)) setRules(rulesData);
      // Detect new alarms since last refresh
      const prevCount = alarms.length;
      const newAlarms = Array.isArray(alarmData) ? alarmData : [];
      if (prevCount > 0 && newAlarms.length > prevCount) {
        const diff = newAlarms.length - prevCount;
        setNewSinceLastRefresh(prev => prev + diff);
        if (soundEnabled && diff > 0) {
          try { const ctx = new (window as any).AudioContext(); const osc = ctx.createOscillator(); const gain = ctx.createGain(); osc.connect(gain); gain.connect(ctx.destination); osc.frequency.value = 880; gain.gain.value = 0.1; osc.start(); osc.stop(ctx.currentTime + 0.15); } catch {}
        }
      }
      setAlarms(newAlarms);
    } catch {}
    setLoading(false);
  }, [alarms.length, soundEnabled]);

  useEffect(() => {
    fetchAlarms();
    if (!autoRefresh) return;
    const t = setInterval(fetchAlarms, 8000);
    return () => clearInterval(t);
  }, [autoRefresh, fetchAlarms]);

  const ackAlarm = async (id: string) => {
    try { await apiPost(`/api/v1/alarms/${id}/acknowledge`); message.success('已确认'); fetchAlarms(); }
    catch { message.error('确认失败'); }
  };

  const resolveAlarm = async () => {
    try { await apiPost(`/api/v1/alarms/${resolveModal.id}/resolve`, { note: resolveNote }); message.success('已解决'); setResolveModal({ open: false, id: '' }); setResolveNote(''); fetchAlarms(); }
    catch { message.error('解决失败'); }
  };

  const batchAck = async () => {
    try { for (const id of selectedRowKeys) await apiPost(`/api/v1/alarms/${id}/acknowledge`); message.success(`已确认 ${selectedRowKeys.length} 条`); setSelectedRowKeys([]); fetchAlarms(); }
    catch { message.error('批量确认失败'); }
  };

  const simulateAlarm = async () => {
    try { const r = await apiPost<any>('/api/v1/alarms/simulate'); message.success(`模拟告警: ${r?.alarm?.type || 'unknown'}`); fetchAlarms(); }
    catch { message.error('模拟失败'); }
  };

  const filtered = severityFilter === 'all' ? alarms : alarms.filter(a => a.severity?.toUpperCase() === severityFilter);

  const columns: ColumnsType<AlarmRecord> = [
    { title: 'ID', dataIndex: 'id', width: 70, render: (v: string) => <Text style={{ color: '#64748b', fontSize: 11 }}>{v?.substring(0, 8)}</Text> },
    { title: '级别', dataIndex: 'severity', width: 80, render: (v: string) => <Tag color={severityColors[v?.toUpperCase()] || 'default'}>{v?.toUpperCase()}</Tag>, sorter: (a, b) => ['CRITICAL','HIGH','MEDIUM','LOW'].indexOf(a.severity?.toUpperCase()||'') - ['CRITICAL','HIGH','MEDIUM','LOW'].indexOf(b.severity?.toUpperCase()||'') },
    { title: '类型', dataIndex: 'type', width: 90, render: (v: string) => <Tag>{v || '—'}</Tag> },
    { title: '位置', dataIndex: 'location', width: 100, render: (v: string) => v || '—' },
    { title: '摄像头', dataIndex: 'cameraId', width: 80, render: (v: string) => <Tag color="blue">{v || '—'}</Tag> },
    { title: '描述', dataIndex: 'message', ellipsis: true, render: (v: string) => v || '—' },
    { title: '状态', dataIndex: 'status', width: 80, render: (v: string) => { const cfg = statusLabels[v] || { color: 'default', text: v }; return <Badge status={cfg.color === 'red' ? 'error' : cfg.color === 'orange' ? 'processing' : 'success'} text={cfg.text} />; } },
    { title: '时间', dataIndex: 'createdAt', width: 140, sorter: (a: any, b: any) => new Date(a.createdAt || '').getTime() - new Date(b.createdAt || '').getTime(), render: (v: string) => <Text style={{ color: '#a0a0a0', fontSize: 11 }}>{v ? new Date(v).toLocaleString() : '—'}</Text> },
    {
      title: '操作', width: 100,
      render: (_: any, r: AlarmRecord) => (
        <Space size="small">
          {r.status !== 'RESOLVED' && <Button size="small" type="link" onClick={() => ackAlarm(r.id)} disabled={r.status === 'ACKNOWLEDGED'}>确认</Button>}
          {r.status !== 'RESOLVED' && <Button size="small" type="link" danger onClick={() => setResolveModal({ open: true, id: r.id })}>解决</Button>}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ color: '#e0e0e0', margin: 0 }}><BellOutlined /> 智能告警 <Badge count={stats.by_status?.TRIGGERED || 0} style={{ backgroundColor: '#ff4d4f' }} /> {newSinceLastRefresh > 0 && <Badge count={`+${newSinceLastRefresh}`} style={{ backgroundColor: '#faad14', marginLeft: 8 }} />}</Title>
        <Space>
          <Button onClick={() => { setSoundEnabled(!soundEnabled); if (!soundEnabled) message.info('声音告警已开启'); else message.info('声音告警已关闭'); }} type={soundEnabled ? 'primary' : 'default'} size="small" danger={soundEnabled}>🔊 {soundEnabled ? '静音' : '声音'}</Button>
          <Button onClick={simulateAlarm} icon={<ThunderboltOutlined />}>模拟告警</Button>
          <Button onClick={() => setAutoRefresh(!autoRefresh)} type={autoRefresh ? 'primary' : 'default'} size="small">{autoRefresh ? '自动刷新' : '手动'}</Button>
          <Button icon={<ReloadOutlined />} onClick={fetchAlarms} loading={loading}>刷新</Button>
        </Space>
      </div>

      {/* Stats */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {[
          { title: '未处理', value: alarms.filter(a => a.status === 'TRIGGERED' || a.status === 'ACTIVE').length, icon: <ThunderboltOutlined />, color: '#ff4d4f' },
          { title: '已确认', value: stats.by_status?.ACKNOWLEDGED || 0, icon: <WarningOutlined />, color: '#faad14' },
          { title: '已解决', value: stats.by_status?.RESOLVED || 0, icon: <CheckCircleOutlined />, color: '#52c41a' },
          { title: '总计', value: stats.total || alarms.length, icon: <AlertOutlined />, color: '#1677ff' },
        ].map(card => (
          <Col xs={12} sm={6} key={card.title}>
            <Card hoverable size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
              <Statistic title={<Text style={{ color: '#a0a0a0', fontSize: 11 }}>{card.title}</Text>} value={card.value} valueStyle={{ color: card.color, fontSize: 22, fontWeight: 700 }} prefix={card.icon} />
            </Card>
          </Col>
        ))}
      </Row>

      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        {
          key: 'alarms', label: <span><BellOutlined /> 告警列表</span>,
          children: (
            <>
              {/* Filter + Batch */}
              <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a', marginBottom: 12 }}>
                <Space wrap>
                  <FilterOutlined style={{ color: '#a0a0a0' }} />
                  <Select value={severityFilter} onChange={setSeverityFilter} size="small" style={{ width: 100 }}
                    options={[{ value: 'all', label: '全部级别' }, { value: 'CRITICAL', label: '严重' }, { value: 'HIGH', label: '高级' }, { value: 'MEDIUM', label: '中级' }]} />
                  {selectedRowKeys.length > 0 && <Button size="small" onClick={batchAck}>批量确认 ({selectedRowKeys.length})</Button>}
                  <Button size="small" icon={<DownloadOutlined />} onClick={() => { const csv = 'ID,Type,Severity,Status,Location\n' + filtered.map(a => [a.id?.substring(0,8), a.type, a.severity, a.status, a.location].join(',')).join('\n'); const blob = new Blob(['﻿' + csv], { type: 'text/csv' }); const url = URL.createObjectURL(blob); const aEl = document.createElement('a'); aEl.href = url; aEl.download = '告警.csv'; aEl.click(); }}>导出CSV</Button>
                </Space>
              </Card>
              <Card bodyStyle={{ padding: 0 }} style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
                {filtered.length > 0 ? (
                  <Table columns={columns} dataSource={filtered} rowKey="id" loading={loading} size="small" pagination={{ pageSize: 15, showTotal: (t: number) => `共 ${t} 条` }}
                    rowSelection={{ selectedRowKeys, onChange: (keys: React.Key[]) => setSelectedRowKeys(keys as string[]) }} style={{ background: 'transparent' }} />
                ) : <Empty description="暂无告警" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ padding: 40 }} />}
              </Card>
            </>
          ),
        },
        {
          key: 'rules', label: <span><SettingOutlined /> 告警规则 ({rules.length})</span>,
          children: (
            <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
              {rules.map(r => (
                <Card key={r.id} size="small" style={{ background: '#0f0f23', border: '1px solid #334155', marginBottom: 8 }}>
                  <Space style={{ width: '100%', justifyContent: 'space-between', display: 'flex' }}>
                    <Space>
                      <Tag color={r.severity === 'CRITICAL' ? 'magenta' : r.severity === 'HIGH' ? 'red' : 'blue'}>{r.severity || 'MEDIUM'}</Tag>
                      <Text strong style={{ color: '#e0e0e0' }}>{r.name}</Text>
                      <Tag>{r.type}</Tag>
                    </Space>
                    <Space>
                      <Switch checked={r.enabled} disabled size="small" />
                      <Text style={{ color: r.enabled ? '#52c41a' : '#ff4d4f', fontSize: 11 }}>{r.enabled ? '启用' : '禁用'}</Text>
                    </Space>
                  </Space>
                  {r.condition && <Text style={{ color: '#64748b', fontSize: 11, marginTop: 4, display: 'block' }}>触发条件: {JSON.stringify(r.condition)}</Text>}
                </Card>
              ))}
              {rules.length === 0 && <Empty description="暂无规则" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
            </Card>
          ),
        },
      ]} />

      <Modal title="解决告警" open={resolveModal.open} onOk={resolveAlarm} onCancel={() => setResolveModal({ open: false, id: '' })} okText="确认解决">
        <Input.TextArea rows={3} placeholder="解决方案备注..." value={resolveNote} onChange={e => setResolveNote(e.target.value)} />
      </Modal>
    </div>
  );
};

export default AlarmPage;
