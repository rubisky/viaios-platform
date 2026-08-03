/** Audit Log — Evidence chain + Governance audit viewer (P2-4) */
import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Modal, Descriptions, Timeline, Row, Col, Statistic, message } from 'antd';
import { AuditOutlined, SafetyCertificateOutlined, LinkOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { apiGet } from '../../api/client';

interface AuditEntry { timestamp: string; agent_id: string; agent_type: string; user_id: string; action: string; decision: string; allowed: boolean; triggered_rules: string[]; }
interface EvidenceChain { chain_id: string; operation: string; status: string; nodes: number; intact: boolean; created_at: string; }

const AuditLog: React.FC = () => {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [chains, setChains] = useState<EvidenceChain[]>([]);
  const [selectedChain, setSelectedChain] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      const [a, e] = await Promise.all([
        apiGet<any>('/api/v1/governance/audit?limit=100'),
        apiGet<any>('/api/v1/evidence/chains'),
      ]);
      setEntries(a?.entries || []);
      setChains(e?.chains || []);
    } catch { /* endpoints may not be available yet */ }
    setLoading(false);
  };

  useEffect(() => { fetch(); }, []);

  const viewChain = async (chainId: string) => {
    try {
      const d = await apiGet<any>(`/api/v1/evidence/chain/${chainId}`);
      setSelectedChain(d);
    } catch { message.error('链未找到'); }
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {[
          { title: '审计条目', value: entries.length, icon: <AuditOutlined />, color: '#1677ff' },
          { title: '证据链', value: chains.length, icon: <LinkOutlined />, color: '#52c41a' },
          { title: '完整链', value: chains.filter(c => c.intact).length, icon: <SafetyCertificateOutlined />, color: '#722ed1' },
          { title: '违规', value: entries.filter(e => !e.allowed).length, icon: <SearchOutlined />, color: '#ff4d4f' },
        ].map(s => (
          <Col xs={12} sm={6} key={s.title}>
            <Card size="small" style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
              <Statistic title={<span style={{ color: '#a0a0a0' }}>{s.title}</span>} value={s.value} prefix={s.icon} valueStyle={{ color: s.color, fontSize: 20 }} />
            </Card>
          </Col>
        ))}
      </Row>

      <Card title={<span style={{ color: '#e0e0e0' }}><AuditOutlined /> Governance Audit Log</span>}
        extra={<Button icon={<ReloadOutlined />} onClick={fetch}>Refresh</Button>}
        style={{ background: '#16213e', borderColor: '#2a2a4a', marginBottom: 16 }}>
        <Table dataSource={entries} loading={loading} rowKey={(_, i) => String(i)} size="small"
          pagination={{ pageSize: 15 }}
          columns={[
            { title: '时间', dataIndex: 'timestamp', render: (v: string) => v?.slice(11, 19) || '', width: 80 },
            { title: '智能体', dataIndex: 'agent_type', width: 100, render: (v: string) => <Tag>{v}</Tag> },
            { title: '用户', dataIndex: 'user_id', width: 80 },
            { title: '动作', dataIndex: 'action', width: 100 },
            { title: '决策', dataIndex: 'decision', width: 100, render: (v: string) => <Tag color={v === 'ALLOW' ? 'green' : v === 'DENY' ? 'red' : 'orange'}>{v}</Tag> },
            { title: '允许', dataIndex: 'allowed', width: 80, render: (v: boolean) => v ? <Tag color="green">Yes</Tag> : <Tag color="red">No</Tag> },
            { title: '规则', dataIndex: 'triggered_rules', render: (v: string[]) => v?.map(r => <Tag key={r} color="orange" style={{ fontSize: 10 }}>{r}</Tag>) },
          ]}
        />
      </Card>

      <Card title={<span style={{ color: '#e0e0e0' }}><LinkOutlined /> Evidence Chains</span>}
        style={{ background: '#16213e', borderColor: '#2a2a4a' }}>
        <Table dataSource={chains} loading={loading} rowKey="chain_id" size="small"
          onRow={r => ({ onClick: () => viewChain(r.chain_id), style: { cursor: 'pointer' } })}
          columns={[
            { title: '链ID', dataIndex: 'chain_id', width: 130 },
            { title: '操作类型', dataIndex: 'operation' },
            { title: '状态', dataIndex: 'status', render: (v: string) => <Tag color={v === 'VERIFIED' ? 'green' : v === 'COMPLETED' ? 'blue' : 'orange'}>{v}</Tag> },
            { title: '节点数', dataIndex: 'nodes', width: 60 },
            { title: '完整', dataIndex: 'intact', width: 80, render: (v: boolean) => v ? <Tag color="green">✓ Intact</Tag> : <Tag color="red">✗ Broken</Tag> },
            { title: '创建时间', dataIndex: 'created_at', width: 160, render: (v: string) => v?.slice(0, 19) },
          ]}
        />
      </Card>

      <Modal open={!!selectedChain} onCancel={() => setSelectedChain(null)} footer={null} width={700}
        title={`Evidence Chain: ${selectedChain?.chain_id}`}>
        {selectedChain && (
          <Timeline items={(selectedChain.nodes || []).map((n: any) => ({
            color: n.checksum === n.previous_checksum ? 'green' : 'red',
            children: (
              <Descriptions size="small" column={1} bordered style={{ background: '#0f0f23' }}>
                <Descriptions.Item label="Step">{n.sequence}</Descriptions.Item>
                <Descriptions.Item label="Type"><Tag>{n.type}</Tag></Descriptions.Item>
                <Descriptions.Item label="Actor">{n.actor}</Descriptions.Item>
                <Descriptions.Item label="Timestamp">{n.timestamp}</Descriptions.Item>
                <Descriptions.Item label="Checksum"><code style={{ fontSize: 10 }}>{n.checksum}</code></Descriptions.Item>
              </Descriptions>
            ),
          }))} />
        )}
      </Modal>
    </div>
  );
};

export default AuditLog;
