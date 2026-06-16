"""JSON exporter — pretty-printed dict keyed by table name."""

from __future__ import annotations

import decimal
import datetime
import json
from typing import Any


def _default(v: Any) -> Any:
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    return str(v)


class JSONExporter:
    def export(self, data: dict[str, list[dict[str, Any]]]) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2, default=_default)
