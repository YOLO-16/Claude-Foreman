import { useState } from 'react';
import { Button, Input, Modal } from 'antd';
import type { Decision } from '../api/types';

interface Props {
  open: boolean;
  decision: Decision | null;
  onRespond: (answer: string, action: 'answer' | 'skip') => void;
  onClose: () => void;
}

export function DecisionModal({ open, decision, onRespond, onClose }: Props) {
  const [answer, setAnswer] = useState('');

  return (
    <Modal
      open={open}
      title="需要人工决策"
      onCancel={onClose}
      footer={[
        <Button key="skip" onClick={() => onRespond('', 'skip')}>
          跳过
        </Button>,
        <Button key="ok" type="primary" onClick={() => onRespond(answer, 'answer')}>
          回答
        </Button>,
      ]}
    >
      <p style={{ whiteSpace: 'pre-wrap' }}>{decision?.question || '等待决策…'}</p>
      {decision?.kind === 'ask_user' && (
        <Input.TextArea
          rows={3}
          placeholder="输入你的决策"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
        />
      )}
    </Modal>
  );
}
