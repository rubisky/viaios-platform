import React, { useEffect, useState, useCallback } from 'react';
import { Card, Typography, Spin, Empty, Row, Col, Tag, Statistic, Space, Button } from 'antd';
import { Node as FlowNode, Edge as FlowEdge, MarkerType } from 'reactflow';
import ReactFlow, { Background, Controls, MiniMap, useNodesState, useEdgesState } from 'reactflow';
import 'reactflow/dist/style.css';
import { ApartmentOutlined, ReloadOutlined, UserOutlined, CarOutlined, VideoCameraOutlined, FolderOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { apiGet } from '../../api/client';

const { Title, Text } = Typography;

interface Entity { id: string; type: string; name: string; properties?: Record<string, string>; }
interface Edge { from: string; to: string; type: string; }

const typeIcons: Record<string, { icon: React.ReactNode; color: string }> = {
  Person: { icon: <UserOutlined />, color: '#1677ff' },
  Vehicle: { icon: <CarOutlined />, color: '#52c41a' },
  Camera: { icon: <VideoCameraOutlined />, color: '#faad14' },
  Case: { icon: <FolderOutlined />, color: '#ff4d4f' },
  Location: { icon: <EnvironmentOutlined />, color: '#722ed1' },
};

const KnowledgeGraph: React.FC = () => {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);
  const [rNodes, setRNodes, onNodesChange] = useNodesState([]);
  const [rEdges, setREdges, onEdgesChange] = useEdgesState([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [entRes, graphRes] = await Promise.all([
        apiGet<any>('/api/v1/knowledge/entities'),
        apiGet<any>('/api/v1/knowledge/graph'),
      ]);
      setEntities(entRes?.entities || []);
      setEdges(graphRes?.edges || []);
      buildGraph(entRes?.entities || [], graphRes?.edges || []);
    } catch { /* silent */ }
    setLoading(false);
  }, []);

  const buildGraph = useCallback((ents: Entity[], edgs: Edge[]) => {
    // Layout: circular around center
    const nodeMap = new Map(ents.map((e, i) => {
      const angle = (i * 2 * Math.PI) / Math.max(ents.length, 1);
      const radius = 180;
      return [e.id, { x: Math.cos(angle) * radius + 300, y: Math.sin(angle) * radius + 250, ...e }];
    }));

    const ns: FlowNode[] = ents.map((e) => {
      const pos = nodeMap.get(e.id)!;
      const cfg = typeIcons[e.type] || { color: '#94a3b8', icon: null };
      return {
        id: e.id, type: 'default',
        data: { label: (
          <div style={{ padding: '4px 8px', textAlign: 'center' }}>
            <div style={{ fontSize: 16, color: cfg.color }}>{cfg.icon}</div>
            <div style={{ color: '#e0e0e0', fontSize: 12, fontWeight: 600 }}>{e.name}</div>
            <div style={{ color: '#64748b', fontSize: 10 }}>{e.type}</div>
          </div>
        )},
        position: { x: pos.x, y: pos.y },
        style: { background: '#1a1a2e', border: `2px solid ${cfg.color}`, borderRadius: 12, padding: 4, width: 120 },
      };
    });

    const es: FlowEdge[] = edgs.map((e, i) => ({
      id: `e${i}`, source: e.from, target: e.to,
      label: e.type.replace('_', ' '),
      animated: true,
      style: { stroke: '#334155', strokeWidth: 1.5 },
      labelStyle: { fill: '#64748b', fontSize: 9, fontWeight: 500 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#334155', width: 12, height: 12 },
    }));

    setRNodes(ns); setREdges(es);
  }, [setRNodes, setREdges]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const typeStats = entities.reduce((acc, e) => { acc[e.type] = (acc[e.type] || 0) + 1; return acc; }, {} as Record<string, number>);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ color: '#e0e0e0', margin: 0 }}>
          <ApartmentOutlined /> 知识图谱
        </Title>
        <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
      </div>

      {/* Stats */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {Object.entries(typeStats).map(([type, count]) => {
          const cfg = typeIcons[type] || { color: '#94a3b8', icon: null };
          return (
            <Col key={type} xs={12} sm={6} md={4}>
              <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
                <Statistic title={<Text style={{ color: '#a0a0a0', fontSize: 11 }}>{type}</Text>}
                  value={count} valueStyle={{ color: cfg.color, fontSize: 20, fontWeight: 600 }}
                  prefix={cfg.icon} />
              </Card>
            </Col>
          );
        })}
        <Col xs={12} sm={6} md={4}>
          <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <Statistic title={<Text style={{ color: '#a0a0a0', fontSize: 11 }}>关系</Text>}
              value={edges.length} valueStyle={{ color: '#13c2c2', fontSize: 20 }} />
          </Card>
        </Col>
      </Row>

      {/* Entity Table + Graph */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card title={<Text style={{ color: '#e0e0e0' }}>实体列表 ({entities.length})</Text>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
            bodyStyle={{ maxHeight: 450, overflow: 'auto', padding: 8 }}>
            {entities.map(e => {
              const cfg = typeIcons[e.type] || { color: '#94a3b8', icon: null };
              return (
                <div key={e.id} style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                  borderBottom: '1px solid #1e293b', cursor: 'pointer',
                }}>
                  <span style={{ color: cfg.color, fontSize: 16 }}>{cfg.icon}</span>
                  <div style={{ flex: 1 }}>
                    <Text strong style={{ color: '#e0e0e0', fontSize: 13 }}>{e.name}</Text>
                    <br />
                    <Text style={{ color: '#64748b', fontSize: 10 }}>{e.id}</Text>
                  </div>
                  <Tag color={cfg.color === '#1677ff' ? 'blue' : cfg.color === '#52c41a' ? 'green' : cfg.color === '#faad14' ? 'gold' : cfg.color === '#ff4d4f' ? 'red' : 'purple'}>{e.type}</Tag>
                </div>
              );
            })}
          </Card>

          {/* Edge Legend */}
          <Card title={<Text style={{ color: '#e0e0e0' }}>关系类型</Text>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginTop: 16 }}>
            <Space wrap>
              {Array.from(new Set(edges.map(e => e.type))).map(type => (
                <Tag key={type} color="blue">{type.replace('_', ' ')}</Tag>
              ))}
            </Space>
          </Card>
        </Col>

        {/* Graph */}
        <Col xs={24} lg={16}>
          <Card bodyStyle={{ padding: 0, height: 500 }}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, overflow: 'hidden' }}>
            {loading ? <Spin size="large" style={{ display: 'block', margin: '200px auto' }} /> :
              rNodes.length > 0 ? (
                <ReactFlow nodes={rNodes} edges={rEdges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
                  fitView attributionPosition="bottom-right">
                  <Background color="#1e293b" gap={20} />
                  <Controls style={{ background: '#1a1a2e', border: '1px solid #334155' }} />
                  <MiniMap style={{ background: '#0f0f23' }} nodeColor="#1677ff" />
                </ReactFlow>
              ) : <Empty description="暂无图谱数据" style={{ paddingTop: 180 }} image={Empty.PRESENTED_IMAGE_SIMPLE} />
            }
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default KnowledgeGraph;
