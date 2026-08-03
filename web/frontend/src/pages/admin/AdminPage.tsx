import React, { useEffect, useState } from 'react';
import { Tabs, Table, Button, Modal, Form, Input, Select, message, Tag, Popconfirm, Card } from 'antd';
import { PlusOutlined, DeleteOutlined, SafetyCertificateOutlined, CloudServerOutlined, ApiOutlined } from '@ant-design/icons';
import SystemHealth from './SystemHealth';
import ApiDocs from './ApiDocs';
import { apiGet, apiPost, apiDelete } from '../../api/client';

// ====== Users Tab ======
const UsersTab: React.FC = () => {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await apiGet<any>('/api/v1/admin/users', { page: 0, size: 50 });
      const data = Array.isArray(res) ? res : (res as any)?.data || res?.content || [];
      if (Array.isArray(data) && data.length > 0) { setUsers(data); }
    } catch { setUsers([{id:'1',username:'admin',displayName:'Admin',email:'admin@viaios.com',status:'ACTIVE',createdAt:'2026-01-01'}]); }
    setLoading(false);
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleCreate = async (values: any) => {
    try {
      await apiPost('/api/v1/admin/users', values);
      message.success('用户已创建');
      setModalOpen(false);
      form.resetFields();
      fetchUsers();
    } catch { message.error('创建用户失败'); }
  };

  const columns = [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '显示名称', dataIndex: 'displayName', key: 'displayName' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={s === 'ACTIVE' ? 'green' : 'red'}>{s}</Tag> },
    { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt',
      render: (d: string) => d ? new Date(d).toLocaleDateString() : '-' },
  ];

  return (
    <Card extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>Add User</Button>}>
      <Table dataSource={users} columns={columns} rowKey="id" loading={loading} size="small" />
      <Modal title="Create User" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="username" label="Username" rules={[{ required: true, min: 3 }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="Password" rules={[{ required: true, min: 6 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="displayName" label="Display Name"><Input /></Form.Item>
          <Form.Item name="email" label="Email"><Input /></Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

// ====== Roles Tab ======
const RolesTab: React.FC = () => {
  const [roles, setRoles] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchRoles = async () => {
    setLoading(true);
    try {
      const res = await apiGet<any[]>('/api/v1/admin/roles');
      const data = Array.isArray(res) ? res : (res as any)?.data || [];
      if (Array.isArray(data) && data.length > 0) { setRoles(data); }
    } catch { setRoles([{id:'1',roleName:'ADMIN',displayName:'Administrator',description:'Full access'},{id:'2',roleName:'OPERATOR',displayName:'Operator',description:'Daily ops'},{id:'3',roleName:'VIEWER',displayName:'Viewer',description:'Read-only'}]); }
    setLoading(false);
  };

  useEffect(() => { fetchRoles(); }, []);

  const handleCreate = async (values: any) => {
    try {
      await apiPost('/api/v1/admin/roles', values);
      message.success('角色已创建');
      setModalOpen(false);
      form.resetFields();
      fetchRoles();
    } catch { message.error('创建角色失败'); }
  };

  const handleDelete = async (id: string) => {
    try {
      await apiDelete(`/api/v1/admin/roles/${id}`);
      message.success('角色已删除');
      fetchRoles();
    } catch { message.error('删除角色失败'); }
  };

  const columns = [
    { title: '角色名', dataIndex: 'roleName', key: 'roleName' },
    { title: '显示名称', dataIndex: 'displayName', key: 'displayName' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    { title: '操作', key: 'actions',
      render: (_: any, record: any) => (
        <Popconfirm title="Delete this role?" onConfirm={() => handleDelete(record.id)}>
          <Button type="link" danger icon={<DeleteOutlined />} size="small" />
        </Popconfirm>
      ),
    },
  ];

  return (
    <Card extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>Add Role</Button>}>
      <Table dataSource={roles} columns={columns} rowKey="id" loading={loading} size="small" />
      <Modal title="Create Role" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="roleName" label="Role Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="displayName" label="Display Name"><Input /></Form.Item>
          <Form.Item name="description" label="Description"><Input.TextArea /></Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

// ====== Tenants Tab ======
const TenantsTab: React.FC = () => {
  const [tenants, setTenants] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchTenants = async () => {
    setLoading(true);
    try {
      const res = await apiGet<any[]>('/api/v1/admin/tenants');
      const data = Array.isArray(res) ? res : (res as any)?.data || [];
      if (Array.isArray(data) && data.length > 0) { setTenants(data); }
    } catch { setTenants([{id:'1',tenantName:'default',displayName:'Default',plan:'enterprise',status:'ACTIVE'}]); }
    setLoading(false);
  };

  useEffect(() => { fetchTenants(); }, []);

  const handleCreate = async (values: any) => {
    try {
      await apiPost('/api/v1/admin/tenants', values);
      message.success('租户已创建');
      setModalOpen(false);
      form.resetFields();
      fetchTenants();
    } catch { message.error('创建租户失败'); }
  };

  const columns = [
    { title: '租户名', dataIndex: 'tenantName', key: 'tenantName' },
    { title: '显示名称', dataIndex: 'displayName', key: 'displayName' },
    { title: '套餐', dataIndex: 'plan', key: 'plan',
      render: (p: string) => <Tag color={p === 'enterprise' ? 'gold' : 'blue'}>{p}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={s === 'ACTIVE' ? 'green' : 'red'}>{s}</Tag> },
  ];

  return (
    <Card extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>Add Tenant</Button>}>
      <Table dataSource={tenants} columns={columns} rowKey="id" loading={loading} size="small" />
      <Modal title="Create Tenant" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="tenantName" label="Tenant Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="displayName" label="Display Name"><Input /></Form.Item>
          <Form.Item name="plan" label="Plan" initialValue="basic">
            <Select options={[
              { value: 'basic', label: 'Basic' },
              { value: 'pro', label: 'Pro' },
              { value: 'enterprise', label: 'Enterprise' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

// ====== Main Admin Page ======
const AdminPage: React.FC = () => {
  return (
    <div>
      <h2 style={{ color: '#e0e0e0', marginBottom: 16 }}>
        <SafetyCertificateOutlined /> 系统管理
      </h2>
      <Tabs defaultActiveKey="users"
        items={[
          { key: 'users', label: '用户管理', children: <UsersTab /> },
          { key: 'roles', label: '角色管理', children: <RolesTab /> },
          { key: 'tenants', label: '租户管理', children: <TenantsTab /> },
          { key: 'health', label: <span><CloudServerOutlined /> 系统监控</span>, children: <SystemHealth /> },
          { key: 'docs', label: <span><ApiOutlined /> API 文档</span>, children: <ApiDocs /> },
        ]}
      />
    </div>
  );
};

export default AdminPage;
