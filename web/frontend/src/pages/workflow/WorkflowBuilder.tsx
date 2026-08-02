/** Workflow Builder — Visual DAG editor using ReactFlow (P4-2) */
import React, { useState, useCallback, useMemo } from 'react';
import { Card, Button, Space, Tag, message, Drawer, Form, Input, Select, InputNumber } from 'antd';
import { PlusOutlined, SaveOutlined, PlayCircleOutlined, NodeIndexOutlined } from '@ant-design/icons';
import ReactFlow, {
  Background, Controls, MiniMap, addEdge, useNodesState, useEdgesState,
  MarkerType, Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';

const nodeTypes = {
  decode: { label: 'Decode', color: '#4ecdc4', icon: '📹' },
  detect: { label: 'Detect', color: '#ff6b6b', icon: '🔍' },
  track: { label: 'Track', color: '#45b7d1', icon: '👣' },
  embed: { label: 'Embed', color: '#96ceb4', icon: '🧬' },
  archive: { label: 'Archive', color: '#f7dc6f', icon: '📦' },
  search: { label: 'Search', color: '#bb8fce', icon: '🔎' },
  reason: { label: 'Reason', color: '#85c1e9', icon: '🧠' },
  report: { label: 'Report', color: '#f8c471', icon: '📝' },
  notify: { label: 'Notify', color: '#e74c3c', icon: '🔔' },
};

const initialNodes = [
  { id: '1', type: 'default', position: { x: 250, y: 0 }, data: { label: '📹 Decode' }, style: { background: '#4ecdc422', border: '2px solid #4ecdc4', borderRadius: 8, padding: 10, color: '#e0e0e0', width: 120 } },
  { id: '2', type: 'default', position: { x: 250, y: 120 }, data: { label: '🔍 Detect' }, style: { background: '#ff6b6b22', border: '2px solid #ff6b6b', borderRadius: 8, padding: 10, color: '#e0e0e0', width: 120 } },
  { id: '3', type: 'default', position: { x: 100, y: 240 }, data: { label: '👣 Track' }, style: { background: '#45b7d122', border: '2px solid #45b7d1', borderRadius: 8, padding: 10, color: '#e0e0e0', width: 120 } },
  { id: '4', type: 'default', position: { x: 400, y: 240 }, data: { label: '🧬 Embed' }, style: { background: '#96ceb422', border: '2px solid #96ceb4', borderRadius: 8, padding: 10, color: '#e0e0e0', width: 120 } },
  { id: '5', type: 'default', position: { x: 250, y: 360 }, data: { label: '📦 Archive' }, style: { background: '#f7dc6f22', border: '2px solid #f7dc6f', borderRadius: 8, padding: 10, color: '#e0e0e0', width: 120 } },
];

const initialEdges = [
  { id: 'e12', source: '1', target: '2', animated: true, style: { stroke: '#4ecdc4' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#4ecdc4' } },
  { id: 'e23', source: '2', target: '3', animated: true, style: { stroke: '#45b7d1' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#45b7d1' } },
  { id: 'e24', source: '2', target: '4', animated: true, style: { stroke: '#96ceb4' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#96ceb4' } },
  { id: 'e35', source: '3', target: '5', style: { stroke: '#666' }, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e45', source: '4', target: '5', style: { stroke: '#666' }, markerEnd: { type: MarkerType.ArrowClosed } },
];

const WorkflowBuilder: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [yaml, setYaml] = useState('');

  const onConnect = useCallback((params: any) => setEdges(eds => addEdge({ ...params, animated: true, style: { stroke: '#4ecdc4' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#4ecdc4' } }), eds), [setEdges]);

  const addNode = (type: string) => {
    const nt = nodeTypes[type as keyof typeof nodeTypes] || { label: type, color: '#666', icon: '⬜' };
    setNodes(nds => [...nds, {
      id: `${Date.now()}`, type: 'default',
      position: { x: Math.random() * 400 + 50, y: Math.random() * 300 + 50 },
      data: { label: `${nt.icon} ${nt.label}` },
      style: { background: `${nt.color}22`, border: `2px solid ${nt.color}`, borderRadius: 8, padding: 10, color: '#e0e0e0', width: 120 },
    }]);
  };

  const generateYAML = () => {
    const y = `workflow:\n  name: visual_pipeline\n  mode: dag\n  steps:\n` +
      nodes.map(n => `    - id: ${n.id}\n      action: ${n.data.label.split(' ')[1]?.toLowerCase() || 'unknown'}`).join('\n');
    setYaml(y); setDrawerOpen(true);
  };

  const execute = async () => {
    generateYAML();
    message.success('Workflow submitted');
  };

  return (
    <div style={{ height: 'calc(100vh - 200px)' }}>
      <Space style={{ marginBottom: 12 }}>
        <span style={{ color: '#e0e0e0', fontSize: 16 }}><NodeIndexOutlined /> Workflow Builder</span>
        {Object.entries(nodeTypes).map(([key, val]) => (
          <Button key={key} size="small" onClick={() => addNode(key)} icon={<PlusOutlined />}>{val.icon} {val.label}</Button>
        ))}
        <Button type="primary" icon={<SaveOutlined />} onClick={generateYAML}>Export YAML</Button>
        <Button type="primary" icon={<PlayCircleOutlined />} onClick={execute} style={{ background: '#52c41a' }}>Execute</Button>
      </Space>

      <Card style={{ height: '100%', background: '#0f0f23', borderColor: '#2a2a4a' }} bodyStyle={{ height: '100%', padding: 0 }}>
        <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} fitView>
          <Background color="#2a2a4a" gap={20} />
          <Controls />
          <MiniMap style={{ background: '#1a1a2e' }} nodeColor={(n: any) => n.style?.border?.split(' ')?.[2] || '#666'} />
          <Panel position="bottom-center">
            <Tag>{nodes.length} nodes · {edges.length} edges</Tag>
          </Panel>
        </ReactFlow>
      </Card>

      <Drawer title="Workflow YAML" open={drawerOpen} onClose={() => setDrawerOpen(false)} width={500}>
        <pre style={{ background: '#0a0e1a', color: '#38bdf8', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: '70vh', fontSize: 13 }}>
          {yaml}
        </pre>
      </Drawer>
    </div>
  );
};

export default WorkflowBuilder;
