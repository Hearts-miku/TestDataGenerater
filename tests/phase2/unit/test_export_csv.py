"""
Phase 2 · 单元测试 — CSV 导出器
覆盖任务：P2-B2
"""

import csv
import io
import zipfile
import pytest
from app.exporter.csv_exp import CSVExporter


@pytest.fixture
def exporter():
    return CSVExporter()


DATA = {
    "users":    [{"id": 1, "email": "a@a.com"}, {"id": 2, "email": "b@b.com"}],
    "products": [{"id": 1, "name": "Widget", "price": 9.99}],
}


class TestCSVExporterFormat:
    def test_output_is_bytes(self, exporter):
        result = exporter.export(DATA)
        assert isinstance(result, bytes)

    def test_output_is_valid_zip(self, exporter):
        result = exporter.export(DATA)
        assert zipfile.is_zipfile(io.BytesIO(result))

    def test_zip_contains_one_csv_per_table(self, exporter):
        result = exporter.export(DATA)
        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            names = {n.lower() for n in zf.namelist()}
        assert "users.csv" in names
        assert "products.csv" in names

    def test_csv_headers_match_keys(self, exporter):
        result = exporter.export(DATA)
        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            with zf.open("users.csv") as f:
                reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
                headers = set(reader.fieldnames or [])
        assert {"id", "email"}.issubset(headers)

    def test_row_count_matches(self, exporter):
        result = exporter.export(DATA)
        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            with zf.open("users.csv") as f:
                rows = list(csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")))
        assert len(rows) == 2

    def test_values_in_csv(self, exporter):
        result = exporter.export(DATA)
        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            with zf.open("users.csv") as f:
                content = f.read().decode("utf-8-sig")
        assert "a@a.com" in content

    def test_null_rendered_as_empty(self, exporter):
        result = exporter.export({"t": [{"id": 1, "val": None}]})
        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            with zf.open("t.csv") as f:
                content = f.read().decode("utf-8-sig")
        # NULL 应渲染为空字符串
        assert "None" not in content

    def test_special_chars_escaped(self, exporter):
        result = exporter.export({"t": [{"desc": 'He said, "hello"'}]})
        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            with zf.open("t.csv") as f:
                rows = list(csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")))
        assert rows[0]["desc"] == 'He said, "hello"'

    def test_empty_table_excluded_from_zip(self, exporter):
        result = exporter.export({"filled": [{"id": 1}], "empty": []})
        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            names = {n.lower() for n in zf.namelist()}
        assert "filled.csv" in names
        assert "empty.csv" not in names
