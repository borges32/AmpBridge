import React, { useState } from 'react';
import { 
  Table, 
  Button, 
  Space, 
  Modal, 
  Form, 
  Input, 
  Switch, 
  message, 
  Popconfirm,
  Tag,
  Card
} from 'antd';
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined, 
  UserOutlined,
  ArrowLeftOutlined 
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import { 
  listUsers, 
  createUser, 
  updateUser, 
  deleteUser 
} from '@/services/userService';
import type { 
  UserDetail, 
  CreateUserRequest, 
  UpdateUserRequest 
} from '@/types';

// ============================================================================
// Users Management Page Component
// ============================================================================

const UsersPage: React.FC = () => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserDetail | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // ============================================================================
  // Queries
  // ============================================================================

  const { data: usersData, isLoading } = useQuery({
    queryKey: ['users', currentPage, pageSize],
    queryFn: () => listUsers(currentPage, pageSize),
  });

  // ============================================================================
  // Mutations
  // ============================================================================

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      message.success('User created successfully');
      queryClient.invalidateQueries({ queryKey: ['users'] });
      handleCloseModal();
    },
    onError: (error: any) => {
      message.error(error.detail || 'Failed to create user');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateUserRequest }) =>
      updateUser(id, data),
    onSuccess: () => {
      message.success('User updated successfully');
      queryClient.invalidateQueries({ queryKey: ['users'] });
      handleCloseModal();
    },
    onError: (error: any) => {
      message.error(error.detail || 'Failed to update user');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      message.success('User deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error: any) => {
      message.error(error.detail || 'Failed to delete user');
    },
  });

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleOpenModal = (user?: UserDetail) => {
    if (user) {
      setEditingUser(user);
      form.setFieldsValue({
        name: user.name,
        email: user.email,
        login: user.login,
        is_active: user.is_active,
      });
    } else {
      setEditingUser(null);
      form.resetFields();
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingUser(null);
    form.resetFields();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingUser) {
        // Update existing user
        const updateData: UpdateUserRequest = {
          name: values.name,
          email: values.email,
          is_active: values.is_active,
        };
        updateMutation.mutate({ id: editingUser.id, data: updateData });
      } else {
        // Create new user
        const createData: CreateUserRequest = {
          name: values.name,
          email: values.email,
          login: values.login,
          password: values.password,
        };
        createMutation.mutate(createData);
      }
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const handleDelete = (userId: number) => {
    deleteMutation.mutate(userId);
  };

  // ============================================================================
  // Table Columns
  // ============================================================================

  const columns: ColumnsType<UserDetail> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => (
        <Space>
          <UserOutlined />
          {text}
        </Space>
      ),
    },
    {
      title: 'Login',
      dataIndex: 'login',
      key: 'login',
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? 'Active' : 'Inactive'}
        </Tag>
      ),
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleOpenModal(record)}
          >
            Edit
          </Button>
          <Popconfirm
            title="Delete user"
            description="Are you sure you want to delete this user?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
            >
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="p-6">
      <Card>
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-4">
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/agents')}
            >
              Back to Agents
            </Button>
            <div>
              <h1 className="text-2xl font-semibold m-0">User Management</h1>
              <p className="text-gray-500 mt-1">
                Manage system users and their permissions
              </p>
            </div>
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => handleOpenModal()}
          >
            New User
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={usersData?.users || []}
          loading={isLoading}
          rowKey="id"
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: usersData?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} users`,
            onChange: (page, size) => {
              setCurrentPage(page);
              setPageSize(size);
            },
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingUser ? 'Edit User' : 'Create New User'}
        open={isModalOpen}
        onOk={handleSubmit}
        onCancel={handleCloseModal}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          className="mt-4"
        >
          <Form.Item
            name="name"
            label="Full Name"
            rules={[
              { required: true, message: 'Please enter the full name' },
              { min: 3, message: 'Name must be at least 3 characters' },
            ]}
          >
            <Input placeholder="John Doe" />
          </Form.Item>

          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: 'Please enter the email' },
              { type: 'email', message: 'Please enter a valid email' },
            ]}
          >
            <Input placeholder="john.doe@example.com" />
          </Form.Item>

          {!editingUser && (
            <>
              <Form.Item
                name="login"
                label="Login"
                rules={[
                  { required: true, message: 'Please enter the login' },
                  { min: 3, message: 'Login must be at least 3 characters' },
                  { pattern: /^[a-zA-Z0-9_]+$/, message: 'Login can only contain letters, numbers and underscore' },
                ]}
              >
                <Input placeholder="johndoe" />
              </Form.Item>

              <Form.Item
                name="password"
                label="Password"
                rules={[
                  { required: true, message: 'Please enter the password' },
                  { min: 6, message: 'Password must be at least 6 characters' },
                ]}
              >
                <Input.Password placeholder="••••••••" />
              </Form.Item>
            </>
          )}

          {editingUser && (
            <Form.Item
              name="is_active"
              label="Active"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default UsersPage;
