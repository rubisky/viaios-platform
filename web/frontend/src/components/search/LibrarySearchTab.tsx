/** LibrarySearchTab — 1:N 目标库检索 */
import React, { useState } from 'react';
import { Upload, Button, Row, Col, Card, Typography, message, Select, Table, Tag, Space, Statistic, Badge } from 'antd';
import { InboxOutlined, SearchOutlined, DatabaseOutlined, ReloadOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { apiPost, apiGet } from '../../api/client';

const { Text } = Typography;
const { Dragger } = Upload;

const libNames: Record<string,string> = {snapshot:'抓拍库',upload:'离线上传库',watchlist:'重点人员库',history:'历史解析库','':'全部库'};
const libColors: Record<string,string> = {snapshot:'blue',upload:'green',watchlist:'red',history:'orange'};

const LibrarySearchTab: React.FC = () => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [library, setLibrary] = useState('');
  const [stats, setStats] = useState<any>({});

  React.useEffect(() => {
    apiGet('/api/v1/library/stats').then(setStats).catch(()=>{});
  }, []);

  const search = async () => {
    if (!fileList.length) { message.warning('请上传目标图片'); return; }
    setLoading(true);
    try {
      const file = fileList[0];
      const base64 = await new Promise<string>((res, rej) => {
        const reader = new FileReader();
        reader.onload = () => res((reader.result as string).split(',')[1]);
        reader.onerror = rej;
        reader.readAsDataURL(file.originFileObj as Blob);
      });

      const r = await apiPost<any>('/api/v1/library/search/1vn', {
        image_data: base64,
        library: library || '',
        top_k: 20,
        min_score: 0.3,
      });
      setResults(r?.results || []);
      message.success(`找到 ${r?.total || 0} 个匹配`);
    } catch { message.error('搜索失败'); }
    setLoading(false);
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {[{ title: '抓拍库', value: stats.by_library?.snapshot||0, color:'#1890ff' },
          { title: '上传库', value: stats.by_library?.upload||0, color:'#52c41a' },
          { title: '布控库', value: stats.by_library?.watchlist||0, color:'#ff4d4f' },
          { title: '历史库', value: stats.by_library?.history||0, color:'#fa8c16' },
        ].map(s => (
          <Col xs={12} sm={6} key={s.title}><Card size="small" style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
            <Statistic title={<span style={{ color: '#a0a0a0' }}>{s.title}</span>} value={s.value} valueStyle={{ color: s.color, fontSize: 18 }} />
          </Card></Col>
        ))}
      </Row>

      <Card style={{ background: '#16213e', borderColor: '#2a2a4a', marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Space>
            <Select style={{ width: 150 }} value={library} onChange={setLibrary} placeholder="全部库"
              options={Object.entries(libNames).map(([k,v]) => ({value:k,label:v}))} />
            <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={search} size="large">
              1:N 目标库检索
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => apiGet('/api/v1/library/stats').then(setStats)}>刷新统计</Button>
          </Space>
          <Dragger fileList={fileList} beforeUpload={f => { setFileList([{uid:'-1',name:f.name,originFileObj:f}]); return false; }}
            onRemove={() => setFileList([])} maxCount={1} accept="image/*">
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">点击或拖拽目标图片</p>
            <p className="ant-upload-hint">支持 JPG/PNG，将搜索全部4个目标库</p>
          </Dragger>
        </Space>
      </Card>

      {results.length > 0 && (
        <Card title={<span style={{ color: '#e0e0e0' }}><DatabaseOutlined /> 检索结果 ({results.length})</span>}
          style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
          <Table dataSource={results} rowKey="target_id" size="small"
            columns={[
              { title: '排名', dataIndex: 'rank', width: 60, render: (v: number) => <Badge count={v} style={{ backgroundColor: v<=3?'#52c41a':'#1677ff' }} /> },
              { title: '名称', dataIndex: 'name', render: (v: string) => <Text style={{ color: '#e0e0e0' }}>{v}</Text> },
              { title: '相似度', dataIndex: 'score', width: 100, render: (v: number) => <Tag color={v>0.8?'green':v>0.6?'blue':'default'}>{(v*100).toFixed(1)}%</Tag> },
              { title: '来源库', dataIndex: 'library', width: 100, render: (v: string) => <Tag color={libColors[v]}>{libNames[v]}</Tag> },
              { title: '类型', dataIndex: 'type', width: 80, render: (v: string) => <Tag>{v}</Tag> },
              { title: '摄像头', dataIndex: 'camera', width: 80 },
              { title: '属性', dataIndex: 'attributes', render: (v: any) => v ? `${v.gender||''} ${v.age_group||''} ${v.upper_color||v.color||''}` : '-' },
            ]} />
        </Card>
      )}
    </div>
  );
};

export default LibrarySearchTab;
