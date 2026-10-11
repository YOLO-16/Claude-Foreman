# 参考项目复用盘点

> 克隆位置：`.refs/`（gitignore，不入库）。原则：MIT/Apache 直接搬并保留版权；AGPL 仅借鉴思路不拷贝。

## 总览

| 仓库 | 许可 | 栈 | 结论 | 主要复用点 |
|------|------|----|------|-----------|
| Claude-Code-Agent-Monitor | MIT | React+Vite+Tailwind+WS+SQLite | **复用** | `useWebSocket.ts`、事件视图、页面骨架 |
| dnvriend/claude-code-scheduler | MIT | Python | **复制** | `services/executor.py`（spawn+stream-json 解析） |
| JCSnap/claude-code-queue | 无 LICENSE | Python | **移植逻辑** | 限流检测、队列状态机、session resume |
| vasiliyk/claude-queue | MIT | Python | **移植逻辑** | 额度检测、优先级+依赖队列 |
| hseinmoussa/claude-autopilot | MIT | Go | **移植逻辑** | 分层限流检测、重置时间解析 |
| kanna | MIT | React+Vite+xterm | **复用逻辑** | WS 客户端、report-sections、TerminalPane |
| sugyan/claude-code-webui | MIT | React | **适配概念** | stream→消息解析管线 |
| siteboon/claudecodeui | **AGPL** | React+xterm | **仅参考** | 任务板/WS context 设计（禁止拷贝） |
| hex/claude-sessions | MIT | Bash | **移植逻辑** | transcript 用量统计、原子入队 |
| cmAIdx/headless-claude-automation-template | MIT | 文档 | **仅参考** | 权限门分层设计 |
| kbwo/ccmanager | MIT | TS/Bun | **仅参考** | 会话恢复模型 |
| wxkingstar/clawrelay-wecom-server | MIT | Python | **移植逻辑** | choice_manager 决策挂起、task_registry |
| jshchnz/claude-code-scheduler | MIT | Node | **跳过** | 无 UI，cron 调度后续再说 |
| benbasha/Claude-Autopilot | MIT | VS Code | **跳过** | 绑定 IDE |
| chenhg5/cc-connect | — | Go | **跳过** | 未来 IM 插件 |

---

## 前端可搬文件

### 直接搬（MIT，逻辑层）

| 源文件 | 用途 |
|--------|------|
| `.refs/kanna/src/client/app/socket.ts` | WS 客户端：心跳、重连退避、topic 订阅、断线续传 |
| `.refs/kanna/src/shared/report-sections.ts` | 报告分节解析（纯 TS，有测试） |
| `.refs/kanna/src/shared/message-preview.ts` | 一行摘要预览（表格用） |
| `.refs/Claude-Code-Agent-Monitor/client/src/hooks/useWebSocket.ts` | WS Hook 封装 |
| `.refs/claude-code-webui/frontend/src/utils/UnifiedMessageProcessor.ts` | stream-json → UI 消息转换 |
| `.refs/claude-code-webui/frontend/src/hooks/streaming/useStreamParser.ts` | 流式解析 Hook |

### 参考改造（换 AntD 5 + 中文 + 我们的 API）

| 源文件 | 改造点 |
|--------|--------|
| `.refs/kanna/src/client/components/chat-ui/TerminalPane.tsx` | xterm 日志面板 → 我们的 LogTerminal |
| `.refs/Claude-Code-Agent-Monitor/client/src/pages/*` | 页面布局/事件视图风格 |
| `.refs/claudecodeui/src/modules/task-master/TaskBoard.tsx` | 任务板布局（**只看不拷**，AGPL） |
| `.refs/claude-code-webui/frontend/src/components/HistoryView.tsx` | 会话/任务列表交互 |

### 放弃

- `benbasha-Claude-Autopilot`：VS Code 扩展，webview 是原生 JS
- `jshchnz-claude-code-scheduler`：纯 CLI 库，无 UI
- `claudecodeui` 文件本体：AGPL 传染，禁止直接拷贝

---

## 后端可搬文件

### 优先 vendor 到 `backend/app/services/vendor/`

| # | 源文件 | 取什么 | 改什么 |
|---|--------|--------|--------|
| 1 | `.refs/claude-code-scheduler/claude_code_scheduler/services/executor.py` | `_execute_real` 命令组装（`--print --output-format stream-json --session-id`）、`_format_jsonl_output`、init 事件取 session_id | Qt 回调 → asyncio.Queue；补 Windows CLI 查找 |
| 2 | `.refs/claude-code-queue/src/claude_code_queue/claude_interface.py` | Popen 启动、flag 探测、SIGTERM→SIGKILL、`_detect_rate_limit` 双层模式 + 重置时间提取 | 改 asyncio 行流；补 `--output-format stream-json` |
| 3 | `.refs/claude-code-queue/src/claude_code_queue/queue_manager.py` | 优先级取任务、限流 park/resume、重试预算、不可重试黑名单 | 文件队列 → SQLite |
| 4 | `.refs/claude-autopilot/internal/detector/` + `matchers.default.yaml` + `timeparse/` | 分层检测（exit code→stderr→stdout）、可配模式、自然语言重置时间 | Go → Python 移植 |
| 5 | `.refs/clawrelay-wecom-server/src/core/choice_manager.py` + `task_registry.py` | 决策挂起/恢复状态、asyncio 按 key 取消 | 内存 → SQLite 持久化 |

### 设计参考（不拷代码）

- `headless-claude-automation-template/docs/reference.md`：6 层权限门（allowedTools→deny→allow→PreToolUse→审批→执行）
- `claude-sessions/lib/57-usage.sh`：从 `~/.claude/projects/**/{session}.jsonl` 做 5h/周窗口 token 归因
- `claude-queue.py` `ClaudeUsageChecker`：claude.ai usage API 轮询（cookie 认证，ToS 灰色，仅备选）

---

## CLI 参数共识（三个 headless 项目一致）

```
claude --print --verbose --output-format stream-json
       [--session-id <uuid>]      # 仅新会话
       [--resume <uuid>]          # 续会话
       [--model M] [--permission-mode P] [--allowed-tools ...]
       [--dangerously-skip-permissions]
       "<prompt>"
```

**要点：**
- `--verbose` 与 `stream-json` 在 print 模式下必须同用
- `--session-id` 仅新建会话时有效；续跑用 `--resume`
- **无 `--max-turns`**（产品文档假设错误）→ 用 timeout + tool_budget + `num_turns`
- Windows 杀进程：SIGTERM→3s→SIGKILL；避免 `os.killpg`

---

## 限流检测模式（合并后）

来自 claude-code-queue（双层）+ claude-autopilot（分层）：

```
usage limit reached | exceeded your rate limit | reached your usage limit
hit your session limit · resets | rate_limit_error | Your limit will reset at
429 | try again in N seconds | retry-after
```

重置时间：unix 时间戳 / ISO+5h / "resets 7am" / 5h 窗口估算（00/05/10/15/20 UTC），上限 24h。

---

## 合规清单

| 仓库 | 许可 | 要求 |
|------|------|------|
| Claude-Code-Agent-Monitor | MIT | 保留版权头 |
| dnvriend/claude-code-scheduler | MIT | 保留版权头 |
| vasiliyk/claude-queue | MIT | 保留版权头 |
| hseinmoussa/claude-autopilot | MIT | 保留版权头 |
| kanna | MIT | 保留版权头 |
| sugyan/claude-code-webui | MIT | 保留版权头 |
| hex/claude-sessions | MIT | 保留版权头 |
| cmAIdx/headless-claude-automation-template | MIT | 保留版权头 |
| kbwo/ccmanager | MIT | 保留版权头 |
| wxkingstar/clawrelay-wecom-server | MIT | 保留版权头 |
| siteboon/claudecodeui | **AGPL-3.0** | **禁止拷贝**，仅阅读借鉴 |
| JCSnap/claude-code-queue | 无 LICENSE 文件 | 移植思路，不整文件拷贝 |

根目录 `THIRD_PARTY_LICENSES` 汇总所有 MIT 版权声明。
