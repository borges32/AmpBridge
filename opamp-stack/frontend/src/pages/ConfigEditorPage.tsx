import React, { useState, useEffect } from 'react';
import { Card, Button, Space, message, Modal, Descriptions, Tag, Spin } from 'antd';
import {
  SaveOutlined,
  HistoryOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import dayjs from 'dayjs';
import MainLayout from '@/components/MainLayout';
import { agentService } from '@/services/agentService';

// ============================================================================
// Config Editor Page Component
// ============================================================================
const ConfigEditorPage: React.FC = () => {
  const { instanceId } = useParams<{ instanceId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editorContent, setEditorContent] = useState<string>('');
  const [hasChanges, setHasChanges] = useState(false);

  // Fetch agent details
  const { data: agent, isLoading: agentLoading } = useQuery({
    queryKey: ['agent', instanceId],
    queryFn: () => agentService.getAgentDetail(instanceId!),
    enabled: !!instanceId,
  });

  // Fetch current config
  const { data: configYaml, isLoading: configLoading, refetch: refetchConfig } = useQuery({
    queryKey: ['agentConfig', instanceId],
    queryFn: async () => {
      const yaml = await agentService.getCurrentConfig(instanceId!);
      return yaml;
    },
    enabled: !!instanceId,
    staleTime: 0, // Consider data always stale
    gcTime: 0, // Don't keep unused data in cache
  });

  // Force refetch when component mounts or returns from another page
  useEffect(() => {
    if (instanceId) {
      refetchConfig();
    }
  }, [instanceId, refetchConfig]);

  // Sync editor content when config data changes
  useEffect(() => {
    if (configYaml) {
      setEditorContent(configYaml);
      setHasChanges(false);
    }
  }, [configYaml]);

  // Save config mutation
  const saveConfigMutation = useMutation({
    mutationFn: (yaml: string) =>
      agentService.saveConfig(instanceId!, { config: yaml }),
    onSuccess: () => {
      message.success('Configuration saved successfully!');
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['agentConfig', instanceId] });
      queryClient.invalidateQueries({ queryKey: ['agent', instanceId] });
    },
    onError: (error: any) => {
      message.error(error.detail || 'Failed to save configuration');
    },
  });

  // Handle save config
  const handleSave = () => {
    Modal.confirm({
      title: 'Save Configuration',
      content: 'Are you sure you want to save and apply this configuration to the agent?',
      okText: 'Save',
      cancelText: 'Cancel',
      onOk: () => {
        saveConfigMutation.mutate(editorContent);
      },
    });
  };

  // Handle editor change
  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined) {
      setEditorContent(value);
      setHasChanges(value !== configYaml);
    }
  };

  // Handle download config
  const handleDownload = () => {
    const blob = new Blob([editorContent], { type: 'text/yaml' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${agent?.host_name}_config.yaml`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  if (agentLoading || configLoading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center h-96">
          <Spin size="large" tip="Loading agent configuration..." />
        </div>
      </MainLayout>
    );
  }

  if (!agent) {
    return (
      <MainLayout>
        <Card>
          <div className="text-center py-8">
            <h2 className="text-xl text-gray-600">Agent not found</h2>
            <Button type="primary" onClick={() => navigate('/agents')} className="mt-4">
              Back to Agents
            </Button>
          </div>
        </Card>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="w-full">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/agents')}
            >
              Back to Agents
            </Button>
            <h1 className="text-3xl font-bold m-0">Agent Configuration</h1>
          </Space>
          <Space>
            <Button
              icon={<HistoryOutlined />}
              onClick={() => navigate(`/agents/${instanceId}/config/history`)}
            >
              View History
            </Button>
            <Button
              icon={<DownloadOutlined />}
              onClick={handleDownload}
            >
              Download
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saveConfigMutation.isPending}
              disabled={!hasChanges}
            >
              Save Configuration
            </Button>
          </Space>
        </div>

        {/* Agent Information */}
        <Card title="Agent Information" className="mb-6">
          <Descriptions column={{ xs: 1, sm: 2, md: 3 }} bordered>
            <Descriptions.Item label="Instance ID">
              <span className="font-mono text-xs">{agent.instance_id}</span>
            </Descriptions.Item>
            <Descriptions.Item label="Hostname">
              <strong>{agent.host_name}</strong>
            </Descriptions.Item>
            <Descriptions.Item label="Operating System">
              {agent.os_type} {agent.os_description}
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
            <Descriptions.Item label="Health Status">
              {agent.healthy ? (
                <Tag color="success" icon={<CheckCircleOutlined />}>
                  Healthy
                </Tag>
              ) : (
                <Tag color="error" icon={<CloseCircleOutlined />}>
                  Unhealthy
                </Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Last Seen">
              {dayjs(agent.last_seen_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            {agent.current_config && (
              <Descriptions.Item label="Current Config Version">
                Version {agent.current_config.version} (
                {dayjs(agent.current_config.created_at).format('YYYY-MM-DD HH:mm:ss')})
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>

        {/* Config Editor */}
        <Card
          title="Configuration Editor (YAML)"
          className="mb-6"
          extra={
            hasChanges && (
              <Tag color="warning">Unsaved Changes</Tag>
            )
          }
        >
          <div className="border border-gray-300 rounded">
            <Editor
              height="700px"
              defaultLanguage="yaml"
              value={editorContent}
              onChange={handleEditorChange}
              theme="vs-light"
              options={{
                minimap: { enabled: true },
                fontSize: 14,
                lineNumbers: 'on',
                rulers: [80, 120],
                wordWrap: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 2,
              }}
            />
          </div>
        </Card>

        {/* Attributes Section (if available) */}
        {agent.agent_description && (
          <Card title="Agent Attributes" className="mb-6">
            {agent.agent_description.identifying_attributes && (
              <div className="mb-4">
                <h3 className="font-semibold mb-2">Identifying Attributes</h3>
                <Descriptions column={2} bordered size="small">
                  {agent.agent_description.identifying_attributes.map((attr, index) => (
                    <Descriptions.Item key={index} label={attr.key}>
                      {JSON.stringify(attr.value)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </div>
            )}
            {agent.agent_description.non_identifying_attributes && (
              <div>
                <h3 className="font-semibold mb-2">Non-Identifying Attributes</h3>
                <Descriptions column={2} bordered size="small">
                  {agent.agent_description.non_identifying_attributes.map((attr, index) => (
                    <Descriptions.Item key={index} label={attr.key}>
                      {JSON.stringify(attr.value)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </div>
            )}
          </Card>
        )}
      </div>
    </MainLayout>
  );
};

export default ConfigEditorPage;
