import React from 'react';
import { Card, Table, Tag, Typography, Row, Col, Space, Input } from 'antd';
import { ApiOutlined, CheckCircleOutlined, SearchOutlined } from '@ant-design/icons';
import { useState } from 'react';

const { Title, Text } = Typography;

interface ApiEndpoint { method: string; path: string; module: string; description: string; status: string; }

const ENDPOINTS: ApiEndpoint[] = [
  { method: 'POST', path: '/api/v1/auth/login', module: 'Auth', description: 'JWT login', status: 'active' },
  { method: 'GET', path: '/api/v1/admin/users', module: 'Admin', description: 'User management', status: 'active' },
  { method: 'GET', path: '/api/v1/admin/roles', module: 'Admin', description: 'Role management', status: 'active' },
  { method: 'GET', path: '/api/v1/cameras', module: 'Camera', description: 'Camera list', status: 'active' },
  { method: 'GET', path: '/api/v1/cameras/stats', module: 'Camera', description: 'Camera statistics', status: 'active' },
  { method: 'GET', path: '/api/v1/cases', module: 'Case', description: 'Case list', status: 'active' },
  { method: 'GET', path: '/api/v1/cases/stats', module: 'Case', description: 'Case statistics', status: 'active' },
  { method: 'GET', path: '/api/v1/alarms', module: 'Alarm', description: 'Alarm list', status: 'active' },
  { method: 'GET', path: '/api/v1/alarms/stats', module: 'Alarm', description: 'Alarm statistics', status: 'active' },
  { method: 'GET', path: '/api/v1/alarms/rules', module: 'Alarm', description: 'Alarm rules', status: 'active' },
  { method: 'GET', path: '/api/v1/agents', module: '智能体', description: 'Agent list', status: 'active' },
  { method: 'POST', path: '/api/v1/agents/plan', module: '智能体', description: 'AI task planning', status: 'active' },
  { method: 'POST', path: '/api/v1/agents/search', module: '智能体', description: 'Intelligent search', status: 'active' },
  { method: 'POST', path: '/api/v1/agents/llm/chat', module: '智能体', description: 'LLM chat', status: 'active' },
  { method: 'POST', path: '/api/v1/agents/orchestrate', module: '智能体', description: 'Multi-agent orchestration', status: 'active' },
  { method: 'POST', path: '/api/v1/agents/memory/remember', module: '智能体', description: 'Memory storage', status: 'active' },
  { method: 'POST', path: '/api/v1/agents/memory/recall', module: '智能体', description: 'Memory retrieval', status: 'active' },
  { method: 'GET', path: '/api/v1/capabilities', module: 'Capability', description: 'Capability list', status: 'active' },
  { method: 'POST', path: '/api/v1/capabilities/benchmark', module: 'Capability', description: 'Model benchmark', status: 'active' },
  { method: 'POST', path: '/api/v1/models/hot-swap', module: 'Model', description: 'Model hot-swap', status: 'active' },
  { method: 'POST', path: '/api/v1/models/init-demo', module: 'Model', description: 'Initialize demo models', status: 'active' },
  { method: 'GET', path: '/api/v1/knowledge/entities', module: 'Knowledge', description: 'Knowledge entities', status: 'active' },
  { method: 'GET', path: '/api/v1/knowledge/graph', module: 'Knowledge', description: 'Knowledge graph', status: 'active' },
  { method: 'POST', path: '/api/v1/knowledge/graphrag/query', module: 'Knowledge', description: 'GraphRAG query', status: 'active' },
  { method: 'GET', path: '/api/v1/reports', module: 'Report', description: 'Report list', status: 'active' },
  { method: 'GET', path: '/api/v1/workflows', module: 'Workflow', description: 'Workflow list', status: 'active' },
  { method: 'GET', path: '/api/v1/trajectory/search', module: 'Trajectory', description: 'Trajectory search', status: 'active' },
  { method: 'GET', path: '/api/v1/trajectory/stats', module: 'Trajectory', description: 'Trajectory statistics', status: 'active' },
  { method: 'GET', path: '/api/v1/search/collections', module: 'Search', description: 'Search collections', status: 'active' },
  { method: 'GET', path: '/api/v1/analysis/stats', module: 'Analysis', description: 'Analysis statistics', status: 'active' },
  { method: 'GET', path: '/api/v1/kernel/models', module: 'Kernel', description: 'Kernel models', status: 'active' },
  { method: 'GET', path: '/api/v1/prompts', module: 'Prompt', description: 'Prompt templates', status: 'active' },
  { method: 'POST', path: '/api/v1/prompts/render', module: 'Prompt', description: 'Render prompt', status: 'active' },
  { method: 'GET', path: '/api/v1/security/roles', module: 'Security', description: 'Security roles', status: 'active' },
  { method: 'GET', path: '/api/v1/policies', module: 'Policy', description: 'Policy list', status: 'active' },
  { method: 'POST', path: '/api/v1/reasoning/reason', module: 'Reasoning', description: 'Reasoning engine', status: 'active' },
  { method: 'GET', path: '/api/v1/video/streams', module: 'Video', description: 'Video streams', status: 'active' },
  { method: 'POST', path: '/api/v1/video/snapshot/{id}', module: 'Video', description: 'Capture snapshot', status: 'active' },
  { method: 'GET', path: '/api/v1/system/metrics', module: 'System', description: 'System metrics', status: 'active' },
  { method: 'POST', path: '/api/v1/data/enriched', module: 'Data', description: 'Enriched demo data', status: 'active' },
];

const methodColors: Record<string, string> = { GET: 'green', POST: 'blue', PUT: 'orange', DELETE: 'red' };

const ApiDocs: React.FC = () => {
  const [search, setSearch] = useState('');
  const filtered = ENDPOINTS.filter(e =>
    !search || e.path.includes(search) || e.description.includes(search) || e.module.includes(search)
  );
  const modules = [...new Set(ENDPOINTS.map(e => e.module))];

  const columns = [
    { title: 'Method', dataIndex: 'method', width: 70, render: (v: string) => <Tag color={methodColors[v]}>{v}</Tag> },
    { title: 'Path', dataIndex: 'path', render: (v: string) => <Text code style={{ color: '#e0e0e0' }}>{v}</Text> },
    { title: 'Module', dataIndex: 'module', width: 100, render: (v: string) => <Tag>{v}</Tag> },
    { title: '描述', dataIndex: 'description' },
    { title: '状态', dataIndex: 'status', width: 70, render: () => <CheckCircleOutlined style={{ color: '#52c41a' }} /> },
  ];

  return (
    <div>
      <Title level={4} style={{ color: '#e0e0e0' }}><ApiOutlined /> API 文档</Title>
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12}><Input prefix={<SearchOutlined />} placeholder="搜索 API..." value={search} onChange={e => setSearch(e.target.value)} /></Col>
        <Col xs={24} sm={12}><Space wrap>{modules.map(m => <Tag key={m} color="blue" style={{ cursor: 'pointer' }} onClick={() => setSearch(m)}>{m}</Tag>)}</Space></Col>
      </Row>
      <Card bodyStyle={{ padding: 0 }} style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
        <Table columns={columns} dataSource={filtered} rowKey="path" size="small" pagination={{ pageSize: 20 }} style={{ background: 'transparent' }} />
      </Card>
      <Text style={{ color: '#64748b', marginTop: 8, display: 'block' }}>{ENDPOINTS.length} endpoints across {modules.length} modules</Text>
    </div>
  );
};

export default ApiDocs;
