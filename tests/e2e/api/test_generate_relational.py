"""
E2E：关系型数据生成
验证 POST /api/generate 对 DDL Schema 的数据生成结果满足约束与数量要求。
"""

import pytest
from conftest import parse_ddl, generate, sql_query


class TestSimpleUserGeneration:
    def test_row_count_matches_request(self, client, ddl_simple_users):
        schema = parse_ddl(client, ddl_simple_users)
        result = generate(client, schema["schema_id"], row_counts={"users": 50})
        assert result["tables"]["users"]["generated"] == 50

    def test_email_values_are_unique(self, client, ddl_simple_users):
        schema = parse_ddl(client, ddl_simple_users)
        generate(client, schema["schema_id"], row_counts={"users": 30})
        count = sql_query(client, "SELECT COUNT(DISTINCT email) AS cnt FROM users")["rows"][0]["cnt"]
        assert count == 30

    def test_username_values_are_unique(self, client, ddl_simple_users):
        schema = parse_ddl(client, ddl_simple_users)
        generate(client, schema["schema_id"], row_counts={"users": 30})
        count = sql_query(client, "SELECT COUNT(DISTINCT username) AS cnt FROM users")["rows"][0]["cnt"]
        assert count == 30

    def test_no_null_in_not_null_columns(self, client, ddl_simple_users):
        schema = parse_ddl(client, ddl_simple_users)
        generate(client, schema["schema_id"], row_counts={"users": 20})
        null_count = sql_query(
            client, "SELECT COUNT(*) AS cnt FROM users WHERE email IS NULL OR username IS NULL"
        )["rows"][0]["cnt"]
        assert null_count == 0


class TestEcommerceConstraintIntegrity:
    @pytest.fixture(autouse=True)
    def _generate_ecommerce(self, client, ddl_ecommerce):
        schema = parse_ddl(client, ddl_ecommerce)
        self.schema_id = schema["schema_id"]
        generate(client, self.schema_id, row_counts={
            "categories": 10,
            "products": 50,
            "users": 30,
            "orders": 80,
            "order_items": 200,
        })

    def test_all_tables_populated(self, client):
        for table, expected in [
            ("categories", 10), ("products", 50),
            ("users", 30), ("orders", 80), ("order_items", 200),
        ]:
            row = sql_query(client, f"SELECT COUNT(*) AS cnt FROM {table}")["rows"][0]
            assert row["cnt"] == expected, f"{table}: expected {expected}, got {row['cnt']}"

    def test_fk_products_category_id_valid(self, client):
        """products.category_id 必须全部在 categories.id 中存在。"""
        orphans = sql_query(client, """
            SELECT COUNT(*) AS cnt FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE c.id IS NULL
        """)["rows"][0]["cnt"]
        assert orphans == 0

    def test_fk_orders_user_id_valid(self, client):
        orphans = sql_query(client, """
            SELECT COUNT(*) AS cnt FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE u.id IS NULL
        """)["rows"][0]["cnt"]
        assert orphans == 0

    def test_fk_order_items_both_fks_valid(self, client):
        orphan_orders = sql_query(client, """
            SELECT COUNT(*) AS cnt FROM order_items oi
            LEFT JOIN orders o ON oi.order_id = o.id
            WHERE o.id IS NULL
        """)["rows"][0]["cnt"]
        orphan_products = sql_query(client, """
            SELECT COUNT(*) AS cnt FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE p.id IS NULL
        """)["rows"][0]["cnt"]
        assert orphan_orders == 0
        assert orphan_products == 0

    def test_enum_values_within_allowed_set(self, client):
        invalid = sql_query(client, """
            SELECT COUNT(*) AS cnt FROM orders
            WHERE status NOT IN ('pending','paid','shipped','completed','cancelled')
        """)["rows"][0]["cnt"]
        assert invalid == 0

    def test_total_amount_positive(self, client):
        negative = sql_query(
            client, "SELECT COUNT(*) AS cnt FROM orders WHERE total_amount <= 0"
        )["rows"][0]["cnt"]
        assert negative == 0

    def test_order_items_quantity_at_least_one(self, client):
        bad = sql_query(
            client, "SELECT COUNT(*) AS cnt FROM order_items WHERE quantity < 1"
        )["rows"][0]["cnt"]
        assert bad == 0


class TestAllTypesGeneration:
    def test_no_type_errors_on_generation(self, client, ddl_all_types):
        """全类型表能生成而不报错。"""
        schema = parse_ddl(client, ddl_all_types)
        result = generate(client, schema["schema_id"], row_counts={"type_coverage": 20})
        assert result["tables"]["type_coverage"]["generated"] == 20

    def test_enum_column_restricted(self, client, ddl_all_types):
        schema = parse_ddl(client, ddl_all_types)
        generate(client, schema["schema_id"], row_counts={"type_coverage": 20})
        invalid = sql_query(
            client, "SELECT COUNT(*) AS cnt FROM type_coverage WHERE col_enum NOT IN ('A','B','C','D')"
        )["rows"][0]["cnt"]
        assert invalid == 0

    def test_default_value_used_when_omitted(self, client, ddl_all_types):
        schema = parse_ddl(client, ddl_all_types)
        generate(client, schema["schema_id"], row_counts={"type_coverage": 10})
        rows = sql_query(client, "SELECT col_default FROM type_coverage LIMIT 10")["rows"]
        # DEFAULT 42 应使 col_default 均为 42（当字段未被覆盖时）
        assert all(r["col_default"] == 42 for r in rows)


class TestLargeVolumeGeneration:
    def test_generate_10k_rows_no_duplicate_pk(self, client, ddl_simple_users):
        schema = parse_ddl(client, ddl_simple_users)
        generate(client, schema["schema_id"], row_counts={"users": 10_000})
        dup = sql_query(client, """
            SELECT COUNT(*) AS cnt FROM (
                SELECT id FROM users GROUP BY id HAVING COUNT(*) > 1
            ) t
        """)["rows"][0]["cnt"]
        assert dup == 0

    def test_generate_10k_unique_emails(self, client, ddl_simple_users):
        schema = parse_ddl(client, ddl_simple_users)
        generate(client, schema["schema_id"], row_counts={"users": 10_000})
        total = sql_query(client, "SELECT COUNT(*) AS cnt FROM users")["rows"][0]["cnt"]
        unique = sql_query(client, "SELECT COUNT(DISTINCT email) AS cnt FROM users")["rows"][0]["cnt"]
        assert unique == total
