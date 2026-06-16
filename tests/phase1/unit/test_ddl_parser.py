"""
Phase 1 · 单元测试 — DDL 解析器
覆盖任务：P1-B2（sqlglot 封装层）

测试对象：backend/app/core/ddl_parser.py :: DDLParser
无外部依赖，纯内存解析。
"""

import pytest
from app.core.ddl_parser import DDLParser


@pytest.fixture
def parser():
    return DDLParser()


# ── 基础解析 ──────────────────────────────────────────────────────────────────

class TestBasicTableExtraction:
    def test_single_table_name(self, parser):
        result = parser.parse("CREATE TABLE users (id INT PRIMARY KEY);")
        assert len(result.tables) == 1
        assert result.tables[0].name == "users"

    def test_multiple_tables(self, parser):
        ddl = """
        CREATE TABLE a (id INT PRIMARY KEY);
        CREATE TABLE b (id INT PRIMARY KEY);
        CREATE TABLE c (id INT PRIMARY KEY);
        """
        result = parser.parse(ddl)
        names = {t.name for t in result.tables}
        assert names == {"a", "b", "c"}

    def test_column_names_extracted(self, parser):
        ddl = "CREATE TABLE t (id INT, name VARCHAR(50), age INT);"
        result = parser.parse(ddl)
        col_names = {c.name for c in result.tables[0].columns}
        assert col_names == {"id", "name", "age"}

    def test_empty_ddl_raises(self, parser):
        with pytest.raises(ValueError, match="empty"):
            parser.parse("")

    def test_invalid_sql_raises(self, parser):
        with pytest.raises(ValueError):
            parser.parse("NOT VALID SQL @@@@")


# ── 列属性提取 ────────────────────────────────────────────────────────────────

class TestColumnAttributes:
    def test_primary_key_flag(self, parser):
        result = parser.parse("CREATE TABLE t (id INT NOT NULL, PRIMARY KEY(id));")
        id_col = next(c for c in result.tables[0].columns if c.name == "id")
        assert id_col.primary_key is True

    def test_inline_primary_key(self, parser):
        result = parser.parse("CREATE TABLE t (id INT PRIMARY KEY, name VARCHAR(50));")
        id_col = next(c for c in result.tables[0].columns if c.name == "id")
        assert id_col.primary_key is True

    def test_auto_increment(self, parser):
        result = parser.parse("CREATE TABLE t (id INT NOT NULL AUTO_INCREMENT, PRIMARY KEY(id));")
        id_col = next(c for c in result.tables[0].columns if c.name == "id")
        assert id_col.auto_increment is True

    def test_not_null_flag(self, parser):
        result = parser.parse("CREATE TABLE t (a VARCHAR(50) NOT NULL, b VARCHAR(50));")
        cols = {c.name: c for c in result.tables[0].columns}
        assert cols["a"].nullable is False
        assert cols["b"].nullable is True

    def test_unique_constraint(self, parser):
        result = parser.parse("CREATE TABLE t (id INT PRIMARY KEY, email VARCHAR(120) UNIQUE);")
        email_col = next(c for c in result.tables[0].columns if c.name == "email")
        assert email_col.unique is True

    def test_default_value_captured(self, parser):
        result = parser.parse("CREATE TABLE t (id INT, status VARCHAR(20) DEFAULT 'active');")
        status_col = next(c for c in result.tables[0].columns if c.name == "status")
        assert status_col.default == "active"

    def test_enum_values(self, parser):
        result = parser.parse(
            "CREATE TABLE t (id INT, role ENUM('admin','user','guest'));"
        )
        role_col = next(c for c in result.tables[0].columns if c.name == "role")
        assert set(role_col.enum_values) == {"admin", "user", "guest"}

    def test_varchar_length(self, parser):
        result = parser.parse("CREATE TABLE t (name VARCHAR(255));")
        col = result.tables[0].columns[0]
        assert col.length == 255

    def test_decimal_precision_scale(self, parser):
        result = parser.parse("CREATE TABLE t (price DECIMAL(10, 2));")
        col = result.tables[0].columns[0]
        assert col.precision == 10
        assert col.scale == 2


# ── 外键提取 ──────────────────────────────────────────────────────────────────

class TestForeignKeyExtraction:
    def test_simple_fk(self, parser):
        ddl = """
        CREATE TABLE parent (id INT PRIMARY KEY);
        CREATE TABLE child (
            id INT PRIMARY KEY,
            parent_id INT NOT NULL,
            FOREIGN KEY (parent_id) REFERENCES parent(id)
        );
        """
        result = parser.parse(ddl)
        child = next(t for t in result.tables if t.name == "child")
        assert len(child.foreign_keys) == 1
        fk = child.foreign_keys[0]
        assert fk.column == "parent_id"
        assert fk.ref_table == "parent"
        assert fk.ref_column == "id"

    def test_multiple_fks_on_same_table(self, parser):
        ddl = """
        CREATE TABLE a (id INT PRIMARY KEY);
        CREATE TABLE b (id INT PRIMARY KEY);
        CREATE TABLE c (
            id INT PRIMARY KEY,
            a_id INT, b_id INT,
            FOREIGN KEY (a_id) REFERENCES a(id),
            FOREIGN KEY (b_id) REFERENCES b(id)
        );
        """
        result = parser.parse(ddl)
        c_table = next(t for t in result.tables if t.name == "c")
        assert len(c_table.foreign_keys) == 2

    def test_self_referencing_fk(self, parser):
        ddl = """
        CREATE TABLE employees (
            id INT PRIMARY KEY,
            manager_id INT,
            FOREIGN KEY (manager_id) REFERENCES employees(id)
        );
        """
        result = parser.parse(ddl)
        emp = result.tables[0]
        fk = emp.foreign_keys[0]
        assert fk.ref_table == "employees"


# ── 类型分类 ──────────────────────────────────────────────────────────────────

class TestTypeCategories:
    @pytest.mark.parametrize("sql_type,expected", [
        ("INT",      "integer"),
        ("BIGINT",   "integer"),
        ("TINYINT",  "integer"),
        ("SMALLINT", "integer"),
        ("FLOAT",    "float"),
        ("DOUBLE",   "float"),
        ("DECIMAL(10,2)", "decimal"),
        ("VARCHAR(50)",   "string"),
        ("CHAR(10)",      "string"),
        ("TEXT",          "text"),
        ("BOOLEAN",       "boolean"),
        ("DATE",          "date"),
        ("DATETIME",      "datetime"),
        ("TIMESTAMP",     "datetime"),
        ("JSON",          "json"),
    ])
    def test_type_category_mapping(self, parser, sql_type, expected):
        result = parser.parse(f"CREATE TABLE t (col {sql_type});")
        col = result.tables[0].columns[0]
        assert col.type_category == expected, f"{sql_type} → expected {expected}, got {col.type_category}"


# ── 方言支持 ──────────────────────────────────────────────────────────────────

class TestDialects:
    def test_mysql_dialect(self, parser):
        result = parser.parse(
            "CREATE TABLE t (id INT NOT NULL AUTO_INCREMENT PRIMARY KEY) ENGINE=InnoDB;",
            dialect="mysql",
        )
        assert result.tables[0].name == "t"

    def test_postgresql_dialect_serial(self, parser):
        result = parser.parse(
            "CREATE TABLE t (id SERIAL PRIMARY KEY, name TEXT NOT NULL);",
            dialect="postgresql",
        )
        id_col = next(c for c in result.tables[0].columns if c.name == "id")
        assert id_col.primary_key is True
        assert id_col.auto_increment is True

    def test_unsupported_dialect_raises(self, parser):
        with pytest.raises(ValueError, match="dialect"):
            parser.parse("CREATE TABLE t (id INT);", dialect="cobol")
