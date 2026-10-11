import { useCallback, useEffect, useState } from 'react';
import { App, Button, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Table, Tag } from 'antd';
import { api } from '../api/client';
import type { Task, TaskMode } from '../api/types';

const STATUS_COLOR: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
  needs_decision: 'warning',
};

const STATUS_LABEL: Record<string, string> = {
  pending: '待执行',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  needs_decision: '待决策',
};

export function TasksPage() {
  const { message } = App.useApp();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [batchOpen, setBatchOpen] = useState(false);
  const [editing, setEditing] = useState<Task | null>(null);
  const [form] = Form.useForm();
  const [batchForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.listTasks({ sort: 'priority' });
      setTasks(r.items);
    } catch (e) {
      message.error(String(e));
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  const submit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await api.updateTask(editing.id, values);
        message.success('已更新');
      } else {
        await api.createTask(values);
        message.success('已创建');
      }
      setModalOpen(false);
      form.resetFields();
      setEditing(null);
      load();
    } catch (e) {
      message.error(String(e));
    }
  };

  const batchSubmit = async () => {
    const values = await batchForm.validateFields();
    try {
      const r = await api.batchImport(values);
      message.success(`已导入 ${r.created.length} 个任务`);
      setBatchOpen(false);
      batchForm.resetFields();
      load();
    } catch (e) {
      message.error(String(e));
    }
  };

  const action = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      message.success(ok);
      load();
    } catch (e) {
      message.error(String(e));
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          onClick={() => {
            setEditing(null);
            form.resetFields();
            setModalOpen(true);
          }}
        >
          新建任务
        </Button>
        <Button onClick={() => setBatchOpen(true)}>批量导入</Button>
        <Button onClick={load}>刷新</Button>
        <Button onClick={() => action(() => api.queueStart(), '队列已启动')}>启动队列</Button>
        <Button onClick={() => action(() => api.queueStop(), '队列已停止')}>停止队列</Button>
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={tasks}
        pagination={{ pageSize: 20 }}
        columns={[
          {
            title: 'ID',
            dataIndex: 'id',
            width: 60,
          },
          {
            title: '内容',
            dataIndex: 'content',
            ellipsis: true,
          },
          {
            title: '优先级',
            dataIndex: 'priority',
            width: 80,
            sorter: (a, b) => a.priority - b.priority,
          },
          {
            title: '标签',
            dataIndex: 'tags',
            width: 150,
            render: (tags: string[]) => tags.map((t) => <Tag key={t}>{t}</Tag>),
          },
          {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (s: string) => <Tag color={STATUS_COLOR[s]}>{STATUS_LABEL[s]}</Tag>,
          },
          {
            title: '模式',
            dataIndex: 'mode',
            width: 100,
            render: (m: TaskMode) => (m === 'autopilot' ? '无人值守' : '有人值守'),
          },
          {
            title: '工具调用',
            dataIndex: 'tool_call_count',
            width: 90,
          },
          {
            title: '操作',
            width: 220,
            render: (_, t) => (
              <Space size={4}>
                {t.status === 'pending' && (
                  <Button size="small" onClick={() => action(() => api.startTask(t.id), '已启动')}>
                    启动
                  </Button>
                )}
                {t.status === 'running' && (
                  <Button size="small" danger onClick={() => action(() => api.stopTask(t.id), '已停止')}>
                    停止
                  </Button>
                )}
                {t.status === 'failed' && (
                  <Button size="small" onClick={() => action(() => api.retryTask(t.id), '已重试')}>
                    重试
                  </Button>
                )}
                <Button
                  size="small"
                  onClick={() => {
                    setEditing(t);
                    form.setFieldsValue(t);
                    setModalOpen(true);
                  }}
                >
                  编辑
                </Button>
                <Popconfirm title="确认删除？" onConfirm={() => action(() => api.deleteTask(t.id), '已删除')}>
                  <Button size="small" danger>
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        open={modalOpen}
        title={editing ? '编辑任务' : '新建任务'}
        onOk={submit}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="content" label="任务描述" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="priority" label="优先级 (1-9)" initialValue={5}>
            <InputNumber min={1} max={9} />
          </Form.Item>
          <Form.Item name="tags" label="标签" initialValue={[]}>
            <Select mode="tags" placeholder="回车添加标签" />
          </Form.Item>
          <Form.Item name="mode" label="模式" initialValue="autopilot">
            <Select
              options={[
                { value: 'autopilot', label: '无人值守' },
                { value: 'interactive', label: '有人值守' },
              ]}
            />
          </Form.Item>
          <Form.Item name="project_path" label="项目路径" initialValue="." >
            <Input />
          </Form.Item>
        </Form>
      </Modal>

      <Modal open={batchOpen} title="批量导入" onOk={batchSubmit} onCancel={() => setBatchOpen(false)}>
        <Form form={batchForm} layout="vertical">
          <Form.Item
            name="text"
            label="每行一个任务"
            rules={[{ required: true }]}
          >
            <Input.TextArea rows={8} placeholder="补全 utils 单测&#10;重构登录模块&#10;更新 README" />
          </Form.Item>
          <Form.Item name="priority" label="优先级" initialValue={5}>
            <InputNumber min={1} max={9} />
          </Form.Item>
          <Form.Item name="mode" label="模式" initialValue="autopilot">
            <Select
              options={[
                { value: 'autopilot', label: '无人值守' },
                { value: 'interactive', label: '有人值守' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
