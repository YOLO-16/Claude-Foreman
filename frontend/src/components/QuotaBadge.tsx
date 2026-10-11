import { useEffect, useState } from 'react';
import { App, Badge, Button, Space, Tooltip } from 'antd';
import { api } from '../api/client';
import type { QuotaStatus } from '../api/types';

interface Props {
  status: QuotaStatus | null;
  onChanged?: () => void;
}

export function QuotaBadge({ status, onChanged }: Props) {
  const { message } = App.useApp();
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!status?.blocked) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [status?.blocked]);

  const unblock = async () => {
    try {
      await api.quotaUnblock();
      message.success('已手动解锁');
      onChanged?.();
    } catch (e) {
      message.error(String(e));
    }
  };

  if (!status?.blocked) {
    return (
      <Tooltip title="API 额度正常">
        <Badge status="success" text="额度 OK" />
      </Tooltip>
    );
  }

  const remaining = Math.max(0, Math.ceil(((status.reset_at ?? now) - now) / 1000));
  const mins = Math.floor(remaining / 60);
  const secs = remaining % 60;
  const tip = `重置时间: ${status.reset_at ? new Date(status.reset_at * 1000).toLocaleString() : '-'}\n模式: ${status.last_signal?.pattern ?? '-'}`;

  return (
    <Space size={4}>
      <Tooltip title={tip}>
        <Badge status="error" text={`额度受限 ${mins}:${String(secs).padStart(2, '0')}`} />
      </Tooltip>
      <Button size="small" onClick={unblock}>
        解锁
      </Button>
    </Space>
  );
}
