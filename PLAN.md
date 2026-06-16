# DataForge 实施计划

> 文档版本：v1.1 | 日期：2026-06-16  
> 状态跟踪：`[ ]` 待办 `[x]` 完成 `[-]` 进行中

---

## 总览

| 阶段 | 主题 | 周期 | 核心交付物 | 阶段门控测试 |
|------|------|------|-----------|------------|
| Phase 1 | MVP 核心生成 | Week 1–3 | DDL解析 + Faker生成 + DuckDB + 基础UI | `tests/phase1/` 全绿 |
| Phase 2 | 可视化与导出 | Week 4–5 | ER图 + 数据预览 + CSV/JSON/SQL导出 | `tests/phase2/` 全绿 |
| Phase 3 | 图数据库支持 | Week 6–7 | Cypher解析 + Kuzu + 图谱UI + Cypher导出 | `tests/phase3/` 全绿 |
| Phase 4 | LangGraph AI | Week 8–9 | AI管道 + LLM配置UI + WS流式进度 | `tests/phase4/` 全绿 |
| Phase 5 | 完善与打磨 | Week 10 | 多方言 + Excel + 百万行批量 + 会话管理 | `tests/phase5/` 全绿 |
| 验收 | 端到端验证 | Week 11 | 全场景E2E通过 | `tests/e2e/` 全绿 |

**最终验收标准**：`tests/e2e/` 下所有 API 测试（pytest）与浏览器测试（Playwright）全部通过。

---

## 开发规范

### 版本控制规则（必须遵守）

> **每完成一个阶段的实施与测试后，必须执行 git commit + git push，再开始下一阶段。**

每个阶段的验收标准代码块末尾均包含此步骤，具体命令：

```powershell
# 阶段测试全绿后执行（将 N 替换为实际阶段号）
git add .
git commit -m "phase N: complete - all tests pass"
git push
```

**原则**：
- 任何阶段的 push 前，该阶段的所有 pytest 测试必须处于全绿状态
- commit message 格式统一：`phase N: <简短描述>`
- 每次 push 是一个可回退的检查点，出现问题可以 `git revert` 到上一阶段

---

## Phase 1 — MVP 核心生成（Week 1–3）

### 目标
用户能在本地启动服务，粘贴 MySQL / PostgreSQL DDL，生成关系数据并写入 DuckDB，通过 SQL Explorer 查询，导出 SQL INSERT 文件。

### 任务清单

#### 后端
- [ ] **P1-B1** 初始化 FastAPI 项目（`uv init`，`pyproject.toml` 配置依赖）
- [ ] **P1-B2** 实现 DDL 解析器（`sqlglot`，支持 MySQL + PostgreSQL）
  - 提取：表、列、类型、PK、FK、UNIQUE、NOT NULL、DEFAULT、ENUM
  - 输出：`RelationalSchemaModel`（Pydantic）
- [ ] **P1-B3** 实现拓扑排序（解决多表 FK 生成顺序）
- [ ] **P1-B4** 实现 Faker 规则引擎（字段名语义推断 + 类型感知）
- [ ] **P1-B5** 实现约束解决器（PK 池、FK 采样、UNIQUE 去重、NOT NULL 填充）
- [ ] **P1-B6** 实现 DuckDB 客户端（建表、批量写入、SQL 查询直通）
- [ ] **P1-B7** 实现 API 端点：
  - `POST /api/parse`（DDL → SchemaModel + 建 DuckDB 表结构）
  - `POST /api/generate`（同步生成 + 写入 DuckDB）
  - `POST /api/db/sql`（只读 SQL 查询，拒绝 DDL/DML 写操作）
  - `GET  /api/db/tables`（表列表 + 列定义）
  - `GET  /api/health`（存活检查）
- [ ] **P1-B8** FastAPI 挂载前端静态文件（`frontend/dist/`）
- [ ] **P1-B9** 编写启动脚本 `scripts/start.ps1` / `scripts/start-dev.ps1` / `Makefile`

#### 前端
- [ ] **P1-F1** 初始化 React + TypeScript + Vite 项目（`pnpm create vite`）
- [ ] **P1-F2** 集成 Ant Design + Tailwind CSS
- [ ] **P1-F3** 实现 Schema Editor（Monaco，SQL 语法高亮）
- [ ] **P1-F4** 实现 SQL Explorer（Monaco SQL + 结果表格，调用 `/api/db/sql`）
- [ ] **P1-F5** Vite 开发模式代理（`/api → :8000`）
- [ ] **P1-F6** Zustand store：schema / generationResult / dbQuery

### 验收标准
```powershell
pytest tests/phase1/ -v                     # 全部通过
curl http://127.0.0.1:8000/api/health       # 200 OK
# 手动验证：粘贴 ecommerce_schema.sql → 生成 → SQL Explorer 执行 JOIN 成功

# ✅ 测试全绿后提交
git add .
git commit -m "phase 1: complete - MVP core generation, all tests pass"
git push
```

### 关联测试
| 测试文件 | 类型 | 覆盖任务 |
|---------|------|---------|
| `tests/phase1/unit/test_ddl_parser.py` | 单元 | P1-B2 |
| `tests/phase1/unit/test_schema_model.py` | 单元 | P1-B2, P1-B3 |
| `tests/phase1/unit/test_faker_rules.py` | 单元 | P1-B4 |
| `tests/phase1/unit/test_constraint_solver.py` | 单元 | P1-B3, P1-B5 |
| `tests/phase1/integration/test_duckdb_client.py` | 集成 | P1-B6 |
| `tests/phase1/integration/test_parse_generate_api.py` | 集成 | P1-B7 |

---

## Phase 2 — 可视化与导出（Week 4–5）

### 目标
ER 图自动渲染 DuckDB Schema；数据预览表格支持分页；Config Panel 配置行数；支持 CSV / JSON / SQL INSERT 导出；启动脚本完善。

### 任务清单

#### 后端
- [ ] **P2-B1** 实现 SQL INSERT 导出器（事务包裹、批量 VALUES）
- [ ] **P2-B2** 实现 CSV 导出器（多表 ZIP 打包，UTF-8 BOM）
- [ ] **P2-B3** 实现 JSON 导出器（按表分组，扁平数组）
- [ ] **P2-B4** 实现 `GET /api/db/er-schema`（返回表、列、FK 元数据供前端渲染）
- [ ] **P2-B5** 实现 `POST /api/export`（format 参数路由不同导出器，流式 FileResponse）

#### 前端
- [ ] **P2-F1** 实现 ER 图组件（React Flow + ELK 自动布局，节点显示列名，边显示 FK）
- [ ] **P2-F2** 实现数据预览表格（TanStack Virtual，分页 50 行/页，列筛选）
- [ ] **P2-F3** 实现 Config Panel（每表行数输入，全局重置按钮）
- [ ] **P2-F4** 实现 Export Panel（格式选择 + 下载按钮）
- [ ] **P2-F5** 生成进度 Toast / Progress Bar

### 验收标准
```powershell
pytest tests/phase2/ -v
# 手动：ecommerce DDL → ER图显示5个表节点 + 3条FK边
# 手动：生成 → 导出 CSV → 解压验证 order_items.csv 行数

# ✅ 测试全绿后提交
git add .
git commit -m "phase 2: complete - visualization and export, all tests pass"
git push
```

### 关联测试
| 测试文件 | 类型 | 覆盖任务 |
|---------|------|---------|
| `tests/phase2/unit/test_export_sql.py` | 单元 | P2-B1 |
| `tests/phase2/unit/test_export_csv.py` | 单元 | P2-B2 |
| `tests/phase2/unit/test_export_json.py` | 单元 | P2-B3 |
| `tests/phase2/integration/test_export_api.py` | 集成 | P2-B5 |
| `tests/phase2/integration/test_static_serve.py` | 集成 | P1-B8（生产模式验证）|

---

## Phase 3 — 图数据库支持（Week 6–7）

### 目标
用户能解析 Cypher Schema，生成图节点和关系并写入 Kuzu；知识图谱可视化；Cypher Explorer 可查询并将结果渲染为局部图；支持 Cypher CREATE 导出。

### 任务清单

#### 后端
- [ ] **P3-B1** 实现 Cypher Schema 解析器（lark-parser，支持节点/关系/约束定义）
  - 输出：`GraphSchemaModel`（节点标签、属性、关系类型、基数约束）
- [ ] **P3-B2** 实现图拓扑排序（节点先于关系，处理自引用关系）
- [ ] **P3-B3** 实现 Kuzu 客户端（建图、批量写入节点/关系、Cypher 查询直通）
- [ ] **P3-B4** 扩展 `POST /api/parse` 支持 `type=cypher`
- [ ] **P3-B5** 扩展 `POST /api/generate` 支持图模式（节点→关系顺序写入 Kuzu）
- [ ] **P3-B6** 实现图 API 端点：
  - `POST /api/graph/cypher`（只读 Cypher 查询）
  - `GET  /api/graph/schema`（节点标签、关系类型、属性元数据）
  - `GET  /api/graph/stats`（节点/关系数量统计）
- [ ] **P3-B7** 实现 Cypher CREATE 导出器

#### 前端
- [ ] **P3-F1** Schema 类型切换（DDL ↔ Cypher，Monaco 语言随之切换）
- [ ] **P3-F2** 知识图谱组件（React Flow + D3 force layout，节点气泡 + 关系箭头）
- [ ] **P3-F3** Cypher Explorer（Monaco Cypher + 查询结果表格 + "以图查看"按钮）
- [ ] **P3-F4** 查询结果图渲染（从节点/关系 JSON 构建 React Flow 临时图）

### 验收标准
```powershell
pytest tests/phase3/ -v
# 手动：social_network.cypher → 图谱显示 User/Post/Tag 三类节点
# 手动：Cypher Explorer 执行 MATCH (u:User)-[:AUTHORED]->(p) RETURN u,p LIMIT 5 → 渲染局部图

# ✅ 测试全绿后提交
git add .
git commit -m "phase 3: complete - graph database support, all tests pass"
git push
```

### 关联测试
| 测试文件 | 类型 | 覆盖任务 |
|---------|------|---------|
| `tests/phase3/unit/test_cypher_parser.py` | 单元 | P3-B1 |
| `tests/phase3/unit/test_graph_constraint_solver.py` | 单元 | P3-B2 |
| `tests/phase3/integration/test_kuzu_client.py` | 集成 | P3-B3 |
| `tests/phase3/integration/test_graph_generate_api.py` | 集成 | P3-B4, P3-B5, P3-B6 |

---

## Phase 4 — LangGraph AI 管道（Week 8–9）

### 目标
LangGraph 四节点工作流上线；UI 提供 LLM 配置面板（base_url / api_key / model）；验证 DeepSeek / Ollama 等平台兼容；LLM 不可达时自动降级；生成进度通过 WebSocket 流式推送。

### 任务清单

#### 后端
- [ ] **P4-B1** 实现 LangGraph 工作流（`ai/pipeline.py`）
  - 节点一：`SchemaContextNode`（分析业务域）
  - 节点二：`RuleInferenceNode`（每字段推断生成规则）
  - 节点三：`BatchGenerationNode`（LLM + Faker 混合批量生成）
  - 节点四：`ValidationNode`（约束校验 + 携带错误上下文重试）
- [ ] **P4-B2** 实现 `LLMConfig`（`base_url` / `api_key` / `model` 三参数，ChatOpenAI 实例化）
- [ ] **P4-B3** 实现 AI 降级逻辑（LLM 调用失败 → 回退 Faker 引擎，`ai_used=False`）
- [ ] **P4-B4** 扩展 `POST /api/generate`：增加 `ai_enabled` 和 `llm_config` 字段
- [ ] **P4-B5** 实现 WebSocket 端点 `WS /ws/generate`（流式推送进度百分比 + 预览行）
- [ ] **P4-B6** 实现 AI 辅助端点（可选，供前端调试管道状态）：
  - `POST /api/ai/analyze-schema`
  - `POST /api/ai/infer-rules`
  - `POST /api/ai/validate-batch`

#### 前端
- [ ] **P4-F1** AI 配置面板（base_url 输入 + api_key 输入 + model 下拉 + 测试连接按钮）
- [ ] **P4-F2** WebSocket 客户端（订阅 `/ws/generate`，更新进度条 + 实时预览前 100 行）
- [ ] **P4-F3** 生成结果增加 `ai_used` 标志展示

### 验收标准
```powershell
pytest tests/phase4/ -v
# 手动（有LLM）：配置 DeepSeek base_url → 生成 → 确认 ai_used=true，数据语义合理
# 手动（无LLM）：配置无效 base_url → 生成 → 确认 ai_used=false，数据正常生成
# 手动：观察 WebSocket 进度条从 0% 到 100%

# ✅ 测试全绿后提交
git add .
git commit -m "phase 4: complete - LangGraph AI pipeline, all tests pass"
git push
```

### 关联测试
| 测试文件 | 类型 | 覆盖任务 |
|---------|------|---------|
| `tests/phase4/unit/test_langgraph_nodes.py` | 单元（mock LLM）| P4-B1 |
| `tests/phase4/unit/test_llm_config.py` | 单元 | P4-B2, P4-B3 |
| `tests/phase4/unit/test_prompts.py` | 单元 | P4-B1 |
| `tests/phase4/integration/test_ai_generate_api.py` | 集成 | P4-B4, P4-B6 |
| `tests/phase4/integration/test_ws_streaming.py` | 集成 | P4-B5 |

---

## Phase 5 — 完善与打磨（Week 10）

### 目标
多方言 DDL 支持完善；Excel 导出；百万行批量生成（分块写入 DuckDB）；用户自定义规则持久化。

### 任务清单

- [ ] **P5-B1** 扩展 DDL 解析方言支持（SQL Server、Oracle）
- [ ] **P5-B2** 实现 Excel 导出器（openpyxl，每表一个 Sheet，首行冻结列头）
- [ ] **P5-B3** 实现批量分块生成（chunk_size=10000，循环写入，内存安全）
- [ ] **P5-B4** 用户自定义规则持久化（JSON 文件 `data/user_rules.json`，跨会话保存）
- [ ] **P5-B5** 多工作区会话管理（schema_id 隔离，DuckDB 按 session 建库）

### 验收标准
```powershell
pytest tests/phase5/ -v
# 手动：SQL Server DDL → 解析 → 生成 → 验证结果
# 手动：请求生成 100万行 → 内存不超过 500MB → 写入完成
# 手动：导出 Excel → 打开确认每表一 Sheet

# ✅ 测试全绿后提交
git add .
git commit -m "phase 5: complete - polish and bulk generation, all tests pass"
git push
```

### 关联测试
| 测试文件 | 类型 | 覆盖任务 |
|---------|------|---------|
| `tests/phase5/unit/test_multi_dialect_parser.py` | 单元 | P5-B1 |
| `tests/phase5/unit/test_batch_chunker.py` | 单元 | P5-B3 |
| `tests/phase5/integration/test_excel_export.py` | 集成 | P5-B2 |
| `tests/phase5/integration/test_bulk_generate_api.py` | 集成 | P5-B3 |

---

## 测试分层策略

```
┌─────────────────────────────────────────────────────────┐
│  E2E（tests/e2e/）                                       │
│  运行时机：阶段全部完成后 + 上线前                       │
│  工具：pytest + httpx（API）/ Playwright（浏览器）       │
├─────────────────────────────────────────────────────────┤
│  集成测试（tests/phaseN/integration/）                   │
│  运行时机：每个阶段开发完成时                            │
│  工具：pytest，需要运行中的 uvicorn / 本地文件系统        │
├─────────────────────────────────────────────────────────┤
│  单元测试（tests/phaseN/unit/）                          │
│  运行时机：每次代码提交前                                │
│  工具：pytest，无外部依赖，使用 mock / 内存对象          │
└─────────────────────────────────────────────────────────┘
```

### 一键运行

```powershell
# 单元测试（最快，无需启动服务）
uv run pytest tests/phase1/unit tests/phase2/unit tests/phase3/unit tests/phase4/unit tests/phase5/unit -v

# 某阶段全部测试
uv run pytest tests/phase1/ -v

# 所有非E2E测试
uv run pytest tests/ --ignore=tests/e2e -v

# 完整E2E（需先启动服务）
.\scripts\start.ps1
uv run pytest tests/e2e/api -v
pnpm exec playwright test --project=chromium
```

---

## 依赖关系

```
Phase 1 (DDL + DuckDB + 基础API)
    │
    ▼
Phase 2 (导出 + ER图)      Phase 3 (Cypher + Kuzu + 图谱)
    │                              │
    └──────────────┬───────────────┘
                   ▼
            Phase 4 (LangGraph AI)
                   │
                   ▼
            Phase 5 (多方言 + Excel + 批量)
                   │
                   ▼
            E2E 验收测试
```

Phase 3 与 Phase 2 可并行开发（后端无依赖，前端 UI 组件独立）。

---

## 风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| sqlglot 对某些 DDL 语法解析不准确 | 中 | 中 | 增加边缘用例到 fixtures；必要时手写 AST 补丁 |
| lark Cypher 语法覆盖不全 | 高 | 中 | Phase 3 早期验证常见 Cypher 模式；准备降级为正则预处理 |
| LangGraph API 调用延迟高 | 中 | 低 | AI 管道设置 30s 超时；降级机制保证不阻塞生成 |
| DuckDB / Kuzu 版本 API 变动 | 低 | 高 | 锁定依赖版本（`uv.lock`）；Phase 1 早期验证 |
| 百万行生成内存溢出 | 中 | 中 | Phase 5 分块策略 + 压测用例提前暴露问题 |

---

## 里程碑

| 里程碑 | 日期（预估）| 验证命令 |
|--------|-----------|---------|
| M1：后端 MVP 可运行 | Week 2 末 | `curl :8000/api/health` |
| M2：前后端联通 | Week 3 末 | 浏览器打开 `localhost:8000` 可生成数据 |
| M3：ER 图 + 导出可用 | Week 5 末 | `pytest tests/phase2/ -v` |
| M4：图数据库可用 | Week 7 末 | `pytest tests/phase3/ -v` |
| M5：AI 管道可用 | Week 9 末 | `pytest tests/phase4/ -v` |
| M6：全功能完成 | Week 10 末 | `pytest tests/phase5/ -v` |
| **M7：E2E 验收通过** | **Week 11 末** | **`pytest tests/e2e/ -v` + Playwright** |

---

*计划版本：v1.1 | 下次评审：Phase 1 完成后*
