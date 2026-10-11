import { useEffect, useMemo, useState } from 'react';
import { App, Badge, Button, Select, Space, Tag } from 'antd';
import { api } from '../api/client';
import type { Decision, Task } from '../api/types';
import { DecisionModal } from '../components/DecisionModal';
import { LogTerminal } from '../components/LogTerminal';
import { QuotaBadge } from '../components/QuotaBadge';
import { useTaskSocket } from '../hooks/useTaskSocket';

export function MonitorPage() {
  const { message } = App.useApp();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [taskId, setTaskId] = useState<number | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const { messages, connected, quota } = useTaskSocket(taskId);

  const loadTasks = async () => {
    try {
      const r = await api.listTasks({ sort: 'created_at' });
      setTasks(r.items);
      if (taskId == null && r.items.length > 0) {
        setTaskId(r.items[0].id);
      }
    } catch (e) {
      message.error(String(e));
    }
  };

  useEffect(() => {
    loadTasks();
    const t = setInterval(loadTasks, 4000);
    return () => clearInterval(t);
  }, []);

  const current = useMemo(() => tasks.find((t) => t.id === taskId) || null, [tasks, taskId]);
  const openDecision = current?.decisions.find((d) => d.status === 'open') || null;

  useEffect(() => {
    if (openDecision) {
      setDecision(openDecision);
      setModalOpen(true);
    }
  }, [openDecision]);

  const respond = async (answer: string, action: 'answer' | 'skip') => {
    if (!current || !decision) return;
    try {
      await api.respondDecision(current.id, decision.id, answer, action);
      message.success('已提交');
      setModalOpen(false);
      setDecision(null);
      loadTasks();
    } catch (e) {
      message.error(String(e));
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 140px)' }}>
      <Space style={{ marginBottom: 12 }} wrap>
        <Select
          style={{ minWidth: 320 }}
          placeholder="选择任务"
          value={taskId}
          onChange={setTaskId}
          options={tasks.map((t) => ({
            value: t.id,
            label: `#${t.id} ${t.content.slice(0, 30)}`,
          }))}
        />
        {current && (
          <>
            <Tag>{current.status}</Tag>
            <Tag>session: {(current.session_id || '-').slice(0, 8)}</Tag>
            <Tag>工具: {current.tool_call_count}</Tag>
            <Badge status={connected ? 'success' : 'error'} text={connected ? '已连接' : '断开'} />
            {openDecision && (
              <Button type="primary" danger onClick={() => setModalOpen(true)}>
                处理决策
              </Button>
            )}
          </>
        )}
        <QuotaBadge status={quota} onChanged={loadTasks} />
      </Space>
      <div style={{ flex: 1, minHeight: 0 }}>
        <LogTerminal messages={messages} />
      </div>
      <DecisionModal
        open={modalOpen}
        decision={decision}
        onRespond={respond}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}
