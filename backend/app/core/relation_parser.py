"""Relation parser — extract table-to-table reference relationships from a
Neo4j/Cypher *schema graph* file (e.g. test_ddl/schema_graph.cypher).

Doris/StarRocks OLAP tables carry no explicit FOREIGN KEY. Instead, the project
ships a hand-curated Cypher schema graph where each edge encodes a join via a
shared column, e.g.::

    MATCH (a:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_AST'})
    MATCH (b:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
    MERGE (a)-[r:BELONGS_TO_CUSTOMER]->(b)
    SET r.via  = 'party_id → party_id', ...

Convention (verified against the file):
  * MERGE arrow goes  child ──▶ parent   (referencing table ──▶ authority table)
  * ``via = 'child_col → parent_col'``   (left = child column, right = parent column)

We turn each edge into a ``Relation(child_table, child_col, parent_table, parent_col)``
so the generator can populate the parent's key pool first and have the child
sample from it — guaranteeing every child key value joins back to a parent row.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# One relationship block: two MATCH lines, a MERGE edge, and the via string.
_BLOCK_RE = re.compile(
    r"MATCH\s*\(\s*(\w+)\s*:Table\s*\{\s*fqn\s*:\s*'([^']+)'\s*\}\s*\)\s*"
    r"MATCH\s*\(\s*(\w+)\s*:Table\s*\{\s*fqn\s*:\s*'([^']+)'\s*\}\s*\)\s*"
    r"MERGE\s*\(\s*(\w+)\s*\)\s*-\s*\[[^\]]*\]\s*->\s*\(\s*(\w+)\s*\)\s*"
    r"SET\s+r\.via\s*=\s*'([^']*)'",
    re.IGNORECASE | re.DOTALL,
)

# Arrows / equivalence markers used inside a via string.
_ARROW_RE = re.compile(r"\s*(?:→|->|↔|⇒|≈)\s*")
# A SQL-ish identifier (ascii). Used to pull the column name out of a segment
# that may also contain CJK annotations like "ar_agt_id 联动".
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Bracketed annotations to strip: full-width （...） and ascii (...).
_BRACKET_RE = re.compile(r"（[^）]*）|\([^)]*\)")


@dataclass(frozen=True)
class Relation:
    """A child column that must reference an existing parent column value."""
    child_table: str
    child_col: str
    parent_table: str
    parent_col: str


def _table_name(fqn: str) -> str:
    """'EDWICL_DATA.C_PT_INDV_CUST_BASIC' -> 'C_PT_INDV_CUST_BASIC'."""
    return fqn.rsplit(".", 1)[-1]


def _first_ident(segment: str) -> str | None:
    m = _IDENT_RE.search(segment)
    return m.group(0) if m else None


def _parse_via(via: str) -> list[tuple[str, str]]:
    """Parse a via string into a list of (child_col, parent_col) pairs.

    Handles:
      'party_id → party_id'                      -> [(party_id, party_id)]
      'ecf_party_id → party_id'                  -> [(ecf_party_id, party_id)]
      'ta_client → cap_acct_no（交易账号）'        -> [(ta_client, cap_acct_no)]
      'a → b  /  c → d'                          -> [(a, b), (c, d)]
      'party_id / cust_no → party_id'            -> [(party_id, party_id), (cust_no, party_id)]
      'cust_no'                                  -> [(cust_no, cust_no)]   (same-name join)
      'cap_acct_no → cap_acct_no / ar_agt_id 联动' -> [(cap_acct_no, cap_acct_no), (ar_agt_id, ar_agt_id)]
    """
    cleaned = _BRACKET_RE.sub("", via)
    pairs: list[tuple[str, str]] = []
    for segment in re.split(r"\s*/\s*", cleaned):
        segment = segment.strip()
        if not segment:
            continue
        parts = _ARROW_RE.split(segment)
        if len(parts) >= 2:
            child = _first_ident(parts[0])
            parent = _first_ident(parts[1])
            if child and parent:
                pairs.append((child, parent))
        else:
            # No arrow — a bare column name implies a same-name join.
            col = _first_ident(segment)
            if col:
                pairs.append((col, col))
    return pairs


def relations_to_cypher(
    relations: list[Relation],
    table_comments: dict[str, str] | None = None,
) -> str:
    """Serialize relations back to a Neo4j/Cypher schema graph.

    Output is compatible with :func:`parse_schema_graph` (round-trips), using
    each table name as its ``fqn``. Single quotes in comments are escaped.
    """
    table_comments = table_comments or {}

    def esc(s: str) -> str:
        return (s or "").replace("\\", "\\\\").replace("'", "\\'")

    tables: list[str] = []
    seen: set[str] = set()
    for r in relations:
        for t in (r.child_table, r.parent_table):
            if t not in seen:
                seen.add(t)
                tables.append(t)

    lines: list[str] = [
        "// ================================================================",
        "// DataForge auto-generated schema graph",
        "// 表间关系（child 引用 parent，via = 连接字段）",
        "// ================================================================",
        "",
        "CREATE CONSTRAINT table_fqn_unique IF NOT EXISTS",
        "  FOR (t:Table) REQUIRE t.fqn IS UNIQUE;",
        "",
    ]
    for t in sorted(tables):
        lines.append(f"MERGE (t:Table {{fqn: '{esc(t)}'}})")
        comment = table_comments.get(t, "")
        lines.append(f"SET t.name = '{esc(t)}', t.comment = '{esc(comment)}';")
        lines.append("")

    lines.append("")
    for r in relations:
        lines.append(f"MATCH (a:Table {{fqn: '{esc(r.child_table)}'}})")
        lines.append(f"MATCH (b:Table {{fqn: '{esc(r.parent_table)}'}})")
        lines.append("MERGE (a)-[r:REFERENCES]->(b)")
        lines.append(f"SET r.via  = '{esc(r.child_col)} → {esc(r.parent_col)}';")
        lines.append("")

    return "\n".join(lines)


def parse_schema_graph(cypher_src: str) -> list[Relation]:
    """Extract all child→parent reference relations from a schema-graph Cypher file."""
    relations: list[Relation] = []
    seen: set[tuple[str, str, str, str]] = set()

    for m in _BLOCK_RE.finditer(cypher_src):
        var1, fqn1, var2, fqn2, merge_from, merge_to, via = m.groups()
        fqn_by_var = {var1: fqn1, var2: fqn2}
        child_fqn = fqn_by_var.get(merge_from)
        parent_fqn = fqn_by_var.get(merge_to)
        if not child_fqn or not parent_fqn:
            continue

        child_table = _table_name(child_fqn)
        parent_table = _table_name(parent_fqn)
        if child_table == parent_table:
            continue  # self-reference: nothing to close

        for child_col, parent_col in _parse_via(via):
            key = (child_table, child_col, parent_table, parent_col)
            if key in seen:
                continue
            seen.add(key)
            relations.append(
                Relation(child_table, child_col, parent_table, parent_col)
            )

    return relations
