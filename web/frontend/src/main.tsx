import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';
import './index.css';

const savedTheme = (localStorage.getItem('viaios_theme') as 'dark' | 'light') || 'dark';
const isDark = savedTheme === 'dark';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ConfigProvider
        locale={zhCN}
        theme={{
          algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
          token: {
            colorPrimary: '#1677ff',
            borderRadius: 6,
            ...(isDark ? {
              colorBgContainer: '#1a1a2e',
              colorBgElevated: '#16213e',
              colorText: '#e0e0e0',
              colorTextSecondary: '#a0a0a0',
              colorBorder: '#2a2a4a',
            } : {}),
          },
        }}
      >
        <App />
      </ConfigProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
