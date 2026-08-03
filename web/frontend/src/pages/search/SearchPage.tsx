import React, { useState, useCallback } from 'react';
import { Tabs, Typography, Collapse, Button, Space, Badge, message } from 'antd';
import {
  SearchOutlined, CameraOutlined,
  DatabaseOutlined, SwapOutlined, FormOutlined, SettingOutlined,
} from '@ant-design/icons';
import ImageSearchTab from '../../components/search/ImageSearchTab';
import TextSearchTab from '../../components/search/TextSearchTab';
import AttributeSearchTab from '../../components/search/AttributeSearchTab';
import CompositeSearchTab from '../../components/search/CompositeSearchTab';
import LibrarySearchTab from '../../components/search/LibrarySearchTab';
import SavedSearchPanel from '../../components/search/SavedSearchPanel';
import { apiGet } from '../../api/client';
import type {
  SearchResult, SearchFilters, SearchMode, SearchParams,
  SavedSearch, LibraryTarget,
} from '../../types/search';
import { DEFAULT_FILTERS } from '../../types/search';

const { Title, Text } = Typography;

const SearchPage: React.FC = () => {
  // Global state
  const [activeTab, setActiveTab] = useState<SearchMode>('image');
  const [filters, setFilters] = useState<SearchFilters>(DEFAULT_FILTERS);
  const [detailResult, setDetailResult] = useState<SearchResult | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [library, setLibrary] = useState<Record<string, LibraryTarget[]>>({});

  // Load library on mount
  React.useEffect(() => {
    (async () => {
      try {
        const r = await apiGet<any>('/api/v1/library/targets?limit=500');
        const items = r?.results || [];
        const grouped: Record<string, any[]> = {};
        items.forEach((t: any) => {
          const lib = t.library || 'other';
          if (!grouped[lib]) grouped[lib] = [];
          grouped[lib].push({ 目标ID: t.id, 名称: t.name, 类型: t.type,
            最近出现: t.timestamp, 特征图片: [], 属性: t.attributes, 标签: [], 关联案件: '' });
        });
        setLibrary(grouped);
      } catch { /* ignore */ }
    })();
  }, []);

  // View detail
  const handleViewDetail = useCallback((r: SearchResult) => {
    setDetailResult(r);
    setDetailOpen(true);
  }, []);

  // Toggle compare
  const handleCompareToggle = useCallback((id: string) => {
    setCompareIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  }, []);

  // Build current search params for save
  const currentParams: SearchParams = {
    mode: activeTab,
    filters,
  };

  const handleLoadSaved = (s: SavedSearch) => {
    setActiveTab(s.mode);
    if (s.params.filters) setFilters(s.params.filters);
    message.info(`已加载: ${s.name}`);
  };

  // Shared component props
  const tabProps = {
    filters,
    onFiltersChange: setFilters,
    onViewDetail: handleViewDetail,
    onCompareToggle: handleCompareToggle,
    compareIds,
    detailResult,
    detailOpen,
    onDetailClose: () => setDetailOpen(false),
  };

  const allTargets = Object.entries(library).flatMap(([cat, targets]) =>
    (targets as LibraryTarget[]).map((t: LibraryTarget) => ({ ...t, 类别: cat }))
  );

  return (
    <div>
      <Space style={{ marginBottom: 8 }}>
        <Title level={3} style={{ color: '#e0e0e0', margin: 0 }}>
          <SearchOutlined /> 目标检索
        </Title>
        {compareIds.length >= 2 && (
          <Button size="small" type="primary" icon={<SwapOutlined />}
            onClick={() => setActiveTab('image')}>
            对比中 ({compareIds.length}) — 点击查看
          </Button>
        )}
      </Space>

      {/* Saved Searches */}
      <SavedSearchPanel
        currentMode={activeTab}
        currentParams={currentParams}
        onLoad={handleLoadSaved}
      />

      {/* 5 Tabs */}
      <Tabs
        activeKey={activeTab}
        onChange={k => setActiveTab(k as SearchMode)}
        style={{ color: '#e0e0e0' }}
        items={[
          {
            key: 'library', label: <span><DatabaseOutlined /> 库检索</span>,
            children: <LibrarySearchTab />,
          } as any,
          {
            key: 'image' as any, label: <span><CameraOutlined /> 图片搜</span>,
            children: <ImageSearchTab />,
          },
          {
            key: 'text', label: <span><FormOutlined /> 文本搜</span>,
            children: <TextSearchTab {...tabProps} />,
          },
          {
            key: 'attribute', label: <span><DatabaseOutlined /> 属性搜</span>,
            children: <AttributeSearchTab {...tabProps} />,
          },
          {
            key: 'composite', label: <span><SettingOutlined /> 综合搜</span>,
            children: <CompositeSearchTab {...tabProps} />,
          },
        ]}
      />

      {/* Library & Compare panels (collapsible) */}
      <Collapse
        ghost
        style={{ marginTop: 24, background: 'transparent' }}
        items={[
          {
            key: 'library',
            label: <Text style={{ color: '#a0a0a0' }}><DatabaseOutlined /> 比对库管理 ({allTargets.length} 个目标)</Text>,
            children: allTargets.length > 0 ? (
              <Space wrap size={[8, 8]}>
                {Object.entries(library).map(([cat, targets]) => (
                  <div key={cat}>
                    <Text strong style={{ color: '#e0e0e0', fontSize: 12 }}>{cat} ({(targets as LibraryTarget[]).length})</Text>
                    <Space wrap size={4} style={{ marginTop: 4 }}>
                      {(targets as LibraryTarget[]).map(t => (
                        <Badge
                          key={t.目标ID}
                          count={compareIds.includes(t.目标ID) ? '对比中' : 0}
                          size="small"
                        >
                          <Button
                            size="small"
                            type={compareIds.includes(t.目标ID) ? 'primary' : 'default'}
                            onClick={() => {
                              setDetailResult({
                                id: t.目标ID, 目标ID: t.目标ID, 名称: t.名称,
                                type: t.类型?.includes('车辆') ? 'vehicle' : 'person',
                                category: cat,
                                imageUrl: t.特征图片?.[0] || '',
                                thumbnailUrl: t.特征图片?.[0] || '',
                                similarityScore: 0, visualScore: 0, attrScore: 0,
                                cameraId: '', cameraName: t.最近出现 || '',
                                timestamp: t.最近出现 || '',
                                attributes: t.属性 || {},
                                tags: t.标签 || [],
                                matchDetail: '',
                                最近出现: t.最近出现,
                                关联案件: t.关联案件,
                              });
                              setDetailOpen(true);
                            }}
                          >
                            {t.名称}
                          </Button>
                        </Badge>
                      ))}
                    </Space>
                  </div>
                ))}
              </Space>
            ) : <Text style={{ color: '#64748b', fontSize: 12 }}>加载中...</Text>,
          },
          ...(compareIds.length >= 2 ? [{
            key: 'compare',
            label: <Text style={{ color: '#a0a0a0' }}><SwapOutlined /> 目标对比 ({compareIds.length})</Text>,
            children: (
              <Space wrap size={[8, 8]}>
                {compareIds.map(tid => {
                  const t = allTargets.find(a => a.目标ID === tid);
                  if (!t) return null;
                  return (
                    <Button key={tid} size="small" type="primary" danger
                      onClick={() => setCompareIds(prev => prev.filter(x => x !== tid))}>
                      {t.名称} ✕
                    </Button>
                  );
                })}
                <Button size="small" onClick={() => setCompareIds([])}>清空</Button>
              </Space>
            ),
          }] : []),
        ]}
      />
    </div>
  );
};

export default SearchPage;
