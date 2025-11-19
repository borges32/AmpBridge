import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import {
  CheckCircleOutlined,
  ApiOutlined,
  DisconnectOutlined,
  CloseCircleOutlined,
  WindowsOutlined,
  AppleOutlined,
} from '@ant-design/icons';
import { AgentStats } from '@/types';

// ============================================================================
// Stats Cards Component
// ============================================================================
interface StatsCardsProps {
  stats: AgentStats;
  loading?: boolean;
}

const StatsCards: React.FC<StatsCardsProps> = ({ stats, loading = false }) => {
  // Extract OS counts from distribution
  const windowsCount = Object.entries(stats.os_distribution)
    .filter(([os]) => os.toLowerCase().includes('windows'))
    .reduce((sum, [, count]) => sum + (count as number), 0);
  
  const linuxCount = Object.entries(stats.os_distribution)
    .filter(([os]) => os.toLowerCase().includes('linux'))
    .reduce((sum, [, count]) => sum + (count as number), 0);

  return (
    <Row gutter={[16, 16]} className="mb-6">
      <Col xs={24} sm={12} lg={6} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="Total Agents"
            value={stats.total_agents}
            prefix={<ApiOutlined />}
            valueStyle={{ color: '#1890ff' }}
          />
        </Card>
      </Col>

      <Col xs={24} sm={12} lg={6} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="Connected"
            value={stats.connected_agents}
            prefix={<CheckCircleOutlined />}
            valueStyle={{ color: '#52c41a' }}
          />
        </Card>
      </Col>

      <Col xs={24} sm={12} lg={6} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="Disconnected"
            value={stats.disconnected_agents}
            prefix={<DisconnectOutlined />}
            valueStyle={{ color: '#faad14' }}
          />
        </Card>
      </Col>

      <Col xs={24} sm={12} lg={6} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="Healthy"
            value={stats.healthy_agents}
            prefix={<CheckCircleOutlined />}
            valueStyle={{ color: '#52c41a' }}
          />
        </Card>
      </Col>

      <Col xs={24} sm={12} lg={6} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="Unhealthy"
            value={stats.unhealthy_agents}
            prefix={<CloseCircleOutlined />}
            valueStyle={{ color: '#ff4d4f' }}
          />
        </Card>
      </Col>

      <Col xs={24} sm={12} lg={6} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="Windows"
            value={windowsCount}
            prefix={<WindowsOutlined />}
            valueStyle={{ color: '#00a4ef' }}
          />
        </Card>
      </Col>

      <Col xs={24} sm={12} lg={6} xl={4}>
        <Card loading={loading}>
          <Statistic
            title="Linux"
            value={linuxCount}
            prefix={<AppleOutlined />}
            valueStyle={{ color: '#f7941e' }}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default StatsCards;
