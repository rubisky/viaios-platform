import React, { useState } from 'react';
import { Input, Button, Card, Typography, Row, Col, Tag, Space, message } from 'antd';
import { SearchOutlined, ThunderboltOutlined, BulbOutlined } from '@ant-design/icons';
import SearchFilters from './SearchFilters';
import ResultGallery from './ResultGallery';
import ResultDetailModal from './ResultDetailModal';
import { apiGet, apiPost } from '../../api/client';
import type { SearchResult, SearchFilters as SearchFiltersType } from '../../types/search';
const { TextArea } = Input;
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

// Color/attribute keyword detection for simulated AI parsing
const ATTR_KEYWORDS: Record<string, RegExp[]> = {
  '上衣颜色': [/红色|黑色|白色|蓝色|灰色|黄色|绿色|棕色/],
  '下衣颜色': [/黑色|蓝色|白色|灰色|棕色/],
  '性别': [/男[性人]|女[性人]/],
  '身高': [/(\d{3})\s*cm/, /身高\s*(\d{3})/],
  '年龄': [/(\d{2})\s*岁/, /年龄\s*(\d{2})/],
  '体型': [/中等|瘦|健壮|胖/],
  '配饰': [/背包|帽子|眼镜|口罩|行李箱/],
};

const PARSE_EXAMPLES = [
  '穿黑色外套、戴口罩、身高约175cm的男性',
  '红色上衣、蓝色牛仔裤、背黑色背包的女性',
  '白色丰田轿车车牌ABC123',
  '约30岁、体型健壮、灰色外套的男性',
];

const TextSearchTab: React.FC<Props> = ({
  filters, onFiltersChange, onViewDetail, onCompareToggle,
  compareIds, detailResult, detailOpen, onDetailClose,
}) => {
  const [query, setQuery] = useState('');
  const [parsedAttrs, setParsedAttrs] = useState<Record<string, string>>({});
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const parseAttributes = (text: string) => {
    const attrs: Record<string, string> = {};
    for (const [key, patterns] of Object.entries(ATTR_KEYWORDS)) {
      for (const re of patterns) {
        const m = text.match(re);
        if (m) { attrs[key] = m[1] || m[0]; break; }
      }
    }
    setParsedAttrs(attrs);
  };

  const fetchSuggestions = async (prefix: string) => {
    if (prefix.length < 2) { setSuggestions([]); return; }
    try {
      const res = await apiGet<any>('/api/v1/search/suggest', { prefix, modality: 'combined' });
      setSuggestions(res?.suggestions || []);
    } catch { /* ignore */ }
  };

  const handleSearch = async () => {
    if (!query.trim()) { message.warning('请输入目标描述'); return; }
    setLoading(true);
    try {
      const res = await apiPost<any>('/api/v1/search/upgraded', {
        query: query.trim(), modality: 'text', top_k: filters.topK,
        filters: { time_range: filters.timeRange, category: filters.category },
      });
      const items = (res?.results || []).map((r: any, i: number) => ({
        id: r.id || `txt_${i}`,
        目标ID: r.id || `TXT${i}`,
        名称: r.name || query.slice(0, 20),
        type: (r.type || 'person') as SearchResult['type'],
        category: r.category || filters.category,
        imageUrl: r.image_url || '', thumbnailUrl: r.thumbnail_url || '',
        similarityScore: r.score ? (r.score * 100) : 0,
        visualScore: r.visual_score ? (r.visual_score * 100) : 0,
        attrScore: r.attr_score ? (r.attr_score * 100) : 0,
        cameraId: r.camera_id || '', cameraName: r.camera_name || '未知',
        timestamp: r.timestamp || '', attributes: r.attributes || parsedAttrs,
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
          title={<Text style={{ color: '#e0e0e0' }}><BulbOutlined /> 文本描述搜索</Text>}
          style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
        >
          <TextArea
            rows={4}
            value={query}
            onChange={e => { setQuery(e.target.value); parseAttributes(e.target.value); }}
            onInput={e => fetchSuggestions((e.target as HTMLTextAreaElement).value)}
            placeholder="描述目标特征, 如: 穿黑色外套、戴口罩、身高约175cm的男性"
            style={{ background: '#0f0f23', color: '#e0e0e0', border: '1px solid #334155', marginBottom: 8 }}
          />

          {/* Suggestions */}
          {suggestions.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <Text style={{ color: '#64748b', fontSize: 11 }}>搜索建议:</Text>
              <Space wrap size={4} style={{ marginTop: 4 }}>
                {suggestions.slice(0, 6).map((s, i) => (
                  <Tag key={i} style={{ cursor: 'pointer', fontSize: 11 }}
                    onClick={() => { setQuery(s); parseAttributes(s); }}>
                    {s}
                  </Tag>
                ))}
              </Space>
            </div>
          )}

          {/* Example queries */}
          <div style={{ marginBottom: 12 }}>
            <Text style={{ color: '#64748b', fontSize: 11 }}>试试看:</Text>
            <Space wrap size={4} style={{ marginTop: 4 }}>
              {PARSE_EXAMPLES.map((ex, i) => (
                <Tag key={i} color="geekblue" style={{ cursor: 'pointer', fontSize: 10 }}
                  onClick={() => { setQuery(ex); parseAttributes(ex); }}>
                  {ex.length > 25 ? ex.slice(0, 25) + '…' : ex}
                </Tag>
              ))}
            </Space>
          </div>

          {/* Parsed Attributes */}
          {Object.keys(parsedAttrs).length > 0 && (
            <Card size="small" title={<Text style={{ color: '#e0e0e0', fontSize: 12 }}><ThunderboltOutlined /> AI 识别属性</Text>}
              style={{ background: '#0f0f23', border: '1px solid #1677ff44', marginBottom: 12 }}>
              <Space wrap size={4}>
                {Object.entries(parsedAttrs).map(([k, v]) => (
                  <Tag key={k} color="blue" closable
                    onClose={() => setParsedAttrs(prev => { const n = { ...prev }; delete n[k]; return n; })}>
                    {k}: {v}
                  </Tag>
                ))}
              </Space>
            </Card>
          )}

          <SearchFilters filters={filters} onChange={onFiltersChange} />
          <Button type="primary" icon={<SearchOutlined />} block size="large"
            loading={loading} disabled={!query.trim()} onClick={handleSearch}>
            文本搜索
          </Button>
        </Card>
      </Col>

      <Col xs={24} lg={14}>
        <Card
          title={<Text style={{ color: '#e0e0e0' }}>
            搜索结果 {results.length > 0 && <Text type="success">({results.length} 条)</Text>}
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

export default TextSearchTab;
