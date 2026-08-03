/** Prompt OS Management — template browser + AB test dashboard */
import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Row, Col, Statistic, Descriptions, Tabs, Progress } from 'antd';
import { ExperimentOutlined } from '@ant-design/icons';
import { apiGet } from '../../api/client';

const PromptManagement: React.FC = () => {
  const [templates, setTemplates] = useState<any[]>([]);
  const [market, setMarket] = useState<any>({});

  useEffect(() => {
    apiGet('/api/v1/prompt-os/templates').then(r => setTemplates(r?.templates || [])).catch(() => {});
    apiGet('/api/v1/prompt-os/market/stats').then(r => setMarket(r || {})).catch(() => {});
  }, []);

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <span style={{ color: '#e0e0e0', fontSize: 18 }}><ExperimentOutlined /> Prompt OS</span>
        <Space>
          <Tag color="purple">{templates.length} templates</Tag>
        </Space>
      </Space>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        {[{ title: '模板', value: templates.length, color: '#722ed1' },
          { title: '市场列表', value: market.total_listings || 0, color: '#1677ff' },
          { title: '平均评分', value: (market.avg_rating || 0).toFixed(1), color: '#fa8c16' },
          { title: '活跃AB测试', value: market.ab_tests || 0, color: '#52c41a' },
        ].map(s => (
          <Col xs={12} sm={6} key={s.title}><Card size="small" style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
            <Statistic title={<span style={{ color: '#a0a0a0' }}>{s.title}</span>} value={s.value} valueStyle={{ color: s.color, fontSize: 20 }} />
          </Card></Col>
        ))}
      </Row>

      <Tabs defaultActiveKey="templates" items={[
        {
          key: 'templates', label: '模板', children: (
            <Card style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
              <Table dataSource={templates} rowKey="name" size="small" pagination={false}
                columns={[
                  { title: '名称', dataIndex: 'name', render: (v: string) => <span style={{ color: '#e0e0e0' }}>{v}</span> },
                  { title: 'Version', dataIndex: 'version', width: 80, render: (v: string) => <Tag>{v}</Tag> },
                  { title: 'Category', dataIndex: 'category', width: 100, render: (v: string) => <Tag color="blue">{v}</Tag> },
                  { title: '状态', dataIndex: 'status', width: 90, render: (v: string) => <Tag color={v==='active'?'green':'default'}>{v}</Tag> },
                  { title: 'Usage', dataIndex: 'usage_count', width: 80 },
                  { title: 'Score', dataIndex: 'avg_score', width: 80, render: (v: number) => <Progress percent={Math.round((v||0)*100)} size="small" /> },
                ]} />
            </Card>
          ),
        },
        {
          key: 'market', label: '市场', children: (
            <Card style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label="Total Listings">{market.total_listings || 0}</Descriptions.Item>
                <Descriptions.Item label="Verified">{market.verified_count || 0}</Descriptions.Item>
                <Descriptions.Item label="Avg Rating">{market.avg_rating || 0}</Descriptions.Item>
                <Descriptions.Item label="Categories">{Object.keys(market.by_category || {}).join(', ')}</Descriptions.Item>
              </Descriptions>
            </Card>
          ),
        },
        {
          key: 'ab', label: 'AB测试', children: (
            <Card style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
              <Button icon={<ExperimentOutlined />}>Create A/B Test</Button>
              <Table style={{ marginTop: 16 }} dataSource={[]} size="small"
                columns={[
                  { title: 'Test', dataIndex: 'name' },
                  { title: '方案A', dataIndex: 'a' },
                  { title: '方案B', dataIndex: 'b' },
                  { title: 'Winner', dataIndex: 'winner', render: (v: string) => <Tag color="green">{v}</Tag> },
                ]} />
            </Card>
          ),
        },
      ]} />
    </div>
  );
};

export default PromptManagement;
