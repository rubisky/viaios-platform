/** FeatureCard — 统一目标特征页卡 (人脸/人体/车辆/步态/非机动车) */
import React from 'react';
import { Card, Tag, Descriptions, Space, Badge, Row, Col, Tooltip } from 'antd';
import {
  UserOutlined, SmileOutlined, CarOutlined, TeamOutlined,
  AimOutlined, EnvironmentOutlined,
} from '@ant-design/icons';

interface FeatureData {
  id: string; name: string; type: string; confidence: number;
  library?: string; camera_id?: string; timestamp?: string;
  faces?: FaceFeature[]; bodies?: BodyFeature[];
  vehicles?: VehicleFeature[]; gaits?: GaitFeature[];
  bikes?: BikeFeature[];
}

interface FaceFeature {
  id: string; confidence: number; gender: string; age: string;
  attributes: Record<string,any>;
}

interface BodyFeature {
  id: string; confidence: number; height?: string; build?: string;
  upper_clothing?: string; upper_color?: string;
  lower_clothing?: string; lower_color?: string;
  has_backpack?: boolean; has_hat?: boolean; has_mask?: boolean;
}

interface VehicleFeature {
  id: string; confidence: number; type: string; color: string;
  plate?: string; brand?: string; direction?: string;
}

interface GaitFeature {
  id: string; confidence: number; pattern?: string; stride?: string;
}

interface BikeFeature {
  id: string; confidence: number; type: string; color: string;
  rider_count?: number; helmet?: boolean;
}

const typeIcons: Record<string, React.ReactNode> = {
  person: <TeamOutlined />, face: <SmileOutlined />,
  vehicle: <CarOutlined />, body: <AimOutlined />,
  gait: <EnvironmentOutlined />, bike: <EnvironmentOutlined />,
};
const typeNames: Record<string,string> = {person:'人员',face:'人脸',vehicle:'车辆',body:'人体',gait:'步态',bike:'非机动车'};
const typeColors: Record<string,string> = {person:'#4ecdc4',face:'#ff6b6b',vehicle:'#45b7d1',body:'#96ceb4',gait:'#f7dc6f',bike:'#bb8fce'};

const FeatureCard: React.FC<{ data: FeatureData; compact?: boolean; checked?: boolean; onToggle?: (id:string) => void }> = ({ data, compact, checked, onToggle }) => {
  const libNames: Record<string,string> = {snapshot:'抓拍',upload:'上传',watchlist:'布控',history:'历史'};
  const isChecked = checked !== undefined ? checked : true;
  const cardStyle = {
    background: isChecked ? '#1a3a5c' : '#0f1525',
    borderColor: isChecked ? typeColors[data.type] : '#2a2a4a',
    cursor: onToggle ? 'pointer' : 'default',
  };

  const renderFaces = () => (data.faces || []).map(f => (
    <Descriptions key={f.id} size="small" column={2} style={{ marginTop: 8 }}>
      <Descriptions.Item label="性别">{f.gender||'-'}</Descriptions.Item>
      <Descriptions.Item label="年龄">{f.age||'-'}</Descriptions.Item>
      <Descriptions.Item label="眼镜">{f.attributes?.glass||'无'}</Descriptions.Item>
      <Descriptions.Item label="口罩">{f.attributes?.mask||'无'}</Descriptions.Item>
    </Descriptions>
  ));

  const renderBodies = () => (data.bodies || []).map(b => (
    <Descriptions key={b.id} size="small" column={2} style={{ marginTop: 8 }}>
      <Descriptions.Item label="上衣">{b.upper_clothing||'-'} {b.upper_color||''}</Descriptions.Item>
      <Descriptions.Item label="下衣">{b.lower_clothing||'-'} {b.lower_color||''}</Descriptions.Item>
      <Descriptions.Item label="体型">{b.build||'-'}</Descriptions.Item>
      <Descriptions.Item label="身高">{b.height||'-'}</Descriptions.Item>
      <Descriptions.Item label="背包"><Tag color={b.has_backpack?'green':'default'}>{b.has_backpack?'有':'无'}</Tag></Descriptions.Item>
      <Descriptions.Item label="帽子"><Tag color={b.has_hat?'green':'default'}>{b.has_hat?'有':'无'}</Tag></Descriptions.Item>
    </Descriptions>
  ));

  const renderVehicles = () => (data.vehicles || []).map(v => (
    <Descriptions key={v.id} size="small" column={2} style={{ marginTop: 8 }}>
      <Descriptions.Item label="类型">{v.type||'-'}</Descriptions.Item>
      <Descriptions.Item label="颜色">{v.color||'-'}</Descriptions.Item>
      <Descriptions.Item label="车牌">{v.plate||'-'}</Descriptions.Item>
      <Descriptions.Item label="品牌">{v.brand||'-'}</Descriptions.Item>
    </Descriptions>
  ));

  const renderGaits = () => (data.gaits || []).map(g => (
    <Descriptions key={g.id} size="small" column={1} style={{ marginTop: 8 }}>
      <Descriptions.Item label="步态模式">{g.pattern||'-'}</Descriptions.Item>
      <Descriptions.Item label="步幅">{g.stride||'-'}</Descriptions.Item>
    </Descriptions>
  ));

  const renderBikes = () => (data.bikes || []).map(b => (
    <Descriptions key={b.id} size="small" column={2} style={{ marginTop: 8 }}>
      <Descriptions.Item label="类型">{b.type||'-'}</Descriptions.Item>
      <Descriptions.Item label="颜色">{b.color||'-'}</Descriptions.Item>
      <Descriptions.Item label="骑行者">{b.rider_count||'1'}人</Descriptions.Item>
      <Descriptions.Item label="头盔"><Tag color={b.helmet?'green':'default'}>{b.helmet?'有':'无'}</Tag></Descriptions.Item>
    </Descriptions>
  ));

  return (
    <Card size="small" hoverable style={cardStyle}
      onClick={() => onToggle?.(data.id)}
      title={
        <Space size={4}>
          {typeIcons[data.type]}&nbsp;
          <span style={{ color: '#e0e0e0', fontSize: compact?12:14 }}>{data.name || typeNames[data.type]}</span>
          <Tag color={typeColors[data.type]} style={{ fontSize:10 }}>{typeNames[data.type]}</Tag>
          <Tag style={{ fontSize:10 }}>{(data.confidence*100).toFixed(0)}%</Tag>
          {data.library && <Tag color="blue" style={{ fontSize:10 }}>{libNames[data.library]||data.library}</Tag>}
        </Space>
      }
    >
      <Space direction="vertical" size={4} style={{ width:'100%' }}>
        {data.camera_id && <span style={{color:'#64748b',fontSize:11}}>📷 {data.camera_id} {data.timestamp?.slice(0,19)||''}</span>}
        {!compact && renderFaces()}
        {!compact && renderBodies()}
        {renderVehicles()}
        {renderGaits()}
        {renderBikes()}
        {compact && (data.faces||[]).length > 0 && <span style={{fontSize:11,color:'#a0a0a0'}}>👤 {(data.faces||[]).length} 人脸</span>}
        {compact && (data.bodies||[]).length > 0 && <span style={{fontSize:11,color:'#a0a0a0'}}>🚶 {(data.bodies||[]).length} 人体</span>}
      </Space>
    </Card>
  );
};

export default FeatureCard;
export type { FeatureData };
