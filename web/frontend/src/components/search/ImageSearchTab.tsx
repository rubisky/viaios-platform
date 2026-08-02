import React, { useState } from 'react';
import { Upload, Button, Row, Col, Card, Typography, message, Image, Badge, Tag } from 'antd';
import { InboxOutlined, SearchOutlined, DeleteOutlined, AimOutlined, CameraOutlined } from '@ant-design/icons';
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

interface DetectedObject {
  id: string; 类别: string; 置信度: number;
  位置: { x1: number; y1: number; x2: number; y2: number };
  缩略图: string;
}

const ImageSearchTab: React.FC<Props> = ({
  filters, onFiltersChange, onViewDetail, onCompareToggle,
  compareIds, detailResult, detailOpen, onDetailClose,
}) => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [detectedObjects, setDetectedObjects] = useState<DetectedObject[]>([]);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [realAI, setRealAI] = useState(false);
  const [loading, setLoading] = useState(false);
  const [, setApiResponse] = useState<any>(null);

  const handleSearch = async () => {
    if (!fileList.length) { message.warning('请先上传目标图片'); return; }
    setLoading(true);
    setDetectedObjects([]);
    setSelectedObjectId(null);
    try {
      const allResults: SearchResult[] = [];
      let allDetections: DetectedObject[] = [];
      for (const file of fileList) {
        const origin = file.originFileObj || file;
        if (!origin) continue;
        const base64 = await fileToBase64(origin as File);
        const res = await apiPost<any>('/api/v1/search/v2/image', {
          image_data: base64,
          category: filters.category,
          top_k: filters.topK,
        });
        setApiResponse(res);
        setRealAI(!!res?.真实AI);

        // Extract detected objects
        const objects = res?.AI检测?.检测对象 || [];
        allDetections = [...allDetections, ...objects.map((o: any) => ({ ...o, id: o.id || `obj_${Math.random().toString(36).slice(2,8)}` }))];

        // Map results
        const items = (res?.结果 || []).map((r: any, i: number) => ({
          id: (r.目标ID || 'r') + '_' + i,
          目标ID: r.目标ID, 名称: r.名称,
          type: (r.类别?.includes('车辆') ? 'vehicle' : 'person') as SearchResult['type'],
          category: r.类别, imageUrl: r.特征图片?.[0] || '',
          thumbnailUrl: r.特征图片?.[0] || '',
          similarityScore: r.综合匹配度 || 0,
          visualScore: r.视觉相似度 || 0, attrScore: r.属性匹配度 || 0,
          cameraId: r.摄像头ID || '', cameraName: r.最近出现 || '未知摄像头',
          timestamp: r.最近出现 || new Date().toISOString(),
          attributes: r.目标属性 || {}, tags: r.标签 || [],
          matchDetail: r.匹配属性 || '', 最近出现: r.最近出现, 关联案件: r.关联案件,
        }));
        allResults.push(...items);
      }

      setDetectedObjects(allDetections);
      const merged = new Map<string, SearchResult>();
      for (const r of allResults) {
        const existing = merged.get(r.目标ID);
        if (!existing || r.similarityScore > existing.similarityScore) merged.set(r.目标ID, r);
      }
      setResults(Array.from(merged.values()).sort((a, b) => b.similarityScore - a.similarityScore));
      message.success(`AI检测: ${allDetections.length}个目标, 比对: ${allResults.length}条结果`);
    } catch {
      message.error('搜索失败, 请重试');
    }
    setLoading(false);
  };

  const scoreColor = (s: number) => (s > 0.7 ? '#52c41a' : s > 0.4 ? '#faad14' : '#8c8c8c');

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={10}>
        <Card title={<Text style={{ color: '#e0e0e0' }}>上传目标图片</Text>}
          style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
          <Dragger multiple maxCount={5} accept="image/*" fileList={fileList}
            beforeUpload={() => false}
            onChange={({ fileList: fl }) => setFileList(fl)}
            itemRender={(_, file) => (
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
            )}>
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text" style={{ color: '#e0e0e0' }}>点击或拖拽上传</p>
            <p className="ant-upload-hint" style={{ color: '#64748b' }}>支持 JPG/PNG, 最多5张, 每张≤10MB</p>
          </Dragger>

          <div style={{ marginTop: 16 }}>
            <SearchFilters filters={filters} onChange={onFiltersChange} />
            <Button type="primary" icon={<SearchOutlined />} block size="large"
              loading={loading} disabled={!fileList.length} onClick={handleSearch}>
              开始分析
            </Button>
            {realAI && <Tag color="green" style={{ marginTop: 8 }}>ONNX 真实AI推理</Tag>}
          </div>
        </Card>
      </Col>

      <Col xs={24} lg={14}>
        {/* Detected Objects Panel */}
        {detectedObjects.length > 0 && (
          <Card
            title={<span style={{ color: '#e0e0e0' }}><AimOutlined /> AI检测目标 ({detectedObjects.length}) — 点击选中一个目标进行比对</span>}
            style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 12 }}
          >
            <div style={{ display: 'flex', gap: 10, overflowX: 'auto', paddingBottom: 8 }}>
              {detectedObjects.map(obj => {
                const isSelected = selectedObjectId === obj.id;
                return (
                  <Card
                    key={obj.id}
                    size="small"
                    hoverable
                    onClick={() => setSelectedObjectId(isSelected ? null : obj.id)}
                    style={{
                      minWidth: 140, cursor: 'pointer', flexShrink: 0,
                      background: isSelected ? '#1a3a5c' : '#0f0f23',
                      border: `2px solid ${isSelected ? '#1677ff' : '#334155'}`,
                      borderRadius: 8,
                    }}
                  >
                    {/* Thumbnail */}
                    <div style={{ width: 120, height: 100, margin: '0 auto 8px', borderRadius: 4, overflow: 'hidden', background: '#1a1a2e', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      {obj.缩略图 ? (
                        <img src={`data:image/jpeg;base64,${obj.缩略图}`} alt={obj.类别}
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      ) : (
                        <CameraOutlined style={{ fontSize: 24, color: '#334155' }} />
                      )}
                    </div>
                    {/* Info */}
                    <Text strong style={{ color: '#e0e0e0', fontSize: 12, display: 'block', textAlign: 'center' }}>
                      {obj.类别 === 'person' ? '人员' : obj.类别 === 'car' ? '轿车' : obj.类别 === 'truck' ? '卡车' : obj.类别 === 'bus' ? '巴士' : obj.类别 === 'motorcycle' ? '摩托' : obj.类别 === 'bicycle' ? '自行车' : obj.类别}
                    </Text>
                    <div style={{ textAlign: 'center', marginTop: 2 }}>
                      <Tag color={scoreColor(obj.置信度)} style={{ fontSize: 10 }}>
                        {Math.round(obj.置信度 * 100)}%
                      </Tag>
                    </div>
                    {isSelected && <Badge status="processing" text={<Text style={{ color: '#1677ff', fontSize: 10 }}>已选中</Text>} />}
                  </Card>
                );
              })}
            </div>
            {selectedObjectId && (
              <div style={{ marginTop: 8 }}>
                <Text style={{ color: '#a0a0a0', fontSize: 12 }}>
                  已选中目标 #{selectedObjectId} — 下方比对结果基于此目标
                </Text>
              </div>
            )}
          </Card>
        )}

        {/* Comparison Results */}
        <Card
          title={<Text style={{ color: '#e0e0e0' }}>
            比对结果 {results.length > 0 && <Tag color="green">{results.length}条</Tag>}
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
