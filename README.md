# DataForge — DDL & Cypher 智能测试数据生成平台

> 根据 SQL DDL 与 Neo4j Cypher Schema 自动生成高质量、关联一致的测试数据，内嵌关系型与图数据库供即时查询，并提供全程可视化交互界面。

---

## 目录

1. [项目概述](#1-项目概述)
2. [核心功能](#2-核心功能)
3. [技术栈](#3-技术栈)
4. [部署模式](#4-部署模式)
5. [高阶架构设计](#5-高阶架构设计)
6. [可扩展性设计](#6-可扩展性设计)
7. [模块详细设计](#7-模块详细设计)
8. [数据流说明](#8-数据流说明)
9. [目录结构](#9-目录结构)
10. [开发路线图](#10-开发路线图)

---

## 1. 项目概述

DataForge 是面向开发者和 QA 工程师的 **可视化测试数据生成与探索平台**。用户只需粘贴 SQL DDL 或 Cypher Schema，系统即可：

- 自动解析表结构 / 图模型（含约束与关系）
- 通过 **LangGraph AI 管道** 生成上下文语义一致的批量数据
- 将数据写入内嵌的 **DuckDB（关系型）** 和 **Kuzu（图）** 数据库
- 提供 **SQL / Cypher 即时查询界面** 与可视化 ER 图 / 知识图谱
- 导出多种格式（SQL INSERT、CSV、JSON、Cypher CREATE、Excel）

### 适用场景

| 场景 | 说明 |
|------|------|
| 后端开发 | 快速填充开发库，验证业务逻辑 |
| QA 测试 | 生成边界值、多样性覆盖的测试集 |
| 图数据库 | 为 Neo4j 图模型生成真实关系网络 |
| 演示数据 | 生成自然语义的展示数据 |
| 数据探索 | 在内嵌 DB 中实时查询 / 关联分析生成结果 |

---

## 2. 核心功能

### 2.1 Schema 解析
- SQL DDL 多方言：MySQL、PostgreSQL、SQL Server、Oracle、SQLite
- Cypher Schema：节点标签、关系类型、属性与约束
- 提取：表/节点、列/属性、主键、外键、唯一约束、枚举值

### 2.2 LangGraph AI 增强数据生成
- **LangGraph 工作流**：多节点有状态 AI 管道（分析 → 推断 → 生成 → 校验 → 重试）
- **OpenAI 兼容协议**：通过 `langchain-openai.ChatOpenAI` 统一接入，支持配置任意第三方平台（OpenAI / Azure OpenAI / DeepSeek / Ollama / OpenRouter 等）
- **规则驱动降级**：AI 不可用时自动降级为 Faker 语义规则引擎
- **约束遵守**：FK 引用完整性、UNIQUE 去重、NOT NULL、拓扑顺序生成

### 2.3 内嵌数据库与即时查询
- **DuckDB（内嵌关系型）**：生成的关系数据直接写入 DuckDB，前端 SQL 编辑器可即时查询、JOIN 分析
- **Kuzu（内嵌图数据库）**：生成的图数据写入 Kuzu，前端 Cypher 编辑器可即时查询，结果渲染为交互式网络图
- 支持查看表 / 节点列表、字段详情、关系拓扑

### 2.4 可视化交互
| 视图 | 内容 |
|------|------|
| ER 图 | 基于 DuckDB Schema 实时渲染，支持拖拽布局 |
| 知识图谱 | 基于 Kuzu Schema + 查询结果的交互式网络图 |
| SQL Explorer | Monaco SQL 编辑器 + DuckDB 查询结果表格 |
| Cypher Explorer | Monaco Cypher 编辑器 + Kuzu 查询结果 + 局部图渲染 |
| 数据预览 | 分页表格，支持行内编辑与列筛选 |
| Config Panel | 每表/节点独立配置生成行数、AI 规则、字段覆盖 |

### 2.5 导出
| 格式 | 描述 |
|------|------|
| SQL INSERT | 带事务的批量插入脚本 |
| CSV | 每表一个文件，ZIP 打包 |
| JSON | 嵌套结构或扁平数组 |
| Cypher CREATE | 可直接执行的 Neo4j 建图语句 |
| Excel (.xlsx) | 多 Sheet，每表一页 |

---

## 3. 技术栈

### 前端

| 分类 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | React | 18.x | UI 组件树 |
| 语言 | TypeScript | 5.x | 类型安全 |
| 构建 | Vite | 5.x | 快速 HMR 开发 |
| UI 组件 | Ant Design | 5.x | 通用组件库 |
| 代码编辑器 | Monaco Editor | 0.50.x | SQL / Cypher / DDL 语法高亮与补全 |
| 图可视化 | React Flow | 11.x | ER 图 / 知识图谱 / 查询结果图 |
| 布局算法 | ELK.js | 0.9.x | ER 图自动布局 |
| D3 力导向 | D3-force | 3.x | 图数据库结果力导向布局 |
| 状态管理 | Zustand | 4.x | 全局状态 |
| 数据请求 | TanStack Query | 5.x | 请求缓存与异步状态 |
| 样式 | Tailwind CSS | 3.x | 工具类样式 |
| 虚拟滚动 | TanStack Virtual | 3.x | 大数据集表格渲染 |

### 后端 — 核心层

| 分类 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | FastAPI | 0.111.x | REST API + WebSocket |
| 语言 | Python | 3.12+ | 核心逻辑 |
| DDL 解析 | sqlglot | 25.x | 多方言 SQL → AST |
| Cypher 解析 | lark-parser（自定义语法） | 1.x | openCypher 子集解析 |
| 数据生成 | Faker | 24.x | 规则驱动基础生成 |
| 数据校验 | Pydantic | 2.x | 内部 Schema 模型 |
| 异步 | asyncio / uvicorn | — | 非阻塞高并发 |
| 导出 | openpyxl / pandas | — | Excel & CSV 处理 |

### 后端 — AI 层（LangGraph）

| 分类 | 技术 | 版本 | 用途 |
|------|------|------|------|
| AI 编排 | **LangGraph** | 0.2.x | 有状态多节点 AI 工作流 |
| LLM 接入 | **langchain-openai** | 0.2.x | OpenAI 兼容协议统一入口 |
| 链抽象 | langchain-core | 0.3.x | Prompt / Chain / Memory |
| 模型配置 | 可配置 `base_url` + `api_key` | — | 见下方兼容列表 |

**支持的 LLM 平台（OpenAI 兼容协议）**：

| 平台 | base_url 示例 | 说明 |
|------|--------------|------|
| OpenAI | `https://api.openai.com/v1` | 官方 GPT-4o / o3 |
| Azure OpenAI | `https://{resource}.openai.azure.com/` | 企业部署 |
| DeepSeek | `https://api.deepseek.com/v1` | 高性价比推理 |
| OpenRouter | `https://openrouter.ai/api/v1` | 多模型路由 |
| Ollama（本地） | `http://localhost:11434/v1` | 离线/私有化部署 |
| LM Studio（本地） | `http://localhost:1234/v1` | 本地模型 UI |
| 任意兼容平台 | 自定义 | 只需 OpenAI 标准协议 |

### 后端 — 内嵌数据库层

| 分类 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 关系型 DB | **DuckDB** | 1.x | 内嵌 OLAP SQL 数据库，存储生成的关系数据 |
| 图 DB | **Kuzu** | 0.6.x | 内嵌图数据库，Cypher 兼容，存储生成的图数据 |
| 关系 DB 驱动 | duckdb-python | — | DuckDB Python API |
| 图 DB 驱动 | kuzu | — | Kuzu Python API |

> **选型理由**
> - **DuckDB**：零服务、文件级部署、完整 SQL + 列式 OLAP 性能，Python 原生 API，支持直接导出 Parquet / CSV
> - **Kuzu**：零服务嵌入式图 DB，原生 openCypher 支持，Python 绑定，读写性能优于 SQLite 图扩展

### 基础设施

| 分类 | 技术 | 用途 |
|------|------|------|
| 包管理 | pnpm（前端）/ uv（后端） | 依赖管理 |
| 后台进程 | uvicorn（后端）/ Vite（前端开发） | 本地后台运行 |
| 启动脚本 | PowerShell `.ps1` + `Makefile` | 一键启停，跨平台 |
| 代码规范 | ESLint + Prettier / Ruff | 统一代码风格 |
| 测试 | Vitest（前端）/ pytest（后端） | 单元与集成测试 |

---

## 4. 部署模式

无需 Docker，两种模式均为纯本地后台进程。

### 4.1 生产模式（单进程·单端口）

```
前端构建产物静态托管在 FastAPI 内部，整个应用只有一个进程、一个端口。

┌──────────────────────────────────────────┐
│  uvicorn  (127.0.0.1:8000)               │
│                                           │
│  /api/*   → FastAPI 路由处理             │
│  /ws/*    → WebSocket 端点               │
│  /*       → 静态文件 (frontend/dist/)    │
│                                           │
│  DuckDB   → data/dataforge.duckdb        │
│  Kuzu     → data/dataforge_graph/        │
└──────────────────────────────────────────┘
```

启动步骤：
```powershell
# 1. 安装依赖
cd frontend && pnpm install && pnpm build   # 构建前端到 frontend/dist/
cd backend  && uv sync                      # 安装 Python 依赖

# 2. 后台启动（Windows PowerShell）
Start-Process -NoNewWindow -FilePath "uv" `
  -ArgumentList "run uvicorn app.main:app --host 127.0.0.1 --port 8000" `
  -WorkingDirectory ".\backend" `
  -RedirectStandardOutput "logs\backend.log" `
  -RedirectStandardError  "logs\backend.err"

# 或一键脚本
.\scripts\start.ps1
```

### 4.2 开发模式（双进程·热重载）

```
frontend (Vite dev server :5173)  ←── HMR，/api/* 代理到 :8000
backend  (uvicorn --reload :8000) ←── 代码改动自动重启
```

```powershell
# 一键启动开发环境
.\scripts\start-dev.ps1

# 手动分别启动
# Terminal 1
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend && pnpm dev   # vite.config.ts 已配置 proxy → :8000
```

### 4.3 脚本说明

| 脚本 | 平台 | 功能 |
|------|------|------|
| `scripts/start.ps1` | Windows | 生产模式后台启动 |
| `scripts/stop.ps1` | Windows | 停止所有后台进程 |
| `scripts/start-dev.ps1` | Windows | 开发模式双进程启动 |
| `Makefile` | Linux/macOS | `make start` / `make dev` / `make stop` |

> **DuckDB 和 Kuzu 均为嵌入式**，随 uvicorn 进程一同启动，数据持久化在本地文件，无需单独启动任何数据库服务。

---

## 5. 高阶架构设计

```
╔══════════════════════════════════════════════════════════════════════╗
║                       BROWSER — React SPA                             ║
╚══════════════════════════════════════════════════════════════════════╝
                                │ REST / WebSocket
╔═══════════════════════════════╧══════════════════════════════════════╗
║              API Layer — FastAPI Routes（薄路由层）                   ║
║   parse.py · generate.py · export.py · db_sql.py · ws/generate.py   ║
╚═══════════════════════════════╤══════════════════════════════════════╝
                                │ Depends() 注入 Service
╔═══════════════════════════════╧══════════════════════════════════════╗
║                    Service Layer（业务编排层）                         ║
║  ┌─────────────┐ ┌───────────────┐ ┌─────────────┐ ┌─────────────┐ ║
║  │ParseService │ │GenerateService│ │ExportService│ │QueryService │ ║
╚══╪═════════════╪═╪═══════════════╪═╪═════════════╪═╪═════════════╪═╝
   │             │ │               │ │             │ │             │
   ▼             ▼ ▼               ▼ ▼             ▼ ▼             ▼
╔══════════════════════════════════════════════════════════════════════╗
║           Interface / Protocol Layer（PEP 544 协议抽象层）            ║
║                                                                       ║
║  ISchemaParser     IGenerationStrategy    IRelationalStore            ║
║  parse(src)→Model  generate(schema,n)     execute_sql() / bulk_insert ║
║                    → list[dict]           get_er_schema()             ║
║                                                                       ║
║  IExporter                                IGraphStore                 ║
║  export(data)→bytes                       execute_cypher()            ║
║                                           bulk_insert_nodes/rels()    ║
╚══════════════════════════════════════════════════════════════════════╝
   │ 注册          │ 注册               │ 注册         │ 注册
╔══╧══════════════╧═══════════════════╧═════════════╧═════════════════╗
║                  Plugin Registries（可插拔实现注册）                   ║
║                                                                       ║
║  ParserRegistry             StrategyFactory                           ║
║  "ddl"    → DDLParser       "rule" → RuleBasedStrategy (Faker)       ║
║  "cypher" → CypherParser    "ai"   → AIEnhancedStrategy (LangGraph)  ║
║                                         │                            ║
║  ExporterRegistry           StoreFactory│   LangGraph Pipeline        ║
║  "sql"    → SQLExporter     "relational"│→  SchemaContextNode         ║
║  "csv"    → CSVExporter     DuckDBStore │   RuleInferenceNode         ║
║  "json"   → JSONExporter    "graph"     │   BatchGenNode              ║
║  "xlsx"   → ExcelExporter   → KuzuStore │   ValidationNode            ║
║  "cypher" → CypherExporter              │   ChatOpenAI(base_url, ...) ║
╚═════════════════════════════════════════╧═══════════════════════════╝
                                │ GenerateService 发布事件
╔═══════════════════════════════╧══════════════════════════════════════╗
║                   Event Bus（进程内异步事件总线）                      ║
║                                                                       ║
║  DataBatchGenerated ──► DuckDBWriteHandler  （写入关系型数据）        ║
║  DataBatchGenerated ──► KuzuWriteHandler    （写入图数据）            ║
║  GenerationProgress ──► WSProgressHandler   （WebSocket 推送进度）    ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 架构分层说明

| 层次 | 职责 | 耦合原则 |
|------|------|---------|
| **API 路由层** | HTTP/WS 协议处理，参数校验，依赖注入 | 仅依赖 Service，不直接调用 Parser/DB |
| **Service 层** | 业务流程编排，事务边界，错误聚合 | 仅通过 Protocol 调用下层，不依赖具体实现类 |
| **Protocol 层** | PEP 544 Protocol 定义（无实现代码） | 零依赖，所有跨层调用的契约 |
| **Plugin Registry 层** | 实现类注册与工厂创建，运行时策略选择 | 依赖 Protocol + 实现，是唯一知道具体类的地方 |
| **Event Bus 层** | 进程内异步事件分发，解耦生成与存储/推送 | 生成器只发布事件，不知道订阅者存在 |
| **LangGraph 层** | 四节点有状态工作流（可选 AI 增强） | 实现 IGenerationStrategy，可被 RuleBasedStrategy 替换 |
| **内嵌 DB 层** | DuckDB / Kuzu 实现 IRelationalStore / IGraphStore | 实现 Protocol，上层无感知具体数据库 |
| **导出层** | 各格式 Exporter 实现 IExporter | 注册于 ExporterRegistry，新格式零路由修改 |

---

## 6. 可扩展性设计

### 扩展点一：新增 Schema 解析器

实现 `ISchemaParser` 并向 `ParserRegistry` 注册，无需修改任何路由或 Service 代码：

```python
# app/core/avro_parser.py（新增文件）
class AvroParser:
    def parse(self, source: str, **options) -> SchemaModel:
        ...

# app/core/__init__.py（添加一行）
ParserRegistry.register("avro", AvroParser)
```

之后 `POST /api/parse` 传入 `{"type": "avro"}` 即自动路由至新解析器。

### 扩展点二：新增导出格式

```python
# app/exporter/parquet_exp.py（新增文件）
class ParquetExporter:
    def export(self, data: DataSet, **options) -> bytes:
        ...

ExporterRegistry.register("parquet", ParquetExporter)
```

`POST /api/export` 传入 `{"format": "parquet"}` 即可用，无需修改路由。

### 扩展点三：切换数据库后端

`IRelationalStore` 将 DB 操作抽象为协议，替换 DuckDB 只需实现新类并修改 `StoreFactory` 映射，上层 Service 无感知：

```python
class IRelationalStore(Protocol):
    def execute_sql(self, sql: str, params=None) -> list[dict]: ...
    def bulk_insert(self, table: str, rows: list[dict]) -> int: ...
    def get_er_schema(self) -> ERSchema: ...
```

### 扩展点四：新增生成策略

```python
class StatisticalSamplingStrategy:
    """从真实数据集采样，而非随机生成"""
    def generate(self, schema: SchemaModel, count: int, **opts) -> list[dict]:
        ...

StrategyFactory.register("statistical", StatisticalSamplingStrategy)
```

通过 `POST /api/generate` 的 `strategy: "statistical"` 参数启用，无需改动 Service 层。

### 事件总线解耦

生成引擎只发布事件，不直接调用 DuckDB/Kuzu/WebSocket，订阅者完全独立：

```python
# 生成器（不知道 DuckDB 或 WebSocket 存在）
await event_bus.publish(DataBatchGenerated(table="users", rows=batch))

# 各订阅者独立注册，互不干扰
@event_bus.subscribe(DataBatchGenerated)
async def write_relational(event: DataBatchGenerated):
    await duckdb_store.bulk_insert(event.table, event.rows)

@event_bus.subscribe(DataBatchGenerated)
async def write_graph(event: DataBatchGenerated):
    if event.table in graph_schema.node_labels:
        await kuzu_store.bulk_insert_nodes(event.table, event.rows)
```

---

## 7. 模块详细设计

### 7.1 DDL 解析模块

```
输入: CREATE TABLE 语句（多方言）
      ↓
sqlglot.parse(dialect=...) → AST
      ↓
TableExtractor
  ├── 表名、列名、数据类型、长度/精度
  ├── PRIMARY KEY、UNIQUE、NOT NULL、DEFAULT
  ├── FOREIGN KEY → 被引用表/列
  ├── CHECK 约束 / ENUM 枚举值
  └── INDEX 定义
      ↓
RelationalSchemaModel（Pydantic）
  └── 写入 DuckDB（CREATE TABLE）
```

**支持方言**：MySQL · PostgreSQL · SQL Server · Oracle · SQLite · BigQuery

### 7.2 Cypher 解析模块

解析目标语法（openCypher Schema 子集）：
```cypher
CREATE CONSTRAINT ON (u:User) ASSERT u.id IS UNIQUE;
CREATE (n:User {id: INT, name: STRING, email: STRING});
// (:User)-[:FOLLOWS {since: DATE}]->(:User)
// (:User)-[:PURCHASED]->(:Order)
// (:Order)-[:CONTAINS {quantity: INT}]->(:Product)
```

提取：节点标签 + 属性类型 + 关系类型 + 关系属性 + 基数约束  
→ `GraphSchemaModel（Pydantic）` → 写入 Kuzu（`CREATE NODE TABLE` / `CREATE REL TABLE`）

### 7.3 LangGraph AI 管道

```
GraphState {
  schema_model: SchemaModel
  domain_context: str          # LLM 推断的业务领域
  field_rules: dict[str, Rule] # 每字段生成规则
  generated_batches: list      # 已生成批次
  validation_errors: list      # 约束违规
  retry_count: int
}

节点定义：

┌─────────────────────────────────────────────────────────┐
│ SchemaContextNode                                         │
│  Prompt: 给定 Schema，分析业务领域与字段语义              │
│  输出: domain_context（如 "电商平台用户订单系统"）        │
└──────────────────────────┬──────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ RuleInferenceNode                                         │
│  Prompt: 基于域上下文，为每字段推断最佳 Faker 规则/模式  │
│  输出: field_rules（如 email → faker.email(domain=co)） │
└──────────────────────────┬──────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ BatchGenerationNode                                       │
│  Prompt: 按规则批量生成 N 行，保证上下文一致性           │
│  LLM 输出 JSON → 与 Faker 规则引擎混合（高开销字段用LLM）│
└──────────────────────────┬──────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ ValidationNode                                            │
│  检查 FK 引用 / UNIQUE / NOT NULL / 类型合法性           │
│  失败 → 回到 BatchGenerationNode（携带错误上下文重试）   │
│  成功 → END                                              │
└─────────────────────────────────────────────────────────┘
```

**LLM 接入配置**（`settings.py`）：
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=settings.llm_model,          # "gpt-4o" / "deepseek-chat" / ...
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,    # 任意 OpenAI 兼容端点
    temperature=0.7,
    max_tokens=4096,
)
```

### 7.4 内嵌数据库层

#### DuckDB（关系型）
```python
import duckdb

conn = duckdb.connect("data/dataforge.duckdb")

# 根据 Schema 建表
conn.execute("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR, ...)")

# 批量写入生成数据
conn.executemany("INSERT INTO users VALUES (?, ?, ...)", rows)

# 前端 SQL 查询直通
conn.execute(user_sql_query).df()  # 返回 pandas DataFrame → JSON
```

API 端点：
- `POST /api/db/sql` — 执行任意 SQL，返回结果集
- `GET /api/db/tables` — 获取所有表与列定义
- `GET /api/db/er-schema` — 获取 ER 元数据（供前端渲染 ER 图）

#### Kuzu（图数据库）
```python
import kuzu

db = kuzu.Database("data/dataforge_graph")
conn = kuzu.Connection(db)

# 根据 Schema 建图
conn.execute("CREATE NODE TABLE User(id INT64, name STRING, PRIMARY KEY(id))")
conn.execute("CREATE REL TABLE FOLLOWS(FROM User TO User, since DATE)")

# 批量写入节点 / 关系
conn.execute("COPY User FROM 'users.csv'")

# 前端 Cypher 查询直通
result = conn.execute(user_cypher_query)
```

API 端点：
- `POST /api/graph/cypher` — 执行任意 Cypher，返回节点/关系结果
- `GET /api/graph/schema` — 获取图 Schema（节点标签、关系类型、属性）
- `GET /api/graph/stats` — 节点/关系数量统计

### 7.5 可视化模块

| 视图 | 数据源 | 技术实现 | 交互 |
|------|--------|---------|------|
| ER 图 | DuckDB Schema API | React Flow + ELK | 拖拽 / 缩放 / 关系高亮 |
| 知识图谱 | Kuzu Schema API | React Flow + D3 force | 点击展开邻居 / 过滤标签 |
| SQL Explorer | DuckDB Query API | Monaco SQL + AG Grid | 自动补全 / 结果导出 |
| Cypher Explorer | Kuzu Query API | Monaco Cypher + React Flow | 查询结果图形化 |
| 数据预览 | 生成结果内存 | TanStack Virtual | 分页 / 列筛选 / 行编辑 |

---

## 8. 数据流说明

```
┌─ 用户粘贴 DDL/Cypher ──────────────────────────────────┐
│                                                          │
│  POST /api/parse                                         │
│    ↓ sqlglot / lark → Internal Schema Model              │
│    ↓ 建 DuckDB 表结构 + Kuzu 图结构                     │
│    ↓ 返回 SchemaGraph JSON                               │
│    → 前端渲染 ER 图 + 知识图谱                          │
│                                                          │
│  用户配置生成参数（行数、AI 开关、LLM 配置）             │
│                                                          │
│  WS /ws/generate  （流式进度推送）                      │
│    ↓ 拓扑排序确定生成顺序                               │
│    ↓ [AI 开启] LangGraph 管道: 分析→推断→生成→校验     │
│    ↓ [AI 关闭] Faker 规则引擎直接生成                   │
│    ↓ 约束解决: FK 引用池 / UNIQUE 去重                  │
│    ↓ 写入 DuckDB（关系数据）+ Kuzu（图数据）            │
│    → 流式推送进度百分比 + 预览前 100 行                 │
│                                                          │
│  前端渲染数据预览表格                                    │
│  用户在 SQL Explorer 查询 DuckDB                        │
│  用户在 Cypher Explorer 查询 Kuzu                       │
│                                                          │
│  POST /api/export?format=sql|csv|json|cypher|xlsx        │
│    → 从 DuckDB/Kuzu 读取 → 序列化 → 流式下载           │
└──────────────────────────────────────────────────────────┘
```

---

## 9. 目录结构

```
DataForge/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SchemaEditor/        # Monaco DDL/Cypher 编辑器
│   │   │   ├── ERDiagram/           # React Flow + ELK ER 图
│   │   │   ├── GraphView/           # React Flow + D3 知识图谱
│   │   │   ├── SQLExplorer/         # Monaco SQL + DuckDB 结果表
│   │   │   ├── CypherExplorer/      # Monaco Cypher + Kuzu 结果图
│   │   │   ├── DataTable/           # TanStack 数据预览
│   │   │   ├── ConfigPanel/         # 生成参数 + AI 配置
│   │   │   └── ExportPanel/         # 导出操作
│   │   ├── stores/                  # Zustand: schema / data / ui
│   │   ├── hooks/                   # useGenerate / useDBQuery 等
│   │   ├── services/                # API 调用 + WS 客户端
│   │   └── types/                   # TS 类型：Schema / DataSet / DBResult
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── interfaces/              # Protocol 抽象层（纯声明，无实现代码）
│   │   │   ├── parser.py            # ISchemaParser
│   │   │   ├── generator.py         # IGenerationStrategy
│   │   │   ├── store.py             # IRelationalStore, IGraphStore
│   │   │   └── exporter.py          # IExporter
│   │   ├── services/                # 业务编排层（路由 → Service → Protocol）
│   │   │   ├── parse_service.py     # ParseService
│   │   │   ├── generate_service.py  # GenerateService（发布 DataBatchGenerated）
│   │   │   ├── export_service.py    # ExportService
│   │   │   └── query_service.py     # QueryService
│   │   ├── events/                  # 进程内异步事件总线
│   │   │   ├── bus.py               # AsyncEventBus（subscribe / publish）
│   │   │   └── types.py             # DataBatchGenerated, GenerationProgress
│   │   ├── api/routes/
│   │   │   ├── parse.py             # POST /api/parse
│   │   │   ├── generate.py          # POST /api/generate
│   │   │   ├── db_sql.py            # POST /api/db/sql, GET /api/db/tables
│   │   │   ├── db_graph.py          # POST /api/graph/cypher, GET /api/graph/schema
│   │   │   └── export.py            # POST /api/export
│   │   ├── api/websocket.py         # WS /ws/generate 流式进度
│   │   ├── core/
│   │   │   ├── ddl_parser.py        # sqlglot 封装，实现 ISchemaParser
│   │   │   ├── cypher_parser.py     # lark 语法解析，实现 ISchemaParser
│   │   │   └── schema_model.py      # Pydantic 内部模型（SchemaModel / ERSchema）
│   │   ├── generator/
│   │   │   ├── strategies/          # IGenerationStrategy 具体实现
│   │   │   │   ├── rule_based.py    # RuleBasedStrategy（Faker + 语义推断）
│   │   │   │   └── ai_enhanced.py   # AIEnhancedStrategy（LangGraph 四节点）
│   │   │   ├── rules.py             # 字段名语义规则表
│   │   │   └── constraint.py        # 约束解决器（FK 引用池 / UNIQUE / 拓扑序）
│   │   ├── ai/
│   │   │   ├── pipeline.py          # LangGraph 工作流定义
│   │   │   ├── nodes.py             # 四节点实现（Context/Rule/Gen/Validate）
│   │   │   ├── prompts.py           # Prompt 模板
│   │   │   └── llm_config.py        # ChatOpenAI 配置（base_url/api_key/model）
│   │   ├── db/
│   │   │   ├── duckdb_client.py     # 实现 IRelationalStore
│   │   │   └── kuzu_client.py       # 实现 IGraphStore
│   │   └── exporter/
│   │       ├── sql.py / csv_exp.py / json_exp.py  # 均实现 IExporter
│   │       ├── cypher_exp.py
│   │       └── excel.py
│   ├── data/                        # DuckDB 文件 + Kuzu 图数据目录（.gitignore）
│   ├── logs/                        # 后台进程日志（.gitignore）
│   ├── pyproject.toml
│   └── main.py
│
├── scripts/
│   ├── start.ps1                    # Windows 生产后台启动
│   ├── start-dev.ps1                # Windows 开发双进程启动
│   ├── stop.ps1                     # Windows 停止所有后台进程
│   └── Makefile                     # Linux/macOS: make start/dev/stop
│
└── README.md
```

---

## 10. 开发路线图

### Phase 1 — MVP 核心生成（第 1-3 周）
- [ ] FastAPI 脚手架 + uv 环境 + 启动脚本（start.ps1 / Makefile）
- [ ] DDL 解析（MySQL / PostgreSQL）
- [ ] Faker 规则引擎生成
- [ ] DuckDB 集成：建表 + 写入 + SQL 查询 API
- [ ] React 脚手架 + Monaco 编辑器 + SQL Explorer UI
- [ ] FastAPI 静态文件挂载（生产模式单进程）

### Phase 2 — 可视化与 ER 图（第 4-5 周）
- [ ] ER 图（React Flow + ELK，数据源为 DuckDB Schema）
- [ ] 数据预览表格（TanStack Virtual）
- [ ] Config Panel（行数 / 字段规则覆盖）
- [ ] CSV / JSON / SQL INSERT 导出

### Phase 3 — 图数据库支持（第 6-7 周）
- [ ] Cypher Schema 解析器（lark）
- [ ] Kuzu 集成：建图 + 写入 + Cypher 查询 API
- [ ] 知识图谱可视化（React Flow + D3 force）
- [ ] Cypher Explorer UI
- [ ] Cypher CREATE 导出

### Phase 4 — LangGraph AI 管道（第 8-9 周）
- [ ] LangGraph 四节点工作流
- [ ] LLM 配置界面（base_url / api_key / model 选择）
- [ ] OpenAI 兼容协议验证（对接 DeepSeek / Ollama 测试）
- [ ] WebSocket 流式生成进度推送
- [ ] AI 降级回退机制（API 不可用时切换 Faker）

### Phase 5 — 完善与打磨（第 10 周）
- [ ] 多方言 DDL（SQL Server / Oracle）
- [ ] Excel 导出（多 Sheet）
- [ ] 用户自定义规则持久化
- [ ] 大批量模式（百万行，分批写入）
- [ ] 会话管理（多 Schema 并行工作区）

---

*文档版本：v0.3 | 更新日期：2026-06-16*
