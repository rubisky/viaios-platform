import React from 'react';
import { Button, Result, Typography, Space } from 'antd';
import { HomeOutlined, ReloadOutlined, BugOutlined } from '@ant-design/icons';

const { Paragraph } = Typography;

interface Props { children: React.ReactNode; fallback?: React.ReactNode; }
interface State { hasError: boolean; error: Error | null; errorInfo: string; }

export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, error: null, errorInfo: '' };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo: errorInfo.componentStack || '' });
    console.error('[ErrorBoundary]', error.message, errorInfo.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: '' });
    window.location.href = '/';
  };

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: '' });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      const msg = this.state.error?.message || '未知错误';
      const isNetwork = msg.includes('Network') || msg.includes('fetch') || msg.includes('timeout');
      const isTypeError = msg.includes('is not a function') || msg.includes('undefined');
      return (
        <div style={{ minHeight: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f0f23' }}>
          <Result
            status={isNetwork ? 'warning' : 'error'}
            icon={isTypeError ? <BugOutlined /> : undefined}
            title={isNetwork ? '网络连接异常' : '页面加载异常'}
            subTitle={
              <div>
                <Paragraph style={{ color: '#a0a0a0', maxWidth: 500 }}>
                  {isNetwork ? '无法连接到服务器，请检查网络后重试。' :
                   isTypeError ? '页面组件加载失败，可能是版本不兼容。请尝试刷新页面。' :
                   `错误详情: ${msg.substring(0, 100)}`}
                </Paragraph>
                {this.state.errorInfo && (
                  <details style={{ marginTop: 8 }}>
                    <summary style={{ color: '#64748b', cursor: 'pointer', fontSize: 12 }}>技术详情</summary>
                    <pre style={{ color: '#64748b', fontSize: 10, maxHeight: 200, overflow: 'auto', textAlign: 'left', background: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                      {this.state.errorInfo.substring(0, 500)}
                    </pre>
                  </details>
                )}
              </div>
            }
            extra={
              <Space>
                <Button type="primary" icon={<ReloadOutlined />} onClick={this.handleRetry}>刷新重试</Button>
                <Button icon={<HomeOutlined />} onClick={this.handleReset}>返回首页</Button>
              </Space>
            }
          />
        </div>
      );
    }
    return this.props.children;
  }
}
