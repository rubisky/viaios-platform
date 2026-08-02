/** Model Management — AI Kernel model lifecycle dashboard (P2-4) */
import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Modal, Descriptions, message, Statistic, Row, Col, Input, Select, Badge } from 'antd';
import { CloudUploadOutlined, RocketOutlined, PauseCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';

interface Model { id: string; name: string; version: string; runtime: string; task: string; status: string; precision: string; gpuMemoryMb: number; avgLatencyMs?: number; createdAt: string; }
interface Capability { id: string; domain: string; displayName: string; category: string; status: string; bindingCount: number; }

const statusColor: Record<string, string> = {
  ACTIVE: 'green', REGISTERED: 'blue', VALIDATED: 'cyan', DEPLOYING: 'orange',
  FAILED: 'red', RETIRED: 'default', ROLLING_BACK: 'magenta',
};

const ModelManagement: React.FC = () => {
  const [models, setModels] = useState<Model[]>([]);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Model | null>(null);
  const [filter, setFilter] = useState('');

  const fetch = async () => {
    setLoading(true);
    try {
      const [m, c] = await Promise.all([
        apiGet<any>('/api/v1/kernel/models'),
        apiGet<any>('/api/v1/kernel/capabilities'),
      ]);
      setModels(m?.models || []);
      setCapabilities(c?.capabilities || []);
    } catch { message.error('Failed to load'); }
    setLoading(false);
  };

  useEffect(() => { fetch(); }, []);

  const deploy = async (id: string) => {
    await apiPost(`/api/v1/kernel/models/${id}/deploy`, { instanceCount: 1, gpuCount: 1, memoryMb: 4096 });
    message.success('Deploy initiated');
    fetch();
  };

  const filtered = models.filter(m => !filter || m.task === filter || m.runtime === filter || m.status === filter || m.name.includes(filter));

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }} wrap>
        <Space>
          <Select style={{ width: 120 }} placeholder="Runtime" allowClear onChange={setFilter}
            options={['ONNX','TENSORRT','TRITON','VLLM'].map(v => ({value:v,label:v}))} />
          <Select style={{ width: 130 }} placeholder="Task" allowClear onChange={setFilter}
            options={['detection','face_recognition','person_reid','vehicle_recog','pose_estimation','vlm','embedding'].map(v => ({value:v,label:v}))} />
          <Input.Search placeholder="Search models..." style={{ width: 200 }} onSearch={setFilter} allowClear />
          <Button icon={<ReloadOutlined />} onClick={fetch}>Refresh</Button>
        </Space>
        <Button type="primary" icon={<CloudUploadOutlined />}>Register Model</Button>
      </Space>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        {[
          { title: 'Total Models', value: models.length, color: '#1677ff' },
          { title: 'Active', value: models.filter(m => m.status === 'ACTIVE').length, color: '#52c41a' },
          { title: 'Capabilities', value: capabilities.length, color: '#722ed1' },
          { title: 'Avg Latency', value: `${Math.round(models.reduce((s, m) => s + (m.avgLatencyMs || 0), 0) / Math.max(models.length, 1))}ms`, color: '#fa8c16' },
        ].map(s => (
          <Col xs={12} sm={6} key={s.title}>
            <Card size="small" style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
              <Statistic title={<span style={{ color: '#a0a0a0' }}>{s.title}</span>} value={s.value} valueStyle={{ color: s.color, fontSize: 20 }} />
            </Card>
          </Col>
        ))}
      </Row>

      <Table dataSource={filtered} loading={loading} rowKey="id" size="small"
        onRow={r => ({ onClick: () => setSelected(r), style: { cursor: 'pointer' } })}
        style={{ background: '#16213e' }}
        columns={[
          { title: 'Name', dataIndex: 'name', render: (v: string, r: Model) => <><Badge status={r.status === 'ACTIVE' ? 'success' : 'processing'} /><span style={{ color: '#e0e0e0' }}>{v}</span></> },
          { title: 'Version', dataIndex: 'version', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Runtime', dataIndex: 'runtime', render: (v: string) => <Tag color="blue">{v}</Tag> },
          { title: 'Task', dataIndex: 'task', render: (v: string) => <Tag color="purple">{v}</Tag> },
          { title: 'Status', dataIndex: 'status', render: (v: string) => <Tag color={statusColor[v] || 'default'}>{v}</Tag> },
          { title: 'Precision', dataIndex: 'precision' },
          { title: 'GPU', dataIndex: 'gpuMemoryMb', render: (v: number) => v ? `${v}MB` : '-' },
          {
            title: 'Actions', render: (_: any, r: Model) => (
              <Space size="small">
                {r.status === 'VALIDATED' && <Button size="small" type="primary" icon={<RocketOutlined />} onClick={e => { e.stopPropagation(); deploy(r.id); }}>Deploy</Button>}
                {r.status === 'ACTIVE' && <Button size="small" icon={<PauseCircleOutlined />} onClick={e => e.stopPropagation()}>Pause</Button>}
              </Space>
            ),
          },
        ]}
      />

      <Modal open={!!selected} onCancel={() => setSelected(null)} footer={null} width={700} title={selected?.name}>
        {selected && (
          <Descriptions column={2} size="small" bordered style={{ background: '#0f0f23' }}>
            <Descriptions.Item label="ID">{selected.id}</Descriptions.Item>
            <Descriptions.Item label="Status"><Tag color={statusColor[selected.status]}>{selected.status}</Tag></Descriptions.Item>
            <Descriptions.Item label="Version">{selected.version}</Descriptions.Item>
            <Descriptions.Item label="Runtime">{selected.runtime}</Descriptions.Item>
            <Descriptions.Item label="Task">{selected.task}</Descriptions.Item>
            <Descriptions.Item label="Precision">{selected.precision}</Descriptions.Item>
            <Descriptions.Item label="GPU Memory">{selected.gpuMemoryMb}MB</Descriptions.Item>
            <Descriptions.Item label="Avg Latency">{selected.avgLatencyMs || '—'}ms</Descriptions.Item>
            <Descriptions.Item label="Created">{selected.createdAt}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default ModelManagement;
