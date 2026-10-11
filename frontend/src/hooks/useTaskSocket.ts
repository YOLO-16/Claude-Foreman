import { useCallback, useEffect, useRef, useState } from 'react';
import type { QuotaStatus, WsMessage } from '../api/types';

export function useTaskSocket(taskId: number | null) {
  const [messages, setMessages] = useState<WsMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const [quota, setQuota] = useState<QuotaStatus | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);

  const connect = useCallback(() => {
    if (taskId == null) return;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws/tasks/${taskId}/logs`);
    wsRef.current = ws;
    ws.onopen = () => {
      setConnected(true);
      retryRef.current = 0;
    };
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as WsMessage;
        if (msg.type === 'ping') return;
        if (msg.type === 'quota') {
          setQuota({
            blocked: msg.blocked ?? false,
            reset_at: msg.reset_at ?? null,
            remaining_sec: msg.remaining_sec ?? 0,
            last_signal: msg.pattern
              ? {
                  pattern: msg.pattern,
                  reset_at: msg.reset_at ?? null,
                  raw: msg.content ?? '',
                  ts: msg.ts ? new Date(msg.ts).getTime() : Date.now(),
                }
              : null,
          });
          return;
        }
        setMessages((prev) => [...prev.slice(-500), msg]);
      } catch {
        /* ignore */
      }
    };
    ws.onclose = () => {
      setConnected(false);
      const delay = Math.min(1000 * 2 ** retryRef.current, 15000);
      retryRef.current += 1;
      setTimeout(connect, delay);
    };
    ws.onerror = () => ws.close();
  }, [taskId]);

  useEffect(() => {
    setMessages([]);
    connect();
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  return { messages, connected, quota, clear: () => setMessages([]) };
}
