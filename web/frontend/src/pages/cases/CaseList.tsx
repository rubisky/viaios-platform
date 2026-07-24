import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Tag, Input, Button, Space, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { SearchOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';

const { Title } = Typography;

interface CaseRecord {
  id: string;
  caseNo?: string;
  title: string;
  description?: string;
  status: string;
  priority?: string;
  createdBy?: string;
  createdAt?: string;
  updatedAt?: string;
}

const statusColors: Record<string, string> = {
  NEW: 'blue', OPEN: 'blue', IN_PROGRESS: 'processing', INVESTIGATING: 'processing',
  CLOSED: 'green', RESOLVED: 'green', PENDING: 'orange', ARCHIVED: 'default',
};
const priorityColors: Record<string, string> = { P0: 'red', P1: 'orange', P2: 'gold', P3: 'blue' };

const CaseList: React.FC = () => {
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  const fetchCases = async () => {
    setLoading(true);
    try {
      const res = await apiGet<any>('/api/v1/cases', { page: 0, size: 50 });
      setCases(Array.isArray(res) ? res : res?.data || []);
    } catch { message.error('加载案件列表失败'); }
    setLoading(false);
  };

  useEffect(() => { fetchCases(); }, []);

  const columns: ColumnsType<CaseRecord> = [
    { title: '案件编号', dataIndex: 'caseNo', key: 'caseNo', width: 120,
      render: (v: string, r: CaseRecord) => v || r.id?.substring(0, 8) || '-' },
    { title: '案件名称', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => <Tag color={statusColors[s] || 'default'}>{s || '-'}</Tag> },
    { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80,
      render: (p: string) => p ? <Tag color={priorityColors[p] || 'default'}>{p}</Tag> : '-' },
    { title: '创建人', dataIndex: 'createdBy', key: 'createdBy', width: 100 },
    { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 160,
      render: (d: string) => d ? new Date(d).toLocaleString('zh-CN') : '-' },
  ];

  const filtered = cases.filter((c) =>
    !search || c.title?.toLowerCase().includes(search.toLowerCase()) ||
    (c.caseNo || c.id)?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={2} style={{ color: '#e0e0e0', margin: 0 }}>案件管理</Title>
        <Space>
          <Input prefix={<SearchOutlined />} placeholder="搜索案件..." value={search}
            onChange={(e) => setSearch(e.target.value)} style={{ width: 250 }} />
          <Button icon={<ReloadOutlined />} onClick={fetchCases}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />}
            onClick={async () => {
              try {
                await apiPost('/api/v1/cases', {
                  title: '新案件 ' + new Date().toLocaleDateString(), status: 'NEW', priority: 'P2',
                });
                message.success('案件已创建');
                fetchCases();
              } catch { message.error('创建失败'); }
            }}>
            新建案件
          </Button>
        </Space>
      </div>
      <Table columns={columns} dataSource={filtered} rowKey="id"
        loading={loading} size="middle"
        onRow={(r) => ({ onClick: () => navigate(`/cases/${r.id}`), style: { cursor: 'pointer' } })}
        style={{ background: '#16213e' }}
        locale={{ emptyText: <span style={{ color: '#a0a0a0' }}>暂无案件数据</span> }} />
    </div>
  );
};

export default CaseList;
