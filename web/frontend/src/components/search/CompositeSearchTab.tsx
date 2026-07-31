import React, { useState } from 'react';
import { Card, Typography, Row, Col, Upload, Button, Input, Slider, Switch, Radio, Space, Select, message, Image } from 'antd';
import { SearchOutlined, CameraOutlined, FormOutlined, SettingOutlined, InboxOutlined, DeleteOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import SearchFilters from './SearchFilters';
import ResultGallery from './ResultGallery';
import ResultDetailModal from './ResultDetailModal';
import { apiPost } from '../../api/client';
import type { SearchResult, SearchFilters as SearchFiltersType, PersonAttributes } from '../../types/search';
import { DEFAULT_PERSON_ATTRS } from '../../types/search';

const { Text } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;

interface Props {
  filters: SearchFiltersType;
  onFiltersChange: (f: SearchFiltersType) => void;
  onViewDetail: (r: SearchResult) => void;
  onCompareToggle: (id: string) => void;
  compareIds: string[];
  detailResult: SearchResult | null;
  detailOpen: boolean;
  onDetailClose: () => void;
}

const FUSION_OPTIONS = [
  { value: 'early', label: 'AND 融合 (所有模态必须同时匹配)' },
  { value: 'late', label: '加权融合 (各模态权重组合)' },
  { value: 'cascade', label: '级联 (图片先搜, 再过滤)' },
];

const CompositeSearchTab: React.FC<Props> = ({
  filters, onFiltersChange, onViewDetail, onCompareToggle,
  compareIds, detailResult, detailOpen, onDetailClose,
}) => {
  // Image sub-state
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [enableImage, setEnableImage] = useState(true);

  // Text sub-state
  const [query, setQuery] = useState('');
  const [enableText, setEnableText] = useState(true);

  // Attribute sub-state
  const [enableAttr, setEnableAttr] = useState(true);
  const [pAttrs, setPAttrs] = useState<PersonAttributes>(DEFAULT_PERSON_ATTRS);

  // Fusion
  const [fusion, setFusion] = useState<'early' | 'late' | 'cascade'>('late');
  const [weights, setWeights] = useState({ image: 0.4, text: 0.35, attr: 0.25 });

  // Results
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const normalizeWeights = (key: 'image' | 'text' | 'attr', value: number) => {
    const others = (['image', 'text', 'attr'] as const).filter(k => k !== key);
    const remaining = 1 - value;
    const sumOther = weights[others[0]] + weights[others[1]];
    const newWeights = { ...weights, [key]: value };
    if (sumOther > 0) {
      newWeights[others[0]] = +(weights[others[0]] / sumOther * remaining).toFixed(2);
      newWeights[others[1]] = +(1 - value - newWeights[others[0]]).toFixed(2);
    } else {
      newWeights[others[0]] = +(remaining / 2).toFixed(2);
      newWeights[others[1]] = +(remaining / 2).toFixed(2);
    }
    setWeights(newWeights);
  };

  const handleSearch = async () => {
    if (!enableImage && !enableText && !enableAttr) {
      message.warning('请至少启用一种搜索模态');
      return;
    }
    setLoading(true);
    try {
      let imageData = '';
      if (enableImage && fileList.length > 0) {
        const file = fileList[0].originFileObj || fileList[0];
        if (file) {
          imageData = await fileToBase64(file as File);
        }
      }

      const res = await apiPost<any>('/api/v1/search/upgraded', {
        query: enableText ? query : '',
        modality: 'combined',
        top_k: filters.topK,
        filters: {
          category: filters.category,
          time_range: filters.timeRange,
          image_data: imageData || undefined,
          attributes: enableAttr ? pAttrs : undefined,
          fusion_strategy: fusion,
          weights: fusion === 'late' ? weights : undefined,
          enabled_modalities: {
            image: enableImage, text: enableText, attribute: enableAttr,
          },
        },
      });

      const items = (res?.results || []).map((r: any, i: number) => ({
        id: r.id || `comp_${i}`, 目标ID: r.id || `COMP${i}`, 名称: r.name || (query.slice(0, 20) || '目标'),
        type: (r.type || 'person') as SearchResult['type'],
        category: r.category || filters.category,
        imageUrl: r.image_url || '', thumbnailUrl: r.thumbnail_url || '',
        similarityScore: r.score ? (r.score * 100) : 0,
        visualScore: r.visual_score ? (r.visual_score * 100) : 0,
        attrScore: r.attr_score ? (r.attr_score * 100) : 0,
        cameraId: r.camera_id || '', cameraName: r.camera_name || '未知',
        timestamp: r.timestamp || '', attributes: r.attributes || {},
        tags: r.tags || [], matchDetail: r.match_detail || '',
      }));
      setResults(items);
      message.success(`综合搜索完成: ${items.length} 条结果`);
    } catch {
      message.error('搜索失败');
    }
    setLoading(false);
  };

  const enabledCount = [+enableImage, +enableText, +enableAttr].reduce((a, b) => a + b, 0);

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={10}>
        <Card
          title={<Text style={{ color: '#e0e0e0' }}><SettingOutlined /> 多模态综合搜索 ({enabledCount}/3)</Text>}
          style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
        >
          {/* Image modality */}
          <Card size="small" title={<Space><Switch size="small" checked={enableImage} onChange={setEnableImage} /><Text style={{ color: '#e0e0e0' }}><CameraOutlined /> 图片</Text></Space>}
            style={{ background: enableImage ? '#0f0f23' : '#0a0a15', border: `1px solid ${enableImage ? '#1677ff44' : '#2a2a4a'}`, marginBottom: 12 }}>
            {enableImage && (
              <Dragger maxCount={1} accept="image/*" fileList={fileList}
                beforeUpload={() => false}
                onChange={({ fileList: fl }) => setFileList(fl)}
                itemRender={(_, file) => (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {file.thumbUrl && <Image src={file.thumbUrl} width={32} height={32} style={{ borderRadius: 4 }} preview={false} />}
                    <Text style={{ color: '#e0e0e0', flex: 1, fontSize: 12 }} ellipsis>{file.name}</Text>
                    <Button size="small" danger icon={<DeleteOutlined />} onClick={() => setFileList([])} />
                  </div>
                )}>
                <p style={{ color: '#64748b', fontSize: 12 }}><InboxOutlined /> 拖拽或点击上传 (可选)</p>
              </Dragger>
            )}
          </Card>

          {/* Text modality */}
          <Card size="small" title={<Space><Switch size="small" checked={enableText} onChange={setEnableText} /><Text style={{ color: '#e0e0e0' }}><FormOutlined /> 文本描述</Text></Space>}
            style={{ background: enableText ? '#0f0f23' : '#0a0a15', border: `1px solid ${enableText ? '#1677ff44' : '#2a2a4a'}`, marginBottom: 12 }}>
            {enableText && (
              <TextArea rows={3} value={query} onChange={e => setQuery(e.target.value)}
                placeholder="描述目标特征以辅助搜索..."
                style={{ background: '#0f0f23', color: '#e0e0e0', border: '1px solid #334155' }} />
            )}
          </Card>

          {/* Attribute modality */}
          <Card size="small" title={<Space><Switch size="small" checked={enableAttr} onChange={setEnableAttr} /><Text style={{ color: '#e0e0e0' }}>属性筛选</Text></Space>}
            style={{ background: enableAttr ? '#0f0f23' : '#0a0a15', border: `1px solid ${enableAttr ? '#1677ff44' : '#2a2a4a'}`, marginBottom: 12 }}>
            {enableAttr && (
              <Row gutter={[8, 8]}>
                <Col span={12}>
                  <Select allowClear value={pAttrs.gender || undefined} onChange={v => setPAttrs(p => ({ ...p, gender: v || '' }))}
                    style={{ width: '100%' }} placeholder="性别" options={[{ value: '男', label: '男' }, { value: '女', label: '女' }]} />
                </Col>
                <Col span={12}>
                  <Select allowClear value={pAttrs.topColor || undefined} onChange={v => setPAttrs(p => ({ ...p, topColor: v || '' }))}
                    style={{ width: '100%' }} placeholder="上衣颜色"
                    options={['红色', '黑色', '白色', '蓝色', '灰色', '黄色', '绿色'].map(c => ({ value: c, label: c }))} />
                </Col>
                <Col span={12}>
                  <Select allowClear value={pAttrs.bottomColor || undefined} onChange={v => setPAttrs(p => ({ ...p, bottomColor: v || '' }))}
                    style={{ width: '100%' }} placeholder="下衣颜色"
                    options={['黑色', '蓝色', '白色', '灰色', '棕色'].map(c => ({ value: c, label: c }))} />
                </Col>
                <Col span={12}>
                  <Select allowClear value={pAttrs.height || undefined} onChange={v => setPAttrs(p => ({ ...p, height: v || '' }))}
                    style={{ width: '100%' }} placeholder="身高"
                    options={[{ value: '矮', label: '矮' }, { value: '中', label: '中等' }, { value: '高', label: '高' }]} />
                </Col>
              </Row>
            )}
          </Card>

          {/* Fusion Strategy */}
          <Card size="small" title={<Text style={{ color: '#e0e0e0', fontSize: 12 }}>融合策略</Text>}
            style={{ background: '#0f0f23', border: '1px solid #2a2a4a', marginBottom: 12 }}>
            <Radio.Group value={fusion} onChange={e => setFusion(e.target.value)}
              style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {FUSION_OPTIONS.map(o => (
                <Radio key={o.value} value={o.value} style={{ color: '#e0e0e0', fontSize: 12 }}>{o.label}</Radio>
              ))}
            </Radio.Group>

            {fusion === 'late' && (
              <div style={{ marginTop: 12, padding: 8, background: '#1a1a2e', borderRadius: 4 }}>
                <Text style={{ color: '#a0a0a0', fontSize: 11 }}>权重分配 (总和=1.0)</Text>
                <Row gutter={8} align="middle" style={{ marginTop: 4 }}>
                  <Col span={6}><Text style={{ color: '#64748b', fontSize: 10 }}>图片</Text></Col>
                  <Col span={14}>
                    <Slider min={0} max={1} step={0.05} value={weights.image}
                      onChange={v => normalizeWeights('image', v as number)} />
                  </Col>
                  <Col span={4}><Text style={{ color: '#1677ff', fontSize: 11 }}>{weights.image.toFixed(2)}</Text></Col>
                </Row>
                <Row gutter={8} align="middle">
                  <Col span={6}><Text style={{ color: '#64748b', fontSize: 10 }}>文本</Text></Col>
                  <Col span={14}>
                    <Slider min={0} max={1} step={0.05} value={weights.text}
                      onChange={v => normalizeWeights('text', v as number)} />
                  </Col>
                  <Col span={4}><Text style={{ color: '#1677ff', fontSize: 11 }}>{weights.text.toFixed(2)}</Text></Col>
                </Row>
                <Row gutter={8} align="middle">
                  <Col span={6}><Text style={{ color: '#64748b', fontSize: 10 }}>属性</Text></Col>
                  <Col span={14}>
                    <Slider min={0} max={1} step={0.05} value={weights.attr}
                      onChange={v => normalizeWeights('attr', v as number)} />
                  </Col>
                  <Col span={4}><Text style={{ color: '#1677ff', fontSize: 11 }}>{weights.attr.toFixed(2)}</Text></Col>
                </Row>
              </div>
            )}
          </Card>

          <SearchFilters filters={filters} onChange={onFiltersChange} />
          <Button type="primary" icon={<SearchOutlined />} block size="large"
            loading={loading} onClick={handleSearch}>
            综合搜索
          </Button>
        </Card>
      </Col>

      <Col xs={24} lg={14}>
        <Card title={<Text style={{ color: '#e0e0e0' }}>搜索结果 {results.length > 0 && <Text type="success">({results.length} 条)</Text>}</Text>}
          style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
          <ResultGallery results={results} loading={loading} onDetail={onViewDetail}
            onCompare={onCompareToggle} compareIds={compareIds} />
        </Card>
      </Col>

      <ResultDetailModal open={detailOpen} result={detailResult} onClose={onDetailClose} />
    </Row>
  );
};

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      resolve(dataUrl.includes('base64,') ? dataUrl.split('base64,')[1] : dataUrl);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default CompositeSearchTab;
