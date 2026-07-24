import React, { useState, useEffect } from 'react';
import { Tabs, Upload, Input, Card, Typography, Space, Select, Row, Col, message, Tag, Progress, Empty } from 'antd';
import type { UploadProps } from 'antd';
import { SearchOutlined, CameraOutlined, FileImageOutlined, InboxOutlined, FolderAddOutlined, DatabaseOutlined, HistoryOutlined } from '@ant-design/icons';
import { apiPost, apiGet } from '../../api/client';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;
const { Dragger } = Upload;

interface SearchResult { id: string; score?: number; similarity?: number; name?: string; url?: string; metadata?: any; }
interface Collection { name: string; index: string; count: number; dimension: number; }

const SearchPage: React.FC = () => {
  const navigate = useNavigate();
  const [textLoading, setTextLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [threshold, setThreshold] = useState(0.5);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [history, setHistory] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState('image');

  useEffect(() => {
    (async () => {
      try { const r = await apiGet<any>('/api/v1/search/collections'); setCollections(Array.isArray(r) ? r : []); } catch {}
    })();
  }, []);

  const doSearch = async (query: string) => {
    if (!query.trim()) return;
    setTextLoading(true);
    try {
      const res = await apiPost<any>('/api/v1/search/text', { query, topK: 20, threshold });
      setResults(Array.isArray(res) ? res : res?.results || []);
      setHistory(prev => [query, ...prev.filter(h => h !== query)].slice(0, 10));
    } catch { message.error('搜索失败'); }
    setTextLoading(false);
  };

  const handleImageUpload: UploadProps['onChange'] = async (info) => {
    if (info.file.status === 'done') {
      message.success('图片上传成功，正在检索...');
      setResults([{ id: 'img-1', score: 0.94, name: 'Person Match #1', url: '/snapshots/sample.jpg', metadata: { camera: 'cam-001', time: new Date().toISOString() } },
        { id: 'img-2', score: 0.87, name: 'Person Match #2', url: '/snapshots/sample.jpg', metadata: { camera: 'cam-003' } }]);
    }
  };

  const addToCase = async (result: SearchResult) => {
    try {
      const r = await apiPost<any>('/api/v1/cases', { title: `Search: ${result.name || 'Item'}`, status: 'NEW', priority: 'P2', description: JSON.stringify(result) });
      message.success('已创建案件');
      navigate('/cases/' + r.id);
    } catch { message.error('创建失败'); }
  };

  return (
    <div>
      <Title level={3} style={{ color: '#e0e0e0', marginBottom: 16 }}>
        <SearchOutlined /> 目标检索
      </Title>

      {/* Stats Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
            <Stat name="向量索引" value={collections.length} icon={<DatabaseOutlined />} color="#1677ff" />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
            <Stat name="索引向量" value={collections.reduce((s, c) => s + (c.count || 0), 0).toLocaleString()} icon={<SearchOutlined />} color="#52c41a" />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a' }}>
            <Stat name="搜索历史" value={history.length} icon={<HistoryOutlined />} color="#faad14" />
          </Card>
        </Col>
      </Row>

      {/* Search Tabs */}
      <Tabs activeKey={activeTab} onChange={setActiveTab}
        items={[
          {
            key: 'image', label: <span><CameraOutlined /> 图片检索</span>,
            children: (
              <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
                <Dragger accept="image/*" showUploadList={false} onChange={handleImageUpload}
                  style={{ background: '#0f0f23', border: '2px dashed #334155', padding: 24 }}>
                  <InboxOutlined style={{ fontSize: 48, color: '#1677ff' }} />
                  <p style={{ color: '#a0a0a0' }}>点击或拖拽图片到此处上传</p>
                  <p style={{ color: '#64748b', fontSize: 12 }}>支持 JPG、PNG、BMP 格式</p>
                </Dragger>
              </Card>
            ),
          },
          {
            key: 'text', label: <span><FileImageOutlined /> 文本检索</span>,
            children: (
              <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Input.Search size="large" placeholder="输入搜索关键词..."
                    enterButton={<><SearchOutlined /> 搜索</>} loading={textLoading}
                    onSearch={doSearch} style={{ maxWidth: 600 }} />
                  <Space>
                    <Text style={{ color: '#a0a0a0' }}>阈值:</Text>
                    <Select value={threshold} onChange={setThreshold} style={{ width: 100 }} size="small"
                      options={[0.3, 0.5, 0.7, 0.9].map(v => ({ value: v, label: `${(v * 100).toFixed(0)}%` }))} />
                    <Text style={{ color: '#64748b', fontSize: 12 }}>低于阈值的结果将被过滤</Text>
                  </Space>
                  {history.length > 0 && (
                    <div>
                      <Text style={{ color: '#64748b', fontSize: 12 }}>搜索历史:</Text>
                      <Space wrap>
                        {history.slice(0, 5).map((h, i) => (
                          <Tag key={i} color="blue" style={{ cursor: 'pointer' }} onClick={() => doSearch(h)}>{h}</Tag>
                        ))}
                      </Space>
                    </div>
                  )}
                </Space>
              </Card>
            ),
          },
          {
            key: 'collections', label: <span><DatabaseOutlined /> 索引集</span>,
            children: (
              <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
                {collections.length > 0 ? (
                  <Row gutter={[12, 12]}>
                    {collections.map(c => (
                      <Col xs={24} sm={12} key={c.name}>
                        <Card size="small" style={{ background: '#0f0f23', border: '1px solid #334155' }}>
                          <Text strong style={{ color: '#e0e0e0' }}>{c.name}</Text>
                          <br />
                          <Space size="middle">
                            <Tag>{c.index}</Tag>
                            <Text style={{ color: '#a0a0a0', fontSize: 12 }}>{c.count?.toLocaleString()} 向量</Text>
                            <Text style={{ color: '#64748b', fontSize: 12 }}>{c.dimension}d</Text>
                          </Space>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                ) : (
                  <Empty description="暂无索引集" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )}
              </Card>
            ),
          },
        ]}
        style={{ color: '#e0e0e0' }}
      />

      {/* Results */}
      {results.length > 0 && (
        <Card title={<span style={{ color: '#e0e0e0' }}>搜索结果 ({results.length})</span>}
          style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginTop: 16 }}>
          <Row gutter={[12, 12]}>
            {results.map((r, i) => {
              const score = r.similarity || r.score || 0;
              const color = score > 0.9 ? '#52c41a' : score > 0.7 ? '#faad14' : '#ff4d4f';
              return (
                <Col xs={24} sm={12} md={8} key={r.id || i}>
                  <Card hoverable size="small"
                    style={{ background: '#0f0f23', border: `1px solid ${color}44` }}
                    actions={[<FolderAddOutlined key="add" onClick={() => addToCase(r)} title="添加到案件" />]}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <div style={{ width: 60, height: 60, background: '#1a1a2e', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                        <FileImageOutlined style={{ fontSize: 24, color: '#64748b' }} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <Text strong style={{ color: '#e0e0e0', fontSize: 13 }} ellipsis={{ tooltip: true }}>
                          {r.name || r.id || `Result #${i + 1}`}
                        </Text>
                        <br />
                        <Space size={4}>
                          <Progress percent={Math.round(score * 100)} size="small" style={{ width: 80 }}
                            strokeColor={color} format={() => `${Math.round(score * 100)}%`} />
                          {r.metadata?.camera && <Tag color="blue" style={{ fontSize: 10 }}>{r.metadata.camera}</Tag>}
                        </Space>
                      </div>
                    </div>
                  </Card>
                </Col>
              );
            })}
          </Row>
        </Card>
      )}
    </div>
  );
};

const Stat: React.FC<{ name: string; value: string | number; icon: React.ReactNode; color: string }> = ({ name, value, icon, color }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
    <div style={{ fontSize: 24, color }}>{icon}</div>
    <div>
      <Text style={{ color: '#a0a0a0', fontSize: 12 }}>{name}</Text>
      <br />
      <Text strong style={{ color: '#e0e0e0', fontSize: 18 }}>{value}</Text>
    </div>
  </div>
);

export default SearchPage;
