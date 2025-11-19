import React, { ReactNode } from 'react';
import { Layout as AntLayout } from 'antd';
import Header from './Header';

const { Content } = AntLayout;

// ============================================================================
// Main Layout Component
// ============================================================================
interface MainLayoutProps {
  children: ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  return (
    <AntLayout className="min-h-screen">
      <Header />
      <Content className="p-6 bg-gray-50">{children}</Content>
    </AntLayout>
  );
};

export default MainLayout;
