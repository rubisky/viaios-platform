import React from 'react';
import { Card, Row, Col, Skeleton } from 'antd';

const DashboardSkeleton: React.FC = () => (
  <div>
    {/* Title skeleton */}
    <Skeleton active paragraph={{ rows: 2 }} style={{ marginBottom: 24 }} />
    {/* Stat cards */}
    <Row gutter={[16, 16]}>
      {[1,2,3,4,5,6,7,8].map(i => (
        <Col xs={24} sm={12} lg={6} key={i}>
          <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
            <Skeleton active paragraph={{ rows: 1 }} />
          </Card>
        </Col>
      ))}
    </Row>
    {/* Quick actions */}
    <div style={{ marginTop: 16 }}>
      <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8 }}>
        <Skeleton active paragraph={{ rows: 1 }} />
      </Card>
    </div>
    {/* Charts */}
    <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
      <Col xs={24} lg={14}>
        <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, height: 280 }}>
          <Skeleton active paragraph={{ rows: 6 }} />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={5}>
        <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, height: 280 }}>
          <Skeleton active paragraph={{ rows: 4 }} />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={5}>
        <Card style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, height: 280 }}>
          <Skeleton active paragraph={{ rows: 4 }} />
        </Card>
      </Col>
    </Row>
  </div>
);

export default DashboardSkeleton;
