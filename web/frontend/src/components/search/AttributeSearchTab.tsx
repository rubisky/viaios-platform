import React, { useState } from 'react';
import { Card, Typography, Row, Col, Select, Slider, Switch, Input, Button, Segmented, Space, message } from 'antd';
import { SearchOutlined, UserOutlined, CarOutlined } from '@ant-design/icons';
import SearchFilters from './SearchFilters';
import ResultGallery from './ResultGallery';
import ResultDetailModal from './ResultDetailModal';
import { apiPost } from '../../api/client';
import type { SearchResult, SearchFilters as SearchFiltersType, PersonAttributes, VehicleAttributes } from '../../types/search';
import { DEFAULT_PERSON_ATTRS, DEFAULT_VEHICLE_ATTRS } from '../../types/search';

const { Text } = Typography;

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

const COLORS = ['红色', '黑色', '白色', '蓝色', '灰色', '黄色', '绿色', '棕色', '银色', '橙色', '紫色'];

const AttributeSearchTab: React.FC<Props> = ({
  filters, onFiltersChange, onViewDetail, onCompareToggle,
  compareIds, detailResult, detailOpen, onDetailClose,
}) => {
  const [mode, setMode] = useState<'person' | 'vehicle'>('person');
  const [pAttrs, setPAttrs] = useState<PersonAttributes>(DEFAULT_PERSON_ATTRS);
  const [vAttrs, setVAttrs] = useState<VehicleAttributes>(DEFAULT_VEHICLE_ATTRS);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const updatePerson = (patch: Partial<PersonAttributes>) => setPAttrs(prev => ({ ...prev, ...patch }));
  const updateVehicle = (patch: Partial<VehicleAttributes>) => setVAttrs(prev => ({ ...prev, ...patch }));

  const handleSearch = async () => {
    setLoading(true);
    try {
      const attrs = mode === 'person' ? pAttrs : vAttrs;
      const res = await apiPost<any>('/api/v1/search/upgraded', {
        modality: 'attribute',
        query: JSON.stringify(attrs),
        top_k: filters.topK,
        filters: { time_range: filters.timeRange, category: filters.category },
      });
      const items = (res?.results || []).map((r: any, i: number) => ({
        id: r.id || `attr_${i}`, 目标ID: r.id || `ATTR${i}`, 名称: r.name || '目标',
        type: (r.type || mode === 'person' ? 'person' : 'vehicle') as SearchResult['type'],
        category: r.category || filters.category,
        imageUrl: r.image_url || '', thumbnailUrl: r.thumbnail_url || '',
        similarityScore: r.score ? (r.score * 100) : 0,
        visualScore: r.visual_score ? (r.visual_score * 100) : 0,
        attrScore: r.attr_score ? (r.attr_score * 100) : 0,
        cameraId: r.camera_id || '', cameraName: r.camera_name || '未知',
        timestamp: r.timestamp || '', attributes: attrs as unknown as Record<string, unknown>,
        tags: r.tags || [], matchDetail: r.match_detail || '',
      }));
      setResults(items);
      message.success(`搜索完成: ${items.length} 条结果`);
    } catch { message.error('搜索失败'); }
    setLoading(false);
  };

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={10}>
        <Card
          title={<Text style={{ color: '#e0e0e0' }}>结构化属性搜索</Text>}
          style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
        >
          {/* Mode Toggle */}
          <Segmented
            block
            value={mode}
            onChange={v => setMode(v as 'person' | 'vehicle')}
            options={[
              { value: 'person', label: <><UserOutlined /> 人员属性</>, icon: <UserOutlined /> },
              { value: 'vehicle', label: <><CarOutlined /> 车辆属性</>, icon: <CarOutlined /> },
            ]}
            style={{ marginBottom: 16, background: '#0f0f23' }}
          />

          {mode === 'person' ? (
            <Card size="small" style={{ background: '#0f0f23', border: '1px solid #2a2a4a', marginBottom: 12 }}>
              <Row gutter={[12, 12]}>
                <Col span={12}>
                  <Text style={{ color: '#a0a0a0', fontSize: 12 }}>性别</Text>
                  <Select allowClear value={pAttrs.gender || undefined} onChange={v => updatePerson({ gender: v || '' })}
                    style={{ width: '100%' }} placeholder="不限"
                    options={[{ value: '男', label: '男' }, { value: '女', label: '女' }]} />
                </Col>
                <Col span={12}>
                  <Text style={{ color: '#a0a0a0', fontSize: 12 }}>身高</Text>
                  <Select allowClear value={pAttrs.height || undefined} onChange={v => updatePerson({ height: v || '' })}
                    style={{ width: '100%' }} placeholder="不限"
                    options={[{ value: '矮', label: '矮 (<165cm)' }, { value: '中', label: '中等 (165-175cm)' }, { value: '高', label: '高 (>175cm)' }]} />
                </Col>
                <Col span={24}>
                  <Text style={{ color: '#a0a0a0', fontSize: 12 }}>年龄段: {pAttrs.ageMin} - {pAttrs.ageMax} 岁</Text>
                  <Slider range min={0} max={100} value={[pAttrs.ageMin, pAttrs.ageMax]}
                    onChange={([min, max]) => updatePerson({ ageMin: min, ageMax: max })} />
                </Col>
                <Col span={12}>
                  <Text style={{ color: '#a0a0a0', fontSize: 12 }}>上衣颜色</Text>
                  <Select allowClear value={pAttrs.topColor || undefined} onChange={v => updatePerson({ topColor: v || '' })}
                    style={{ width: '100%' }} placeholder="不限"
                    options={COLORS.map(c => ({ value: c, label: <Space><span style={{ display:'inline-block',width:12,height:12,borderRadius:2,background:c,verticalAlign:'middle' }} />{c}</Space> }))} />
                </Col>
                <Col span={12}>
                  <Text style={{ color: '#a0a0a0', fontSize: 12 }}>下衣颜色</Text>
                  <Select allowClear value={pAttrs.bottomColor || undefined} onChange={v => updatePerson({ bottomColor: v || '' })}
                    style={{ width: '100%' }} placeholder="不限"
                    options={COLORS.map(c => ({ value: c, label: <Space><span style={{ display:'inline-block',width:12,height:12,borderRadius:2,background:c,verticalAlign:'middle' }} />{c}</Space> }))} />
                </Col>
                <Col span={6}>
                  <Text style={{ color: '#a0a0a0', fontSize: 11 }}>帽子</Text><br />
                  <Switch size="small" checked={pAttrs.hasHat} onChange={v => updatePerson({ hasHat: v })} />
                </Col>
                <Col span={6}>
                  <Text style={{ color: '#a0a0a0', fontSize: 11 }}>眼镜</Text><br />
                  <Switch size="small" checked={pAttrs.hasGlasses} onChange={v => updatePerson({ hasGlasses: v })} />
                </Col>
                <Col span={6}>
                  <Text style={{ color: '#a0a0a0', fontSize: 11 }}>口罩</Text><br />
                  <Switch size="small" checked={pAttrs.hasMask} onChange={v => updatePerson({ hasMask: v })} />
                </Col>
                <Col span={6}>
                  <Text style={{ color: '#a0a0a0', fontSize: 11 }}>背包</Text><br />
                  <Switch size="small" checked={pAttrs.hasBag} onChange={v => updatePerson({ hasBag: v })} />
                </Col>
              </Row>
            </Card>
          ) : (
            <Card size="small" style={{ background: '#0f0f23', border: '1px solid #2a2a4a', marginBottom: 12 }}>
              <Row gutter={[12, 12]}>
                <Col span={12}>
                  <Text style={{ color: '#a0a0a0', fontSize: 12 }}>车辆类型</Text>
                  <Select allowClear value={vAttrs.vehicleType || undefined} onChange={v => updateVehicle({ vehicleType: v || '' })}
                    style={{ width: '100%' }} placeholder="不限"
                    options={['轿车', 'SUV', '面包车', '卡车'].map(t => ({ value: t, label: t }))} />
                </Col>
                <Col span={12}>
                  <Text style={{ color: '#a0a0a0', fontSize: 12 }}>颜色</Text>
                  <Select allowClear value={vAttrs.color || undefined} onChange={v => updateVehicle({ color: v || '' })}
                    style={{ width: '100%' }} placeholder="不限"
                    options={COLORS.map(c => ({ value: c, label: <Space><span style={{ display:'inline-block',width:12,height:12,borderRadius:2,background:c }} />{c}</Space> }))} />
                </Col>
                <Col span={12}>
                  <Text style={{ color: '#a0a0a0', fontSize: 12 }}>品牌</Text>
                  <Input value={vAttrs.brand} onChange={e => updateVehicle({ brand: e.target.value })}
                    placeholder="如: 丰田" style={{ background: '#0f0f23', color: '#e0e0e0' }} />
                </Col>
                <Col span={12}>
                  <Text style={{ color: '#a0a0a0', fontSize: 12 }}>型号</Text>
                  <Input value={vAttrs.model} onChange={e => updateVehicle({ model: e.target.value })}
                    placeholder="如: 凯美瑞" style={{ background: '#0f0f23', color: '#e0e0e0' }} />
                </Col>
                <Col span={24}>
                  <Text style={{ color: '#a0a0a0', fontSize: 12 }}>车牌号 (部分匹配)</Text>
                  <Input value={vAttrs.plateNumber} onChange={e => updateVehicle({ plateNumber: e.target.value.toUpperCase() })}
                    placeholder="如: ABC123" style={{ background: '#0f0f23', color: '#e0e0e0' }} />
                </Col>
              </Row>
            </Card>
          )}

          <SearchFilters filters={filters} onChange={onFiltersChange} />
          <Button type="primary" icon={<SearchOutlined />} block size="large"
            loading={loading} onClick={handleSearch}>
            属性搜索
          </Button>
        </Card>
      </Col>

      <Col xs={24} lg={14}>
        <Card
          title={<Text style={{ color: '#e0e0e0' }}>
            {mode === 'person' ? <UserOutlined /> : <CarOutlined />}
            {' '}搜索结果 {results.length > 0 && <Text type="success">({results.length} 条)</Text>}
          </Text>}
          style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
        >
          <ResultGallery results={results} loading={loading} onDetail={onViewDetail}
            onCompare={onCompareToggle} compareIds={compareIds} />
        </Card>
      </Col>

      <ResultDetailModal open={detailOpen} result={detailResult} onClose={onDetailClose} />
    </Row>
  );
};

export default AttributeSearchTab;
