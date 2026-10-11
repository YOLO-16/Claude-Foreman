import { useCallback, useEffect, useState } from 'react';
import { App, Button, Drawer, Input, Space, Table, Tag } from 'antd';
import ReactMarkdown from 'react-markdown';
import { api } from '../api/client';
import type { ReportSummary } from '../api/types';

const STATUS_COLOR: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
  needs_decision: 'warning',
};

export function ReportsPage() {
  const { message } = App.useApp();
  const [items, setItems] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [open, setOpen] = useState(false);
  const [markdown, setMarkdown] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (q) params.q = q;
      if (sessionId) params.session_id = sessionId;
      const r = await api.listReports(params);
      setItems(r.items);
    } catch (e) {
      message.error(String(e));
    } finally {
      setLoading(false);
    }
  }, [q, sessionId, message]);

  useEffect(() => {
    load();
  }, [load]);

  const view = async (id: number) => {
    try {
      const r = await api.getReport(id);
      setMarkdown(r.markdown);
      setOpen(true);
    } catch (e) {
      message.error(String(e));
    }
  };

  const exportMd = async (id: number) => {
    try {
      const r = await api.getReport(id);
      const blob = new Blob([r.markdown], { type: 'text/markdown' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `task_${id}.md`;
      a.click();
    } catch (e) {
      message.error(String(e));
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          placeholder="搜索任务内容"
          allowClear
          onSearch={setQ}
          style={{ width: 240 }}
        />
        <Input.Search
          placeholder="Session ID"
          allowClear
          onSearch={setSessionId}
          style={{ width: 240 }}
        />
        <Button onClick={load}>刷新</Button>
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '内容', dataIndex: 'content', ellipsis: true },
          {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (s: string) => <Tag color={STATUS_COLOR[s]}>{s}</Tag>,
          },
          {
            title: 'Session',
            dataIndex: 'session_id',
            width: 140,
            render: (s: string | null) => (s ? s.slice(0, 8) : '-'),
          },
          { title: '工具调用', dataIndex: 'tool_call_count', width: 90 },
          {
            title: '完成时间',
            dataIndex: 'completed_at',
            width: 170,
            render: (s: string | null) => (s ? s.slice(0, 19).replace('T', ' ') : '-'),
          },
          {
            title: '操作',
            width: 140,
            render: (_, t) => (
              <Space>
                <Button size="small" onClick={() => view(t.id)}>
                  查看
                </Button>
                <Button size="small" onClick={() => exportMd(t.id)}>
                  导出
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <Drawer
        open={open}
        title="任务报告"
        width={720}
        onClose={() => setOpen(false)}
      >
        <div style={{ padding: 16, overflow: 'auto', background: '#fff', borderRadius: 4 }}>
          <ReactMarkdown>{markdown}</ReactMarkdown>
        </div>
      </Drawer>
    </div>
  );
}
