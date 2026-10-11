# 额度感知调度（v0.2）

Foreman 在检测到 Claude API 额度限制时会自动暂停队列、重置后恢复。覆盖范围：

- **检测**：实时扫描 stream-json 输出中的额度 marker
- **暂停**：调度器在额度被锁期间不取新任务
- **重置解析**：从错误消息提取 unix 时间戳或 "try again in N seconds"
- **手动解锁**：`POST /api/quota/unblock` 立刻恢复

## 检测模式

合并 `claude-code-queue` 双层 + `claude-autopilot` 分层检测的产物：

```
usage limit reached | exceeded your rate limit | reached your usage limit
hit your session limit | rate_limit_error | Your limit will reset at
429 | try again in N seconds | retry-after
```

定义在 `backend/app/services/stream_parser.py:RATE_LIMIT_PATTERNS`。

## 重置时间解析

`_extract_reset()` 按顺序尝试：

1. **unix 时间戳**（10–13 位数字）：秒级自动转毫秒；只接受未来 24h 内的时间戳。
2. **"try again in N seconds/minutes/hours"**：单位转换到 unix 时间。
3. 都解析不到 → 默认 +5 分钟。

```python
# stream_parser.py
m = _RESET_TS.search(text)   # 1735689600
m = _RESET_IN.search(text)   # "try again in 300 seconds"
```

## 工作流

```
[CLI 输出] → [stream_parser 实时扫描]
                    ↓ 命中
              emit rate_limit 事件
                    ↓
              executor 标记 parser.rate_limit_signal
                    ↓
              _pump 返回 → kill proc
                    ↓
              gate.block(reset_at, pattern, raw)
                    ↓
              bus.publish(0, {type:"quota", ...})
                    ↓
              任务标 failed (受害者，不阻塞)
                    ↓
              scheduler._loop 检测 gate.is_blocked() → await gate.wait()
                    ↓
              timer 到点 / 手动 unblock → scheduler 恢复取新任务
```

## API

| 方法 | 路径 | 用途 |
|------|------|------|
| `GET` | `/api/quota` | 状态：`{blocked, reset_at, remaining_sec, last_signal}` |
| `POST` | `/api/quota/unblock` | 立即解锁（不等待 timer） |

WS 事件（订阅 task_id=0 或任意 task_id 都会收到）：

```json
{
  "type": "quota",
  "blocked": true,
  "reset_at": 1735689600.0,
  "remaining_sec": 287.4,
  "pattern": "usage limit reached",
  "ts": "2026-10-11T15:00:00Z"
}
```

## 行为约束

- **受害者不背锅**：触发 rate limit 的任务标 `failed`（error 含重置时间），用户可单点 retry。
- **不降级**：已有更晚的 reset_at 时，新信号不会覆盖。
- **幂等解锁**：多次 `unblock()` 安全。
- **跨任务持久**：进程内单例 gate（重启后清空）。下一迭代：持久化到 SQLite 跨重启恢复。

## E2E 测试

`scripts/fake_claude.py` 支持：

```bash
# 跑 1 步后发 rate limit，标记 "try again in 60 seconds"
python scripts/fake_claude.py -p "any" --quota-after 1 --quota-resets-in 60
```

`backend/tests/test_executor_quota.py::test_rate_limit_blocks_gate` 验证：
- 任务标 failed 且 error 含 `usage limit reached`
- `gate.status()["blocked"]` 为 True
- `reset_at` 已设置
- 调用 `gate.unblock()` 后状态清除

## 设计取舍

- **不持久化**：gate 状态仅进程内。Claude 重启后若仍撞额度，会再次触发；这是可接受的（数据规模小）。
- **不并发**：单 gate，单 worker。并发跑多 Claude 实例是下一迭代。
- **不精读窗口**：不解析 5h/周配额窗（参考 `claude-sessions` 的 `57-usage.sh`），仅响应"撞墙了"信号。
