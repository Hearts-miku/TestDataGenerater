"""CSV exporter — one CSV per table, bundled in a ZIP archive (UTF-8 BOM)."""

from __future__ import annotations

import csv
import io
import zipfile
from typing import Any


class CSVExporter:
    def export(self, data: dict[str, list[dict[str, Any]]]) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for table, rows in data.items():
                if not rows:
                    continue
                text_buf = io.StringIO()
                writer = csv.DictWriter(text_buf, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                for row in rows:
                    # Render None as empty string
                    writer.writerow({k: ("" if v is None else v) for k, v in row.items()})
                # Prepend UTF-8 BOM so Excel opens without mojibake
                content = ("﻿" + text_buf.getvalue()).encode("utf-8")
                zf.writestr(f"{table}.csv", content)
        return buf.getvalue()
