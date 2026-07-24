import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Tag, Button, Timeline, Typography, Spin, message, Modal, Form, Input, Select, Row, Col, Empty } from 'antd';
import { ArrowLeftOutlined, PlusOutlined, ApartmentOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';

const { Title } = Typography;

interface Evidence {
  id: string; evidenceType?: string; type?: string; title?: string;
  description?: string; source?: string; url?: string; createdAt?: string; reliabilityScore?: number;
}
interface CaseRecord {
  id: string; caseNo?: string; title: string; description?: string; status: string;
  priority?: string; createdBy?: string; createdAt?: string; closedAt?: string;
}

const CaseDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState<CaseRecord | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [evForm] = Form.useForm();

  const fetchEvidence = async () => {
    if (!id) return;
    try { const evRes = await apiGet<Evidence[]>(`/api/v1/cases/${id}/evidence`); setEvidence(Array.isArray(evRes) ? evRes : []); } catch {}
  };

  useEffect(() => {
    (async () => {
      if (!id) return;
      setLoading(true);
      try { const r = await apiGet<CaseRecord>(`/api/v1/cases/${id}`); setCaseData(r); } catch { message.error('加载失败'); }
      await fetchEvidence();
      setLoading(false);
    })();
  }, [id]);

  const handleAddEvidence = async (values: any) => {
    if (!id) return;
    try { await apiPost(`/api/v1/cases/${id}/evidence`, values); message.success('已添加'); setModalOpen(false); evForm.resetFields(); fetchEvidence(); }
    catch { message.error('添加失败'); }
  };

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!caseData) return <div style={{ color: '#e0e0e0' }}>案件不存在</div>;

  const sc: Record<string, string> = { NEW: 'blue', IN_PROGRESS: 'processing', CLOSED: 'green' };
  const timelineItems = evidence.map((e) => ({
    color: (e.reliabilityScore ?? 0) > 0.8 ? 'green' : 'blue',
    children: <div>
      <div style={{ color: '#e0e0e0', fontWeight: 500 }}>{e.title || e.type || '证据'}</div>
      <div style={{ color: '#a0a0a0', fontSize: 12 }}>{e.source || e.description || ''}</div>
    </div>,
  }));

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cases')} type="text" style={{ color: '#1677ff', marginBottom: 16 }}>返回</Button>
      <Title level={2} style={{ color: '#e0e0e0' }}>{caseData.title}</Title>
      <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', marginBottom: 16 }}>
        <Descriptions column={3} size="small" labelStyle={{ color: '#a0a0a0' }} contentStyle={{ color: '#e0e0e0' }}>
          <Descriptions.Item label="编号">{caseData.caseNo || caseData.id?.substring(0, 8)}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={sc[caseData.status] || 'default'}>{caseData.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="优先级"><Tag color={caseData.priority === 'P0' ? 'red' : 'blue'}>{caseData.priority || '-'}</Tag></Descriptions.Item>
          <Descriptions.Item label="创建时间">{caseData.createdAt ? new Date(caseData.createdAt).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title={<span style={{ color: '#e0e0e0' }}>证据链 ({evidence.length})</span>}
            extra={<Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>添加证据</Button>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            {evidence.length > 0 ? <Timeline items={timelineItems} /> : <span style={{ color: '#a0a0a0' }}>暂无证据</span>}
          </Card>
        </Col>

        {/* Evidence Graph */}
        <Col xs={24} lg={10}>
          <Card title={<span style={{ color: '#e0e0e0' }}><ApartmentOutlined /> 证据关联图</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
            bodyStyle={{ padding: 8 }}>
            <EvidenceGraph caseId={id || ''} evidence={evidence} />
          </Card>
        </Col>
      </Row>
      <Modal title="添加证据" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => evForm.submit()}>
        <Form form={evForm} layout="vertical" onFinish={handleAddEvidence}>
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="type" label="类型" initialValue="IMAGE"><Select options={[{ value: 'IMAGE', label: '图片' }, { value: 'VIDEO', label: '视频' }, { value: 'DOCUMENT', label: '文档' }]} /></Form.Item>
          <Form.Item name="url" label="URL"><Input placeholder="/evidence/file.jpg" /></Form.Item>
          <Form.Item name="source" label="来源"><Input placeholder="camera-001" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CaseDetail;

// SVG force-directed evidence graph
const EvidenceGraph: React.FC<{ caseId: string; evidence: Evidence[] }> = ({ caseId, evidence }) => {
  const [graph, setGraph] = useState<{ nodes: { id: string; label: string; x: number; y: number }[]; edges: { from: string; to: string; type: string }[] }>({ nodes: [], edges: [] });

  useEffect(() => {
    (async () => {
      try {
        const r = await apiGet<any>('/api/v1/knowledge/graph');
        if (r.edges) {
          const nodeIds = new Set<string>();
          r.edges.forEach((e: any) => { nodeIds.add(e.from); nodeIds.add(e.to); });
          const nodes = Array.from(nodeIds).map((id, i) => ({
            id: id as string,
            label: (id as string).replace('-', ' '),
            x: Math.cos(i * 2 * Math.PI / nodeIds.size) * 100 + 150,
            y: Math.sin(i * 2 * Math.PI / nodeIds.size) * 100 + 130,
          }));
          setGraph({ nodes, edges: r.edges });
        } else {
          // Generate from evidence
          const nodes = [{ id: 'case', label: '案件', x: 150, y: 100 } as const,
            ...evidence.map((e, i) => ({ id: e.id || `ev-${i}`, label: (e.title || e.type || '证据').substring(0, 8), x: Math.cos(i * 1.5) * 100 + 150, y: Math.sin(i * 1.5) * 80 + 200 }))];
          const edges = evidence.map((e, i) => ({ from: 'case', to: e.id || `ev-${i}`, type: 'RELATES_TO' }));
          setGraph({ nodes: nodes as any, edges });
        }
      } catch { /* use empty */ }
    })();
  }, [caseId, evidence]);

  if (graph.nodes.length === 0) return <Empty description="暂无关联图" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ height: 280 }} />;

  return (
    <svg width="100%" height="280" viewBox="0 0 300 300" style={{ background: '#0f0f23', borderRadius: 8 }}>
      {/* Edges */}
      {graph.edges.map((e, i) => {
        const from = graph.nodes.find(n => n.id === e.from);
        const to = graph.nodes.find(n => n.id === e.to);
        if (!from || !to) return null;
        return <line key={i} x1={from.x} y1={from.y} x2={to.x} y2={to.y}
          stroke="#334155" strokeWidth={2} strokeDasharray="5,5">
          <title>{e.type}</title>
        </line>;
      })}
      {/* Nodes */}
      {graph.nodes.map(n => (
        <g key={n.id}>
          <circle cx={n.x} cy={n.y} r={22} fill={n.id === 'case' ? '#1677ff' : '#52c41a'}
            stroke="#fff" strokeWidth={2} />
          <text x={n.x} y={n.y} textAnchor="middle" dy=".35em" fill="#fff" fontSize={9} fontWeight={600}>
            {n.label}
          </text>
        </g>
      ))}
    </svg>
  );
};
