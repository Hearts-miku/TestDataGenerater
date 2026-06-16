# 测试目录总览

```
tests/
├── phase1/          Week 1-3：MVP 核心 — DDL解析、Faker规则、约束解决器、DuckDB
├── phase2/          Week 4-5：导出格式 — SQL INSERT、CSV、JSON、静态文件服务
├── phase3/          Week 6-7：图数据库 — Cypher解析、Kuzu客户端、图生成API
├── phase4/          Week 8-9：AI管道 — LangGraph节点、LLM配置、WebSocket流式
├── phase5/          Week 10：完善 — 多方言、分块批量、Excel导出
└── e2e/             Week 11：端到端验收 — 完整用户流程（API + 浏览器）
```

## 测试分层

| 层次 | 目录 | 工具 | 外部依赖 | 运行速度 |
|------|------|------|---------|---------|
| 单元 | `phaseN/unit/` | pytest | 无（mock/内存） | 快（< 5s） |
| 集成 | `phaseN/integration/` | pytest + httpx | uvicorn 运行中 | 中（< 60s） |
| E2E API | `e2e/api/` | pytest + httpx | uvicorn 运行中 | 慢（< 300s） |
| E2E 浏览器 | `e2e/browser/` | Playwright | 服务 + 浏览器 | 慢（< 600s） |

## 快速运行

```powershell
# 1. 仅单元测试（无需启动服务，最快）
uv run pytest tests/phase1/unit tests/phase2/unit tests/phase3/unit tests/phase4/unit tests/phase5/unit -v

# 2. 某阶段全部测试
uv run pytest tests/phase1 -v

# 3. 所有非E2E测试（需启动服务）
.\scripts\start.ps1
uv run pytest tests/ --ignore=tests/e2e -v

# 4. 跳过慢速测试（百万行等）
uv run pytest tests/ --ignore=tests/e2e -v -m "not slow"

# 5. 完整E2E验收
uv run pytest tests/e2e/api -v
pnpm exec playwright test --project=chromium

# 6. 查看覆盖率
uv run pytest tests/ --ignore=tests/e2e --cov=app --cov-report=html
```

## 阶段门控

每个阶段开始开发前，确认上一阶段测试全绿：

```powershell
uv run pytest tests/phase1 -v   # Phase 2 开始前
uv run pytest tests/phase2 -v   # Phase 3 开始前
uv run pytest tests/phase3 -v   # Phase 4 开始前
uv run pytest tests/phase4 -v   # Phase 5 开始前
uv run pytest tests/phase5 -v   # E2E 验收前
uv run pytest tests/e2e/api -v  # 上线前
```

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `DATAFORGE_URL` | `http://127.0.0.1:8000` | 被测服务地址 |
