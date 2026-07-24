import React from 'react';
import { Button, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import { HomeOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();
  return (
    <div style={{
      minHeight: '60vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', textAlign: 'center',
    }}>
      <Title level={1} style={{ color: '#e0e0e0', fontSize: 72, margin: 0 }}>404</Title>
      <Title level={3} style={{ color: '#a0a0a0', marginTop: 8 }}>页面未找到</Title>
      <Text style={{ color: '#64748b', marginBottom: 24 }}>
        您访问的页面不存在或已被移除
      </Text>
      <Button type="primary" size="large" icon={<HomeOutlined />} onClick={() => navigate('/')}>
        返回首页
      </Button>
    </div>
  );
};

export default NotFoundPage;
