/** Document Center — Evidence documents & reports management */
import React, { useState } from 'react';
import { Card, Table, Tag, Button, Space, Row, Col, Statistic, Upload, message } from 'antd';
import { FileTextOutlined, UploadOutlined, DownloadOutlined, EyeOutlined } from '@ant-design/icons';

const mockDocs = [
  { id: 'D001', name: 'Investigation Report #1', type: 'report', format: 'pdf', size: '2.4MB', case: 'CASE001', created: '2026-08-02', status: 'verified' },
  { id: 'D002', name: 'Evidence Photo A', type: 'image', format: 'jpg', size: '1.1MB', case: 'CASE001', created: '2026-08-02', status: 'verified' },
  { id: 'D003', name: 'Surveillance Log', type: 'log', format: 'json', size: '0.5MB', case: '—', created: '2026-08-02', status: 'draft' },
];

const DocumentCenter: React.FC = () => {
  const [docs] = useState(mockDocs);
  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <span style={{ color: '#e0e0e0', fontSize: 18 }}><FileTextOutlined /> Document Center</span>
        <Space>
          <Button icon={<UploadOutlined />}>Upload</Button>
        </Space>
      </Space>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {[{ title: 'Documents', value: docs.length, color: '#1677ff' },
          { title: 'Verified', value: docs.filter(d => d.status === 'verified').length, color: '#52c41a' },
          { title: 'Total Size', value: '4.0MB', color: '#722ed1' },
        ].map(s => (
          <Col xs={12} sm={8} key={s.title}><Card size="small" style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
            <Statistic title={<span style={{ color: '#a0a0a0' }}>{s.title}</span>} value={s.value} valueStyle={{ color: s.color, fontSize: 20 }} />
          </Card></Col>
        ))}
      </Row>
      <Card style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
        <Table dataSource={docs} rowKey="id" size="small" pagination={false}
          columns={[
            { title: 'Name', dataIndex: 'name', render: (v: string) => <span style={{ color: '#e0e0e0' }}>{v}</span> },
            { title: 'Type', dataIndex: 'type', width: 80, render: (v: string) => <Tag>{v}</Tag> },
            { title: 'Format', dataIndex: 'format', width: 70, render: (v: string) => <Tag color="blue">{v}</Tag> },
            { title: 'Case', dataIndex: 'case', width: 80 },
            { title: 'Status', dataIndex: 'status', width: 90, render: (v: string) => <Tag color={v==='verified'?'green':'gold'}>{v}</Tag> },
            { title: 'Size', dataIndex: 'size', width: 70 },
            { title: 'Actions', width: 100, render: () => (
              <Space size="small">
                <Button size="small" icon={<EyeOutlined />}>View</Button>
                <Button size="small" icon={<DownloadOutlined />}>DL</Button>
              </Space>
            )},
          ]} />
      </Card>
    </div>
  );
};
export default DocumentCenter;
