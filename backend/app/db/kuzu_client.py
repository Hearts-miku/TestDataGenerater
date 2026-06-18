"""KuzuClient — in-memory graph store with a kuzu-compatible API surface.

A pure-Python in-memory implementation until kuzu ships Python 3.14 wheels.
The public interface mirrors kuzu's Python client so it can be swapped later.
"""

from __future__ import annotations

import operator
import re
from typing import Any

from app.core.schema_model import GraphSchemaModel, NodeDef, RelationshipDef

# ── Write-operation guard ─────────────────────────────────────────────────────

_WRITE_RE = re.compile(
    r'^\s*(CREATE|MERGE|DELETE|SET|REMOVE|DROP)\b|'
    r'\bDETACH\s+DELETE\b|\bDETACH\b',
    re.IGNORECASE,
)

# ── Cypher mini-parser regexes ────────────────────────────────────────────────

_MATCH_NODE_RE = re.compile(
    r'MATCH\s+\((\w+)(?::(\w+))?\)',
    re.IGNORECASE,
)
_MATCH_REL_RE = re.compile(
    r'MATCH\s+\((\w*)(?::(\w+))?\)\s*-\[(?:\w+)?:(\w+)\]->\s*\((\w*)(?::(\w+))?\)',
    re.IGNORECASE,
)
_WHERE_RE = re.compile(r'\bWHERE\b(.*?)(?=\bRETURN\b)', re.IGNORECASE | re.DOTALL)
_RETURN_RE = re.compile(r'\bRETURN\b(.*?)(?=\bORDER\s+BY\b|\bLIMIT\b|$)', re.IGNORECASE | re.DOTALL)
_ORDER_RE = re.compile(r'\bORDER\s+BY\s+(\w+)\.(\w+)', re.IGNORECASE)
_LIMIT_RE = re.compile(r'\bLIMIT\s+(\d+)\b', re.IGNORECASE)
_COUNT_RE = re.compile(r'count\s*\(\s*(\*|\w+)\s*\)\s+AS\s+(\w+)', re.IGNORECASE)
_PROP_RETURN_RE = re.compile(r'(\w+)\.(\w+)\s+AS\s+(\w+)')
_BARE_VAR_RE = re.compile(r'^(\w+)$')
_WHERE_COND_RE = re.compile(
    r'(\w+)\.(\w+)\s*(>=|<=|<>|!=|>|<|=)\s*'
    r'([\d.]+|\'[^\']*\'|"[^"]*")',
)

_OPS = {
    '>': operator.gt, '<': operator.lt,
    '>=': operator.ge, '<=': operator.le,
    '=': operator.eq, '<>': operator.ne, '!=': operator.ne,
}


def _coerce(val_str: str) -> Any:
    s = val_str.strip("'\"")
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _apply_where(rows: list[dict], where_clause: str, var: str) -> list[dict]:
    conditions = _WHERE_COND_RE.findall(where_clause)
    if not conditions:
        return rows
    result = []
    for row in rows:
        match = True
        for v, prop, op_str, rhs_str in conditions:
            if v != var:
                continue
            lhs = row.get(prop)
            rhs = _coerce(rhs_str)
            op_fn = _OPS.get(op_str)
            if op_fn is None:
                continue
            try:
                if not op_fn(lhs, rhs):
                    match = False
                    break
            except TypeError:
                match = False
                break
        if match:
            result.append(row)
    return result


class KuzuClient:
    """In-memory graph store — kuzu-compatible public API."""

    def __init__(self, path: str = ":memory:") -> None:
        self._path = path
        self._nodes: dict[str, list[dict[str, Any]]] = {}
        self._rels: dict[str, list[dict[str, Any]]] = {}
        self._node_schema: dict[str, list] = {}
        self._rel_schema: dict[str, dict] = {}

    # ── Schema management ──────────────────────────────────────────────────────

    def create_graph(self, schema: GraphSchemaModel) -> None:
        """Idempotent — creates tables that don't exist yet."""
        for node in schema.nodes:
            self._nodes.setdefault(node.label, [])
            self._node_schema[node.label] = node.properties

        for rel in schema.relationships:
            self._rels.setdefault(rel.type, [])
            self._rel_schema[rel.type] = {
                "from": rel.from_label,
                "to": rel.to_label,
                "props": rel.properties,
            }

    def reset(self) -> None:
        self._nodes.clear()
        self._rels.clear()
        self._node_schema.clear()
        self._rel_schema.clear()

    def close(self) -> None:
        pass

    # ── Data insertion ─────────────────────────────────────────────────────────

    def insert_nodes(self, label: str, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        self._nodes.setdefault(label, []).extend(rows)
        return len(rows)

    def insert_rels(self, rel_type: str, rows: list[dict[str, Any]]) -> int:
        """Each row must have from_id and to_id plus optional properties."""
        if not rows:
            return 0
        meta = self._rel_schema.get(rel_type, {})
        from_label = meta.get("from", "")
        to_label = meta.get("to", "")

        # Build id→row maps for endpoint lookup
        from_rows = {r.get("id"): r for r in self._nodes.get(from_label, [])}
        to_rows = {r.get("id"): r for r in self._nodes.get(to_label, [])}

        enriched: list[dict[str, Any]] = []
        for row in rows:
            fid = row.get("from_id")
            tid = row.get("to_id")
            if fid not in from_rows or tid not in to_rows:
                continue
            enriched.append({
                "_from_label": from_label,
                "_to_label": to_label,
                "_from_id": fid,
                "_to_id": tid,
                **{k: v for k, v in row.items() if k not in ("from_id", "to_id")},
            })
        self._rels.setdefault(rel_type, []).extend(enriched)
        return len(enriched)

    # ── Cypher query execution ─────────────────────────────────────────────────

    def query(self, cypher: str) -> list[dict[str, Any]]:
        stripped = cypher.strip()
        if _WRITE_RE.match(stripped):
            raise PermissionError(f"Write operations are not allowed in Cypher Explorer: {stripped[:60]}")
        if re.search(r'\b(DETACH\s+)?DELETE\b|\bCREATE\b|\bMERGE\b|\bSET\b|\bREMOVE\b|\bDROP\b', stripped, re.IGNORECASE):
            raise PermissionError(f"Write operations are not allowed in Cypher Explorer: {stripped[:60]}")
        return self._execute(stripped)

    def _execute(self, cypher: str) -> list[dict[str, Any]]:
        # Try relationship pattern first (more specific)
        rm = _MATCH_REL_RE.search(cypher)
        if rm:
            return self._exec_rel_query(cypher, rm)

        nm = _MATCH_NODE_RE.search(cypher)
        if nm:
            return self._exec_node_query(cypher, nm)

        return []

    def _exec_node_query(self, cypher: str, m: re.Match) -> list[dict[str, Any]]:
        var, label = m.group(1), m.group(2) or ""
        rows = list(self._nodes.get(label, []))

        # WHERE
        wm = _WHERE_RE.search(cypher)
        if wm:
            rows = _apply_where(rows, wm.group(1), var)

        # ORDER BY
        om = _ORDER_RE.search(cypher)
        if om:
            _, prop = om.group(1), om.group(2)
            rows = sorted(rows, key=lambda r: (r.get(prop) is None, r.get(prop)))

        # LIMIT
        lm = _LIMIT_RE.search(cypher)
        if lm:
            rows = rows[:int(lm.group(1))]

        return self._build_return(cypher, var, rows)

    def _exec_rel_query(self, cypher: str, m: re.Match) -> list[dict[str, Any]]:
        from_var, from_label, rel_type, to_var, to_label = (
            m.group(1) or "", m.group(2) or "",
            m.group(3),
            m.group(4) or "", m.group(5) or "",
        )
        # Resolve anonymous node labels from schema when not specified in query
        rel_meta = self._rel_schema.get(rel_type, {})
        if not from_label:
            from_label = rel_meta.get("from", "")
        if not to_label:
            to_label = rel_meta.get("to", "")
        rels = list(self._rels.get(rel_type, []))

        # Build joined rows
        from_map = {r.get("id"): r for r in self._nodes.get(from_label, [])}
        to_map = {r.get("id"): r for r in self._nodes.get(to_label, [])}

        joined: list[dict[str, Any]] = []
        for rel in rels:
            frow = from_map.get(rel.get("_from_id"))
            trow = to_map.get(rel.get("_to_id"))
            if frow is None or trow is None:
                continue
            joined.append({
                "_rel": rel,
                from_var: frow,
                to_var: trow,
            })

        # WHERE (applies to flat properties via var.prop notation)
        wm = _WHERE_RE.search(cypher)
        if wm:
            where_str = wm.group(1)
            filtered = []
            for jrow in joined:
                match = True
                for v, prop, op_str, rhs_str in _WHERE_COND_RE.findall(where_str):
                    node_row = jrow.get(v, {})
                    if not isinstance(node_row, dict):
                        match = False
                        break
                    lhs = node_row.get(prop)
                    rhs = _coerce(rhs_str)
                    op_fn = _OPS.get(op_str)
                    if op_fn:
                        try:
                            if not op_fn(lhs, rhs):
                                match = False
                                break
                        except TypeError:
                            match = False
                            break
                if match:
                    filtered.append(jrow)
            joined = filtered

        # ORDER BY
        om = _ORDER_RE.search(cypher)
        if om:
            sort_var, sort_prop = om.group(1), om.group(2)
            joined = sorted(joined, key=lambda jr: (
                not isinstance(jr.get(sort_var), dict),
                jr.get(sort_var, {}).get(sort_prop) if isinstance(jr.get(sort_var), dict) else None,
            ))

        # LIMIT
        lm = _LIMIT_RE.search(cypher)
        if lm:
            joined = joined[:int(lm.group(1))]

        return self._build_rel_return(cypher, from_var, to_var, joined)

    def _build_return(self, cypher: str, var: str, rows: list[dict]) -> list[dict]:
        ret_m = _RETURN_RE.search(cypher)
        ret_str = ret_m.group(1).strip() if ret_m else var

        # count(n) AS alias  or  count(*) AS alias
        cm = _COUNT_RE.search(ret_str)
        if cm:
            return [{cm.group(2): len(rows)}]

        # var.prop AS alias
        prop_returns = _PROP_RETURN_RE.findall(ret_str)
        if prop_returns:
            result = []
            for row in rows:
                out: dict[str, Any] = {}
                for v, prop, alias in prop_returns:
                    if v == var:
                        out[alias] = row.get(prop)
                result.append(out)
            return result

        # bare var → return all props
        if _BARE_VAR_RE.match(ret_str.strip()):
            return list(rows)

        return list(rows)

    def _build_rel_return(self, cypher: str, from_var: str, to_var: str, joined: list[dict]) -> list[dict]:
        ret_m = _RETURN_RE.search(cypher)
        ret_str = ret_m.group(1).strip() if ret_m else f"{from_var}, {to_var}"

        # count(*) AS alias  or  count(var) AS alias
        cm = _COUNT_RE.search(ret_str)
        if cm:
            return [{cm.group(2): len(joined)}]

        # var.prop AS alias
        prop_returns = _PROP_RETURN_RE.findall(ret_str)
        if prop_returns:
            result = []
            for jr in joined:
                out: dict[str, Any] = {}
                for v, prop, alias in prop_returns:
                    node_row = jr.get(v)
                    if isinstance(node_row, dict):
                        out[alias] = node_row.get(prop)
                result.append(out)
            return result

        # Return all props from both nodes
        result = []
        for jr in joined:
            out = {}
            for v in (from_var, to_var):
                node = jr.get(v, {})
                if isinstance(node, dict):
                    for k, val in node.items():
                        out[f"{v}.{k}"] = val
            result.append(out)
        return result

    # ── Metadata ───────────────────────────────────────────────────────────────

    def get_schema(self) -> dict:
        nodes = [
            {
                "label": label,
                "properties": [
                    {"name": p.name, "type_category": p.type_category}
                    for p in props
                ],
            }
            for label, props in self._node_schema.items()
        ]
        relationships = [
            {
                "type": rel_type,
                "from_label": meta["from"],
                "to_label": meta["to"],
                "properties": [
                    {"name": p.name, "type_category": p.type_category}
                    for p in meta["props"]
                ],
            }
            for rel_type, meta in self._rel_schema.items()
        ]
        return {"nodes": nodes, "relationships": relationships}

    def get_stats(self) -> dict:
        return {
            "node_counts": {label: len(rows) for label, rows in self._nodes.items()},
            "rel_counts": {rel_type: len(rows) for rel_type, rows in self._rels.items()},
        }

    def list_node_labels(self) -> list[str]:
        return list(self._nodes.keys())

    def list_rel_types(self) -> list[str]:
        return list(self._rels.keys())
