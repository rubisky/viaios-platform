import React, { useEffect, useState } from 'react';
import { Badge, Popover, List, Typography, Tag, Button } from 'antd';
import { BellOutlined } from '@ant-design/icons';
import { apiGet } from '../api/client';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;

const NotificationBell: React.FC = () => {
  const [alarms, setAlarms] = useState<any[]>([]);
  const [count, setCount] = useState(0);
  const navigate = useNavigate();

  const fetchAlarms = async () => {
    try {
      const res = await apiGet<any>('/api/v1/alarms', { status: 'TRIGGERED' });
      const data = Array.isArray(res) ? res : res?.data || [];
      setAlarms(data.slice(0, 10));
      setCount(data.length);
    } catch {}
  };

  useEffect(() => { fetchAlarms(); const t = setInterval(fetchAlarms, 30000); return () => clearInterval(t); }, []);

  const content = (
    <div style={{ width: 320, maxHeight: 400, overflow: 'auto' }}>
      <List size="small" dataSource={alarms} locale={{ emptyText: '暂无活跃告警' }}
        renderItem={(a: any) => (
          <List.Item style={{ cursor: 'pointer' }} onClick={() => navigate('/surveillance')}>
            <div style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Tag color={a.severity === 'CRITICAL' ? 'red' : 'orange'}>{a.severity || 'MEDIUM'}</Tag>
                <Text style={{ fontSize: 11, color: '#64748b' }}>
                  {a.triggeredAt ? new Date(a.triggeredAt).toLocaleTimeString() : ''}
                </Text>
              </div>
              <Text style={{ fontSize: 13 }}>{a.message || a.type || 'Alarm'}</Text>
            </div>
          </List.Item>
        )} />
      {alarms.length > 0 && (
        <div style={{ textAlign: 'center', padding: 8 }}>
          <Button size="small" type="link" onClick={() => navigate('/surveillance')}>查看全部</Button>
        </div>
      )}
    </div>
  );

  return (
    <Popover content={content} title="实时告警" trigger="click">
      <Badge count={count} size="small">
        <BellOutlined style={{ fontSize: 18, color: count > 0 ? '#faad14' : '#e0e0e0', cursor: 'pointer' }} />
      </Badge>
    </Popover>
  );
};

export default NotificationBell;
