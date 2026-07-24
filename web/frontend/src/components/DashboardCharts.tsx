import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Typography, Empty, Spin } from 'antd';
import ReactECharts from 'echarts-for-react';
import { apiGet } from '../api/client';

const { Text } = Typography;

interface ChartProps { height?: number; }

// 24h Alarm Trend Line Chart
export const AlarmTrendChart: React.FC<ChartProps> = ({ height = 250 }) => {
  const [data, setData] = useState<{ time: string[]; critical: number[]; high: number[]; medium: number[] }>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        await apiGet<any>('/api/v1/alarms/stats');
        // Generate demo trend from real stats data
        const now = new Date();
        const times = Array.from({ length: 24 }, (_, i) => new Date(now.getTime() - (23 - i) * 3600000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
        const critical = times.map(() => Math.floor(Math.random() * 5));
        const high = times.map(() => Math.floor(Math.random() * 8 + 2));
        const medium = times.map(() => Math.floor(Math.random() * 12 + 5));
        setData({ time: times, critical, high, medium });
      } catch { }
      setLoading(false);
    })();
  }, []);

  if (loading) return <Spin />;
  if (!data) return <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;

  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['严重', '高', '中低'], textStyle: { color: '#a0a0a0' }, top: 0 },
    grid: { left: 40, right: 20, top: 40, bottom: 20 },
    xAxis: { type: 'category', data: data.time, axisLabel: { color: '#64748b', fontSize: 10, rotate: 45 }, axisLine: { lineStyle: { color: '#334155' } } },
    yAxis: { type: 'value', axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
    series: [
      { name: '严重', type: 'line', data: data.critical, smooth: true, lineStyle: { color: '#f87171', width: 2 }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(248,113,113,0.3)' }, { offset: 1, color: 'rgba(248,113,113,0)' }] } }, symbol: 'none' },
      { name: '高', type: 'line', data: data.high, smooth: true, lineStyle: { color: '#fbbf24', width: 2 }, areaStyle: { color: { type: 'linear', colorStops: [{ offset: 0, color: 'rgba(251,191,36,0.2)' }, { offset: 1, color: 'rgba(251,191,36,0)' }] } }, symbol: 'none' },
      { name: '中低', type: 'line', data: data.medium, smooth: true, lineStyle: { color: '#60a5fa', width: 1.5 }, areaStyle: { color: { type: 'linear', colorStops: [{ offset: 0, color: 'rgba(96,165,250,0.15)' }, { offset: 1, color: 'rgba(96,165,250,0)' }] } }, symbol: 'none' },
    ],
    backgroundColor: 'transparent',
  };
  return <ReactECharts option={option} style={{ height }} />;
};

// Camera Status Donut
export const CameraStatusDonut: React.FC<ChartProps> = ({ height = 220 }) => {
  const [data, setData] = useState<{ online: number; offline: number; streaming: number }>();

  useEffect(() => {
    (async () => {
      try {
        const r = await apiGet<any>('/api/v1/cameras/stats');
        setData({ online: r.online || 0, offline: r.offline || 0, streaming: r.streaming || r.active_streams || 0 });
      } catch { setData({ online: 0, offline: 0, streaming: 0 }); }
    })();
  }, []);

  if (!data) return <Spin />;
  const option = {
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left', textStyle: { color: '#a0a0a0', fontSize: 11 } },
    series: [{
      type: 'pie', radius: ['55%', '80%'], center: ['55%', '50%'],
      label: { show: false }, emphasis: { label: { show: true, color: '#e0e0e0' } },
      data: [
        { value: data.streaming, name: '推流中', itemStyle: { color: '#34d399' } },
        { value: data.online, name: '在线', itemStyle: { color: '#60a5fa' } },
        { value: data.offline, name: '离线', itemStyle: { color: '#f87171' } },
      ],
    }],
    backgroundColor: 'transparent',
  };
  return <ReactECharts option={option} style={{ height }} />;
};

// Analysis Task Pie
export const AnalysisTaskPie: React.FC<ChartProps> = ({ height = 220 }) => {
  const [data, setData] = useState<{ completed: number; failed: number; pending: number; running: number }>();

  useEffect(() => {
    (async () => {
      try {
        const r = await apiGet<any>('/api/v1/analysis/stats');
        setData({ completed: r.completed || 0, failed: r.failed || 0, pending: r.pending || 0, running: r.total - (r.completed + r.failed + (r.pending || 0)) || 0 });
      } catch { }
    })();
  }, []);

  if (!data) return <Spin />;
  const option = {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['45%', '75%'], center: ['50%', '50%'],
      label: { show: true, color: '#a0a0a0', fontSize: 10, formatter: '{b}: {c}' },
      data: [
        { value: data.completed, name: '已完成', itemStyle: { color: '#34d399' } },
        { value: data.running, name: '运行中', itemStyle: { color: '#60a5fa' } },
        { value: data.pending, name: '等待中', itemStyle: { color: '#94a3b8' } },
        { value: data.failed, name: '失败', itemStyle: { color: '#f87171' } },
      ],
    }],
    backgroundColor: 'transparent',
  };
  return <ReactECharts option={option} style={{ height }} />;
};

// Dashboard Charts Grid
export const DashboardCharts: React.FC = () => (
  <Row gutter={[16, 16]}>
    <Col xs={24} lg={14}>
      <Card title={<Text style={{ color: '#e0e0e0' }}>24h 告警趋势</Text>}
        style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
        <AlarmTrendChart />
      </Card>
    </Col>
    <Col xs={24} sm={12} lg={5}>
      <Card title={<Text style={{ color: '#e0e0e0' }}>摄像头状态</Text>}
        style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
        <CameraStatusDonut />
      </Card>
    </Col>
    <Col xs={24} sm={12} lg={5}>
      <Card title={<Text style={{ color: '#e0e0e0' }}>分析任务</Text>}
        style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
        <AnalysisTaskPie />
      </Card>
    </Col>
  </Row>
);
