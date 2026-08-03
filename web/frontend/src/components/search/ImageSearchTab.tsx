/** ImageSearchTab — 上传→AI解析→选目标→检索 */
import React, { useState } from 'react';
import { Upload, Button, Row, Col, Card, Typography, message, Select, Checkbox, Space, Tag, Spin, Empty } from 'antd';
import { InboxOutlined, SearchOutlined, AimOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { apiPost } from '../../api/client';

const { Text } = Typography;
const { Dragger } = Upload;

interface DetectedObject {
  id: string; class: string; confidence: number;
  bbox: [number,number,number,number]; embedding: number[];
  attributes: Record<string,any>;
}
interface SearchResult { target_id:string; name:string; score:number; rank:number; library:string; type:string; camera:string; attributes:any; }

const classColors: Record<string,string> = { person:'#4ecdc4', face:'#ff6b6b', vehicle:'#45b7d1', body:'#96ceb4' };
const classNames: Record<string,string> = { person:'人员', face:'人脸', vehicle:'车辆', body:'人体' };

const ImageSearchTab: React.FC = () => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [objects, setObjects] = useState<DetectedObject[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [detecting, setDetecting] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchLib, setSearchLib] = useState('');

  // Step 1: 上传并解析
  const handleUpload = async (file: UploadFile) => {
    setFileList([file]);
    setObjects([]); setSelected([]); setResults([]);
    setDetecting(true);
    try {
      const f = file.originFileObj as Blob;
      const base64 = await new Promise<string>((res, rej) => {
        const r = new FileReader(); r.onload = () => res((r.result as string).split(',')[1]); r.onerror = rej;
        r.readAsDataURL(f);
      });
      const resp = await apiPost<any>('/api/v1/search/detect', { image_data: base64 });
      const objs = resp?.objects || [];
      setObjects(objs);
      if (objs.length === 0) message.info('未检测到目标');
      else message.success(`检测到 ${objs.length} 个目标`);
      // 默认全选
      setSelected(objs.map((o: DetectedObject) => o.id));
    } catch { message.error('检测失败'); }
    setDetecting(false);
    return false;
  };

  // Step 2: 选择目标并检索
  const handleSearch = async () => {
    if (!selected.length) { message.warning('请选择目标'); return; }
    setSearching(true);
    try {
      const selObjects = objects.filter(o => selected.includes(o.id));
      const allResults: SearchResult[] = [];
      for (const obj of selObjects) {
        const r = await apiPost<any>('/api/v1/library/search/1vn', {
          embedding: obj.embedding,
          library: searchLib || '',
          top_k: 10,
          min_score: 0.3,
        });
        if (r?.results) allResults.push(...r.results);
      }
      // 去重+排序
      const seen = new Set<string>();
      const merged = allResults
        .filter(r => { const k = r.target_id; if (seen.has(k)) return false; seen.add(k); return true; })
        .sort((a,b) => b.score - a.score)
        .slice(0, 50);
      setResults(merged);
      message.success(`找到 ${merged.length} 个匹配`);
    } catch { message.error('检索失败'); }
    setSearching(false);
  };

  const toggleSelect = (id: string) => {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x!==id) : [...prev, id]);
  };

  const selCount = selected.length;

  return (
    <div>
      {/* 上传区 */}
      <Card style={{ background: '#16213e', borderColor: '#2a2a4a', marginBottom: 16 }}>
        <Dragger fileList={fileList} beforeUpload={handleUpload as any}
          onRemove={() => { setFileList([]); setObjects([]); setResults([]); }}
          maxCount={1} accept="image/*" disabled={detecting}>
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">上传目标图片</p>
          <p className="ant-upload-hint">系统将自动解析图中的人脸、人体、车辆等目标</p>
        </Dragger>
      </Card>

      {/* 检测目标区 */}
      {detecting && <div style={{ textAlign:'center', padding:40 }}><Spin tip="AI 解析中..." /></div>}

      {objects.length > 0 && !detecting && (
        <Card title={<span style={{ color:'#e0e0e0' }}><AimOutlined /> 检测到 {objects.length} 个目标（勾选要检索的）</span>}
          extra={<Space>
            <Button size="small" onClick={() => setSelected(objects.map(o=>o.id))}>全选</Button>
            <Button size="small" onClick={() => setSelected([])}>取消</Button>
            <Select style={{ width:120 }} value={searchLib} onChange={setSearchLib} placeholder="全部库"
              options={[{value:'',label:'全部库'},{value:'snapshot',label:'抓拍库'},{value:'upload',label:'上传库'},{value:'watchlist',label:'布控库'},{value:'history',label:'历史库'}]} />
            <Button type="primary" icon={<SearchOutlined />} loading={searching} onClick={handleSearch}
              disabled={selCount===0}>检索选中 ({selCount})</Button>
          </Space>}
          style={{ background:'#16213e', borderColor:'#2a2a4a', marginBottom:16 }}>
          <Row gutter={[12,12]}>
            {objects.map(obj => (
              <Col xs={12} sm={8} md={6} key={obj.id}>
                <Card size="small" hoverable
                  style={{ background: selected.includes(obj.id)?'#1a3a5c':'#0f1525', borderColor: selected.includes(obj.id)?classColors[obj.class]:'#2a2a4a' }}
                  onClick={() => toggleSelect(obj.id)}>
                  <Space direction="vertical" style={{ width:'100%' }}>
                    <Space>
                      <Checkbox checked={selected.includes(obj.id)} />
                      <Tag color={classColors[obj.class]}>{classNames[obj.class]||obj.class}</Tag>
                      <Tag>{(obj.confidence*100).toFixed(0)}%</Tag>
                    </Space>
                    <Text style={{ color:'#a0a0a0', fontSize:11 }}>
                      {obj.attributes?.gender||''} {obj.attributes?.age_group||''} {obj.attributes?.upper_color||obj.attributes?.color||''}
                    </Text>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {/* 检索结果 */}
      {results.length > 0 && (
        <Card title={<span style={{ color:'#e0e0e0' }}>检索结果 ({results.length})</span>}
          style={{ background:'#16213e', borderColor:'#2a2a4a' }}>
          <Row gutter={[8,8]}>
            {results.slice(0,30).map(r => (
              <Col xs={12} sm={8} md={6} key={r.target_id}>
                <Card size="small" style={{ background:'#0f1525', borderColor:'#2a2a4a' }}>
                  <Space direction="vertical" size={2}>
                    <Text strong style={{ color:'#e0e0e0', fontSize:13 }}>{r.name}</Text>
                    <Text style={{ color:'#52c41a', fontSize:12 }}>相似度 {(r.score*100).toFixed(1)}%</Text>
                    <Space size={4}>
                      <Tag color="blue" style={{ fontSize:10 }}>{r.library==='snapshot'?'抓拍':r.library==='upload'?'上传':r.library==='watchlist'?'布控':r.library}</Tag>
                      <Tag style={{ fontSize:10 }}>{r.type}</Tag>
                    </Space>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {objects.length===0 && !detecting && fileList.length>0 && (
        <Empty description="未检测到目标，请尝试其他图片" />
      )}
    </div>
  );
};

export default ImageSearchTab;
