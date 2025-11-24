import React, { useState } from 'react';
import { Table, Button, Tag, Space, Input, Select, Card, message, Modal } from 'antd';
import {
  DownloadOutlined,
  EyeOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SearchOutlined,
  FileExcelOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import MainLayout from '@/components/MainLayout';
import StatsCards from '@/components/StatsCards';
import { agentService } from '@/services/agentService';
import { Agent, AgentListParams } from '@/types';

dayjs.extend(relativeTime);

const { Search } = Input;
const { Option } = Select;

// ============================================================================
// Agents Page Component
// ============================================================================
const AgentsPage: React.FC = () => {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<AgentListParams>({
    page: 1,
    size: 10,
  });

  // Fetch agents with filters
  const { data: agentsData, isLoading: agentsLoading, refetch: refetchAgents } = useQuery({
    queryKey: ['agents', filters],
    queryFn: () => agentService.getAgents(filters),
  });

  // Fetch stats
  const { data: statsData, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ['agentStats'],
    queryFn: () => agentService.getAgentStats(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Handle export to CSV
  const handleExportCSV = async () => {
    try {
      const blob = await agentService.exportAgentsCSV();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `agents_export_${dayjs().format('YYYY-MM-DD_HH-mm-ss')}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      message.success('Agents exported to CSV successfully');
    } catch (error: any) {
      message.error(error.detail || 'Failed to export agents to CSV');
    }
  };

  // Handle download config
  const handleDownloadConfig = async (agent: Agent) => {
    try {
      const blob = await agentService.downloadConfig(agent.instance_id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${agent.host_name}_config.yaml`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      message.success('Config downloaded successfully');
    } catch (error: any) {
      message.error(error.detail || 'Failed to download config');
    }
  };

  // Handle view health - navigate to health detail page
  const handleViewHealth = (agent: Agent) => {
    navigate(`/agents/${agent.instance_id}/health`);
  };

  // Handle delete agent with double confirmation
  const handleDeleteAgent = (agent: Agent) => {
    Modal.confirm({
      title: 'Delete Agent?',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>
            Are you sure you want to <strong className="text-red-600">permanently delete</strong> this agent?
          </p>
          <div className="mt-3 p-3 bg-gray-100 rounded">
            <p className="mb-1">
              <strong>Instance ID:</strong> {agent.instance_id}
            </p>
            <p className="mb-1">
              <strong>Hostname:</strong> {agent.host_name}
            </p>
          </div>
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
            <p className="text-red-700 font-semibold mb-2">⚠️ Warning: This action cannot be undone!</p>
            <p className="text-sm text-red-600">This will permanently delete:</p>
            <ul className="text-sm text-red-600 ml-4 mt-1">
              <li>• Agent information</li>
              <li>• All health history records</li>
              <li>• All configuration versions</li>
              <li>• All pipeline health records</li>
            </ul>
          </div>
        </div>
      ),
      okText: 'Yes, Delete',
      okType: 'danger',
      cancelText: 'Cancel',
      width: 600,
      onOk: async () => {
        try {
          const result = await agentService.deleteAgent(agent.instance_id);
          message.success(result.message || 'Agent deleted successfully');
          // Refetch both agents list and stats
          refetchAgents();
          refetchStats();
        } catch (error: any) {
          message.error(error.detail || 'Failed to delete agent');
        }
      },
    });
  };

  // Table columns definition
  const columns: ColumnsType<Agent> = [
    {
      title: 'Instance ID',
      dataIndex: 'instance_id',
      key: 'instance_id',
      width: 300,
      ellipsis: true,
      render: (text) => <span className="font-mono text-xs">{text}</span>,
    },
    {
      title: 'Hostname',
      dataIndex: 'host_name',
      key: 'host_name',
      width: 200,
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: 'OS',
      dataIndex: 'os_type',
      key: 'os_type',
      width: 150,
      render: (text, record) => (
        <div>
          <div>{text}</div>
          <div className="text-xs text-gray-500">{record.os_description}</div>
        </div>
      ),
    },
    {
      title: 'Connection',
      dataIndex: 'is_connected',
      key: 'is_connected',
      width: 120,
      render: (is_connected) =>
        is_connected ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>
            Connected
          </Tag>
        ) : (
          <Tag color="default" icon={<CloseCircleOutlined />}>
            Disconnected
          </Tag>
        ),
    },
    {
      title: 'Last Seen',
      dataIndex: 'last_seen_at',
      key: 'last_seen_at',
      width: 180,
      render: (text) => (
        <span className="text-gray-600">{dayjs(text).fromNow()}</span>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => handleDownloadConfig(record)}
            title="Download Config"
          />
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewHealth(record)}
            title="View Health"
          />
          <Button
            type="primary"
            size="small"
            icon={<SettingOutlined />}
            onClick={() => navigate(`/agents/${record.instance_id}/config`)}
            title="View/Edit Config"
          >
            Config
          </Button>
          <Button
            type="text"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteAgent(record)}
            title="Delete Agent"
          />
        </Space>
      ),
    },
  ];

  // Handle table pagination change
  const handleTableChange = (pagination: TablePaginationConfig) => {
    setFilters({
      ...filters,
      page: pagination.current || 1,
      size: pagination.pageSize || 10,
    });
  };

  // Handle search
  const handleSearch = (value: string) => {
    setFilters({ ...filters, search: value || undefined, page: 1 });
  };

  // Handle filter changes
  const handleFilterChange = (key: keyof AgentListParams, value: any) => {
    setFilters({ ...filters, [key]: value === 'all' ? undefined : value, page: 1 });
  };

  return (
    <MainLayout>
      <div className="w-full">
        {/* Header with Export Button */}
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Agent Management</h1>
          <Button
            type="primary"
            icon={<FileExcelOutlined />}
            onClick={handleExportCSV}
            loading={agentsLoading}
          >
            Export to CSV
          </Button>
        </div>

        {/* Stats Cards */}
        <StatsCards
          stats={
            statsData || {
              total_agents: 0,
              connected_agents: 0,
              disconnected_agents: 0,
              healthy_agents: 0,
              unhealthy_agents: 0,
              os_distribution: {},
            }
          }
          loading={statsLoading}
        />

        {/* Filters */}
        <Card className="mb-6">
          <Space wrap className="w-full">
            <Search
              placeholder="Search by hostname or instance ID"
              allowClear
              enterButton={<SearchOutlined />}
              style={{ width: 300 }}
              onSearch={handleSearch}
            />

            <Select
              placeholder="OS Type"
              style={{ width: 150 }}
              allowClear
              onChange={(value) => handleFilterChange('os_type', value)}
            >
              <Option value="all">All OS</Option>
              {statsData?.os_distribution &&
                Object.keys(statsData.os_distribution).map((os) => (
                  <Option key={os} value={os}>
                    {os} ({statsData.os_distribution[os]})
                  </Option>
                ))}
            </Select>

            <Select
              placeholder="Connection Status"
              style={{ width: 180 }}
              allowClear
              onChange={(value) => handleFilterChange('connected', value)}
            >
              <Option value="all">All Connections</Option>
              <Option value={true}>Connected</Option>
              <Option value={false}>Disconnected</Option>
            </Select>

            <Select
              placeholder="Health Status"
              style={{ width: 160 }}
              allowClear
              onChange={(value) => handleFilterChange('healthy', value)}
            >
              <Option value="all">All Health</Option>
              <Option value={true}>Healthy</Option>
              <Option value={false}>Unhealthy</Option>
            </Select>
          </Space>
        </Card>

        {/* Agents Table */}
        <Card>
          <Table<Agent>
            columns={columns}
            dataSource={agentsData?.agents || []}
            loading={agentsLoading}
            rowKey="id"
            pagination={{
              current: filters.page,
              pageSize: filters.size,
              total: agentsData?.total || 0,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              showTotal: (total) => `Total ${total} agents`,
            }}
            onChange={handleTableChange}
            scroll={{ x: 'max-content' }}
          />
        </Card>
      </div>
    </MainLayout>
  );
};

export default AgentsPage;
