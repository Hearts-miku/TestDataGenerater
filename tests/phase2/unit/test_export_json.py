"""
Phase 2 · 单元测试 — JSON 导出器
覆盖任务：P2-B3
"""

import json
import pytest
from app.exporter.json_exp import JSONExporter


@pytest.fixture
def exporter():
    return JSONExporter()


DATA = {
    "users":    [{"id": 1, "email": "a@a.com"}, {"id": 2, "email": "b@b.com"}],
    "products": [{"id": 1, "name": "Widget", "price": 9.99}],
}


class TestJSONExporterFormat:
    def test_output_is_valid_json(self, exporter):
        result = exporter.export(DATA)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_all_tables_present(self, exporter):
        parsed = json.loads(exporter.export(DATA))
        assert "users" in parsed and "products" in parsed

    def test_row_counts_correct(self, exporter):
        parsed = json.loads(exporter.export(DATA))
        assert len(parsed["users"]) == 2
        assert len(parsed["products"]) == 1

    def test_values_preserved(self, exporter):
        parsed = json.loads(exporter.export(DATA))
        emails = {r["email"] for r in parsed["users"]}
        assert emails == {"a@a.com", "b@b.com"}

    def test_null_values_as_json_null(self, exporter):
        result = exporter.export({"t": [{"id": 1, "val": None}]})
        parsed = json.loads(result)
        assert parsed["t"][0]["val"] is None

    def test_numeric_types_preserved(self, exporter):
        result = exporter.export({"t": [{"price": 9.99, "qty": 3}]})
        parsed = json.loads(result)
        assert parsed["t"][0]["price"] == 9.99
        assert isinstance(parsed["t"][0]["qty"], int)

    def test_boolean_as_json_bool(self, exporter):
        result = exporter.export({"t": [{"flag": True}]})
        parsed = json.loads(result)
        assert parsed["t"][0]["flag"] is True

    def test_empty_table_has_empty_array(self, exporter):
        result = exporter.export({"users": [], "products": DATA["products"]})
        parsed = json.loads(result)
        assert parsed["users"] == []

    def test_output_is_pretty_printed(self, exporter):
        result = exporter.export(DATA)
        assert "\n" in result  # pretty-printed

    def test_large_dataset_valid_json(self, exporter):
        rows = [{"id": i, "val": f"v{i}"} for i in range(10_000)]
        result = exporter.export({"big": rows})
        parsed = json.loads(result)
        assert len(parsed["big"]) == 10_000
