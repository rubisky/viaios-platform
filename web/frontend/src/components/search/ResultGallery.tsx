import React, { useState } from 'react';
import { Card, Tag, Badge, Button, Space, Empty, Typography, Checkbox, Tooltip } from 'antd';
import { EyeOutlined, CameraOutlined, SwapOutlined, FileAddOutlined, ExportOutlined } from '@ant-design/icons';
import type { SearchResult } from '../../types/search';

const { Text, Paragraph } = Typography;

interface Props {
  results: SearchResult[];
  loading: boolean;
  onDetail: (result: SearchResult) => void;
  onCompare?: (resultId: string) => void;
  onAddToCase?: (resultIds: string[]) => void;
  onExport?: (resultIds: string[]) => void;
  compareIds?: string[];
}

const ResultGallery: React.FC<Props> = ({
  results, loading, onDetail, onCompare, onAddToCase, onExport, compareIds = [],
}) => {
  const [selected, setSelected] = useState<string[]>([]);
  const hasSelection = selected.length > 0;

  const toggleSelect = (id: string) => {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const selectAll = () => {
    if (selected.length === results.length) setSelected([]);
    else setSelected(results.map(r => r.id));
  };

  const scoreColor = (s: number) => (s > 85 ? '#52c41a' : s > 60 ? '#faad14' : '#ff4d4f');

  if (loading) {
    return <Text style={{ color: '#a0a0a0' }}>正在搜索中...</Text>;
  }

  if (!results.length) {
    return (
      <Empty
        description={<Text style={{ color: '#64748b' }}>暂无结果, 尝试调整筛选条件或换一张图片</Text>}
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <div>
      {/* Toolbar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <Space>
          <Button size="small" onClick={selectAll}>
            {selected.length === results.length ? '取消全选' : `全选 (${results.length})`}
          </Button>
          {hasSelection && <Text style={{ color: '#1677ff', fontSize: 12 }}>已选 {selected.length} 项</Text>}
        </Space>
        <Space>
          {hasSelection && onCompare && (
            <Button size="small" icon={<SwapOutlined />} onClick={() => selected.forEach(onCompare)}>
              对比 ({selected.length})
            </Button>
          )}
          {hasSelection && onAddToCase && (
            <Button size="small" type="primary" icon={<FileAddOutlined />} onClick={() => onAddToCase(selected)}>
              加入案件
            </Button>
          )}
          {hasSelection && onExport && (
            <Button size="small" icon={<ExportOutlined />} onClick={() => onExport(selected)}>
              导出
            </Button>
          )}
        </Space>
      </div>

      {/* Masonry Gallery */}
      <div style={{
        columns: '3 280px',
        columnGap: 12,
      }}>
        {results.map(r => (
          <div key={r.id} style={{
            breakInside: 'avoid',
            marginBottom: 12,
            position: 'relative',
          }}>
            <Checkbox
              checked={selected.includes(r.id)}
              onChange={() => toggleSelect(r.id)}
              style={{ position: 'absolute', top: 8, left: 8, zIndex: 2 }}
            />

            <Card
              hoverable
              size="small"
              style={{
                background: '#0f0f23',
                border: `1px solid ${scoreColor(r.similarityScore)}44`,
                borderRadius: 8,
                overflow: 'hidden',
              }}
              onClick={() => onDetail(r)}
            >
              {/* Thumbnail */}
              <div style={{
                width: '100%', height: 140, background: '#1a1a2e',
                borderRadius: 4, display: 'flex', alignItems: 'center',
                justifyContent: 'center', marginBottom: 8,
              }}>
                {r.thumbnailUrl ? (
                  <img src={r.thumbnailUrl} alt={r.名称}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 4 }} />
                ) : (
                  <CameraOutlined style={{ fontSize: 32, color: '#334155' }} />
                )}
              </div>

              {/* Score Badge */}
              <Badge.Ribbon
                text={`${r.similarityScore}%`}
                color={scoreColor(r.similarityScore)}
                style={{ top: -4 }}
              />

              {/* Info */}
              <Text strong style={{ color: '#e0e0e0', fontSize: 13, display: 'block' }}>
                {r.名称}
              </Text>
              <Text style={{ color: '#64748b', fontSize: 11 }}>{r.category}</Text>
              <Paragraph style={{ color: '#64748b', fontSize: 10, margin: '4px 0' }} ellipsis={{ rows: 1 }}>
                {r.cameraName} · {r.timestamp}
              </Paragraph>

              {/* Tags */}
              <Space size={2} wrap>
                {r.tags.slice(0, 3).map(t => (
                  <Tag key={t} style={{ fontSize: 10, margin: 1 }}>{t}</Tag>
                ))}
              </Space>

              {/* Actions */}
              <div style={{ marginTop: 8, display: 'flex', gap: 4 }}>
                <Tooltip title="详情">
                  <Button size="small" type="link" icon={<EyeOutlined />}
                    onClick={(e) => { e.stopPropagation(); onDetail(r); }} />
                </Tooltip>
                {onCompare && (
                  <Tooltip title={compareIds.includes(r.id) ? '取消对比' : '加入对比'}>
                    <Button size="small" type="link" icon={<SwapOutlined />}
                      onClick={(e) => { e.stopPropagation(); onCompare(r.id); }}
                      danger={compareIds.includes(r.id)} />
                  </Tooltip>
                )}
              </div>
            </Card>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ResultGallery;
