import { useEffect, useRef, useState } from 'react';
import type { WsMessage } from '../api/types';

const COLORS: Record<string, string> = {
  stdout: '#d4d4d4',
  stderr: '#f48771',
  tool_call: '#9cdcfe',
  system: '#c586c0',
  result: '#b5cea8',
  decision: '#dcdcaa',
};

export function LogTerminal({ messages }: { messages: WsMessage[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    if (autoScroll && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight;
    }
  }, [messages, autoScroll]);

  const shown = filter
    ? messages.filter((m) => (m.content || '').toLowerCase().includes(filter.toLowerCase()))
    : messages;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <input
          placeholder="过滤日志"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{ flex: 1, padding: '4px 8px', background: '#1e1e1e', color: '#ccc', border: '1px solid #444', borderRadius: 4 }}
        />
        <label style={{ color: '#aaa', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
          <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} />
          自动滚动
        </label>
      </div>
      <div
        ref={ref}
        style={{
          flex: 1,
          overflow: 'auto',
          background: '#0d1117',
          border: '1px solid #30363d',
          borderRadius: 4,
          padding: 8,
          fontFamily: 'Consolas, monospace',
          fontSize: 12,
          lineHeight: 1.5,
        }}
      >
        {shown.map((m, i) => (
          <div key={i} style={{ color: COLORS[m.log_type || m.type] || '#d4d4d4', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            <span style={{ color: '#666' }}>[{m.ts?.slice(11, 19) || ''}] </span>
            {m.content || m.question || m.status || m.type}
          </div>
        ))}
        {shown.length === 0 && <div style={{ color: '#666' }}>暂无日志</div>}
      </div>
    </div>
  );
}
