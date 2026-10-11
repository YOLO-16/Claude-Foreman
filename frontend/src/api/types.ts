export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'needs_decision';
export type TaskMode = 'interactive' | 'autopilot';

export interface Decision {
  id: string;
  kind: string;
  tool_name: string | null;
  question: string;
  status: string;
  created_at: string;
}

export interface Task {
  id: number;
  content: string;
  priority: number;
  tags: string[];
  status: TaskStatus;
  mode: TaskMode;
  session_id: string | null;
  report_path: string | null;
  project_path: string;
  error: string | null;
  tool_call_count: number;
  retry_count: number;
  max_retries: number;
  timeout_seconds: number;
  tool_budget: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  decisions: Decision[];
}

export interface LogLine {
  id: number;
  task_id: number;
  log_content: string;
  log_type: string;
  timestamp: string;
}

export interface ReportSummary {
  id: number;
  content: string;
  status: TaskStatus;
  mode: TaskMode;
  session_id: string | null;
  report_path: string | null;
  started_at: string | null;
  completed_at: string | null;
  tool_call_count: number;
}

export interface WsMessage {
  type: string;
  task_id?: number;
  log_type?: string;
  content?: string;
  status?: string;
  decision_id?: string;
  question?: string;
  kind?: string;
  ts?: string;
}
