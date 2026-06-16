"""
Phase 5 · 单元测试 — 多方言 DDL 解析
覆盖任务：P5-B1（SQL Server、Oracle 方言）
"""

import pytest
from app.core.ddl_parser import DDLParser


@pytest.fixture
def parser():
    return DDLParser()


# ── SQL Server ────────────────────────────────────────────────────────────────

class TestSQLServerDialect:
    MSSQL_DDL = """
    CREATE TABLE dbo.employees (
        id         INT          NOT NULL IDENTITY(1,1),
        first_name NVARCHAR(50) NOT NULL,
        last_name  NVARCHAR(50) NOT NULL,
        email      NVARCHAR(120) NOT NULL,
        salary     DECIMAL(18, 2),
        hired_at   DATETIME2    NOT NULL DEFAULT GETUTCDATE(),
        is_active  BIT          NOT NULL DEFAULT 1,
        CONSTRAINT PK_employees PRIMARY KEY (id),
        CONSTRAINT UQ_employees_email UNIQUE (email)
    );
    """

    def test_table_name_extracted(self, parser):
        result = parser.parse(self.MSSQL_DDL, dialect="tsql")
        assert result.tables[0].name in ("employees", "dbo.employees")

    def test_identity_as_auto_increment(self, parser):
        result = parser.parse(self.MSSQL_DDL, dialect="tsql")
        id_col = next(c for c in result.tables[0].columns if c.name == "id")
        assert id_col.auto_increment is True

    def test_nvarchar_mapped_to_string(self, parser):
        result = parser.parse(self.MSSQL_DDL, dialect="tsql")
        fn_col = next(c for c in result.tables[0].columns if c.name == "first_name")
        assert fn_col.type_category == "string"

    def test_bit_mapped_to_boolean(self, parser):
        result = parser.parse(self.MSSQL_DDL, dialect="tsql")
        flag_col = next(c for c in result.tables[0].columns if c.name == "is_active")
        assert flag_col.type_category == "boolean"

    def test_datetime2_mapped_to_datetime(self, parser):
        result = parser.parse(self.MSSQL_DDL, dialect="tsql")
        dt_col = next(c for c in result.tables[0].columns if c.name == "hired_at")
        assert dt_col.type_category == "datetime"

    def test_named_pk_constraint_detected(self, parser):
        result = parser.parse(self.MSSQL_DDL, dialect="tsql")
        id_col = next(c for c in result.tables[0].columns if c.name == "id")
        assert id_col.primary_key is True

    def test_named_unique_constraint(self, parser):
        result = parser.parse(self.MSSQL_DDL, dialect="tsql")
        em_col = next(c for c in result.tables[0].columns if c.name == "email")
        assert em_col.unique is True


# ── Oracle ────────────────────────────────────────────────────────────────────

class TestOracleDialect:
    ORACLE_DDL = """
    CREATE TABLE customers (
        customer_id  NUMBER(10)     NOT NULL,
        first_name   VARCHAR2(50)   NOT NULL,
        last_name    VARCHAR2(50)   NOT NULL,
        email        VARCHAR2(120)  NOT NULL,
        credit_limit NUMBER(12, 2),
        join_date    DATE           DEFAULT SYSDATE,
        CONSTRAINT pk_customers PRIMARY KEY (customer_id),
        CONSTRAINT uq_cust_email UNIQUE (email)
    );

    CREATE SEQUENCE customers_seq START WITH 1 INCREMENT BY 1;
    """

    def test_table_name_extracted(self, parser):
        result = parser.parse(self.ORACLE_DDL, dialect="oracle")
        names = {t.name for t in result.tables}
        assert "customers" in names

    def test_varchar2_mapped_to_string(self, parser):
        result = parser.parse(self.ORACLE_DDL, dialect="oracle")
        cust = next(t for t in result.tables if t.name == "customers")
        fn_col = next(c for c in cust.columns if c.name == "first_name")
        assert fn_col.type_category == "string"

    def test_number_mapped_to_integer_or_decimal(self, parser):
        result = parser.parse(self.ORACLE_DDL, dialect="oracle")
        cust = next(t for t in result.tables if t.name == "customers")
        id_col    = next(c for c in cust.columns if c.name == "customer_id")
        price_col = next(c for c in cust.columns if c.name == "credit_limit")
        assert id_col.type_category in ("integer", "decimal")
        assert price_col.type_category == "decimal"

    def test_sequence_ignored_no_extra_table(self, parser):
        result = parser.parse(self.ORACLE_DDL, dialect="oracle")
        table_names = {t.name for t in result.tables}
        assert "customers_seq" not in table_names


# ── 交叉方言验证 ──────────────────────────────────────────────────────────────

class TestCrossDialectConsistency:
    @pytest.mark.parametrize("ddl,dialect", [
        (
            "CREATE TABLE t (id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(50));",
            "mysql",
        ),
        (
            "CREATE TABLE t (id SERIAL PRIMARY KEY, name VARCHAR(50));",
            "postgresql",
        ),
        (
            "CREATE TABLE t (id INT NOT NULL IDENTITY(1,1), name NVARCHAR(50), CONSTRAINT PK_t PRIMARY KEY (id));",
            "tsql",
        ),
        (
            "CREATE TABLE t (id NUMBER(10) NOT NULL, name VARCHAR2(50), CONSTRAINT pk_t PRIMARY KEY (id));",
            "oracle",
        ),
    ])
    def test_auto_increment_pk_detected_across_dialects(self, parser, ddl, dialect):
        result = parser.parse(ddl, dialect=dialect)
        id_col = next(c for c in result.tables[0].columns if c.name == "id")
        assert id_col.primary_key is True
