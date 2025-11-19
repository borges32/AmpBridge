import React from 'react';
import { Table, Card, Tag, Button, Space, Spin, Alert, Descriptions } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ArrowLeftOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import MainLayout from '@/components/MainLayout';
import { agentService } from '@/services/agentService';
import { AgentHealth, AgentPipelineHealth } from '@/types';

dayjs.extend(relativeTime);

// ============================================================================
// Agent Health Detail Page Component
// ============================================================================
const AgentHealthPage: React.FC = () => {
  const navigate = useNavigate();
  const { instanceId } = useParams<{ instanceId: string }>();

  // Fetch agent details
  const { data: agent, isLoading: agentLoading } = useQuery({
    queryKey: ['agent', instanceId],
    queryFn: () => agentService.getAgentDetail(instanceId!),
    enabled: !!instanceId,
  });

  // Fetch health history
  const {
    data: healthRecords,
    isLoading: healthLoading,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ['agentHealth', instanceId],
    queryFn: () => agentService.getAgentHealth(instanceId!, 100),
    enabled: !!instanceId,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch pipeline health
  const {
    data: pipelineHealthRecords,
    isLoading: pipelineHealthLoading,
    refetch: refetchPipelineHealth,
  } = useQuery({
    queryKey: ['agentPipelineHealth', instanceId],
    queryFn: () => agentService.getAgentPipelineHealth(instanceId!),
    enabled: !!instanceId,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  const isLoading = agentLoading || healthLoading || pipelineHealthLoading;
  const latestHealth = healthRecords?.[0];

  // Format unix nano timestamp
  const formatNanoTimestamp = (nanoTimestamp?: number | null) => {
    if (!nanoTimestamp) return 'N/A';
    try {
      const milliseconds = Number(nanoTimestamp) / 1000000;
      return dayjs(milliseconds).format('YYYY-MM-DD HH:mm:ss');
    } catch {
      return 'Invalid date';
    }
  };

  // Table columns definition
  const columns: ColumnsType<AgentHealth> = [
    {
      title: 'Timestamp',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
      defaultSortOrder: 'descend',
    },
    {
      title: 'Health Status',
      dataIndex: 'healthy',
      key: 'healthy',
      width: 120,
      render: (healthy) =>
        healthy ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>
            Healthy
          </Tag>
        ) : (
          <Tag color="error" icon={<CloseCircleOutlined />}>
            Unhealthy
          </Tag>
        ),
      filters: [
        { text: 'Healthy', value: true },
        { text: 'Unhealthy', value: false },
      ],
      onFilter: (value, record) => record.healthy === value,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 150,
      render: (status) => {
        const color =
          status === 'StatusOk' || status === 'StatusOK'
            ? 'green'
            : status === 'StatusFailed'
            ? 'red'
            : 'orange';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: 'Up',
      dataIndex: 'up',
      key: 'up',
      width: 80,
      render: (up) => (up ? 'Yes' : 'No'),
    },
    {
      title: 'Status Time',
      dataIndex: 'status_time_unix_nano',
      key: 'status_time_unix_nano',
      width: 180,
      render: formatNanoTimestamp,
    },
  ];

  // Pipeline health table columns
  const pipelineColumns: ColumnsType<AgentPipelineHealth> = [
    {
      title: 'Component Type',
      dataIndex: 'component_type',
      key: 'component_type',
      width: 140,
      filters: [
        { text: 'Pipeline', value: 'pipeline' },
        { text: 'Exporter', value: 'exporter' },
        { text: 'Processor', value: 'processor' },
        { text: 'Receiver', value: 'receiver' },
        { text: 'Extension', value: 'extension' },
      ],
      onFilter: (value, record) => record.component_type === value,
      render: (type: string) => (
        <Tag color="blue">{type}</Tag>
      ),
    },
    {
      title: 'Component Name',
      dataIndex: 'component_name',
      key: 'component_name',
      ellipsis: true,
    },
    {
      title: 'Parent Pipeline',
      dataIndex: 'parent_pipeline',
      key: 'parent_pipeline',
      width: 150,
      render: (parent) => parent || '-',
    },
    {
      title: 'Health Status',
      dataIndex: 'healthy',
      key: 'healthy',
      width: 120,
      render: (healthy) =>
        healthy ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>
            Healthy
          </Tag>
        ) : (
          <Tag color="error" icon={<CloseCircleOutlined />}>
            Unhealthy
          </Tag>
        ),
      filters: [
        { text: 'Healthy', value: true },
        { text: 'Unhealthy', value: false },
      ],
      onFilter: (value, record) => record.healthy === value,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => {
        const color =
          status === 'StatusOk' || status === 'StatusOK'
            ? 'green'
            : status === 'StatusFailed'
            ? 'red'
            : 'orange';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: 'Last Error',
      dataIndex: 'last_error',
      key: 'last_error',
      ellipsis: true,
      render: (error) => error || '-',
    },
    {
      title: 'Last Updated',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
      defaultSortOrder: 'descend',
    },
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/agents')}
            >
              Back to Agents
            </Button>
            <h1 className="text-2xl font-bold m-0">Agent Health Details</h1>
          </Space>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                refetchHealth();
                refetchPipelineHealth();
              }}
              loading={healthLoading || pipelineHealthLoading}
            >
              Refresh
            </Button>
          </Space>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center py-20">
            <Spin size="large" />
          </div>
        ) : !agent ? (
          <Alert
            message="Agent Not Found"
            description="The requested agent could not be found."
            type="error"
            showIcon
          />
        ) : (
          <>
            {/* Agent Information Card */}
            <Card title="Agent Information" className="shadow-sm">
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="Instance ID" span={2}>
                  <span className="font-mono text-xs">{agent.instance_id}</span>
                </Descriptions.Item>
                <Descriptions.Item label="Hostname">
                  {agent.host_name}
                </Descriptions.Item>
                <Descriptions.Item label="OS">
                  {agent.os_type} - {agent.os_description}
                </Descriptions.Item>
                <Descriptions.Item label="Service">
                  {agent.service_name || 'N/A'}
                </Descriptions.Item>
                <Descriptions.Item label="Version">
                  {agent.service_version || 'N/A'}
                </Descriptions.Item>
                <Descriptions.Item label="Architecture">
                  {agent.host_arch || 'N/A'}
                </Descriptions.Item>
                <Descriptions.Item label="Connection Status">
                  {agent.is_connected ? (
                    <Tag color="success" icon={<CheckCircleOutlined />}>
                      Connected
                    </Tag>
                  ) : (
                    <Tag color="default" icon={<CloseCircleOutlined />}>
                      Disconnected
                    </Tag>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="Last Seen">
                  {dayjs(agent.last_seen_at).format('YYYY-MM-DD HH:mm:ss')} (
                  {dayjs(agent.last_seen_at).fromNow()})
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* Current Health Status Card */}
            {latestHealth && (
              <Card title="Current Health Status" className="shadow-sm">
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="Health Status">
                    {latestHealth.healthy ? (
                      <Tag color="success" icon={<CheckCircleOutlined />}>
                        Healthy
                      </Tag>
                    ) : (
                      <Tag color="error" icon={<CloseCircleOutlined />}>
                        Unhealthy
                      </Tag>
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="Status">
                    {latestHealth.status}
                  </Descriptions.Item>
                  <Descriptions.Item label="Up">
                    {latestHealth.up ? 'Yes' : 'No'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Status Time">
                    {formatNanoTimestamp(latestHealth.status_time_unix_nano)}
                  </Descriptions.Item>
                  <Descriptions.Item label="Last Error" span={2}>
                    {latestHealth.last_error || 'No errors'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Last Updated">
                    {dayjs(latestHealth.created_at).format('YYYY-MM-DD HH:mm:ss')} (
                    {dayjs(latestHealth.created_at).fromNow()})
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            )}

            {/* Pipeline/Component Health Table */}
            <Card title="Pipeline & Component Health" className="shadow-sm">
              {!pipelineHealthRecords || pipelineHealthRecords.length === 0 ? (
                <Alert
                  message="No Pipeline Health Data"
                  description="No pipeline/component health records found for this agent."
                  type="info"
                  showIcon
                />
              ) : (
                <Table
                  columns={pipelineColumns}
                  dataSource={pipelineHealthRecords}
                  rowKey="id"
                  pagination={{
                    defaultPageSize: 10,
                    showSizeChanger: true,
                    pageSizeOptions: ['10', '20', '50', '100'],
                    showTotal: (total) => `Total ${total} components`,
                  }}
                  scroll={{ x: 'max-content' }}
                  size="small"
                />
              )}
            </Card>

            {/* Health History Table */}
            <Card title="Health History" className="shadow-sm">
              {!healthRecords || healthRecords.length === 0 ? (
                <Alert
                  message="No Health Data"
                  description="No health records found for this agent."
                  type="info"
                  showIcon
                />
              ) : (
                <Table
                  columns={columns}
                  dataSource={healthRecords}
                  rowKey="id"
                  pagination={{
                    defaultPageSize: 10,
                    showSizeChanger: true,
                    pageSizeOptions: ['10', '20', '50', '100'],
                    showTotal: (total) => `Total ${total} records`,
                  }}
                  scroll={{ x: 'max-content' }}
                  size="small"
                />
              )}
            </Card>
          </>
        )}
      </div>
    </MainLayout>
  );
};

export default AgentHealthPage;
