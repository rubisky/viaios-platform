import React, { useCallback, useEffect, useState } from 'react';
import { Card, Button, Tag, Space, Typography, message, Select, Row, Col, Empty } from 'antd';
import { PlayCircleOutlined, ReloadOutlined, ApartmentOutlined, StopOutlined } from '@ant-design/icons';
import ReactFlow, { Background, Controls, MiniMap, Node, Edge, MarkerType, useNodesState, useEdgesState } from 'reactflow';
import 'reactflow/dist/style.css';
import { apiGet, apiPost } from '../../api/client';

const { Title, Text } = Typography;

const NODE_COLORS: Record<string, string> = {
  COMPLETED: '#52c41a', RUNNING: '#1677ff', PENDING: '#d9d9d9', FAILED: '#ff4d4f', CANCELLED: '#faad14',
};

const WorkflowEditor: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState('video-analysis');

  const templates: Record<string, string[]> = {
    'video-analysis': ['Video Ingest', 'Frame Extract', 'Object Detect', 'Tracking', 'Embedding', 'Report'],
    'alarm-handling': ['Alarm Trigger', 'Evaluate', 'Snapshot', 'Case Create', 'Notify'],
    'search-pipeline': ['Query Parse', 'NLU Embed', 'Vector Search', 'Attribute Filter', 'Rank', 'Return'],
  };

  const buildFlow = useCallback((steps: string[]) => {
    const ns: Node[] = steps.map((label, i) => ({
      id: `${i}`, type: 'default',
      data: { label },
      position: { x: i * 180 + 50, y: Math.sin(i * 1.5) * 40 + 60 },
      style: {
        background: '#1a1a2e', color: '#e0e0e0', border: '1px solid #334155',
        borderRadius: 8, padding: '10px 20px', fontSize: 13, width: 140,
      },
    }));
    const es: Edge[] = steps.slice(1).map((_, i) => ({
      id: `e${i}-${i + 1}`, source: `${i}`, target: `${i + 1}`,
      animated: true,
      style: { stroke: '#1677ff', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#1677ff' },
    }));
    setNodes(ns); setEdges(es);
  }, [setNodes, setEdges]);

  useEffect(() => { buildFlow(templates[selectedTemplate]); }, [selectedTemplate, buildFlow]);

  const fetchWorkflows = async () => {
    try {
      const r = await apiGet<any>('/api/v1/workflows/history');
      setWorkflows(Array.isArray(r) ? r.slice(0, 10) : []);
    } catch {}
  };
  useEffect(() => { fetchWorkflows(); }, []);

  const execute = async () => {
    setLoading(true);
    try {
      const r = await apiPost<any>('/api/v1/workflows/execute', {
        workflow: selectedTemplate,
        definition: templates[selectedTemplate].join('->'),
        steps: templates[selectedTemplate].map((name, i) => ({ step: i + 1, name })),
      });
      message.success(`工作流 ${r.workflowId || r.id} 已启动`);
      fetchWorkflows();
    } catch { message.error('执行失败'); }
    setLoading(false);
  };

  const cancel = async (id: string) => {
    try { await apiPost(`/api/v1/workflows/${id}/cancel`); message.success('已取消'); fetchWorkflows(); }
    catch { message.error('取消失败'); }
  };

  const selectTemplate = (name: string) => {
    setSelectedTemplate(name);
    buildFlow(templates[name]);
  };

  return (
    <div>
      <Title level={3} style={{ color: '#e0e0e0', marginBottom: 16 }}>
        <ApartmentOutlined /> 工作流编排
      </Title>

      <Row gutter={[16, 16]}>
        {/* Visual DAG Editor */}
        <Col xs={24} lg={16}>
          <Card title={<span style={{ color: '#e0e0e0' }}>DAG 可视化</span>}
            extra={
              <Space>
                <Select value={selectedTemplate} onChange={selectTemplate} style={{ width: 180 }}>
                  {Object.keys(templates).map(k => (
                    <Select.Option key={k} value={k}>{k}</Select.Option>
                  ))}
                </Select>
                <Button type="primary" icon={<PlayCircleOutlined />} onClick={execute} loading={loading}>
                  执行
                </Button>
              </Space>
            }
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
            bodyStyle={{ padding: 0, height: 400 }}>
            {nodes.length > 0 ? (
              <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
                fitView attributionPosition="bottom-left">
                <Background color="#2a2a4a" gap={20} />
                <Controls />
                <MiniMap style={{ background: '#0f0f23' }} nodeColor="#1677ff" />
              </ReactFlow>
            ) : (
              <Empty description="选择模板或构建工作流" style={{ paddingTop: 120 }} image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>

        {/* Template Library */}
        <Col xs={24} lg={8}>
          <Card title={<span style={{ color: '#e0e0e0' }}>工作流模板</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
            {Object.entries(templates).map(([key, steps]) => (
              <Card key={key} size="small" hoverable
                style={{
                  background: selectedTemplate === key ? '#1a3a5c' : '#0f0f23',
                  border: selectedTemplate === key ? '1px solid #1677ff' : '1px solid #334155',
                  marginBottom: 8, cursor: 'pointer',
                }}
                onClick={() => selectTemplate(key)}>
                <Text strong style={{ color: '#e0e0e0' }}>{key}</Text>
                <div style={{ marginTop: 4 }}>
                  {steps.map((s, i) => (
                    <Tag key={i} color="blue" style={{ marginBottom: 4 }}>{s}</Tag>
                  ))}
                </div>
              </Card>
            ))}
          </Card>

          {/* Execution History */}
          <Card title={<span style={{ color: '#e0e0e0' }}>执行历史</span>}
            extra={<Button icon={<ReloadOutlined />} size="small" onClick={fetchWorkflows}>刷新</Button>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            {workflows.map((w, i) => {
              const id = w.workflowId || w.id || `wf-${i}`;
              const status = w.status || 'PENDING';
              return (
                <div key={id} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '8px 0', borderBottom: '1px solid #2a2a4a',
                }}>
                  <div>
                    <Text style={{ color: '#e0e0e0', fontSize: 13 }}>{id.substring(0, 12)}</Text>
                    <br />
                    <Text style={{ color: '#64748b', fontSize: 11 }}>
                      {w.createdAt ? new Date(w.createdAt).toLocaleTimeString() : '—'}
                    </Text>
                  </div>
                  <Space>
                    <Tag color={NODE_COLORS[status] ? undefined : 'default'}
                      style={{ color: NODE_COLORS[status] || undefined }}>
                      {status}
                    </Tag>
                    {status === 'RUNNING' && (
                      <Button size="small" danger icon={<StopOutlined />} onClick={() => cancel(id)}>取消</Button>
                    )}
                  </Space>
                </div>
              );
            })}
            {workflows.length === 0 && <Empty description="暂无记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default WorkflowEditor;
