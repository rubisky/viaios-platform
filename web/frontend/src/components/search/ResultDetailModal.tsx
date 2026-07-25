import React from 'react';
import { Modal, Descriptions, Tag, Button, Space, Typography, Image, Divider } from 'antd';
import { EnvironmentOutlined, FileAddOutlined, NodeIndexOutlined, ClockCircleOutlined } from '@ant-design/icons';
import type { SearchResult } from '../../types/search';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

interface Props {
  open: boolean;
  result: SearchResult | null;
  onClose: () => void;
  onAddToCase?: (resultId: string) => void;
}

const ResultDetailModal: React.FC<Props> = ({ open, result, onClose, onAddToCase }) => {
  const navigate = useNavigate();

  if (!result) return null;

  const scoreColor = (s: number) => (s > 85 ? '#52c41a' : s > 60 ? '#faad14' : '#ff4d4f');

  return (
    <Modal
      title={<Title level={4} style={{ color: '#e0e0e0', margin: 0 }}>{result.名称}</Title>}
      open={open}
      onCancel={onClose}
      width={640}
      footer={
        <Space>
          <Button onClick={onClose}>关闭</Button>
          {onAddToCase && (
            <Button type="primary" icon={<FileAddOutlined />} onClick={() => onAddToCase(result.id)}>
              加入案件
            </Button>
          )}
          <Button
            type="default"
            icon={<NodeIndexOutlined />}
            onClick={() => navigate(`/trajectory?targetId=${result.目标ID}`)}
          >
            轨迹分析
          </Button>
        </Space>
      }
      styles={{
        body: { background: '#0d1b2a', padding: 16 },
        header: { background: '#0d1b2a', borderBottom: '1px solid #2a2a4a' },
      }}
    >
      {/* Image */}
      <div style={{
        width: '100%', height: 280, background: '#1a1a2e',
        borderRadius: 8, display: 'flex', alignItems: 'center',
        justifyContent: 'center', marginBottom: 16,
      }}>
        {result.imageUrl ? (
          <Image src={result.imageUrl} alt={result.名称}
            style={{ maxWidth: '100%', maxHeight: 280, objectFit: 'contain', borderRadius: 8 }}
            fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
          />
        ) : (
          <div style={{ textAlign: 'center' }}>
            <EnvironmentOutlined style={{ fontSize: 48, color: '#334155' }} />
            <p style={{ color: '#64748b', fontSize: 12 }}>无预览图</p>
          </div>
        )}
      </div>

      {/* Scores */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <div style={{ flex: 1, textAlign: 'center', padding: 12, background: '#16213e', borderRadius: 8 }}>
          <div style={{ fontSize: 28, fontWeight: 'bold', color: scoreColor(result.similarityScore) }}>
            {result.similarityScore}%
          </div>
          <Text style={{ color: '#64748b', fontSize: 11 }}>综合匹配度</Text>
        </div>
        <div style={{ flex: 1, textAlign: 'center', padding: 12, background: '#16213e', borderRadius: 8 }}>
          <div style={{ fontSize: 22, fontWeight: 'bold', color: '#1677ff' }}>{result.visualScore}%</div>
          <Text style={{ color: '#64748b', fontSize: 11 }}>视觉相似度</Text>
        </div>
        <div style={{ flex: 1, textAlign: 'center', padding: 12, background: '#16213e', borderRadius: 8 }}>
          <div style={{ fontSize: 22, fontWeight: 'bold', color: '#52c41a' }}>{result.attrScore}%</div>
          <Text style={{ color: '#64748b', fontSize: 11 }}>属性匹配度</Text>
        </div>
      </div>

      <Divider style={{ borderColor: '#2a2a4a', margin: '12px 0' }} />

      {/* Metadata */}
      <Descriptions column={2} size="small"
        labelStyle={{ color: '#a0a0a0' }}
        contentStyle={{ color: '#e0e0e0' }}>
        <Descriptions.Item label="类别">
          <Tag color="blue">{result.category}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="目标ID">{result.目标ID}</Descriptions.Item>
        <Descriptions.Item label="摄像头">{result.cameraName}</Descriptions.Item>
        <Descriptions.Item label={<><ClockCircleOutlined /> 时间</>}>{result.timestamp}</Descriptions.Item>
      </Descriptions>

      {result.attributes && Object.keys(result.attributes).length > 0 && (
        <>
          <Divider style={{ borderColor: '#2a2a4a', margin: '12px 0' }} />
          <Title level={5} style={{ color: '#e0e0e0', marginBottom: 8 }}>目标属性</Title>
          <Space wrap>
            {Object.entries(result.attributes).map(([k, v]) => (
              <Tag key={k} style={{ fontSize: 11 }}>{k}: {String(v)}</Tag>
            ))}
          </Space>
        </>
      )}

      {/* Tags */}
      {result.tags.length > 0 && (
        <>
          <Divider style={{ borderColor: '#2a2a4a', margin: '12px 0' }} />
          <div>
            {result.tags.map(t => <Tag key={t}>{t}</Tag>)}
          </div>
        </>
      )}

      {/* Match detail */}
      {result.matchDetail && (
        <>
          <Divider style={{ borderColor: '#2a2a4a', margin: '12px 0' }} />
          <Text style={{ color: '#a0a0a0', fontSize: 12 }}>匹配详情: {result.matchDetail}</Text>
        </>
      )}

      {/* Case link */}
      {result.关联案件 && (
        <div style={{ marginTop: 12 }}>
          <Text style={{ color: '#a0a0a0', fontSize: 12 }}>关联案件: {result.关联案件}</Text>
        </div>
      )}
    </Modal>
  );
};

export default ResultDetailModal;
