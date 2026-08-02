import React, { useState, Suspense, lazy } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Dropdown, Space, Grid, ConfigProvider, theme as antTheme, Breadcrumb, Spin, Drawer } from 'antd';
import type { MenuProps } from 'antd';
import {
  DashboardOutlined, SearchOutlined, FolderOpenOutlined, FileTextOutlined,
  SettingOutlined, VideoCameraOutlined, ApartmentOutlined, AimOutlined, NodeIndexOutlined,
  UserOutlined, LogoutOutlined, MenuOutlined,
} from '@ant-design/icons';
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const CaseList = lazy(() => import('@/pages/cases/CaseList'));
const SearchPage = lazy(() => import('@/pages/search/SearchPage'));
const AlarmPage = lazy(() => import('@/pages/surveillance/AlarmPage'));
const AdminPage = lazy(() => import('@/pages/admin/AdminPage'));
const LoginPage = lazy(() => import('@/pages/LoginPage'));
const CameraList = lazy(() => import('@/pages/cameras/CameraList'));
const CameraDetail = lazy(() => import('@/pages/cameras/CameraDetail'));
const CaseDetail = lazy(() => import('@/pages/cases/CaseDetail'));
const ReportPage = lazy(() => import('@/pages/reports/ReportPage'));
const TrajectoryViewer = lazy(() => import('@/pages/trajectory/TrajectoryViewer'));
const WorkflowEditor = lazy(() => import('@/pages/workflow/WorkflowEditor'));
const KnowledgeGraph = lazy(() => import('@/pages/knowledge/KnowledgeGraph'));
const ModelManagement = lazy(() => import('@/pages/admin/ModelManagement'));
const AuditLog = lazy(() => import('@/pages/admin/AuditLog'));
const SystemDiagnostics = lazy(() => import('@/pages/admin/SystemDiagnostics'));
const SettingsWizard = lazy(() => import('@/pages/admin/SettingsWizard'));
const AlarmCenter = lazy(() => import('@/pages/surveillance/AlarmCenter'));
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'));
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
  { key: '/models', icon: <SettingOutlined />, label: '模型管理' },
  { key: '/audit', icon: <SettingOutlined />, label: '审计日志' },
  { key: '/diagnostics', icon: <SettingOutlined />, label: '系统诊断' },
  { key: '/wizard', icon: <SettingOutlined />, label: '设置向导' },
];

const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.lg;
  const [collapsed, setCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, logout, theme, setTheme } = useAppStore();

  const selectedKey = menuItems.find(
    (item) => item && 'key' in item && location.pathname.startsWith(item.key as string) && item.key !== '/'
  ) ? (menuItems.find((item) => item && 'key' in item && location.pathname.startsWith(item.key as string) && item.key !== '/') as { key: string }).key
    : location.pathname;

  const userMenuItems: MenuProps['items'] = [
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: logout },
  ];

  const handleMenuClick = (key: string) => {
    navigate(key);
    setMobileMenuOpen(false);
  };

  const isDark = theme === 'dark';

  const sidebarBg = isDark ? '#0f0f23' : '#001529';

  const menuNode = (
    <>
      <div style={{
        height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#fff', fontSize: collapsed && !isMobile ? 16 : 20, fontWeight: 700, letterSpacing: 2,
        borderBottom: '1px solid #2a2a4a',
      }}>
        {collapsed && !isMobile ? 'VI' : 'VIAIOS'}
      </div>
      <Menu theme="dark" mode="inline" selectedKeys={[selectedKey === '/' ? '/' : selectedKey]}
        items={menuItems} onClick={({ key }) => handleMenuClick(key)}
        style={{ background: 'transparent', borderRight: 0 }} />
    </>
  );

  return (
    <ConfigProvider theme={{ algorithm: isDark ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm }}>
    <Layout style={{ minHeight: '100vh', background: isDark ? '#0f0f23' : '#f0f2f5', transition: 'background 0.3s' }}>
      {/* Mobile drawer menu */}
      {isMobile ? (
        <Drawer
          placement="left"
          open={mobileMenuOpen}
          onClose={() => setMobileMenuOpen(false)}
          width={260}
          styles={{ body: { padding: 0, background: sidebarBg } }}
          closeIcon={null}
        >
          {menuNode}
        </Drawer>
      ) : (
        /* Desktop sidebar */
        <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}
          breakpoint="lg" collapsedWidth={64}
          trigger={isMobile ? null : undefined}
          style={{ background: sidebarBg, borderRight: `1px solid ${isDark ? '#2a2a4a' : '#0a0a1e'}`,
            transition: 'all 0.3s', position: 'sticky', top: 0, height: '100vh', overflow: 'auto' }}>
          {menuNode}
        </Sider>
      )}
      <Layout>
        <Header style={{
          background: isDark ? '#0f0f23' : '#001529',
          padding: isMobile ? '0 12px' : '0 24px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          borderBottom: `1px solid ${isDark ? '#2a2a4a' : '#0a0a1e'}`,
          height: 64, transition: 'background 0.3s',
        }}>
          <Space>
            {isMobile && (
              <Button type="text" icon={<MenuOutlined />}
                style={{ color: '#e0e0e0' }}
                onClick={() => setMobileMenuOpen(true)} />
            )}
            <span style={{
              color: '#e0e0e0', fontSize: isMobile ? 14 : 16, fontWeight: 500,
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {isMobile ? 'VIAIOS' : 'VIAIOS 智能视频侦查平台'}
            </span>
          </Space>
          <Space size={isMobile ? 'small' : 'large'}>
            <Button type="text"
              style={{ color: '#e0e0e0', fontSize: isMobile ? 16 : 18 }}
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              title={theme === 'dark' ? '切换浅色' : '切换深色'}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </Button>
            {!isMobile && <NotificationBell />}
            <Dropdown menu={{ items: userMenuItems }}>
              <Button type="text" style={{ color: '#e0e0e0' }}>
                <Space size={4}>
                  <UserOutlined />
                  {!isMobile && (user?.username || 'User')}
                </Space>
              </Button>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{
          margin: isMobile ? 8 : 16, padding: isMobile ? 12 : 24,
          background: isDark ? '#0f0f23' : '#fff', borderRadius: 8,
          border: `1px solid ${isDark ? '#2a2a4a' : '#e5e7eb'}`,
          minHeight: 280, overflow: 'auto', transition: 'background 0.3s, border-color 0.3s',
        }}>
          {!isMobile && (
            <Breadcrumb style={{ marginBottom: 16 }}
              items={location.pathname.split('/').filter(Boolean).map((p) => ({
                title: p.charAt(0).toUpperCase() + p.slice(1).replace(/-/g, ' '),
              }))} />
          )}
          <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', padding: 100 }}><Spin size="large" /></div>}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/cases" element={<CaseList />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/cameras" element={<CameraList />} />
            <Route path="/cameras/:id" element={<CameraDetail />} />
            <Route path="/cases/:id" element={<CaseDetail />} />
            <Route path="/surveillance" element={<AlarmPage />} />
            <Route path="/alarms" element={<AlarmCenter />} />
            <Route path="/trajectory" element={<TrajectoryViewer />} />
            <Route path="/workflow" element={<WorkflowEditor />} />
            <Route path="/reports" element={<ReportPage />} />
            <Route path="/knowledge" element={<KnowledgeGraph />} />
            <Route path="/settings" element={<AdminPage />} />
            <Route path="/models" element={<ModelManagement />} />
            <Route path="/audit" element={<AuditLog />} />
            <Route path="/diagnostics" element={<SystemDiagnostics />} />
            <Route path="/wizard" element={<SettingsWizard />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
          </Suspense>
        </Content>
      </Layout>
    </Layout>
    </ConfigProvider>
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
