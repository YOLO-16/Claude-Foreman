# Claude Foreman

面向 Claude Code 重度用户的任务调度控制台：批量任务排队、物理会话隔离、有人/无人值守双模式执行。

## 快速开始

```bash
# 后端
cd backend
pip install -e ".[dev]"
python -m uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173

## 测试与检查

```bash
npm run test   # vitest + pytest
npm run lint   # eslint + ruff
```

## 目录

- `backend/` FastAPI + SQLModel + SQLite
- `frontend/` React 18 + Ant Design 5 + Vite
- `data/` 运行时数据库与报告（gitignore）
- `.refs/` 参考项目克隆（gitignore，见 `docs/REUSE.md`）
- `scripts/fake_claude.py` 测试替身

## 安全提示

无人值守模式使用 `--dangerously-skip-permissions`，仅在可信/可丢弃的项目目录下启用。
