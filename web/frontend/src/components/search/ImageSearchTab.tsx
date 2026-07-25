import React, { useState } from 'react';
import { Upload, Button, Row, Col, Card, Typography, message, Image } from 'antd';
import { InboxOutlined, SearchOutlined, DeleteOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import SearchFilters from './SearchFilters';
import ResultGallery from './ResultGallery';
import ResultDetailModal from './ResultDetailModal';
import { apiPost } from '../../api/client';
import type { SearchResult, SearchFilters as SearchFiltersType } from '../../types/search';

const { Text } = Typography;
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

const ImageSearchTab: React.FC<Props> = ({
  filters, onFiltersChange, onViewDetail, onCompareToggle,
  compareIds, detailResult, detailOpen, onDetailClose,
}) => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!fileList.length) { message.warning('请先上传目标图片'); return; }
    setLoading(true);
    try {
      const allResults: SearchResult[] = [];
      for (const file of fileList) {
        const origin = file.originFileObj || file;
        if (!origin) continue;
        const base64 = await fileToBase64(origin as File);
        const res = await apiPost<any>('/api/v1/search/v2/image', {
          image_data: base64,
          category: filters.category,
          top_k: filters.topK,
        });
        const items = (res?.结果 || []).map((r: any, i: number) => ({
          id: r.目标ID + '_' + i,
          目标ID: r.目标ID,
          名称: r.名称,
          type: r.类别?.includes('车辆') ? 'vehicle' as const : 'person' as const,
          category: r.类别,
          imageUrl: r.特征图片?.[0] || '',
          thumbnailUrl: r.特征图片?.[0] || '',
          similarityScore: r.综合匹配度 || 0,
          visualScore: r.视觉相似度 || 0,
          attrScore: r.属性匹配度 || 0,
          cameraId: r.摄像头ID || '',
          cameraName: r.最近出现 || '未知摄像头',
          timestamp: r.最近出现 || new Date().toISOString(),
          attributes: r.目标属性 || {},
          tags: r.标签 || [],
          matchDetail: r.匹配属性 || '',
          最近出现: r.最近出现,
          关联案件: r.关联案件,
        }));
        allResults.push(...items);
      }
      // Merge & dedup by 目标ID, keep highest score
      const merged = new Map<string, SearchResult>();
      for (const r of allResults) {
        const existing = merged.get(r.目标ID);
        if (!existing || r.similarityScore > existing.similarityScore) {
          merged.set(r.目标ID, r);
        }
      }
      const final = Array.from(merged.values()).sort((a, b) => b.similarityScore - a.similarityScore);
      setResults(final);
      message.success(`搜索完成: ${final.length} 条结果`);
    } catch {
      message.error('搜索失败, 请重试');
    }
    setLoading(false);
  };

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={10}>
        <Card
          title={<Text style={{ color: '#e0e0e0' }}>上传目标图片</Text>}
          style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
        >
          <Dragger
            multiple
            maxCount={5}
            accept="image/*"
            fileList={fileList}
            beforeUpload={(file) => {
              const isImage = file.type.startsWith('image/');
              if (!isImage) message.error(`${file.name} 不是图片文件`);
              const lt10M = file.size / 1024 / 1024 < 10;
              if (!lt10M) message.error(`${file.name} 超过 10MB 限制`);
              return isImage && lt10M ? Upload.LIST_IGNORE : Upload.LIST_IGNORE;
            }}
            onChange={({ fileList: fl }) => setFileList(fl)}
            itemRender={(_originNode, file) => (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
                {file.thumbUrl ? (
                  <Image src={file.thumbUrl} width={40} height={40} style={{ objectFit: 'cover', borderRadius: 4 }} preview={false} />
                ) : (
                  <div style={{ width: 40, height: 40, background: '#1a1a2e', borderRadius: 4 }} />
                )}
                <Text style={{ color: '#e0e0e0', flex: 1, fontSize: 12 }} ellipsis>{file.name}</Text>
                <Button type="link" size="small" danger icon={<DeleteOutlined />}
                  onClick={() => setFileList(prev => prev.filter(f => f.uid !== file.uid))} />
              </div>
            )}
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text" style={{ color: '#e0e0e0' }}>点击或拖拽上传</p>
            <p className="ant-upload-hint" style={{ color: '#64748b' }}>
              支持 JPG/PNG/BMP, 最多5张, 每张不超过10MB
            </p>
          </Dragger>

          <div style={{ marginTop: 16 }}>
            <SearchFilters filters={filters} onChange={onFiltersChange} />
            <Button
              type="primary" icon={<SearchOutlined />} block size="large"
              loading={loading} disabled={!fileList.length}
              onClick={handleSearch}
            >
              {fileList.length > 1 ? `开始比对 (${fileList.length} 张图片)` : '开始比对'}
            </Button>
          </div>
        </Card>
      </Col>

      <Col xs={24} lg={14}>
        <Card
          title={<Text style={{ color: '#e0e0e0' }}>
            比对结果 {results.length > 0 && <Text type="success" style={{ fontSize: 14 }}>({results.length} 条)</Text>}
          </Text>}
          style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}
        >
          <ResultGallery
            results={results}
            loading={loading}
            onDetail={onViewDetail}
            onCompare={onCompareToggle}
            compareIds={compareIds}
          />
        </Card>
      </Col>

      <ResultDetailModal
        open={detailOpen}
        result={detailResult}
        onClose={onDetailClose}
      />
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

export default ImageSearchTab;
