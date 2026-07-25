import React, { useState, useEffect } from 'react';
import { Card, Typography, Button, Modal, Input, Switch, Space, Tag, Empty, message } from 'antd';
import { SaveOutlined, ClockCircleOutlined, SearchOutlined } from '@ant-design/icons';
import type { SavedSearch, SearchMode, SearchParams } from '../../types/search';

const { Text } = Typography;
const STORAGE_KEY = 'viaios_saved_searches';

interface Props {
  currentMode: SearchMode;
  currentParams: SearchParams | null;
  onLoad: (saved: SavedSearch) => void;
}

const MODE_LABELS: Record<SearchMode, string> = {
  image: '图片搜', text: '文本搜', attribute: '属性搜', composite: '综合搜',
};

const SavedSearchPanel: React.FC<Props> = ({ currentMode, currentParams, onLoad }) => {
  const [saved, setSaved] = useState<SavedSearch[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [alertOnNew, setAlertOnNew] = useState(false);

  useEffect(() => {
    try {
      const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      setSaved(data);
    } catch { /* ignore */ }
  }, []);

  const persist = (items: SavedSearch[]) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    setSaved(items);
  };

  const handleSave = () => {
    if (!saveName.trim()) { message.warning('请输入搜索名称'); return; }
    if (!currentParams) { message.warning('请先执行搜索'); return; }

    const item: SavedSearch = {
      id: Date.now().toString(36),
      name: saveName.trim(),
      mode: currentMode,
      params: currentParams,
      createdAt: new Date().toISOString(),
      alertOnNew: alertOnNew,
    };
    persist([item, ...saved]);
    setModalOpen(false);
    setSaveName('');
    setAlertOnNew(false);
    message.success('搜索已保存');
  };

  const handleDelete = (id: string) => {
    persist(saved.filter(s => s.id !== id));
  };

  return (
    <>
      <Card size="small" title={<Text style={{ color: '#e0e0e0', fontSize: 12 }}><ClockCircleOutlined /> 保存的搜索</Text>}
        style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}
        extra={
          <Button size="small" icon={<SaveOutlined />} type="link"
            onClick={() => setModalOpen(true)} disabled={!currentParams}>
            保存当前搜索
          </Button>
        }>
        {saved.length === 0 ? (
          <Empty description={<Text style={{ color: '#64748b', fontSize: 12 }}>暂无保存的搜索</Text>}
            image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Space wrap size={[4, 4]}>
            {saved.map(s => (
              <Tag key={s.id} closable color="blue" style={{ cursor: 'pointer', marginRight: 0 }}
                onClose={() => handleDelete(s.id)}
                onClick={() => onLoad(s)}>
                <Space size={2}>
                  <SearchOutlined style={{ fontSize: 10 }} />
                  <span style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', display: 'inline-block', verticalAlign: 'middle' }}>
                    {s.name}
                  </span>
                  <span style={{ fontSize: 10, opacity: 0.5 }}>({MODE_LABELS[s.mode]})</span>
                  {s.alertOnNew && <span style={{ fontSize: 10, color: '#52c41a' }}>●</span>}
                </Space>
              </Tag>
            ))}
          </Space>
        )}
      </Card>

      <Modal title="保存搜索" open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)}
        okText="保存" cancelText="取消" width={400}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text style={{ color: '#a0a0a0', fontSize: 12 }}>搜索名称</Text>
            <Input value={saveName} onChange={e => setSaveName(e.target.value)}
              placeholder={`我的${MODE_LABELS[currentMode] || ''}搜索`}
              style={{ background: '#0f0f23', color: '#e0e0e0' }} />
          </div>
          <div>
            <Space>
              <Switch size="small" checked={alertOnNew} onChange={setAlertOnNew} />
              <Text style={{ color: '#a0a0a0', fontSize: 12 }}>新结果提醒</Text>
            </Space>
          </div>
        </Space>
      </Modal>
    </>
  );
};

export default SavedSearchPanel;
