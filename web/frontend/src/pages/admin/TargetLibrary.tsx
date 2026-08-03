/** Target Library — 目标库管理 */
import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Row, Col, Statistic, Select } from 'antd';
import { DatabaseOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiGet } from '../../api/client';

const libColors: Record<string,string>={snapshot:'blue',upload:'green',watchlist:'red',history:'orange'};
const libNames: Record<string,string>={snapshot:'抓拍库',upload:'离线上传库',watchlist:'重点人员库',history:'历史解析库'};

const TargetLibrary: React.FC = () => {
  const [stats, setStats] = useState<any>({});
  const [targets, setTargets] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');

  const fetch = async () => {
    setLoading(true);
    try {
      const [s, t] = await Promise.all([
        apiGet('/api/v1/library/stats'),
        apiGet(`/api/v1/library/targets?limit=200${filter ? `&library=${filter}` : ''}`),
      ]);
      setStats(s || {});
      setTargets((t as any)?.results || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetch(); }, [filter]);

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <span style={{ color: '#e0e0e0', fontSize: 18 }}><DatabaseOutlined /> 目标库管理</span>
        <Space>
          <Select style={{ width: 130 }} placeholder="全部库" allowClear onChange={(v: any) => setFilter(v||'')}
            options={Object.entries(libNames).map(([k,v]) => ({value:k,label:v}))} />
          <Button icon={<ReloadOutlined />} loading={loading} onClick={fetch}>刷新</Button>
        </Space>
      </Space>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        {[{ title: '总目标数', value: stats.total_targets || 0, color: '#1677ff' },
          { title: '抓拍库', value: stats.by_library?.snapshot || 0, color: '#1890ff' },
          { title: '重点人员', value: stats.by_library?.watchlist || 0, color: '#ff4d4f' },
          { title: '存储', value: `${stats.storage_mb || 0}MB`, color: '#722ed1' },
        ].map(s => (
          <Col xs={12} sm={6} key={s.title}><Card size="small" style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
            <Statistic title={<span style={{ color: '#a0a0a0' }}>{s.title}</span>} value={s.value} valueStyle={{ color: s.color, fontSize: 20 }} />
          </Card></Col>
        ))}
      </Row>

      <Card style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
        <Table dataSource={targets} loading={loading} rowKey="id" size="small"
          columns={[
            { title: '名称', dataIndex: 'name', render: (v: string) => <span style={{ color: '#e0e0e0' }}>{v}</span> },
            { title: '库', dataIndex: 'library', width: 100, render: (v: string) => <Tag color={libColors[v]||'default'}>{libNames[v]||v}</Tag> },
            { title: '类型', dataIndex: 'type', width: 80, render: (v: string) => <Tag>{v}</Tag> },
            { title: '摄像头', dataIndex: 'camera_id', width: 80 },
            { title: '时间', dataIndex: 'timestamp', width: 160, render: (v: string) => v?.slice(0,19) },
            { title: '属性', dataIndex: 'attributes', render: (v: any) => v ? `${v.gender||''} ${v.age_group||''} ${v.upper_color||v.color||''}` : '-' },
          ]} />
      </Card>
    </div>
  );
};
export default TargetLibrary;
