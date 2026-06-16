# DataForge 使用指南

> Phase 1 — 基于规则的关系型数据生成，运行于本地，无需联网。

---

## 目录

1. [环境要求](#1-环境要求)
2. [安装与启动](#2-安装与启动)
3. [界面概览](#3-界面概览)
4. [Schema 编辑器](#4-schema-编辑器)
5. [数据生成](#5-数据生成)
6. [SQL 探索器](#6-sql-探索器)
7. [支持的 DDL 方言与语法](#7-支持的-ddl-方言与语法)
8. [语义字段推断规则](#8-语义字段推断规则)
9. [REST API 参考](#9-rest-api-参考)
10. [常见问题](#10-常见问题)

---

## 1. 环境要求

| 依赖 | 最低版本 | 用途 |
|------|---------|------|
| Python | 3.11+ | 后端运行时 |
| [uv](https://docs.astral.sh/uv/) | 0.4+ | Python 包管理 |
| Node.js | 18+ | 前端构建 |
| pnpm | 8+ | 前端包管理 |

> **Windows 用户**：在 PowerShell 中执行脚本前，确保已允许本地脚本执行：
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

## 2. 安装与启动

### 首次安装

```powershell
# 克隆仓库
git clone https://github.com/Hearts-miku/TestDataGenerater.git
cd TestDataGenerater

# 安装后端依赖
cd backend
uv sync
cd ..

# 安装前端依赖
cd frontend
pnpm install
cd ..
```

### 生产模式（推荐）

前端构建后由 FastAPI 统一托管，**只需一个端口**：

```powershell
.\scripts\start.ps1
```

启动后访问 **http://localhost:8000**

脚本会自动完成：
1. `pnpm build` — 编译前端到 `frontend/dist/`
2. 启动 uvicorn，同时提供 API 和静态文件服务

### 开发模式（双热重载）

后端代码改动自动重启，前端 HMR 即时刷新：

```powershell
.\scripts\start-dev.ps1
```

| 服务 | 地址 |
|------|------|
| 前端（Vite HMR） | http://localhost:5173 |
| 后端 API | http://localhost:8000 |

开发模式中前端访问 `/api/*` 会自动代理到 `:8000`。

### 手动启动

```powershell
# Terminal 1 — 后端
cd backend
uv run uvicorn main:app --port 8000 --reload

# Terminal 2 — 前端（开发模式）
cd frontend
pnpm dev
```

---

## 3. 界面概览

打开浏览器访问应用后，顶部有三个 Tab：

```
┌─────────────────────────────────────────────────┐
│  DataForge  Test Data Generator                  │
├──────────┬──────────────┬───────────────────────┤
│  Schema  │   Generate   │    SQL Explorer        │
└──────────┴──────────────┴───────────────────────┘
```

| Tab | 作用 |
|-----|------|
| **Schema** | 粘贴/编辑 DDL，选择方言，解析为内部 Schema 模型 |
| **Generate** | 配置每张表要生成的行数，一键生成并写入 DuckDB |
| **SQL Explorer** | 对 DuckDB 中已生成的数据执行 SQL 查询 |

典型使用流程：**Schema → Generate → SQL Explorer**

---

## 4. Schema 编辑器

### 4.1 基本操作

1. 打开 **Schema** Tab
2. 在编辑器中粘贴你的 DDL 语句（默认已有示例）
3. 从下拉框选择 SQL 方言（默认 `mysql`）
4. 点击 **Parse DDL** 按钮

解析成功后：
- 绿色标签显示识别到的表数量：`2 tables`
- 蓝色标签显示本次 Schema 的唯一 ID（前 8 位）
- 底部显示生成顺序（考虑外键拓扑排序）：`categories → products`

解析失败时顶部显示红色错误提示，常见原因见[第 10 节](#10-常见问题)。

### 4.2 示例 DDL

**单表（含约束）**
```sql
CREATE TABLE users (
    id         INT          NOT NULL AUTO_INCREMENT,
    email      VARCHAR(120) NOT NULL UNIQUE,
    username   VARCHAR(50)  NOT NULL UNIQUE,
    birth_date DATE,
    is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id)
);
```

**多表（含外键）**
```sql
CREATE TABLE categories (
    id   INT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE products (
    id          INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
    category_id INT           NOT NULL,
    name        VARCHAR(200)  NOT NULL,
    price       DECIMAL(10,2) NOT NULL,
    sku         VARCHAR(50)   UNIQUE,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
```

DataForge 会自动识别外键依赖，先生成 `categories` 再生成 `products`，保证引用完整性。

### 4.3 切换方言

| 方言值 | 对应数据库 | 典型特征 |
|--------|-----------|---------|
| `mysql` | MySQL / MariaDB | `AUTO_INCREMENT`, `ENUM(...)` |
| `postgresql` | PostgreSQL | `SERIAL`, `BIGSERIAL`, `TEXT` |
| `sqlite` | SQLite | `INTEGER PRIMARY KEY` 自增 |
| `tsql` | SQL Server | `IDENTITY(1,1)`, `NVARCHAR` |
| `oracle` | Oracle | `NUMBER`, `VARCHAR2` |
| `bigquery` | BigQuery | `INT64`, `FLOAT64`, `ARRAY` |

---

## 5. 数据生成

### 5.1 配置行数

切换到 **Generate** Tab，可以看到解析出的所有表，每张表右侧有一个数字输入框：

```
┌──────────┬────┬──────┬────┬──────────┬──────────────┐
│ 表名     │ PK │ Cols │ FK │ Row count │ Generated    │
├──────────┼────┼──────┼────┼──────────┼──────────────┤
│ categories│ id │  2   │  0 │  [  10 ] │     —        │
│ products  │ id │  5   │  1 │ [ 100 ] │     —        │
└──────────┴────┴──────┴────┴──────────┴──────────────┘
```

- 输入框默认值为 **10**，支持 0 ~ 100,000
- 设为 **0** 表示跳过该表，不生成也不清空
- 按回车或切换焦点后即时生效

### 5.2 执行生成

点击 **Generate (N rows)** 按钮，按钮上实时显示总行数。

生成完成后：
- 每张表右侧 **Generated** 列显示绿色标签，注明实际写入行数
- 底部 Statistic 卡片汇总各表生成结果
- 数据已写入内嵌 DuckDB，可立即在 SQL Explorer 查询

> **注意**：每次点击 Generate 会**清空**该表已有数据再重新生成，确保 `AUTO_INCREMENT` 从 1 开始，不会产生主键冲突。

### 5.3 外键约束处理

DataForge 按拓扑顺序生成（被引用表优先），然后从已生成的主键池中随机抽样填充外键列。

例如生成 5 条 categories、20 条 products 时：
- `categories.id` 生成 1～5
- `products.category_id` 从 {1,2,3,4,5} 中随机取值

若引用表行数为 0（跳过生成），外键列将填 `NULL`。

---

## 6. SQL 探索器

### 6.1 执行查询

切换到 **SQL Explorer** Tab：

1. 在 Monaco 编辑器中输入 SQL（默认有示例查询）
2. 点击 **Run** 按钮（或使用快捷键）
3. 下方表格展示查询结果，支持分页（每页 50 行）

### 6.2 示例查询

**查看所有用户**
```sql
SELECT * FROM users LIMIT 20;
```

**多表 JOIN**
```sql
SELECT p.name, p.price, c.name AS category
FROM products p
JOIN categories c ON p.category_id = c.id
ORDER BY p.price DESC
LIMIT 10;
```

**统计分析**
```sql
SELECT
    c.name AS category,
    COUNT(p.id) AS product_count,
    AVG(p.price) AS avg_price,
    MIN(p.price) AS min_price,
    MAX(p.price) AS max_price
FROM categories c
LEFT JOIN products p ON p.category_id = c.id
GROUP BY c.name
ORDER BY product_count DESC;
```

**验证外键完整性**
```sql
-- 应返回 0 行（无孤儿记录）
SELECT COUNT(*) AS orphan_count
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
WHERE c.id IS NULL;
```

### 6.3 限制

SQL 探索器仅允许 `SELECT` 查询，写操作（`INSERT`/`UPDATE`/`DELETE`/`DROP` 等）会返回 403 错误。如需修改数据，请通过 Generate 重新生成。

---

## 7. 支持的 DDL 方言与语法

### MySQL

```sql
CREATE TABLE orders (
    order_id    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id     INT NOT NULL,
    status      ENUM('pending','paid','shipped','cancelled') NOT NULL DEFAULT 'pending',
    total       DECIMAL(12,2) NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### PostgreSQL

```sql
CREATE TABLE sessions (
    id         BIGSERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    token      VARCHAR(255) NOT NULL UNIQUE,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### SQL Server

```sql
CREATE TABLE employees (
    employee_id INT IDENTITY(1,1) PRIMARY KEY,
    first_name  NVARCHAR(50) NOT NULL,
    last_name   NVARCHAR(50) NOT NULL,
    email       NVARCHAR(120) NOT NULL UNIQUE,
    hire_date   DATE NOT NULL,
    salary      DECIMAL(10,2)
);
```

### SQLite

```sql
CREATE TABLE notes (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    title      TEXT NOT NULL,
    content    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### 支持的约束语法汇总

| 约束 | 支持 | 示例 |
|------|------|------|
| `PRIMARY KEY` | ✅ | 列内联或表级定义均可 |
| `FOREIGN KEY ... REFERENCES` | ✅ | 自动推断引用列（可省略列名） |
| `NOT NULL` | ✅ | 生成时不产生 NULL |
| `UNIQUE` | ✅ | 生成值去重 |
| `AUTO_INCREMENT` / `SERIAL` / `IDENTITY` | ✅ | 从 1 开始自增 |
| `DEFAULT` | ✅ | 解析默认值（不影响生成） |
| `ENUM(...)` | ✅ | 从枚举值中随机选取 |
| `DECIMAL(p,s)` | ✅ | 精度/小数位数影响生成值范围 |
| `VARCHAR(n)` | ✅ | 生成长度 ≤ n 的字符串 |
| `CHECK` | ⚠️ | 解析但不强制执行 |

---

## 8. 语义字段推断规则

DataForge 根据**字段名**（大小写不敏感）自动选择最合适的 Faker 生成策略，生成语义相关的真实数据，而不是随机字符串。

### 常用字段名 → 生成策略对照表

| 字段名模式 | 生成示例 | 说明 |
|-----------|---------|------|
| `email`, `user_email` | `alice@example.com` | 邮箱地址 |
| `phone`, `mobile`, `tel` | `+1-555-234-5678` | 电话号码 |
| `username`, `user_name` | `john_doe42` | 用户名 |
| `first_name`, `given_name` | `Alice` | 名 |
| `last_name`, `surname` | `Johnson` | 姓 |
| `name`, `full_name`, `display_name` | `Alice Johnson` | 全名 |
| `address`, `street`, `addr` | `123 Main St` | 街道地址 |
| `city` | `New York` | 城市名 |
| `country` | `United States` | 国家名 |
| `zip`, `postal_code`, `postcode` | `10001` | 邮编 |
| `url`, `website`, `homepage` | `https://example.com` | URL |
| `ip_address`, `ip_addr` | `192.168.1.42` | IPv4 地址 |
| `uuid`, `guid` | `550e8400-e29b-41d4-a716-...` | UUID v4 |
| `company`, `company_name`, `org` | `Acme Corp` | 公司名 |
| `description`, `bio`, `summary` | 多句自然语言文本 | 长文本 |
| `sku`, `product_code`, `item_code` | `SKU-A3F7K2` | 商品编号 |
| `price`, `unit_price`, `cost` | `29.99` | 价格（2位小数） |
| `amount`, `total`, `balance` | `1234.56` | 金额 |
| `age`, `years`, `count`, `quantity` | `34` | 整数（合理范围） |
| `is_*`, `has_*`, `active`, `enabled` | `true` / `false` | 布尔值 |
| `created_at`, `updated_at`, `timestamp` | `2024-03-15 09:23:11` | 日期时间 |
| `birth_date`, `dob`, `birthday` | `1990-07-22` | 生日（合理年龄范围） |

### 推断优先级

字段名匹配 > 字段类型兜底。未匹配语义规则时，按 SQL 类型生成：

| SQL 类型 | 兜底生成 |
|---------|---------|
| `INT` / `BIGINT` | 随机整数（0 ~ 10000） |
| `FLOAT` / `DOUBLE` | 随机浮点数 |
| `DECIMAL(p,s)` | 带精度小数 |
| `VARCHAR(n)` | 随机字母数字串（长度 ≤ n） |
| `TEXT` | 随机单词 |
| `BOOLEAN` | 随机 true/false |
| `DATE` | 随机日期（近 5 年） |
| `DATETIME` / `TIMESTAMP` | 随机时间戳（近 1 年） |
| `ENUM(v1, v2, ...)` | 从枚举值随机选取 |

### 字段命名建议

为获得最真实的生成数据，建议字段名使用上表中的常见模式。例如：

```sql
-- 语义识别效果好
CREATE TABLE customers (
    id         INT PRIMARY KEY AUTO_INCREMENT,
    email      VARCHAR(120) UNIQUE,  -- → 邮箱格式
    first_name VARCHAR(50),          -- → 真实名字
    phone      VARCHAR(20),          -- → 电话格式
    city       VARCHAR(80),          -- → 城市名
    created_at DATETIME              -- → 时间戳
);

-- 语义识别效果差（会退化为随机字符串）
CREATE TABLE customers (
    id  INT PRIMARY KEY AUTO_INCREMENT,
    f1  VARCHAR(120),  -- 不知道语义 → 随机字符串
    f2  VARCHAR(50),
    f3  VARCHAR(20)
);
```

---

## 9. REST API 参考

DataForge 后端暴露标准 REST API，可在不使用前端界面的情况下直接调用。

**Base URL**：`http://localhost:8000/api`

### 9.1 健康检查

```http
GET /api/health
```

```json
{ "status": "ok", "memory_mb": 42 }
```

### 9.2 解析 DDL

```http
POST /api/parse
Content-Type: application/json

{
    "source": "CREATE TABLE users (...);",
    "type": "ddl",
    "dialect": "mysql"
}
```

**响应**
```json
{
    "schema_id": "28614e8c-3ccc-4c88-959a-fd975db4fbfc",
    "schema_type": "relational",
    "dialect": "mysql",
    "tables": [
        {
            "name": "users",
            "columns": [
                {
                    "name": "id",
                    "type_category": "integer",
                    "nullable": false,
                    "primary_key": true,
                    "auto_increment": true,
                    "unique": false,
                    "length": null,
                    "enum_values": null
                }
            ],
            "primary_key": ["id"],
            "foreign_keys": []
        }
    ],
    "generation_order": [
        { "step": 0, "name": "users", "kind": "table" }
    ]
}
```

**错误码**

| 状态码 | 原因 |
|--------|------|
| 422 | DDL 为空、语法无效、或未提供 `type` 字段 |
| 400 | 不支持的 `type` 值 |

### 9.3 生成数据

```http
POST /api/generate
Content-Type: application/json

{
    "schema_id": "28614e8c-3ccc-4c88-959a-fd975db4fbfc",
    "row_counts": {
        "categories": 10,
        "products": 100
    }
}
```

**响应**
```json
{
    "schema_id": "28614e8c-...",
    "tables": {
        "categories": { "generated": 10 },
        "products":   { "generated": 100 }
    },
    "ai_used": false,
    "generation_meta": {
        "chunk_size": 10000,
        "chunks_total": 1
    }
}
```

**注意**：`schema_id` 必须来自最近的 `/api/parse` 响应；服务重启后 Schema 缓存清空，需重新 Parse。

### 9.4 SQL 查询

```http
POST /api/db/sql
Content-Type: application/json

{
    "sql": "SELECT * FROM products ORDER BY price DESC LIMIT 5"
}
```

**响应**
```json
{
    "rows": [
        { "id": 42, "name": "Widget Pro", "price": 99.99, "category_id": 3 },
        ...
    ],
    "count": 5
}
```

**错误码**

| 状态码 | 原因 |
|--------|------|
| 403 | SQL 含写操作（INSERT/UPDATE/DELETE/DROP 等） |
| 400 | SQL 语法错误或引用了不存在的表/列 |

### 9.5 查看表结构

```http
GET /api/db/tables
```

**响应**
```json
{
    "tables": [
        {
            "name": "users",
            "columns": [
                { "name": "id",    "type": "BIGINT",  "nullable": false },
                { "name": "email", "type": "VARCHAR",  "nullable": false }
            ]
        }
    ]
}
```

### 9.6 ER Schema 元数据

```http
GET /api/db/er-schema
```

**响应**
```json
{
    "tables": [ ... ],
    "foreign_keys": [
        {
            "from_table": "products",
            "from_col":   "category_id",
            "to_table":   "categories",
            "to_col":     "id"
        }
    ]
}
```

### 完整工作流示例（curl）

```bash
# 1. 解析 DDL
SCHEMA_ID=$(curl -s -X POST http://localhost:8000/api/parse \
  -H "Content-Type: application/json" \
  -d '{
    "source": "CREATE TABLE users (id INT AUTO_INCREMENT PRIMARY KEY, email VARCHAR(120) UNIQUE, name VARCHAR(100));",
    "type": "ddl",
    "dialect": "mysql"
  }' | python -c "import sys,json; print(json.load(sys.stdin)['schema_id'])")

echo "Schema ID: $SCHEMA_ID"

# 2. 生成 50 条数据
curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d "{\"schema_id\": \"$SCHEMA_ID\", \"row_counts\": {\"users\": 50}}"

# 3. 查询
curl -s -X POST http://localhost:8000/api/db/sql \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users LIMIT 5"}'
```

---

## 10. 常见问题

### Q：Parse DDL 报错 "empty DDL"

**原因**：编辑器中内容为空或全为空白。  
**解决**：粘贴有效的 DDL 语句后再点击 Parse。

---

### Q：Parse DDL 报错 422 但 DDL 看起来正确

**可能原因与排查**：
1. **方言不匹配**：SQL Server 的 `IDENTITY(1,1)` 需选 `tsql`，不能用 `mysql`
2. **不支持的语法**：某些数据库厂商特有语法（如 MySQL 的 `KEY`索引定义行）在其他方言下会报错
3. **注释格式**：某些内联注释可能干扰解析，先删除注释再试

---

### Q：生成报错 "no rows for FK reference table"

**原因**：某张表的外键引用了另一张 `row_counts` 为 0 的表。  
**解决**：确保被引用表（父表）的行数 > 0，或者将子表行数也设为 0 跳过。

---

### Q：生成数据后查询返回空表

**可能原因**：
1. 在 SQL Explorer 输入的表名大小写与 DDL 不符（DuckDB 默认区分引号内大小写）
2. 生成时 `row_counts` 中该表值为 0

**排查**：先执行 `SELECT * FROM information_schema.tables WHERE table_schema='main'` 确认表名。

---

### Q：服务重启后 Generate 报错 "schema not found"

**原因**：Schema 存储在进程内存（`SchemaRegistry`），重启后清空。  
**解决**：重新切换到 Schema Tab，点击 **Parse DDL** 重新解析，然后再生成。

---

### Q：生成百万级数据时内存占用高

**建议**：
- 每张表单次生成建议不超过 **10 万行**
- 如需更大数据量，拆分多次生成（后续版本将支持分批流式写入）

---

### Q：如何保留之前生成的数据再追加新数据？

**现阶段不支持追加**。每次点击 Generate 会先清空目标表再重新生成。  
后续版本将增加 Append 模式选项。

---

### Q：Windows 下运行脚本报 "uv: not found"

安装 uv：
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

然后重新打开 PowerShell 窗口使 PATH 生效。

---

### Q：pnpm 版本不符合要求

```powershell
npm install -g pnpm@latest
```

---

*文档版本：v1.0 | 对应 Phase 1 | 更新日期：2026-06-16*
