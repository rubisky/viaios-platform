import React, { useEffect, useState } from 'react';
import { Tabs, Table, Button, Modal, Form, Input, Select, message, Tag, Popconfirm, Card } from 'antd';
import { PlusOutlined, DeleteOutlined, SafetyCertificateOutlined, CloudServerOutlined } from '@ant-design/icons';
import SystemHealth from './SystemHealth';
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
      setUsers((res as any).data || res || []);
    } catch { message.error('Failed to load users'); }
    setLoading(false);
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleCreate = async (values: any) => {
    try {
      await apiPost('/api/v1/admin/users', values);
      message.success('User created');
      setModalOpen(false);
      form.resetFields();
      fetchUsers();
    } catch { message.error('Failed to create user'); }
  };

  const columns = [
    { title: 'Username', dataIndex: 'username', key: 'username' },
    { title: 'Display Name', dataIndex: 'displayName', key: 'displayName' },
    { title: 'Email', dataIndex: 'email', key: 'email' },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={s === 'ACTIVE' ? 'green' : 'red'}>{s}</Tag> },
    { title: 'Created', dataIndex: 'createdAt', key: 'createdAt',
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
      setRoles(Array.isArray(res) ? res : (res as any)?.data || []);
    } catch { message.error('Failed to load roles'); }
    setLoading(false);
  };

  useEffect(() => { fetchRoles(); }, []);

  const handleCreate = async (values: any) => {
    try {
      await apiPost('/api/v1/admin/roles', values);
      message.success('Role created');
      setModalOpen(false);
      form.resetFields();
      fetchRoles();
    } catch { message.error('Failed to create role'); }
  };

  const handleDelete = async (id: string) => {
    try {
      await apiDelete(`/api/v1/admin/roles/${id}`);
      message.success('Role deleted');
      fetchRoles();
    } catch { message.error('Failed to delete role'); }
  };

  const columns = [
    { title: 'Role Name', dataIndex: 'roleName', key: 'roleName' },
    { title: 'Display Name', dataIndex: 'displayName', key: 'displayName' },
    { title: 'Description', dataIndex: 'description', key: 'description' },
    { title: 'Actions', key: 'actions',
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
      setTenants(Array.isArray(res) ? res : (res as any)?.data || []);
    } catch { message.error('Failed to load tenants'); }
    setLoading(false);
  };

  useEffect(() => { fetchTenants(); }, []);

  const handleCreate = async (values: any) => {
    try {
      await apiPost('/api/v1/admin/tenants', values);
      message.success('Tenant created');
      setModalOpen(false);
      form.resetFields();
      fetchTenants();
    } catch { message.error('Failed to create tenant'); }
  };

  const columns = [
    { title: 'Tenant Name', dataIndex: 'tenantName', key: 'tenantName' },
    { title: 'Display Name', dataIndex: 'displayName', key: 'displayName' },
    { title: 'Plan', dataIndex: 'plan', key: 'plan',
      render: (p: string) => <Tag color={p === 'enterprise' ? 'gold' : 'blue'}>{p}</Tag> },
    { title: 'Status', dataIndex: 'status', key: 'status',
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
        ]}
      />
    </div>
  );
};

export default AdminPage;
