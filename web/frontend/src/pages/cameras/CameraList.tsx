import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Tag, Button, Space, Typography, Modal, Form, Input, Select, message } from 'antd';
import { PlusOutlined, ReloadOutlined, VideoCameraOutlined } from '@ant-design/icons';
import { apiGet, apiPost } from '../../api/client';

const { Title } = Typography;

interface Camera {
  id: string;
  name: string;
  location?: string;
  protocol?: string;
  ipAddress?: string;
  status: string;
  resolution?: string;
  fps?: number;
  lastSeenAt?: string;
}

const statusColors: Record<string, string> = { ONLINE: 'green', STREAMING: 'cyan', OFFLINE: 'red', ERROR: 'orange' };

const CameraList: React.FC = () => {
  const navigate = useNavigate();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchCameras = async () => {
    setLoading(true);
    try {
      const res = await apiGet<any>('/api/v1/cameras');
      setCameras(Array.isArray(res) ? res : res?.data || []);
    } catch { message.error('加载摄像头列表失败'); }
    setLoading(false);
  };

  useEffect(() => { fetchCameras(); }, []);

  const handleCreate = async (values: any) => {
    try {
      await apiPost('/api/v1/cameras', values);
      message.success('摄像头已添加');
      setModalOpen(false); form.resetFields(); fetchCameras();
    } catch { message.error('添加失败'); }
  };

  const handleToggle = async (id: string, currentStatus: string) => {
    try {
      if (currentStatus === 'STREAMING' || currentStatus === 'ONLINE') {
        await apiPost(`/api/v1/cameras/${id}/stop`);
      } else {
        await apiPost(`/api/v1/cameras/${id}/start`);
      }
      message.success('操作成功'); fetchCameras();
    } catch { message.error('操作失败'); }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '位置', dataIndex: 'location', key: 'location' },
    { title: '协议', dataIndex: 'protocol', key: 'protocol', width: 80,
      render: (p: string) => <Tag>{p || 'RTSP'}</Tag> },
    { title: 'IP', dataIndex: 'ipAddress', key: 'ipAddress', width: 130 },
    { title: '分辨率', dataIndex: 'resolution', key: 'resolution', width: 100 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90,
      render: (s: string) => <Tag color={statusColors[s] || 'default'}>{s || '-'}</Tag> },
    { title: '最后在线', dataIndex: 'lastSeenAt', key: 'lastSeenAt', width: 160,
      render: (d: string) => d ? new Date(d).toLocaleString('zh-CN') : '-' },
    { title: '操作', key: 'actions', width: 120,
      render: (_: any, r: Camera) => (
        <Button size="small" onClick={() => handleToggle(r.id, r.status)}
          type={r.status === 'STREAMING' ? 'default' : 'primary'}>
          {r.status === 'STREAMING' || r.status === 'ONLINE' ? '停止' : '启动'}
        </Button>
      )},
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={2} style={{ color: '#e0e0e0', margin: 0 }}>
          <VideoCameraOutlined style={{ marginRight: 8 }} />摄像头管理
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchCameras}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>添加摄像头</Button>
        </Space>
      </div>
      <Table columns={columns} dataSource={cameras} rowKey="id" loading={loading} size="middle"
        onRow={(r) => ({ onClick: () => navigate(`/cameras/${r.id}`), style: { cursor: 'pointer' } })} />
      <Modal title="添加摄像头" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="location" label="位置"><Input /></Form.Item>
          <Form.Item name="ipAddress" label="IP 地址"><Input /></Form.Item>
          <Form.Item name="protocol" label="协议" initialValue="RTSP">
            <Select options={[
              { value: 'RTSP', label: 'RTSP' }, { value: 'GB28181', label: 'GB28181' },
              { value: 'ONVIF', label: 'ONVIF' }, { value: 'RTMP', label: 'RTMP' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CameraList;
