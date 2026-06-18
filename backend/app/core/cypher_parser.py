"""Cypher schema parser — comment-based and standard Cypher syntax.

Supported syntax (comment-based)::

    CREATE CONSTRAINT ON (alias:Label) ASSERT alias.prop IS UNIQUE;
    // (:Label {prop: TYPE, prop2: TYPE})
    // (:FromLabel)-[:REL_TYPE {prop: TYPE}]->(:ToLabel)
    // (:Label)          # node with no properties

Supported syntax (standard Cypher — parsed as fallback when no comment notation found)::

    CREATE CONSTRAINT name IF NOT EXISTS FOR (n:Label) REQUIRE n.prop IS UNIQUE;
    MERGE (alias:Label {prop: value}) SET alias.prop = value, ...
    MATCH (a:LabelA {...}) MATCH (b:LabelB {...}) MERGE (a)-[r:REL_TYPE]->(b) SET r.p = ...
"""

from __future__ import annotations

import re
from typing import Optional

from app.core.relation_parser import parse_schema_graph
from app.core.schema_model import (
    GenerationStep,
    GraphSchemaModel,
    NodeDef,
    PropertyDef,
    RelationalSchemaModel,
    RelationshipDef,
)

# ── Comment-based notation regexes ───────────────────────────────────────────

# // (:Label {props})  or  // (:Label)
_NODE_LINE_RE = re.compile(
    r'^//\s*\(:(\w+)(?:\s*\{([^}]*)\})?\)\s*$'
)
# // (:From)-[:REL {props}]->(:To)  or  // (:From)-[:REL]->(:To)
_REL_LINE_RE = re.compile(
    r'^//\s*\(:(\w+)\)-\[:(\w+)(?:\s*\{([^}]*)\})?\]->\(:(\w+)\)\s*$'
)
# CREATE CONSTRAINT ON (alias:Label) ASSERT alias.prop IS UNIQUE  (old syntax)
_CONSTRAINT_RE = re.compile(
    r'CREATE\s+CONSTRAINT\s+ON\s+\(\w+:(\w+)\)\s+ASSERT\s+\w+\.(\w+)\s+IS\s+UNIQUE',
    re.IGNORECASE,
)
# prop: TYPE  (inside { } in comment-based notation)
_PROP_RE = re.compile(r'(\w+)\s*:\s*(\w+)')

# ── Standard Cypher fallback regexes ─────────────────────────────────────────

# MATCH/MERGE (alias:Label {inline_props})
_STD_NODE_RE = re.compile(
    r'(?:MATCH|MERGE)\s*\(\s*(\w+):(\w+)(?:\s*\{([^}]*)\})?\s*\)',
    re.IGNORECASE,
)
# MERGE (from_var)-[rel_var:REL_TYPE {optional}]->(to_var)
_STD_REL_RE = re.compile(
    r'MERGE\s*\(\s*(\w+)\s*\)-\[\s*(\w+):(\w+)(?:\s*\{[^}]*)?\s*\]->\(\s*(\w+)\s*\)',
    re.IGNORECASE,
)
# SET or comma continuation: alias.prop =  (also bare continuation lines like "    t.name = ...")
_STD_SET_RE = re.compile(r'(?:SET|,)\s*(\w+)\.(\w+)\s*=', re.IGNORECASE)
_STD_PROP_CONT_RE = re.compile(r'^(\w+)\.(\w+)\s*=', re.IGNORECASE)
# Neo4j 4.x+ constraint: CREATE CONSTRAINT name [IF NOT EXISTS] FOR (n:Label) REQUIRE n.prop IS UNIQUE
_NEO4J4_CONSTRAINT_RE = re.compile(
    r'CREATE\s+CONSTRAINT\s+\w+(?:\s+IF\s+NOT\s+EXISTS)?\s+FOR\s*\(\s*\w+:(\w+)\s*\)\s+REQUIRE\s+\w+\.(\w+)\s+IS\s+UNIQUE',
    re.IGNORECASE,
)

_TYPE_MAP: dict[str, str] = {
    'INT': 'integer', 'INT8': 'integer', 'INT16': 'integer',
    'INT32': 'integer', 'INT64': 'integer', 'INTEGER': 'integer',
    'SERIAL': 'integer', 'UINT8': 'integer', 'UINT16': 'integer',
    'UINT32': 'integer', 'UINT64': 'integer',
    'FLOAT': 'float', 'FLOAT32': 'float', 'FLOAT64': 'float', 'DOUBLE': 'float',
    'STRING': 'string', 'VARCHAR': 'string', 'CHAR': 'string',
    'TEXT': 'text', 'BLOB': 'text',
    'BOOLEAN': 'boolean', 'BOOL': 'boolean',
    'DATE': 'date',
    'TIMESTAMP': 'datetime', 'DATETIME': 'datetime',
    'TIMESTAMP_NS': 'datetime', 'TIMESTAMP_SEC': 'datetime',
    'INTERVAL': 'string', 'UUID': 'string',
}


def _map_type(raw: str) -> str:
    return _TYPE_MAP.get(raw.upper(), 'unknown')


def _parse_props(props_str: Optional[str]) -> list[PropertyDef]:
    if not props_str:
        return []
    return [
        PropertyDef(name=m.group(1), type_category=_map_type(m.group(2)), raw_type=m.group(2).upper())
        for m in _PROP_RE.finditer(props_str)
    ]


class CypherParser:
    """Parse Cypher schema notation (comment-based or standard MERGE/MATCH/SET) into RelationalSchemaModel."""

    def parse(self, source: str) -> RelationalSchemaModel:
        if not source or not source.strip():
            raise ValueError("empty schema: no input provided")

        # Phase 1: collect explicit node defs and constraints from comment-based notation
        nodes_map: dict[str, NodeDef] = {}
        rels: list[RelationshipDef] = []
        unique_props: dict[str, set[str]] = {}

        for line in source.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('--') or stripped.startswith('/*') or stripped.startswith('*/'):
                continue

            cm = _CONSTRAINT_RE.search(stripped)
            if cm:
                label, prop = cm.group(1), cm.group(2)
                unique_props.setdefault(label, set()).add(prop)
                continue

            if stripped.startswith('//'):
                rm = _REL_LINE_RE.match(stripped)
                if rm:
                    from_l, rel_type, props_str, to_l = rm.groups()
                    props = _parse_props(props_str)
                    rels.append(RelationshipDef(type=rel_type, from_label=from_l, to_label=to_l, properties=props))
                    continue

                nm = _NODE_LINE_RE.match(stripped)
                if nm:
                    label, props_str = nm.groups()
                    props = _parse_props(props_str)
                    if label in nodes_map:
                        existing = nodes_map[label]
                        known = {p.name for p in existing.properties}
                        extra = [p for p in props if p.name not in known]
                        nodes_map[label] = NodeDef(
                            label=label,
                            properties=list(existing.properties) + extra,
                            unique_properties=existing.unique_properties,
                        )
                    else:
                        nodes_map[label] = NodeDef(label=label, properties=props)
                    continue
                continue

            if stripped.startswith('(') or stripped.startswith('[') or stripped.startswith('-['):
                raise ValueError(f"Malformed schema definition: {stripped!r}")

        # Phase 1b: if comment-based notation found nothing, try standard Cypher.
        if not nodes_map and not rels:
            # First, detect an *instance-level table-relationship graph*: nodes all
            # share one label (e.g. :Table) and are distinguished by an `fqn`
            # property, with edges connecting specific instances via shared columns
            # (the format of test_ddl/schema_graph.cypher). Parsing that as a plain
            # schema collapses every table into a single :Table node, which is wrong.
            table_rels = parse_schema_graph(source)
            if table_rels:
                nodes_map, rels = self._build_from_table_relations(source, table_rels)
            else:
                nodes_map, rels = self._parse_standard_cypher(source, unique_props)

        # Phase 2: validate relationship endpoints
        for rel in rels:
            from_l, to_l = rel.from_label, rel.to_label
            if from_l == to_l:
                nodes_map.setdefault(from_l, NodeDef(label=from_l))
            else:
                for label in (from_l, to_l):
                    if label not in nodes_map:
                        raise ValueError(
                            f"undefined node label {label!r} referenced in "
                            f"relationship {rel.type!r}"
                        )

        # Phase 3: apply unique constraints; auto-create node stubs from constraint labels
        for label, props_set in unique_props.items():
            if label in nodes_map:
                existing = nodes_map[label]
                merged = sorted(set(existing.unique_properties) | props_set)
                nodes_map[label] = NodeDef(
                    label=label,
                    properties=existing.properties,
                    unique_properties=merged,
                )
            else:
                nodes_map[label] = NodeDef(
                    label=label,
                    properties=[],
                    unique_properties=sorted(props_set),
                )

        if not nodes_map and not rels:
            raise ValueError(
                "empty schema: no node or relationship definitions found.\n"
                "DataForge expects comment-based schema notation, e.g.:\n"
                "  // (:User {id: INT, name: STRING})\n"
                "  // (:User)-[:FOLLOWS]->(:User)\n"
                "  CREATE CONSTRAINT ON (u:User) ASSERT u.id IS UNIQUE;\n"
                "Or standard Cypher MERGE/MATCH/SET statements (Neo4j export format)."
            )

        # Build generation order: nodes first, then relationships
        nodes = list(nodes_map.values())
        steps: list[GenerationStep] = [
            GenerationStep(step=i, name=n.label, kind="node")
            for i, n in enumerate(nodes)
        ] + [
            GenerationStep(step=len(nodes) + i, name=r.type, kind="relationship")
            for i, r in enumerate(rels)
        ]

        return RelationalSchemaModel(
            schema_type="graph",
            dialect="cypher",
            nodes=nodes,
            relationships=rels,
            generation_order=steps,
        )

    def _build_from_table_relations(
        self,
        source: str,
        relations: list,
    ) -> tuple[dict[str, NodeDef], list[RelationshipDef]]:
        """Build a graph schema from an instance-level table-relationship graph.

        Each distinct table (``fqn``) becomes its own node (label = table name),
        and every shared-column edge becomes a relationship ``child → parent``,
        labelled with the join columns. This makes the Graph view show the real
        table network instead of collapsing everything into one :Table node.
        """
        def tname(fqn: str) -> str:
            return fqn.rsplit('.', 1)[-1]

        tables: set[str] = set()
        for r in relations:
            tables.add(r.child_table)
            tables.add(r.parent_table)
        # Include isolated tables that are declared but have no edges.
        for m in re.finditer(r"fqn\s*:\s*'([^']+)'", source):
            tables.add(tname(m.group(1)))

        nodes_map = {t: NodeDef(label=t) for t in sorted(tables)}
        rels = [
            RelationshipDef(
                type=f"{r.child_col}→{r.parent_col}",
                from_label=r.child_table,
                to_label=r.parent_table,
            )
            for r in relations
        ]
        return nodes_map, rels

    def _parse_standard_cypher(
        self,
        source: str,
        unique_props: dict[str, set[str]],
    ) -> tuple[dict[str, NodeDef], list[RelationshipDef]]:
        """Extract schema from standard Cypher MERGE/MATCH/SET statements.

        Handles Neo4j data-loading scripts where nodes are created via MERGE and
        relationships via MATCH+MERGE patterns. All property types default to STRING
        since Cypher scripts carry values, not type annotations.
        """
        # Collect Neo4j 4.x+ constraints from the full source (may span two lines)
        for cm in _NEO4J4_CONSTRAINT_RE.finditer(source):
            label, prop = cm.group(1), cm.group(2)
            unique_props.setdefault(label, set()).add(prop)

        var_to_label: dict[str, str] = {}      # node alias → label
        rel_var_to_type: dict[str, str] = {}   # relationship alias → type
        label_props: dict[str, set[str]] = {}  # label → property name set
        rel_props: dict[str, set[str]] = {}    # rel type → property name set

        # Ordered list of unique rel defs (from_label, rel_type, to_label)
        rel_defs: list[tuple[str, str, str]] = []
        seen_rel_types: set[str] = set()

        for line in source.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            # MATCH/MERGE node: capture alias → label, plus inline property names
            for nm in _STD_NODE_RE.finditer(stripped):
                var, label, inline_props = nm.group(1), nm.group(2), nm.group(3)
                var_to_label[var] = label
                label_props.setdefault(label, set())
                if inline_props:
                    # Extract property names from {key: value, ...}
                    for key in re.findall(r'(\w+)\s*:', inline_props):
                        label_props[label].add(key)

            # MERGE relationship: (from_var)-[rel_var:TYPE]->(to_var)
            rm = _STD_REL_RE.search(stripped)
            if rm:
                from_var, rel_alias, rel_type, to_var = rm.groups()
                rel_var_to_type[rel_alias] = rel_type
                if rel_type not in seen_rel_types:
                    from_label = var_to_label.get(from_var, '')
                    to_label = var_to_label.get(to_var, '')
                    if from_label and to_label:
                        rel_defs.append((from_label, rel_type, to_label))
                        seen_rel_types.add(rel_type)

            # SET / comma / bare continuation: alias.prop = value
            for pattern in (_STD_SET_RE, _STD_PROP_CONT_RE):
                for sm in pattern.finditer(stripped):
                    var, prop = sm.group(1), sm.group(2)
                    if var in var_to_label:
                        label_props[var_to_label[var]].add(prop)
                    elif var in rel_var_to_type:
                        rel_props.setdefault(rel_var_to_type[var], set()).add(prop)

        # Build NodeDef objects
        nodes_map: dict[str, NodeDef] = {}
        for label, props in label_props.items():
            prop_defs = [
                PropertyDef(name=p, type_category='string', raw_type='STRING')
                for p in sorted(props)
            ]
            nodes_map[label] = NodeDef(label=label, properties=prop_defs)

        # Build RelationshipDef objects
        rels: list[RelationshipDef] = []
        for from_label, rel_type, to_label in rel_defs:
            props = [
                PropertyDef(name=p, type_category='string', raw_type='STRING')
                for p in sorted(rel_props.get(rel_type, set()))
            ]
            rels.append(RelationshipDef(
                type=rel_type,
                from_label=from_label,
                to_label=to_label,
                properties=props,
            ))

        return nodes_map, rels
