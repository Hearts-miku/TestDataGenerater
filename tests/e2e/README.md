# E2E 测试说明

## 目录结构

```
tests/e2e/
├── fixtures/
│   ├── ddl/
│   │   ├── simple_users.sql       # 单表：基础解析与生成
│   │   ├── ecommerce_schema.sql   # 多表 FK：电商场景（主力测试用例）
│   │   ├── all_types.sql          # 全数据类型覆盖
│   │   └── postgresql_schema.sql  # PostgreSQL 方言验证
│   └── cypher/
│       ├── social_network.cypher  # 社交图：多种关系类型
│       └── knowledge_graph.cypher # 知识图谱：自引用、属性关系
│
├── api/                           # pytest 后端 API 级 E2E 测试
│   ├── test_parse_ddl.py          # DDL 解析
│   ├── test_parse_cypher.py       # Cypher 解析
│   ├── test_generate_relational.py # 关系数据生成 + 约束验证
│   ├── test_generate_graph.py     # 图数据生成 + 引用完整性
│   ├── test_duckdb_query.py       # SQL Explorer API + 安全
│   ├── test_kuzu_query.py         # Cypher Explorer API + 安全
│   ├── test_export.py             # 所有导出格式
│   └── test_ai_pipeline.py        # LangGraph 管道 + 降级逻辑
│
├── browser/                       # Playwright 浏览器 E2E 测试
│   ├── test_ddl_flow.spec.ts      # DDL 完整用户流
│   ├── test_cypher_flow.spec.ts   # Cypher 完整用户流
│   └── playwright.config.ts
│
├── conftest.py                    # pytest 公共 fixtures
└── README.md
```

---

## 前置条件

1. 启动 DataForge 后端服务：

```powershell
# 方式 A：脚本启动
.\scripts\start.ps1

# 方式 B：手动启动
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. 确认服务可达：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health
```

---

## 运行 API 测试（pytest）

```powershell
# 安装依赖（仅首次）
cd backend
uv sync --group test

# 运行所有 API E2E 测试
uv run pytest tests/e2e/api -v

# 运行单个文件
uv run pytest tests/e2e/api/test_generate_relational.py -v

# 运行单个用例
uv run pytest tests/e2e/api/test_generate_relational.py::TestEcommerceConstraintIntegrity::test_fk_products_category_id_valid -v

# 指定后端地址（默认 http://127.0.0.1:8000）
$env:DATAFORGE_URL="http://127.0.0.1:8000"
uv run pytest tests/e2e/api -v
```

---

## 运行浏览器测试（Playwright）

```powershell
# 安装依赖（仅首次）
cd tests/e2e/browser
pnpm install
pnpm exec playwright install --with-deps

# 运行所有浏览器测试
pnpm exec playwright test

# 有头模式调试（可看到浏览器操作）
pnpm exec playwright test --headed

# 只跑 DDL 流程
pnpm exec playwright test test_ddl_flow.spec.ts

# 指定浏览器
pnpm exec playwright test --project=chromium

# 查看 HTML 报告
pnpm exec playwright show-report
```

---

## 测试覆盖场景

### API 测试（pytest）

| 文件 | 场景 | 关键断言 |
|------|------|---------|
| test_parse_ddl | DDL 解析正确性 | 表名、列名、FK、ENUM、拓扑序 |
| test_parse_cypher | Cypher 解析正确性 | 节点标签、关系类型、约束、自引用 |
| test_generate_relational | 关系数据生成 | 行数准确、UNIQUE 无重复、FK 引用完整、ENUM 值合法 |
| test_generate_graph | 图数据生成 | 节点/关系数量、端点类型正确、唯一约束 |
| test_duckdb_query | SQL Explorer | SELECT/JOIN/聚合执行、DDL 写操作被拒绝 |
| test_kuzu_query | Cypher Explorer | MATCH/路径查询、写操作被拒绝、模式端点 |
| test_export | 导出格式验证 | SQL 含 INSERT + COMMIT、CSV 可解析、JSON 结构正确、xlsx 合法 |
| test_ai_pipeline | LangGraph + 降级 | ai_used 标志、LLM 不可达自动降级、约束仍被满足 |

### 浏览器测试（Playwright）

| 文件 | 场景 |
|------|------|
| test_ddl_flow | 粘贴 DDL → ER 图 → Config → 生成 → SQL Explorer → 导出 |
| test_cypher_flow | 粘贴 Cypher → 图谱视图 → 生成 → Cypher Explorer → 图结果 → 导出 |

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATAFORGE_URL` | `http://127.0.0.1:8000` | 被测服务地址 |

---

## CI 建议

```yaml
# .github/workflows/e2e.yml 参考片段
- name: Start DataForge
  run: uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 &
  working-directory: backend

- name: Wait for service
  run: |
    for i in {1..30}; do
      curl -sf http://127.0.0.1:8000/api/health && break || sleep 2
    done

- name: Run API E2E tests
  run: uv run pytest tests/e2e/api -v --tb=short
  working-directory: backend

- name: Run Browser E2E tests
  run: pnpm exec playwright test --reporter=github
  working-directory: tests/e2e/browser
```
