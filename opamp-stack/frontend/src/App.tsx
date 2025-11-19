import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import { AuthProvider } from '@/contexts/AuthContext';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import LoginPage from '@/pages/LoginPage';
import AgentsPage from '@/pages/AgentsPage';
import AgentHealthPage from '@/pages/AgentHealthPage';
import ConfigEditorPage from '@/pages/ConfigEditorPage';
import ConfigHistoryPage from '@/pages/ConfigHistoryPage';
import '@/styles/index.css';

// ============================================================================
// React Query Client Configuration
// ============================================================================
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

// ============================================================================
// App Component
// ============================================================================
const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        theme={{
          token: {
            colorPrimary: '#1890ff',
            borderRadius: 6,
          },
        }}
      >
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Public Route */}
              <Route path="/login" element={<LoginPage />} />

              {/* Protected Routes */}
              <Route element={<ProtectedRoute />}>
                <Route path="/agents" element={<AgentsPage />} />
                <Route path="/agents/:instanceId/health" element={<AgentHealthPage />} />
                <Route path="/agents/:instanceId/config" element={<ConfigEditorPage />} />
                <Route path="/agents/:instanceId/config/history" element={<ConfigHistoryPage />} />
              </Route>

              {/* Default Redirect */}
              <Route path="/" element={<Navigate to="/agents" replace />} />
              <Route path="*" element={<Navigate to="/agents" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ConfigProvider>
    </QueryClientProvider>
  );
};

export default App;
