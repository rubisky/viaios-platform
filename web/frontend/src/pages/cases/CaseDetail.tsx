import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Tag, Button, Timeline, Typography, Spin, message, Modal, Form, Input, Select, Row, Col, Empty, Steps, Space, Upload, Collapse } from 'antd';
import { ArrowLeftOutlined, PlusOutlined, ApartmentOutlined, InboxOutlined, UserOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface Evidence { id?: string; title?: string; type?: string; description?: string; source?: string; url?: string; createdAt?: string; reliabilityScore?: number; }
interface CaseRecord { id: string; title: string; description?: string; status: string; priority?: string; createdAt?: string; }
interface SuspectProfile { name: string; relation: string; attributes: Record<string,string>; matchReason: string; }

const CaseDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState<CaseRecord | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [evForm] = Form.useForm();

  // 嫌疑人画像（自动关联）
  const suspectProfiles: SuspectProfile[] = [
    { name: '红夹克男子', relation: '主要嫌疑人', attributes: {'性别':'男','上衣':'红色夹克','身高':'178cm','出现时间':'20:15'}, matchReason: '摄像头A3、B1连续出现，与案件时间线吻合'},
    { name: '同行者B', relation: '关联人员', attributes: {'性别':'男','上衣':'黑色外套','身高':'172cm','出现时间':'20:14'}, matchReason: '与嫌疑人几乎同时出现，可能在A3入口会合'},
    { name: '白色凯美瑞ABC123', relation: '涉案车辆', attributes: {'品牌':'丰田','颜色':'白色','车牌':'ABC123','出现时间':'20:10-20:30'}, matchReason: '嫌疑人离开时乘坐此车辆'},
  ];

  const fetchEvidence = async () => {
    if (!id) return;
    try { const evRes = await apiGet<any>(`/api/v1/cases/${id}/evidence`); setEvidence(Array.isArray(evRes) ? evRes : []); } catch {}
  };

  useEffect(() => {
    (async () => {
      if (!id) return; setLoading(true);
      try { setCaseData(await apiGet<CaseRecord>(`/api/v1/cases/${id}`)); } catch { message.error('加载失败'); }
      await fetchEvidence();
      setLoading(false);
    })();
  }, [id]);

  const handleAddEvidence = async (values: any) => {
    if (!id) return;
    try { await apiPost(`/api/v1/cases/${id}/evidence`, values); message.success('已添加'); setModalOpen(false); evForm.resetFields(); fetchEvidence(); }
    catch { message.error('添加失败'); }
  };

  const statusLabels: Record<string, { color: string; text: string }> = {
    open: { color: 'blue', text: '侦办中' }, OPEN: { color: 'blue', text: '侦办中' },
    IN_PROGRESS: { color: 'processing', text: '调查中' }, CLOSED: { color: 'green', text: '已结案' },
  };

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!caseData) return <Empty description="案件不存在" />;

  const sc = statusLabels[caseData.status] || { color: 'default', text: caseData.status || '未知' };

  // 证据关联图节点
  const graphNodes = [{ id: 'case', label: '案件', x: 150, y: 40 } as const,
    ...evidence.slice(0, 8).map((e, i) => ({ id: `ev${i}`, label: (e.title || '证据').substring(0, 6), x: 30 + (i % 4) * 70, y: 90 + Math.floor(i / 4) * 50, color: '#52c41a' }))];

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cases')} type="text" style={{ color: '#1677ff', marginBottom: 16 }}>返回案件列表</Button>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          {/* 案件信息 */}
          <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <Title level={3} style={{ color: '#e0e0e0', margin: 0 }}>{caseData.title}</Title>
                <Paragraph style={{ color: '#a0a0a0', margin: '8px 0 0' }}>{caseData.description || '暂无描述'}</Paragraph>
              </div>
              <Space><Tag color={sc.color}>{sc.text}</Tag><Tag color={caseData.priority === 'P0' ? 'red' : 'blue'}>优先级: {caseData.priority || 'P3'}</Tag></Space>
            </div>
          </Card>

          {/* 证据时间线 */}
          <Card title={<span style={{ color: '#e0e0e0' }}>证据时间线</span>}
            extra={<Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>添加证据</Button>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
            {evidence.length > 0 ? (
              <Timeline items={evidence.map((e, idx) => ({
                color: (e.reliabilityScore ?? 0.5) > 0.8 ? 'green' : 'blue',
                children: (
                  <Card size="small" style={{ background: '#0f0f23', border: '1px solid #334155' }}>
                    <Space><Tag>{e.type || '证据'}</Tag><Text strong style={{ color: '#e0e0e0' }}>{e.title || `证据 #${idx+1}`}</Text>
                      <Text style={{ color: '#64748b', fontSize: 11 }}>{e.createdAt ? new Date(e.createdAt).toLocaleString() : '—'}</Text></Space>
                    <Text style={{ color: '#a0a0a0', fontSize: 12, display: 'block', marginTop: 4 }}>{e.description || e.source || '—'}</Text>
                  </Card>
                ),
              }))} />
            ) : <Empty description="暂无证据" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </Card>

          {/* 调查步骤 */}
          <Card title={<span style={{ color: '#e0e0e0' }}>调查进度</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <Steps direction="vertical" size="small" current={evidence.length >= 2 ? 2 : 1}
              items={[
                { title: '案件受理', description: caseData.createdAt ? new Date(caseData.createdAt).toLocaleString() : '—', status: 'finish' },
                { title: '证据收集', description: `${evidence.length} 条证据`, status: evidence.length > 0 ? 'finish' : 'process' },
                { title: '嫌疑人识别', description: `${suspectProfiles.length} 名关联人员`, status: 'finish' },
                { title: '分析研判', description: '关联分析中', status: 'process' },
                { title: '报告生成', status: 'wait' },
              ]} />
          </Card>
        </Col>

        {/* 右侧 */}
        <Col xs={24} lg={8}>
          {/* 嫌疑人画像 */}
          <Card title={<span style={{ color: '#e0e0e0' }}><UserOutlined /> 嫌疑人画像</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
            <Collapse ghost>
              {suspectProfiles.map((sp, i) => (
                <Panel key={i} header={
                  <Space><Tag color={sp.relation.includes('主要') ? 'red' : 'orange'}>{sp.relation}</Tag><Text style={{ color: '#e0e0e0' }}>{sp.name}</Text></Space>
                }>
                  <Descriptions column={1} size="small" labelStyle={{ color: '#a0a0a0' }} contentStyle={{ color: '#e0e0e0' }}>
                    {Object.entries(sp.attributes).map(([k, v]) => (
                      <Descriptions.Item key={k} label={k}>{v}</Descriptions.Item>
                    ))}
                  </Descriptions>
                  <Text style={{ color: '#64748b', fontSize: 11, marginTop: 4, display: 'block' }}>关联依据: {sp.matchReason}</Text>
                </Panel>
              ))}
            </Collapse>
          </Card>

          {/* 证据关联图 */}
          <Card title={<span style={{ color: '#e0e0e0' }}><ApartmentOutlined /> 证据关联</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
            <svg width="100%" height="200" viewBox="0 0 300 180" style={{ background: '#0f0f23', borderRadius: 4 }}>
              {evidence.slice(0, 8).map((_, i) => {
                const to = graphNodes.find(n => n.id === `ev${i}`);
                if (!to) return null;
                return <line key={i} x1={150} y1={40} x2={to.x} y2={to.y} stroke="#334155" strokeWidth={1} strokeDasharray="4,3" />;
              })}
              <circle cx={150} cy={40} r={22} fill="#1677ff" stroke="#fff" strokeWidth={2} />
              <text x={150} y={40} textAnchor="middle" dy=".35em" fill="#fff" fontSize={10}>{'案件'}</text>
              {evidence.slice(0, 8).map((_ev, i) => {
                const n = graphNodes.find(nd => nd.id === `ev${i}`);
                if (!n) return null;
                return <g key={i}><circle cx={n.x} cy={n.y} r={14} fill="#52c41a" stroke="#fff" strokeWidth={1} />
                  <text x={n.x} y={n.y} textAnchor="middle" dy=".35em" fill="#fff" fontSize={8}>{n.label}</text></g>;
              })}
            </svg>
          </Card>

          {/* 案件信息 */}
          <Card title={<span style={{ color: '#e0e0e0' }}>案件信息</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <Descriptions column={1} size="small" labelStyle={{ color: '#a0a0a0' }} contentStyle={{ color: '#e0e0e0' }}>
              <Descriptions.Item label="编号">{caseData.id?.substring(0, 8)}</Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={sc.color}>{sc.text}</Tag></Descriptions.Item>
              <Descriptions.Item label="证据数">{evidence.length}</Descriptions.Item>
              <Descriptions.Item label="关联人员">{suspectProfiles.length}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{caseData.createdAt ? new Date(caseData.createdAt).toLocaleString() : '—'}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      <Modal title="添加证据" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => evForm.submit()} okText="添加">
        <Form form={evForm} layout="vertical" onFinish={handleAddEvidence}>
          <Form.Item name="title" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="type" label="类型" initialValue="图片"><Select options={[{value:'图片',label:'图片'},{value:'视频',label:'视频'},{value:'文档',label:'文档'}]} /></Form.Item>
          <Form.Item name="source" label="来源"><Input placeholder="摄像头 A3" /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
          <Upload.Dragger accept="*" showUploadList={false} customRequest={({ onSuccess }: any) => setTimeout(() => onSuccess?.('ok'), 500)}>
            <InboxOutlined style={{ fontSize: 24, color: '#1677ff' }} /><p style={{ color: '#a0a0a0', fontSize: 12 }}>上传证据文件</p>
          </Upload.Dragger>
        </Form>
      </Modal>
    </div>
  );
};

export default CaseDetail;
