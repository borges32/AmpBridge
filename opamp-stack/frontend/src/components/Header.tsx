import React from 'react';
import { Layout, Avatar, Dropdown, Button } from 'antd';
import { UserOutlined, LogoutOutlined, TeamOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import type { MenuProps } from 'antd';

const { Header: AntHeader } = Layout;

// ============================================================================
// Header Component
// ============================================================================
const Header: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'user',
      label: user?.username || 'User',
      icon: <UserOutlined />,
      disabled: true,
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      label: 'Logout',
      icon: <LogoutOutlined />,
      onClick: logout,
    },
  ];

  return (
    <AntHeader className="flex items-center justify-between bg-white shadow-sm px-6">
      <div className="flex items-center gap-4">
        <img 
          src="/logo.png" 
          alt="OpAMP Logo" 
          className="h-10 w-10 object-contain"
        />
        <h1 className="text-xl font-semibold m-0">OpAMP Dashboard</h1>
      </div>

      <div className="flex items-center gap-4">
        <Button type="text" onClick={() => navigate('/agents')}>
          Agents
        </Button>
        
        <Button 
          type="text" 
          icon={<TeamOutlined />}
          onClick={() => navigate('/users')}
        >
          Users
        </Button>

        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Avatar icon={<UserOutlined />} className="cursor-pointer" />
        </Dropdown>
      </div>
    </AntHeader>
  );
};

export default Header;
