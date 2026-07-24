import React, { useEffect, useState } from 'react';
import { Table, Tag, Button, Space, Typography, Modal, Form, Input, Select, message, Row, Col, Card, Statistic, Progress, Empty } from 'antd';
import { FileTextOutlined, ReloadOutlined, DownloadOutlined, PlusOutlined, FilePdfOutlined, FileWordOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';

const { Title, Text } = Typography;

interface Report {
  id: string; caseId?: string; templateId?: string; title?: string; name?: string;
  status: string; type?: string; outputFormat?: string; outputUrl?: string; createdAt?: string;
}

const statusColors: Record<string, string> = { PENDING: 'orange', GENERATING: 'processing', COMPLETED: 'green', FAILED: 'red' };

const ReportPage: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchReports = async () => {
    setLoading(true);
    try {
      const r = await apiGet<any>('/api/v1/reports');
      setReports(Array.isArray(r) ? r : []);
    } catch { message.error('加载报告失败'); }
    setLoading(false);
  };

  useEffect(() => { fetchReports(); }, []);

  const handleGenerate = async (values: any) => {
    try {
      await apiPost('/api/v1/reports/generate', values);
      message.success('报告生成任务已提交');
      setModalOpen(false); form.resetFields(); fetchReports();
    } catch { message.error('生成失败'); }
  };

  const completed = reports.filter(r => r.status === 'COMPLETED').length;
  const generating = reports.filter(r => r.status === 'GENERATING' || r.status === 'PENDING').length;

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title', render: (v: string, r: Report) => <Text strong style={{ color: '#e0e0e0' }}>{v || r.name || 'Untitled'}</Text> },
    { title: '类型', dataIndex: 'type', key: 'type', width: 120, render: (v: string) => <Tag color="blue">{v?.replace('_', ' ') || '—'}</Tag> },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (v: string) => <Tag color={statusColors[v] || 'default'}>{v}</Tag>,
    },
    {
      title: '格式', dataIndex: 'outputFormat', key: 'format', width: 80,
      render: (v: string) => <Tag icon={v === 'PDF' ? <FilePdfOutlined /> : <FileWordOutlined />}>{v}</Tag>,
    },
    {
      title: '时间', dataIndex: 'createdAt', key: 'createdAt', width: 160,
      render: (v: string) => <Text style={{ color: '#a0a0a0', fontSize: 12 }}>{v ? new Date(v).toLocaleString() : '—'}</Text>,
    },
    {
      title: '操作', key: 'actions', width: 80,
      render: (_: any, r: Report) => (
        r.status === 'COMPLETED' ? <Button size="small" type="link" icon={<DownloadOutlined />}>下载</Button> : null
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ color: '#e0e0e0', margin: 0 }}>
          <FileTextOutlined /> 报告中心
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchReports} loading={loading}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>生成报告</Button>
        </Space>
      </div>

      {/* Stats Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card hoverable style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>已完成</Text>} value={completed}
              prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a', fontSize: 28, fontWeight: 700 }} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card hoverable style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>生成中</Text>} value={generating}
              prefix={<ReloadOutlined spin />} valueStyle={{ color: '#1677ff', fontSize: 28 }} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card hoverable style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <Statistic title={<Text style={{ color: '#a0a0a0' }}>总计</Text>} value={reports.length}
              prefix={<FileTextOutlined />} valueStyle={{ color: '#faad14', fontSize: 28 }} />
          </Card>
        </Col>
      </Row>

      {/* Report Table */}
      <Card title={<span style={{ color: '#e0e0e0' }}>报告列表</span>}
        style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
        bodyStyle={{ padding: 0 }}>
        {reports.length > 0 ? (
          <Table columns={columns} dataSource={reports} rowKey="id" loading={loading} size="small"
            pagination={{ pageSize: 15, showSizeChanger: true }} style={{ background: 'transparent' }} />
        ) : (
          <Empty description="暂无报告" style={{ padding: 40 }} image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      {/* Type Breakdown */}
      {reports.length > 0 && (
        <Card title={<span style={{ color: '#e0e0e0' }}>类型分布</span>}
          style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginTop: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            {Object.entries(
              reports.reduce((acc, r) => { const t = r.type || 'other'; acc[t] = (acc[t] || 0) + 1; return acc; }, {} as Record<string, number>)
            ).map(([type, count]) => (
              <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <Text style={{ color: '#e0e0e0', width: 120 }}>{type.replace('_', ' ')}</Text>
                <Progress percent={Math.round(count / reports.length * 100)} size="small"
                  style={{ flex: 1 }} strokeColor="#1677ff" format={() => `${count}`} />
              </div>
            ))}
          </Space>
        </Card>
      )}

      <Modal title="生成报告" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}
        okText="提交">
        <Form form={form} layout="vertical" onFinish={handleGenerate}>
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input placeholder="Weekly Report W30" />
          </Form.Item>
          <Form.Item name="type" label="类型" initialValue="weekly" rules={[{ required: true }]}>
            <Select options={[
              { value: 'weekly', label: '周报' }, { value: 'monthly', label: '月报' },
              { value: 'case_analysis', label: '案件分析' }, { value: 'evidence_report', label: '证据报告' },
            ]} />
          </Form.Item>
          <Form.Item name="outputFormat" label="输出格式" initialValue="PDF">
            <Select options={[{ value: 'PDF', label: 'PDF' }, { value: 'DOCX', label: 'DOCX' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ReportPage;
