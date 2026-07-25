import React, { useEffect, useState } from 'react';
import { Table, Tag, Button, Space, Typography, Modal, Form, Input, Select, message, Row, Col, Card, Statistic, Empty, Radio } from 'antd';
import { FileTextOutlined, ReloadOutlined, DownloadOutlined, PlusOutlined, FilePdfOutlined, FileWordOutlined, CheckCircleOutlined, FilterOutlined, EyeOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';

const { Title, Text } = Typography;

interface Report { id: string; title?: string; type?: string; status: string; outputFormat?: string; createdAt?: string; }
const statusColors: Record<string, string> = { PENDING: 'orange', GENERATING: 'processing', COMPLETED: 'green', FAILED: 'red' };

const TEMPLATES = [
  { value: 'weekly', label: '周报', desc: '本周告警统计 + 案件进展汇总', icon: '📊' },
  { value: 'monthly', label: '月报', desc: '月度运营分析 + 趋势图表', icon: '📈' },
  { value: 'case_analysis', label: '案件分析', desc: '案件详情 + 证据链 + 嫌疑人画像', icon: '🔍' },
  { value: 'evidence_report', label: '证据报告', desc: '证据清单 + 关联分析', icon: '📋' },
  { value: 'alarm_summary', label: '告警汇总', desc: '告警统计 + 处理时效分析', icon: '🚨' },
];

const ReportPage: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [form] = Form.useForm();
  const [selectedTemplate, setSelectedTemplate] = useState('weekly');

  const fetchReports = async () => {
    setLoading(true);
    try { const r = await apiGet<any>('/api/v1/reports'); setReports(Array.isArray(r) ? r : []); } catch {}
    setLoading(false);
  };
  useEffect(() => { fetchReports(); }, []);

  const handleGenerate = async (values: any) => {
    try {
      await apiPost('/api/v1/reports/generate', { ...values, type: selectedTemplate });
      message.success('报告生成任务已提交'); setModalOpen(false); form.resetFields(); fetchReports();
    } catch { message.error('生成失败'); }
  };

  const handleDownload = (report: Report) => {
    message.success(`下载 ${report.title || '报告'}.${(report.outputFormat || 'pdf').toLowerCase()}`);
  };

  const filtered = statusFilter === 'all' ? reports : reports.filter(r => r.status === statusFilter);
  const completed = reports.filter(r => r.status === 'COMPLETED').length;

  const columns = [
    { title: '标题', dataIndex: 'title', render: (v: string) => <Text strong style={{ color: '#e0e0e0' }}>{v || 'Untitled'}</Text> },
    { title: '类型', dataIndex: 'type', width: 100, render: (v: string) => <Tag color="blue">{v?.replace('_', ' ') || '—'}</Tag> },
    { title: '状态', dataIndex: 'status', width: 90, render: (v: string) => <Tag color={statusColors[v] || 'default'}>{v}</Tag> },
    { title: '格式', dataIndex: 'outputFormat', width: 70, render: (v: string) => <Tag icon={v === 'PDF' ? <FilePdfOutlined /> : <FileWordOutlined />}>{v}</Tag> },
    { title: '时间', dataIndex: 'createdAt', width: 140, render: (v: string) => <Text style={{ color: '#a0a0a0', fontSize: 12 }}>{v ? new Date(v).toLocaleString() : '—'}</Text> },
    {
      title: '操作', width: 140,
      render: (_: any, r: Report) => (
        <Space>
          {r.status === 'COMPLETED' && <Button size="small" type="link" icon={<DownloadOutlined />} onClick={() => handleDownload(r)}>下载</Button>}
          <Button size="small" type="link" icon={<EyeOutlined />}>预览</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ color: '#e0e0e0', margin: 0 }}><FileTextOutlined /> 报告中心</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchReports} loading={loading}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>生成报告</Button>
        </Space>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card hoverable size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>已完成</Text>} value={completed} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a', fontSize: 24, fontWeight: 700 }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card hoverable size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>生成中</Text>} value={reports.filter(r => r.status === 'GENERATING' || r.status === 'PENDING').length} prefix={<ReloadOutlined spin />} valueStyle={{ color: '#1677ff', fontSize: 24 }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card hoverable size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>总计</Text>} value={reports.length} prefix={<FileTextOutlined />} valueStyle={{ color: '#faad14', fontSize: 24 }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card hoverable size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>本月</Text>} value={reports.filter(r => r.createdAt && new Date(r.createdAt).getMonth() === new Date().getMonth()).length} valueStyle={{ color: '#13c2c2', fontSize: 24 }} />
          </Card>
        </Col>
      </Row>

      {/* Filter */}
      <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }} bodyStyle={{ padding: 12 }}>
        <Space>
          <FilterOutlined style={{ color: '#a0a0a0' }} />
          <Radio.Group value={statusFilter} onChange={e => setStatusFilter(e.target.value)} optionType="button" size="small">
            <Radio.Button value="all">全部</Radio.Button>
            <Radio.Button value="COMPLETED">已完成</Radio.Button>
            <Radio.Button value="GENERATING">生成中</Radio.Button>
            <Radio.Button value="PENDING">待处理</Radio.Button>
          </Radio.Group>
        </Space>
      </Card>

      <Card bodyStyle={{ padding: 0 }} style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
        {filtered.length > 0 ? (
          <Table columns={columns} dataSource={filtered} rowKey="id" loading={loading} size="small" pagination={{ pageSize: 15 }} style={{ background: 'transparent' }} />
        ) : <Empty description="暂无报告" style={{ padding: 40 }} image={Empty.PRESENTED_IMAGE_SIMPLE} />}
      </Card>

      <Modal title="生成报告" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()} okText="提交生成" width={560}>
        <Form form={form} layout="vertical" onFinish={handleGenerate}>
          <Form.Item label="模板"><div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {TEMPLATES.map(t => (
              <Card key={t.value} size="small" hoverable onClick={() => setSelectedTemplate(t.value)}
                style={{ background: selectedTemplate === t.value ? '#1a3a5c' : '#0f0f23', border: selectedTemplate === t.value ? '1px solid #1677ff' : '1px solid #334155', width: 140, cursor: 'pointer' }}>
                <Text style={{ fontSize: 18 }}>{t.icon}</Text>
                <Text strong style={{ color: '#e0e0e0', display: 'block', fontSize: 13 }}>{t.label}</Text>
                <Text style={{ color: '#64748b', fontSize: 10 }}>{t.desc}</Text>
              </Card>
            ))}
          </div></Form.Item>
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input placeholder="输入报告标题" /></Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="outputFormat" label="格式" initialValue="PDF"><Select options={[{ value: 'PDF', label: 'PDF' }, { value: 'DOCX', label: 'DOCX' }]} /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="caseId" label="关联案件"><Input placeholder="可选" /></Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default ReportPage;
