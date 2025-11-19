import React, { useState } from 'react';
import { Card, Button, Table, Tag, Space, Modal, message, Spin } from 'antd';
import { ArrowLeftOutlined, EyeOutlined, RollbackOutlined, DownloadOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import Editor from '@monaco-editor/react';
import dayjs from 'dayjs';
import MainLayout from '@/components/MainLayout';
import { agentService } from '@/services/agentService';
import { ConfigVersion } from '@/types';

// ============================================================================
// Config History Page Component
// ============================================================================
const ConfigHistoryPage: React.FC = () => {
  const { instanceId } = useParams<{ instanceId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedVersion, setSelectedVersion] = useState<ConfigVersion | null>(null);
  const [viewModalVisible, setViewModalVisible] = useState(false);

  // Fetch agent details
  const { data: agent } = useQuery({
    queryKey: ['agent', instanceId],
    queryFn: () => agentService.getAgentDetail(instanceId!),
    enabled: !!instanceId,
  });

  // Fetch config history
  const { data: history, isLoading } = useQuery({
    queryKey: ['configHistory', instanceId],
    queryFn: () => agentService.getConfigHistory(instanceId!),
    enabled: !!instanceId,
  });

  // Restore config mutation
  const restoreConfigMutation = useMutation({
    mutationFn: (version: number) =>
      agentService.restoreConfig(instanceId!, version),
    onSuccess: () => {
      message.success('Configuration restored successfully!');
      queryClient.invalidateQueries({ queryKey: ['agentConfig', instanceId] });
      queryClient.invalidateQueries({ queryKey: ['configHistory', instanceId] });
      queryClient.invalidateQueries({ queryKey: ['agent', instanceId] });
      // Force refetch before navigating to ensure fresh data
      queryClient.refetchQueries({ queryKey: ['agentConfig', instanceId] });
      navigate(`/agents/${instanceId}/config`);
    },
    onError: (error: any) => {
      message.error(error.detail || 'Failed to restore configuration');
    },
  });

  // Handle back to config
  const handleBackToConfig = () => {
    // Invalidate queries to ensure fresh data when returning
    queryClient.invalidateQueries({ queryKey: ['agentConfig', instanceId] });
    navigate(`/agents/${instanceId}/config`);
  };

  // Handle view version
  const handleViewVersion = (record: ConfigVersion) => {
    setSelectedVersion(record);
    setViewModalVisible(true);
  };

  // Handle download version
  const handleDownloadVersion = (version: ConfigVersion) => {
    try {
      // Create a blob from the config content
      const blob = new Blob([version.effective_config], { type: 'text/yaml' });
      const url = window.URL.createObjectURL(blob);
      
      // Create a temporary link and trigger download
      const link = document.createElement('a');
      link.href = url;
      link.download = `agent_${instanceId}_config_v${version.version}.yaml`;
      document.body.appendChild(link);
      link.click();
      
      // Clean up
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      message.success(`Configuration v${version.version} downloaded successfully`);
    } catch (error) {
      message.error('Failed to download configuration');
      console.error('Download error:', error);
    }
  };

  // Handle restore version
  const handleRestoreVersion = (version: ConfigVersion) => {
    Modal.confirm({
      title: 'Restore Configuration',
      content: (
        <div>
          <p>Are you sure you want to restore this configuration version?</p>
          <p className="mt-2">
            <strong>Version:</strong> {version.version}
          </p>
          <p>
            <strong>Created:</strong> {dayjs(version.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </p>
          <p>
            <strong>Source:</strong> {version.source}
          </p>
          <p className="mt-2 text-orange-600">
            This will create a new version with the content from version {version.version} and
            send it to the agent.
          </p>
        </div>
      ),
      okText: 'Restore',
      cancelText: 'Cancel',
      okButtonProps: { danger: true },
      onOk: () => {
        restoreConfigMutation.mutate(version.version);
      },
    });
  };

  // Table columns
  const columns: ColumnsType<ConfigVersion> = [
    {
      title: 'Version',
      dataIndex: 'version',
      key: 'version',
      width: 100,
      render: (version) => (
        <div>
          <strong className="text-lg">v{version}</strong>
          {agent?.current_config?.version === version && (
            <Tag color="blue" className="ml-2">
              Current
            </Tag>
          )}
        </div>
      ),
    },
    {
      title: 'Config Hash',
      dataIndex: 'config_hash',
      key: 'config_hash',
      width: 300,
      ellipsis: true,
      render: (hash) => <span className="font-mono text-xs">{hash}</span>,
    },
    {
      title: 'Source',
      dataIndex: 'source',
      key: 'source',
      width: 150,
      render: (source) => {
        const colors: Record<string, string> = {
          MANUAL_UPDATE: 'green',
          SYNC_JOB: 'blue',
          RESTORE: 'orange',
        };
        return <Tag color={colors[source] || 'default'}>{source}</Tag>;
      },
    },
    {
      title: 'Created By',
      dataIndex: 'updated_by_user_id',
      key: 'updated_by_user_id',
      width: 150,
      render: (userId) => userId ? `User ${userId}` : <span className="text-gray-400">System</span>,
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 200,
      render: (createdAt) => dayjs(createdAt).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
      defaultSortOrder: 'descend',
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
            icon={<EyeOutlined />}
            onClick={() => handleViewVersion(record)}
          >
            View
          </Button>
          <Button
            type="text"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => handleDownloadVersion(record)}
          >
            Download
          </Button>
          {agent?.current_config?.version !== record.version && (
            <Button
              type="link"
              size="small"
              icon={<RollbackOutlined />}
              onClick={() => handleRestoreVersion(record)}
              loading={restoreConfigMutation.isPending}
            >
              Restore
            </Button>
          )}
        </Space>
      ),
    },
  ];

  if (isLoading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center h-96">
          <Spin size="large" tip="Loading configuration history..." />
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="w-full">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold">Configuration History</h1>
            {agent && (
              <p className="text-gray-600 mt-2">
                Agent: <strong>{agent.host_name}</strong> ({agent.instance_id})
              </p>
            )}
          </div>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={handleBackToConfig}
          >
            Back to Config
          </Button>
        </div>

        {/* History Table */}
        <Card>
          <Table<ConfigVersion>
            columns={columns}
            dataSource={history || []}
            rowKey="id"
            pagination={{
              defaultPageSize: 10,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              showTotal: (total) => `Total ${total} versions`,
            }}
            scroll={{ x: 'max-content' }}
          />
        </Card>

        {/* View Version Modal */}
        <Modal
          title={`Configuration Version ${selectedVersion?.version}`}
          open={viewModalVisible}
          onCancel={() => setViewModalVisible(false)}
          width="90%"
          style={{ maxWidth: 1400 }}
          footer={[
            <Button key="close" onClick={() => setViewModalVisible(false)}>
              Close
            </Button>,
            selectedVersion && (
              <Button
                key="download"
                icon={<DownloadOutlined />}
                onClick={() => {
                  handleDownloadVersion(selectedVersion);
                }}
              >
                Download
              </Button>
            ),
            selectedVersion &&
              agent?.current_config?.version !== selectedVersion.version && (
                <Button
                  key="restore"
                  type="primary"
                  danger
                  icon={<RollbackOutlined />}
                  onClick={() => {
                    setViewModalVisible(false);
                    handleRestoreVersion(selectedVersion);
                  }}
                  loading={restoreConfigMutation.isPending}
                >
                  Restore This Version
                </Button>
              ),
          ]}
        >
          {selectedVersion && (
            <div>
              <div className="mb-4 p-4 bg-gray-50 rounded">
                <Space direction="vertical" size="small">
                  <div>
                    <strong>Version:</strong> {selectedVersion.version}
                  </div>
                  <div>
                    <strong>Created:</strong>{' '}
                    {dayjs(selectedVersion.created_at).format('YYYY-MM-DD HH:mm:ss')}
                  </div>
                  <div>
                    <strong>Source:</strong>{' '}
                    <Tag color="blue">{selectedVersion.source}</Tag>
                  </div>
                  {selectedVersion.updated_by_user_id && (
                    <div>
                      <strong>Created By:</strong> User {selectedVersion.updated_by_user_id}
                    </div>
                  )}
                  <div>
                    <strong>Config Hash:</strong>{' '}
                    <span className="font-mono text-xs">{selectedVersion.config_hash}</span>
                  </div>
                </Space>
              </div>

              <div className="border border-gray-300 rounded">
                <Editor
                  height="600px"
                  defaultLanguage="yaml"
                  value={selectedVersion.effective_config}
                  theme="vs-light"
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                  }}
                />
              </div>
            </div>
          )}
        </Modal>
      </div>
    </MainLayout>
  );
};

export default ConfigHistoryPage;
