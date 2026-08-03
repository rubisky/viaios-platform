/** Target Library Manager — 抓拍库/上传库/布控库/历史库 全管理 */
import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Row, Col, Statistic, Select, Upload, Modal, Input, message, Tabs, Popconfirm } from 'antd';
import { DatabaseOutlined, UploadOutlined, ReloadOutlined, DeleteOutlined, PlusOutlined, InboxOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';

const libNames: Record<string,string> = {snapshot:'抓拍库',upload:'离线上传库',watchlist:'重点人员库',history:'历史解析库'};
const libColors: Record<string,string> = {snapshot:'blue',upload:'green',watchlist:'red',history:'orange'};
const typeNames: Record<string,string> = {person:'人员',vehicle:'车辆',face:'人脸',body:'人体'};

const TargetLibrary: React.FC = () => {
  const [stats, setStats] = useState<any>({});
  const [targets, setTargets] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('all');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadLib, setUploadLib] = useState('upload');
  const [uploadName, setUploadName] = useState('');
  const [uploadBase64, setUploadBase64] = useState('');
  const [ingesting, setIngesting] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      const lib = activeTab === 'all' ? '' : activeTab;
      const [s, t] = await Promise.all([
        apiGet('/api/v1/library/stats'),
        apiGet(`/api/v1/library/targets?limit=500${lib ? `&library=${lib}` : ''}`),
      ]);
      setStats(s || {});
      setTargets((t as any)?.results || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetch(); }, [activeTab]);

  const handleUpload = async () => {
    if (!uploadBase64) { message.warning('请选择图片'); return; }
    setIngesting(true);
    try {
      await apiPost('/api/v1/library/ingest', {
        image_data: uploadBase64,
        library: uploadLib,
        name: uploadName || `${libNames[uploadLib]}_${Date.now()}`,
      });
      message.success('入库成功');
      setUploadOpen(false);
      setUploadBase64('');
      fetch();
    } catch { message.error('入库失败'); }
    setIngesting(false);
  };

  const handleDelete = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/library/targets/${id}`, { method: 'DELETE' });
      if (res.ok) { message.success('已删除'); fetch(); }
      else { message.error('删除失败'); }
    } catch { message.error('删除失败'); }
  };

  const handleBatchUpload = async (file: File) => {
    const reader = new FileReader();
    reader.onload = async () => {
      const b64 = (reader.result as string).split(',')[1];
      try {
        await apiPost('/api/v1/library/ingest', {
          image_data: b64,
          library: activeTab === 'all' ? 'upload' : activeTab,
          name: file.name,
        });
        message.success(`${file.name} 已入库`);
        fetch();
      } catch { message.error(`${file.name} 入库失败`); }
    };
    reader.readAsDataURL(file);
    return false;
  };

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <span style={{ color: '#e0e0e0', fontSize: 18 }}><DatabaseOutlined /> 目标库管理</span>
        <Space>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={fetch}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setUploadLib(activeTab==='all'?'upload':activeTab); setUploadOpen(true); }}>添加目标</Button>
        </Space>
      </Space>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        {Object.entries(libNames).map(([key, name]) => (
          <Col xs={12} sm={6} key={key}>
            <Card size="small" hoverable
              style={{ background: activeTab===key?'#1a3a5c':'#16213e', borderColor: activeTab===key?libColors[key]:'#2a2a4a', cursor:'pointer' }}
              onClick={() => setActiveTab(key)}>
              <Statistic title={<span style={{ color: '#a0a0a0' }}>{name}</span>}
                value={stats.by_library?.[key]||0} valueStyle={{ color: libColors[key], fontSize: 22 }} />
            </Card>
          </Col>
        ))}
      </Row>

      <Tabs activeKey={activeTab} onChange={setActiveTab}
        items={[
          { key: 'all', label: `全部 (${stats.total_targets||0})` },
          ...Object.entries(libNames).map(([k,v]) => ({ key: k, label: `${v} (${stats.by_library?.[k]||0})` })),
        ]}
        tabBarExtraContent={
          <Upload beforeUpload={handleBatchUpload} showUploadList={false} accept="image/*">
            <Button icon={<UploadOutlined />} size="small">批量上传</Button>
          </Upload>
        }
      />

      <Card style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
        <Table dataSource={targets} loading={loading} rowKey="id" size="small"
          columns={[
            { title: '名称', dataIndex: 'name', width: 140, render: (v: string) => <span style={{ color: '#e0e0e0' }}>{v}</span> },
            { title: '库', dataIndex: 'library', width: 90, render: (v: string) => <Tag color={libColors[v]}>{libNames[v]}</Tag> },
            { title: '类型', dataIndex: 'type', width: 70, render: (v: string) => <Tag>{typeNames[v]||v}</Tag> },
            { title: '摄像头', dataIndex: 'camera_id', width: 80 },
            { title: '时间', dataIndex: 'timestamp', width: 160, render: (v: string) => v?.slice(0,19) },
            { title: '属性', dataIndex: 'attributes', ellipsis: true,
              render: (v: any) => v ? `${v.gender||''} ${v.age_group||''} ${v.upper_color||v.color||''}` : '-' },
            { title: '操作', width: 80,
              render: (_: any, r: any) => (
                <Popconfirm title="确认删除?" onConfirm={() => handleDelete(r.id)}>
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              ),
            },
          ]} />
      </Card>

      <Modal title="添加目标" open={uploadOpen} onCancel={() => setUploadOpen(false)} onOk={handleUpload} confirmLoading={ingesting}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Select style={{ width: '100%' }} value={uploadLib} onChange={setUploadLib}
            options={Object.entries(libNames).map(([k,v]) => ({value:k,label:v}))} />
          <Input placeholder="名称（可选）" value={uploadName} onChange={e => setUploadName(e.target.value)} />
          <Upload.Dragger beforeUpload={f => { const r=new FileReader(); r.onload=()=>setUploadBase64((r.result as string).split(',')[1]); r.readAsDataURL(f); return false; }}
            onRemove={() => setUploadBase64('')} maxCount={1} accept="image/*">
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">点击或拖拽图片上传</p>
          </Upload.Dragger>
        </Space>
      </Modal>
    </div>
  );
};

export default TargetLibrary;
