import React, { useState } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Dropdown, Space } from 'antd';
import type { MenuProps } from 'antd';
import {
  DashboardOutlined, SearchOutlined, FolderOpenOutlined, FileTextOutlined,
  SettingOutlined, VideoCameraOutlined, ApartmentOutlined, AimOutlined, NodeIndexOutlined,
  UserOutlined, LogoutOutlined,
} from '@ant-design/icons';
import Dashboard from '@/pages/Dashboard';
import CaseList from '@/pages/cases/CaseList';
import SearchPage from '@/pages/search/SearchPage';
import AlarmPage from '@/pages/surveillance/AlarmPage';
import AdminPage from '@/pages/admin/AdminPage';
import LoginPage from '@/pages/LoginPage';
import CameraList from '@/pages/cameras/CameraList';
import CameraDetail from '@/pages/cameras/CameraDetail';
import CaseDetail from '@/pages/cases/CaseDetail';
import ReportPage from '@/pages/reports/ReportPage';
import TrajectoryViewer from '@/pages/trajectory/TrajectoryViewer';
import WorkflowEditor from '@/pages/workflow/WorkflowEditor';
import KnowledgeGraph from '@/pages/knowledge/KnowledgeGraph';
import NotFoundPage from '@/pages/NotFoundPage';
import AuthGuard from '@/components/AuthGuard';
import NotificationBell from '@/components/NotificationBell';
import ErrorBoundary from '@/components/ErrorBoundary';
import useAppStore from '@/stores/useAppStore';

const { Header, Sider, Content } = Layout;

type MenuItem = Required<MenuProps>['items'][number];

const menuItems: MenuItem[] = [
  { key: '/', icon: <DashboardOutlined />, label: '视频侦查' },
  { key: '/search', icon: <SearchOutlined />, label: '目标检索' },
  { key: '/cameras', icon: <VideoCameraOutlined />, label: '摄像头' },
  { key: '/cases', icon: <FolderOpenOutlined />, label: '案件管理' },
  { key: '/surveillance', icon: <VideoCameraOutlined />, label: '智能研判' },
  { key: '/trajectory', icon: <AimOutlined />, label: '轨迹回放' },
  { key: '/workflow', icon: <NodeIndexOutlined />, label: '工作流' },
  { key: '/reports', icon: <FileTextOutlined />, label: '报告中心' },
  { key: '/knowledge', icon: <ApartmentOutlined />, label: '知识图谱' },
  { key: '/settings', icon: <SettingOutlined />, label: '系统管理' },
];

const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAppStore();

  const selectedKey = menuItems.find(
    (item) => item && 'key' in item && location.pathname.startsWith(item.key as string) && item.key !== '/'
  ) ? (menuItems.find((item) => item && 'key' in item && location.pathname.startsWith(item.key as string) && item.key !== '/') as { key: string }).key
    : location.pathname;

  const userMenuItems: MenuProps['items'] = [
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: logout },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}
        style={{ background: '#0f0f23', borderRight: '1px solid #2a2a4a' }}>
        <div style={{
          height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontSize: collapsed ? 16 : 20, fontWeight: 700, letterSpacing: 2,
          borderBottom: '1px solid #2a2a4a',
        }}>
          {collapsed ? 'VI' : 'VIAIOS'}
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[selectedKey === '/' ? '/' : selectedKey]}
          items={menuItems} onClick={({ key }) => navigate(key)}
          style={{ background: 'transparent', borderRight: 0 }} />
      </Sider>
      <Layout>
        <Header style={{
          background: '#0f0f23', padding: '0 24px', display: 'flex',
          alignItems: 'center', justifyContent: 'space-between',
          borderBottom: '1px solid #2a2a4a', height: 64,
        }}>
          <span style={{ color: '#e0e0e0', fontSize: 16, fontWeight: 500 }}>
            VIAIOS 智能视频侦查平台
          </span>
          <Space size="large">
            <NotificationBell />
            <Dropdown menu={{ items: userMenuItems }}>
              <Button type="text" style={{ color: '#e0e0e0' }}>
                <Space>
                  <UserOutlined />
                  {user?.username || 'User'}
                </Space>
              </Button>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{
          margin: 16, padding: 24, background: '#0f0f23', borderRadius: 8,
          border: '1px solid #2a2a4a', minHeight: 280, overflow: 'auto',
        }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/cases" element={<CaseList />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/cameras" element={<CameraList />} />
            <Route path="/cameras/:id" element={<CameraDetail />} />
            <Route path="/cameras/:id" element={<CameraDetail />} />
            <Route path="/cases/:id" element={<CaseDetail />} />
            <Route path="/surveillance" element={<AlarmPage />} />
            <Route path="/trajectory" element={<TrajectoryViewer />} />
            <Route path="/workflow" element={<WorkflowEditor />} />
            <Route path="/reports" element={<ReportPage />} />
            <Route path="/knowledge" element={<KnowledgeGraph />} />
            <Route path="/settings" element={<AdminPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
};

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="*" element={
        <AuthGuard><ErrorBoundary><MainLayout /></ErrorBoundary></AuthGuard>
      } />
    </Routes>
  );
};

export default App;
