import type { LogLine, ReportSummary, Task, TaskMode } from './types';

const BASE = '/api';

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || r.statusText);
  }
  if (r.status === 204) return undefined as T;
  return r.json();
}

export const api = {
  listTasks: (params?: Record<string, string>) =>
    req<{ items: Task[]; total: number }>(
      '/tasks' + (params ? '?' + new URLSearchParams(params) : ''),
    ),
  createTask: (body: Partial<Task> & { content: string }) =>
    req<Task>('/tasks', { method: 'POST', body: JSON.stringify(body) }),
  batchImport: (body: { text: string; mode?: TaskMode; priority?: number; tags?: string[] }) =>
    req<{ created: Task[] }>('/tasks/batch', { method: 'POST', body: JSON.stringify(body) }),
  updateTask: (id: number, body: Partial<Task>) =>
    req<Task>(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteTask: (id: number) => req<void>(`/tasks/${id}`, { method: 'DELETE' }),
  startTask: (id: number) => req<{ ok: boolean }>(`/tasks/${id}/start`, { method: 'POST' }),
  stopTask: (id: number) => req<{ ok: boolean }>(`/tasks/${id}/stop`, { method: 'POST' }),
  retryTask: (id: number) => req<{ ok: boolean }>(`/tasks/${id}/retry`, { method: 'POST' }),
  getLogs: (id: number, afterId = 0) =>
    req<{ items: LogLine[] }>(`/tasks/${id}/logs?after_id=${afterId}`),
  queueStatus: () =>
    req<{ running_id: number | null; pending: number[]; is_active: boolean }>('/queue'),
  queueStart: () => req<{ ok: boolean }>('/queue/start', { method: 'POST' }),
  queueStop: () => req<{ ok: boolean }>('/queue/stop', { method: 'POST' }),
  listReports: (params?: Record<string, string>) =>
    req<{ items: ReportSummary[]; total: number }>(
      '/reports' + (params ? '?' + new URLSearchParams(params) : ''),
    ),
  getReport: (id: number) =>
    req<{ markdown: string; meta: Record<string, unknown> }>(`/reports/${id}`),
  respondDecision: (taskId: number, decisionId: string, answer: string, action = 'answer') =>
    req<{ ok: boolean }>(`/tasks/${taskId}/decisions/${decisionId}/respond`, {
      method: 'POST',
      body: JSON.stringify({ answer, action }),
    }),
};
