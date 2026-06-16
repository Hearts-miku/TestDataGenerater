"""SQL INSERT exporter — wraps data in a transaction, one INSERT per row."""

from __future__ import annotations

from typing import Any


class SQLExporter:
    def export(self, data: dict[str, list[dict[str, Any]]]) -> str:
        lines: list[str] = ["BEGIN;", ""]
        for table, rows in data.items():
            if not rows:
                continue
            cols = list(rows[0].keys())
            col_str = ", ".join(cols)
            for row in rows:
                vals = ", ".join(self._fmt(row.get(c)) for c in cols)
                lines.append(f"INSERT INTO {table} ({col_str}) VALUES ({vals});")
            lines.append("")
        lines.append("COMMIT;")
        return "\n".join(lines)

    @staticmethod
    def _fmt(v: Any) -> str:
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "1" if v else "0"
        if isinstance(v, (int, float)):
            return str(v)
        # String: escape embedded single quotes
        return "'" + str(v).replace("'", "''") + "'"
