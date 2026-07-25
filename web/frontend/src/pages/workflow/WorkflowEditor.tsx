import React, { useCallback, useEffect, useState } from 'react';
import { Card, Button, Tag, Space, Typography, message, Select, Row, Col, Empty, Modal, Input, Popconfirm } from 'antd';
import { PlayCircleOutlined, ReloadOutlined, ApartmentOutlined, StopOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import ReactFlow, { Background, Controls, MiniMap, Node, Edge, MarkerType, useNodesState, useEdgesState, addEdge, Connection } from 'reactflow';
import 'reactflow/dist/style.css';
import { apiGet, apiPost } from '../../api/client';

const { Title, Text } = Typography;

const TEMPLATES: Record<string, string[]> = {
  'video-analysis': ['Video Ingest', 'Frame Extract', 'Object Detect', 'Tracking', 'Embedding', 'Report'],
  'alarm-handling': ['Alarm Trigger', 'Evaluate', 'Snapshot', 'Case Create', 'Notify'],
  'search-pipeline': ['Query Parse', 'NLU Embed', 'Vector Search', 'Filter', 'Rank', 'Return'],
  'case-investigation': ['Evidence Collect', 'Timeline Build', 'Relation Analyze', 'Suspect ID', 'Report'],
  'system-monitor': ['Health Check', 'Metrics Collect', 'Anomaly Detect', 'Alert', 'Auto-Recovery'],
};

const WorkflowEditor: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [template, setTemplate] = useState('video-analysis');
  const [customSteps, setCustomSteps] = useState<string[]>([]);
  const [newStepName, setNewStepName] = useState('');
  const [modalOpen, setModalOpen] = useState(false);

  const buildFlow = useCallback((steps: string[]) => {
    const ns: Node[] = steps.map((label, i) => ({
      id: `${i}`, type: 'default',
      data: { label },
      position: { x: i * 160 + 50, y: Math.sin(i * 1.2) * 30 + 80 },
      style: {
        background: '#1a1a2e', color: '#e0e0e0', border: '1px solid #334155',
        borderRadius: 8, padding: '8px 16px', fontSize: 12, width: 130, textAlign: 'center',
      },
    }));
    const es: Edge[] = steps.slice(1).map((_, i) => ({
      id: `e${i}-${i + 1}`, source: `${i}`, target: `${i + 1}`,
      animated: true, style: { stroke: '#1677ff', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#1677ff' },
    }));
    setNodes(ns); setEdges(es);
  }, [setNodes, setEdges]);

  useEffect(() => {
    const steps = customSteps.length > 0 ? customSteps : TEMPLATES[template];
    buildFlow(steps);
  }, [template, customSteps, buildFlow]);

  const fetchWorkflows = async () => {
    try {
      const r = await apiGet<any>('/api/v1/workflows/history');
      setWorkflows(Array.isArray(r) ? r.slice(0, 10) : []);
    } catch { /* empty */ }
  };
  useEffect(() => { fetchWorkflows(); }, []);

  const execute = async () => {
    setLoading(true);
    const steps = customSteps.length > 0 ? customSteps : TEMPLATES[template];
    try {
      const r = await apiPost<any>('/api/v1/workflows/execute', { workflow: template, definition: steps.join('->'), steps: steps.map((n, i) => ({ step: i + 1, name: n })) });
      message.success(`已启动: ${r.workflowId || r.id}`);
      fetchWorkflows();
    } catch { message.error('执行失败'); }
    setLoading(false);
  };

  const cancel = async (id: string) => {
    try { await apiPost(`/api/v1/workflows/${id}/cancel`); message.success('已取消'); fetchWorkflows(); }
    catch { message.error('取消失败'); }
  };

  const addStep = () => {
    if (!newStepName.trim()) return;
    setCustomSteps(prev => [...prev, newStepName.trim()]);
    setNewStepName(''); setModalOpen(false);
  };

  const removeStep = (idx: number) => {
    setCustomSteps(prev => prev.filter((_, i) => i !== idx));
  };

  const onConnect = useCallback((params: Connection) => {
    setEdges(eds => addEdge(params, eds));
  }, [setEdges]);

  const selectTemplate = (name: string) => {
    setTemplate(name); setCustomSteps([]);
  };

  const useTemplate = () => { setCustomSteps([]); };
  const useCustom = () => { setCustomSteps(['Start', 'Process', 'End']); };

  const steps = customSteps.length > 0 ? customSteps : TEMPLATES[template];

  return (
    <div>
      <Title level={3} style={{ color: '#e0e0e0', marginBottom: 16 }}><ApartmentOutlined /> 工作流编排</Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title={<Text style={{ color: '#e0e0e0' }}>DAG 可视化编辑器</Text>}
            extra={
              <Space>
                <Select value={template} onChange={selectTemplate} style={{ width: 150 }}>
                  {Object.keys(TEMPLATES).map(k => <Select.Option key={k} value={k}>{k}</Select.Option>)}
                </Select>
                <Button size="small" onClick={useCustom}>自定义</Button>
                <Button size="small" onClick={useTemplate}>用模板</Button>
                <Button type="primary" icon={<PlayCircleOutlined />} onClick={execute} loading={loading}>执行</Button>
              </Space>
            }
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
            bodyStyle={{ padding: 0, height: 450 }}>
            {nodes.length > 0 ? (
              <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
                onConnect={onConnect} fitView>
                <Background color="#1e293b" gap={20} />
                <Controls style={{ background: '#1a1a2e' }} />
                <MiniMap style={{ background: '#0f0f23' }} nodeColor="#1677ff" />
              </ReactFlow>
            ) : <Empty style={{ paddingTop: 120 }} image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          {/* Step Editor */}
          <Card title={<Text style={{ color: '#e0e0e0' }}>步骤编辑</Text>}
            extra={<Button icon={<PlusOutlined />} size="small" onClick={() => setModalOpen(true)}>添加</Button>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
            {steps.map((s, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', borderBottom: '1px solid #1e293b' }}>
                <Space>
                  <Tag color="blue">{i + 1}</Tag>
                  <Text style={{ color: '#e0e0e0', fontSize: 13 }}>{s}</Text>
                </Space>
                {customSteps.length > 0 && (
                  <Popconfirm title="删除此步骤?" onConfirm={() => removeStep(i)}>
                    <Button type="text" danger size="small" icon={<DeleteOutlined />} />
                  </Popconfirm>
                )}
              </div>
            ))}
            {steps.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无步骤" />}
          </Card>

          {/* Execution History */}
          <Card title={<Text style={{ color: '#e0e0e0' }}>执行历史</Text>}
            extra={<Button icon={<ReloadOutlined />} size="small" onClick={fetchWorkflows}>刷新</Button>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            {workflows.map((w, i) => {
              const id = w.workflowId || w.id || `wf-${i}`;
              const status = w.status || 'PENDING';
              return (
                <div key={id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #1e293b' }}>
                  <div>
                    <Text style={{ color: '#e0e0e0', fontSize: 13 }}>{id.substring(0, 12)}</Text>
                    <br />
                    <Text style={{ color: '#64748b', fontSize: 11 }}>{w.createdAt ? new Date(w.createdAt).toLocaleTimeString() : '—'}</Text>
                  </div>
                  <Space>
                    <Tag color={status === 'COMPLETED' ? 'green' : status === 'RUNNING' ? 'blue' : 'default'}>{status}</Tag>
                    {status === 'RUNNING' && <Button size="small" danger icon={<StopOutlined />} onClick={() => cancel(id)} />}
                  </Space>
                </div>
              );
            })}
            {workflows.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无记录" />}
          </Card>
        </Col>
      </Row>

      <Modal title="添加步骤" open={modalOpen} onOk={addStep} onCancel={() => setModalOpen(false)}>
        <Input placeholder="步骤名称" value={newStepName} onChange={e => setNewStepName(e.target.value)} onPressEnter={addStep} />
      </Modal>
    </div>
  );
};

export default WorkflowEditor;
