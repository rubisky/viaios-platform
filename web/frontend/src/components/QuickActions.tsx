import React from 'react';
import { Card, Row, Col, Typography } from 'antd';
import { SearchOutlined, VideoCameraOutlined, FolderAddOutlined, FileTextOutlined, AlertOutlined, ApartmentOutlined, AimOutlined, NodeIndexOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;

const actions = [
  { icon: <SearchOutlined style={{ fontSize: 20 }} />, label: '目标检索', desc: '图片/文本搜索', path: '/search', color: '#1677ff' },
  { icon: <VideoCameraOutlined style={{ fontSize: 20 }} />, label: '查看摄像头', desc: '实时监控画面', path: '/cameras', color: '#52c41a' },
  { icon: <FolderAddOutlined style={{ fontSize: 20 }} />, label: '新建案件', desc: '创建调查案件', path: '/cases', color: '#faad14' },
  { icon: <AlertOutlined style={{ fontSize: 20 }} />, label: '告警中心', desc: '查看和处理告警', path: '/surveillance', color: '#ff4d4f' },
  { icon: <AimOutlined style={{ fontSize: 20 }} />, label: '轨迹分析', desc: '目标轨迹回放', path: '/trajectory', color: '#13c2c2' },
  { icon: <ApartmentOutlined style={{ fontSize: 20 }} />, label: '知识图谱', desc: '实体关系分析', path: '/knowledge', color: '#722ed1' },
  { icon: <NodeIndexOutlined style={{ fontSize: 20 }} />, label: '工作流', desc: '任务编排执行', path: '/workflow', color: '#eb2f96' },
  { icon: <FileTextOutlined style={{ fontSize: 20 }} />, label: '报告中心', desc: '查看和生成报告', path: '/reports', color: '#2f54eb' },
];

const QuickActions: React.FC = () => {
  const navigate = useNavigate();
  return (
    <Card title={<Text style={{ color: '#e0e0e0' }}>快捷操作</Text>}
      style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
      <Row gutter={[12, 12]}>
        {actions.map(a => (
          <Col xs={12} sm={6} key={a.path}>
            <Card hoverable size="small"
              onClick={() => navigate(a.path)}
              style={{
                background: '#0f0f23', border: `1px solid ${a.color}33`, borderRadius: 8,
                cursor: 'pointer', textAlign: 'center', transition: 'all 0.2s',
              }}
              bodyStyle={{ padding: '16px 8px' }}>
              <div style={{ color: a.color, marginBottom: 8 }}>{a.icon}</div>
              <Text strong style={{ color: '#e0e0e0', fontSize: 13, display: 'block' }}>{a.label}</Text>
              <Text style={{ color: '#64748b', fontSize: 11 }}>{a.desc}</Text>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>
  );
};

export default QuickActions;
