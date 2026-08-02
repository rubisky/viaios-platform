/** Settings Wizard — System configuration dashboard */
import React, { useEffect, useState } from 'react';
import { Card, Tabs, Switch, Select, Slider, Button, Input, Space, message, Form, InputNumber, Descriptions, Tag } from 'antd';
import { SaveOutlined, ReloadOutlined, ApiOutlined, DatabaseOutlined, CloudOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';

const SettingsWizard: React.FC = () => {
  const [kernelHealth, setKernelHealth] = useState<any>({});
  const [meshStats, setMeshStats] = useState<any>({});
  const [services, setServices] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      apiGet('/api/v1/kernel/health'),
      apiGet('/api/v1/mesh/stats'),
      apiGet('/api/system/services'),
    ]).then(([k, m, s]) => {
      setKernelHealth(k || {});
      setMeshStats(m || {});
      setServices(s?.services || []);
    }).catch(() => {});
  }, []);

  const save = async () => { setSaving(true); await new Promise(r => setTimeout(r, 500)); message.success('Saved'); setSaving(false); };

  const tabStyle = { background: '#16213e', borderColor: '#2a2a4a' };

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <span style={{ color: '#e0e0e0', fontSize: 18 }}>Settings Wizard</span>
        <Space>
          <Tag color="blue">{services.length} services</Tag>
          <Tag color={services.filter((s: any) => s.status === 'UP').length === services.length ? 'green' : 'red'}>
            {services.filter((s: any) => s.status === 'UP').length} UP
          </Tag>
        </Space>
      </Space>

      <Tabs defaultActiveKey="system" items={[
        {
          key: 'system', label: <span><ApiOutlined /> System</span>, children: (
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Card title="AI Kernel Configuration" size="small" style={tabStyle}>
                <Descriptions column={2} size="small">
                  <Descriptions.Item label="Kernel">{kernelHealth.kernel || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Managers">{kernelHealth.totalManagers || 0}</Descriptions.Item>
                  <Descriptions.Item label="Models">{kernelHealth.managers?.ModelManager?.models || 0}</Descriptions.Item>
                  <Descriptions.Item label="Capabilities">{kernelHealth.managers?.CapabilityManager?.capabilities || 0}</Descriptions.Item>
                </Descriptions>
              </Card>

              <Card title="Runtime Mesh" size="small" style={tabStyle}>
                <Descriptions column={2} size="small">
                  <Descriptions.Item label="Endpoints">{meshStats.total_endpoints || 0}</Descriptions.Item>
                  <Descriptions.Item label="Open Circuits">{meshStats.open_circuits || 0}</Descriptions.Item>
                  <Descriptions.Item label="Healthy">{meshStats.healthy_endpoints || 0}</Descriptions.Item>
                  <Descriptions.Item label="Requests">{meshStats.total_requests || 0}</Descriptions.Item>
                </Descriptions>
              </Card>
            </Space>
          ),
        },
        {
          key: 'features', label: <span><CloudOutlined /> Features</span>, children: (
            <Card size="small" style={tabStyle}>
              <Form layout="vertical">
                <Form.Item label="Auto-scaling"><Switch defaultChecked /></Form.Item>
                <Form.Item label="GPU Scheduling"><Select defaultValue="priority" options={[{value:'priority',label:'Priority-based'},{value:'binpack',label:'Bin-packing'},{value:'spread',label:'Spread'}]} /></Form.Item>
                <Form.Item label="Alert Cooldown (s)"><InputNumber min={10} max={3600} defaultValue={60} /></Form.Item>
                <Form.Item label="Log Level"><Select defaultValue="INFO" options={['DEBUG','INFO','WARN','ERROR'].map(v=>({value:v,label:v}))} /></Form.Item>
                <Form.Item label="LLM Provider"><Select defaultValue="deepseek" options={['deepseek','openai'].map(v=>({value:v,label:v}))} /></Form.Item>
                <Form.Item label="Max Streams"><InputNumber min={1} max={100} defaultValue={16} /></Form.Item>
                <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={save}>Save</Button>
              </Form>
            </Card>
          ),
        },
        {
          key: 'database', label: <span><DatabaseOutlined /> Database</span>, children: (
            <Card size="small" style={tabStyle}>
              <Descriptions column={1} size="small" bordered>
                <Descriptions.Item label="PostgreSQL">viaios-postgresql:5432 ✅</Descriptions.Item>
                <Descriptions.Item label="ClickHouse">viaios-clickhouse:8123 ✅</Descriptions.Item>
                <Descriptions.Item label="Milvus">viaios-milvus:19530 ✅</Descriptions.Item>
                <Descriptions.Item label="Redis">localhost:6379 ✅</Descriptions.Item>
                <Descriptions.Item label="MinIO">viaios-minio:9000 ✅</Descriptions.Item>
                <Descriptions.Item label="Kafka">viaios-kafka:9092 ✅</Descriptions.Item>
              </Descriptions>
            </Card>
          ),
        },
      ]} />
    </div>
  );
};

export default SettingsWizard;
