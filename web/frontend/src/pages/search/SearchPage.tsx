import React, { useState, useEffect } from 'react';
import { Card, Typography, Space, Select, message, Tag, Button, Row, Col, Empty, Descriptions, Tabs, Badge, Progress, Drawer } from 'antd';
import { SearchOutlined, CameraOutlined, InboxOutlined, EyeOutlined, DatabaseOutlined, SwapOutlined } from '@ant-design/icons';
import { apiPost, apiGet } from '../../api/client';

const { Title, Text } = Typography;

interface MatchResult { 目标ID: string; 名称: string; 类别: string; 标签: string[]; 综合匹配度: number; 视觉相似度: number; 属性匹配度: number;
  匹配属性: string; 特征图片?: string[]; 最近出现?: string; 关联案件?: string; 目标属性?: any; }
interface LibraryTarget { 目标ID: string; 名称: string; 类型: string; 属性: any; 标签: string[]; 特征图片?: string[]; 最近出现?: string; 关联案件?: string; }

const SearchPage: React.FC = () => {
  const [results, setResults] = useState<MatchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [category, setCategory] = useState('嫌疑人员');
  const [library, setLibrary] = useState<Record<string, LibraryTarget[]>>({});
  const [previewTarget, setPreviewTarget] = useState<LibraryTarget | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [compareIds, setCompareIds] = useState<string[]>([]);

  // 加载比对库
  useEffect(() => {
    (async () => {
      try { const r = await apiGet<any>('/api/v1/search/v2/library'); setLibrary(r?.比对库 || {}); } catch {}
    })();
  }, []);

  // ===== 图片比对 — 原生HTML input =====
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) { message.warning('请选择图片文件'); return; }
    setLoading(true);
    const reader = new FileReader();
    reader.onload = async (ev) => {
      try {
        const dataUrl = ev.target?.result as string || '';
        const base64 = dataUrl.includes('base64,') ? dataUrl.split('base64,')[1] : dataUrl;
        const res = await apiPost<any>('/api/v1/search/v2/image', { image_data: base64, category, top_k: 10 });
        setResults(res?.结果 || []);
        message.success(`比对完成: ${res?.结果?.length || 0} 条匹配`);
      } catch { message.error('比对失败'); }
      setLoading(false);
    };
    reader.onerror = () => { message.error('读取失败'); setLoading(false); };
    reader.readAsDataURL(file);
  };

  // ===== 目标预览 =====
  const previewLibraryTarget = (targetId: string) => {
    for (const cat of Object.values(library)) {
      const found = cat.find((t: any) => t.目标ID === targetId);
      if (found) { setPreviewTarget(found); setDrawerOpen(true); return; }
    }
    message.warning('目标未找到');
  };

  // ===== 多目标对比 =====
  const toggleCompare = (targetId: string) => {
    setCompareIds(prev => prev.includes(targetId) ? prev.filter(id => id !== targetId) : [...prev, targetId]);
  };

  // 所有库目标列表
  const allTargets = Object.entries(library).flatMap(([cat, targets]) =>
    (targets as LibraryTarget[]).map(t => ({ ...t, 类别: cat })));

  return (
    <div>
      <Title level={3} style={{ color: '#e0e0e0', marginBottom: 16 }}><SearchOutlined /> 目标检索</Title>

      <Tabs defaultActiveKey="image" items={[{
        key: 'image', label: <span><CameraOutlined /> 图片比对</span>,
        children: (
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={10}>
              <Card title={<Text style={{ color: '#e0e0e0' }}>上传目标图片</Text>} style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text style={{ color: '#a0a0a0', fontSize: 12 }}>选择比对范围:</Text>
                  <Select value={category} onChange={setCategory} style={{ width: '100%' }}
                    options={Object.keys(library).map(k => ({ value: k, label: `${k} (${(library[k] || []).length}个目标)` }))} />
                  <input type="file" accept="image/*" ref={fileInputRef}
                    onChange={handleFileChange} style={{ display: 'none' }} id="image-upload" />
                  <label htmlFor="image-upload" style={{ display: 'block', cursor: 'pointer' }}>
                  <div style={{ background: '#0f0f23', border: '2px dashed #334155', padding: 20, borderRadius: 8, textAlign: 'center' }}>
                    <InboxOutlined style={{ fontSize: 40, color: '#1677ff' }} />
                    <p style={{ color: '#a0a0a0', marginTop: 8 }}>点击上传图片</p>
                    <p style={{ color: '#64748b', fontSize: 11 }}>系统自动提取特征并与库中目标比对</p>
                  </div>
                </label>
                </Space>
              </Card>
            </Col>
            <Col xs={24} lg={14}>
              <Card title={<Text style={{ color: '#e0e0e0' }}>比对结果 {results.length > 0 && <Tag color="green">{results.length}条</Tag>}</Text>}
                style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
                {loading ? <Text style={{ color: '#a0a0a0' }}>正在提取特征并比对...</Text> :
                 results.length > 0 ? results.map((r, _i) => (
                  <Card key={r.目标ID} size="small" hoverable
                    style={{ background: '#0f0f23', border: `1px solid ${r.综合匹配度 > 85 ? '#52c41a' : r.综合匹配度 > 60 ? '#faad14' : '#ff4d4f'}44`, marginBottom: 8 }}>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                      <div style={{ width: 50, height: 50, background: '#1a1a2e', borderRadius: 4, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <CameraOutlined style={{ fontSize: 20, color: '#64748b' }} />
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Space>
                            <Badge status={r.综合匹配度 > 85 ? 'success' : r.综合匹配度 > 60 ? 'warning' : 'error'} />
                            <Text strong style={{ color: '#e0e0e0' }}>{r.名称}</Text>
                            <Tag color="blue">{r.类别}</Tag>
                            <Tag color={r.综合匹配度 > 85 ? 'green' : r.综合匹配度 > 60 ? 'orange' : 'red'}>{r.综合匹配度}%</Tag>
                          </Space>
                          <Space size="small">
                            <Button size="small" type="link" icon={<EyeOutlined />} onClick={() => previewLibraryTarget(r.目标ID)}>详情</Button>
                            <Button size="small" type="link" onClick={() => toggleCompare(r.目标ID)}>{compareIds.includes(r.目标ID) ? '取消对比' : '对比'}</Button>
                          </Space>
                        </div>
                        <Row gutter={8} style={{ marginTop: 4 }}>
                          <Col span={12}><Text style={{ color: '#a0a0a0', fontSize: 11 }}>视觉相似度</Text><Progress percent={Math.round(r.视觉相似度)} size="small" strokeColor="#1677ff" /></Col>
                          <Col span={12}><Text style={{ color: '#a0a0a0', fontSize: 11 }}>属性匹配度</Text><Progress percent={Math.round(r.属性匹配度)} size="small" strokeColor="#52c41a" /></Col>
                        </Row>
                        <Text style={{ color: '#64748b', fontSize: 11, marginTop: 4, display: 'block' }}>{r.匹配属性}</Text>
                        <Space size={4} style={{ marginTop: 4 }}>{r.标签?.map((t: string) => <Tag key={t} style={{ fontSize: 10 }}>{t}</Tag>)}</Space>
                      </div>
                    </div>
                  </Card>
                )) : <Empty description="上传图片开始比对" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
              </Card>
            </Col>
          </Row>
        ),
      }, {
        key: 'library', label: <span><DatabaseOutlined /> 比对库管理 ({allTargets.length})</span>,
        children: (
          <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            {Object.entries(library).map(([cat, targets]) => (
              <div key={cat} style={{ marginBottom: 16 }}>
                <Title level={5} style={{ color: '#e0e0e0' }}>{cat} ({(targets as LibraryTarget[]).length})</Title>
                <Row gutter={[12, 12]}>
                  {(targets as LibraryTarget[]).map(t => (
                    <Col xs={24} sm={12} md={8} lg={6} key={t.目标ID}>
                      <Card size="small" hoverable style={{ background: '#0f0f23', border: '1px solid #334155' }}
                        actions={[<EyeOutlined key="view" onClick={() => previewLibraryTarget(t.目标ID)} />]}>
                        <Text strong style={{ color: '#e0e0e0', fontSize: 13 }}>{t.名称}</Text><br />
                        <Text style={{ color: '#64748b', fontSize: 11 }}>ID: {t.目标ID}</Text>
                        <div style={{ marginTop: 4 }}>
                          {t.标签?.map((tag: string) => <Tag key={tag} style={{ fontSize: 10 }}>{tag}</Tag>)}
                        </div>
                        <Descriptions column={1} size="small" style={{ marginTop: 4 }} labelStyle={{ color: '#64748b', fontSize: 10 }} contentStyle={{ color: '#e0e0e0', fontSize: 10 }}>
                          {(t.最近出现 || t.关联案件) && <Descriptions.Item label="最近">{t.最近出现 || t.关联案件}</Descriptions.Item>}
                        </Descriptions>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </div>
            ))}
            {Object.keys(library).length === 0 && <Empty description="加载中..." />}
          </Card>
        ),
      }, {
        key: 'compare', label: <span><SwapOutlined /> 目标对比 {compareIds.length > 0 && <Badge count={compareIds.length} />}</span>,
        children: (
          <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            {compareIds.length >= 2 ? (
              <Row gutter={[12, 12]}>
                {compareIds.map(tid => {
                  const t = allTargets.find((a: any) => a.目标ID === tid);
                  if (!t) return null;
                  return (
                    <Col xs={24} sm={12} md={8} key={tid}>
                      <Card size="small" title={<Text style={{ color: '#e0e0e0' }}>{t.名称}</Text>}
                        style={{ background: '#0f0f23', border: '1px solid #334155' }}>
                        {t.属性 && <Descriptions column={1} size="small" labelStyle={{ color: '#64748b', fontSize: 10 }} contentStyle={{ color: '#e0e0e0', fontSize: 10 }}>
                          {Object.entries(t.属性).map(([k, v]) => (
                            <Descriptions.Item key={k} label={k}>{String(v)}</Descriptions.Item>
                          ))}
                        </Descriptions>}
                        {t.最近出现 && <Text style={{ color: '#a0a0a0', fontSize: 11 }}>最近: {t.最近出现}</Text>}
                      </Card>
                    </Col>
                  );
                })}
              </Row>
            ) : (
              <Empty description={'在比对结果或库中点击「对比」添加，至少需要2个目标'} image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        ),
      }]} />

      {/* 目标详情抽屉 */}
      <Drawer title="目标详情" open={drawerOpen} onClose={() => setDrawerOpen(false)} width={480}>
        {previewTarget && (
          <>
            <Title level={4} style={{ color: '#e0e0e0' }}>{previewTarget.名称}</Title>
            <Space style={{ marginBottom: 12 }}>{previewTarget.标签?.map(t => <Tag key={t}>{t}</Tag>)}</Space>
            <Card title="属性信息" size="small" style={{ background: '#16213e', marginBottom: 12 }}>
              {previewTarget.属性 && <Descriptions column={2} size="small" labelStyle={{ color: '#a0a0a0' }} contentStyle={{ color: '#e0e0e0' }}>
                {Object.entries(previewTarget.属性).map(([k, v]) => (
                  <Descriptions.Item key={k} label={k}>{String(v)}</Descriptions.Item>
                ))}
              </Descriptions>}
            </Card>
            <Card title="特征图片" size="small" style={{ background: '#16213e', marginBottom: 12 }}>
              <Space wrap>
                {(previewTarget.特征图片 || ['/preview/placeholder.jpg']).map((_img: string, i: number) => (
                  <div key={i} style={{ width: 100, height: 80, background: '#1a1a2e', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <CameraOutlined style={{ fontSize: 24, color: '#64748b' }} />
                  </div>
                ))}
              </Space>
            </Card>
            {(previewTarget as any).最近出现 && <Text style={{ color: '#a0a0a0' }}>最近出现: {(previewTarget as any).最近出现}</Text>}
            {(previewTarget as any).关联案件 && <><br /><Text style={{ color: '#a0a0a0' }}>关联案件: {(previewTarget as any).关联案件}</Text></>}
          </>
        )}
      </Drawer>
    </div>
  );
};

export default SearchPage;
