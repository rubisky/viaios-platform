import React, { useState } from 'react';
import { Card, Form, Input, Button, Typography, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import useAppStore from '../stores/useAppStore';
import { apiPost } from '../api/client';

const { Title, Text } = Typography;

interface LoginResponse {
  accessToken?: string;
  refreshToken?: string;
  expiresIn?: number;
  username?: string;
  role?: string;
}

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setToken, setUser } = useAppStore();

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    // Call gateway auth endpoint
    const res = await apiPost<LoginResponse>('/api/v1/auth/login', values);
    setLoading(false);

    if (res.accessToken) {
      setToken(res.accessToken);
      setUser({
        id: '1',
        username: res.username || values.username,
        role: res.role || 'ADMIN',
        tenantId: 'default',
      });
      message.success('登录成功');
      navigate('/', { replace: true });
      return;
    }

    message.error('登录失败，请检查用户名和密码');
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #0a0e1a 0%, #0d1220 100%)',
    }}>
      <Card style={{
        width: 400, background: '#16213e', border: '1px solid #2a2a4a',
        boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2} style={{ color: '#e0e0e0', margin: 0 }}>VIAIOS</Title>
          <Text style={{ color: '#a0a0a0' }}>智能视频侦查平台</Text>
        </div>
        <Form onFinish={handleLogin} size="large">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" autoFocus />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登 录
            </Button>
          </Form.Item>
        </Form>
        <div style={{ textAlign: 'center' }}>
          <Text style={{ color: '#64748b', fontSize: 12 }}>
            默认账户: admin / viaios-admin-2024
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;
