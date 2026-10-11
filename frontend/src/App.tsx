import { useState } from 'react';
import { App as AntApp, Layout, Menu } from 'antd';
import { MonitorPage } from './pages/MonitorPage';
import { ReportsPage } from './pages/ReportsPage';
import { TasksPage } from './pages/TasksPage';

const items = [
  { key: 'tasks', label: '任务管理' },
  { key: 'monitor', label: '实时监控' },
  { key: 'reports', label: '报告中心' },
];

export default function App() {
  const [page, setPage] = useState('tasks');

  return (
    <AntApp>
      <Layout style={{ minHeight: '100vh' }}>
        <Layout.Header style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{ color: '#fff', fontSize: 18, fontWeight: 600, marginRight: 32 }}>
            Claude Foreman
          </div>
          <Menu
            theme="dark"
            mode="horizontal"
            selectedKeys={[page]}
            items={items}
            onClick={(e) => setPage(e.key)}
            style={{ flex: 1, minWidth: 0 }}
          />
        </Layout.Header>
        <Layout.Content style={{ padding: 24 }}>
          {page === 'tasks' && <TasksPage />}
          {page === 'monitor' && <MonitorPage />}
          {page === 'reports' && <ReportsPage />}
        </Layout.Content>
      </Layout>
    </AntApp>
  );
}
