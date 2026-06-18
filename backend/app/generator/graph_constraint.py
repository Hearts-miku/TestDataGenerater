"""GraphConstraintSolver — generation order, node ID pools, deduplication."""

from __future__ import annotations

import random
from typing import Any

from app.core.schema_model import GenerationStep, GraphSchemaModel


class GraphConstraintSolver:
    def __init__(self, schema: GraphSchemaModel) -> None:
        self._schema = schema
        # node_id_pool[label] = list of generated IDs available for relationship sampling
        self._node_id_pool: dict[str, list[Any]] = {}

    # ── Generation order ──────────────────────────────────────────────────────

    def generation_order(self) -> list[GenerationStep]:
        """All nodes first (in schema order), then all relationships."""
        steps: list[GenerationStep] = [
            GenerationStep(step=i, name=n.label, kind="node")
            for i, n in enumerate(self._schema.nodes)
        ]
        base = len(steps)
        steps += [
            GenerationStep(step=base + i, name=r.type, kind="relationship")
            for i, r in enumerate(self._schema.relationships)
        ]
        return steps

    # ── Node ID pool management ───────────────────────────────────────────────

    def register_node_ids(self, label: str, ids: list[Any]) -> None:
        self._node_id_pool.setdefault(label, []).extend(ids)

    def sample_node_ids(self, label: str, n: int) -> list[Any]:
        pool = self._node_id_pool.get(label, [])
        if not pool:
            raise ValueError(f"no nodes registered for label {label!r} — generate nodes first")
        return [random.choice(pool) for _ in range(n)]

    # ── Deduplication ─────────────────────────────────────────────────────────

    def deduplicate_nodes(
        self,
        batch: list[dict[str, Any]],
        unique_props: list[str],
    ) -> list[dict[str, Any]]:
        seen: set[tuple] = set()
        result: list[dict[str, Any]] = []
        for row in batch:
            key = tuple(row.get(p) for p in unique_props)
            if key not in seen:
                seen.add(key)
                result.append(row)
        return result

    def deduplicate_rels(
        self,
        rels: list[dict[str, Any]],
        unique_on: list[str],
    ) -> list[dict[str, Any]]:
        seen: set[tuple] = set()
        result: list[dict[str, Any]] = []
        for rel in rels:
            key = tuple(rel.get(k) for k in unique_on)
            if key not in seen:
                seen.add(key)
                result.append(rel)
        return result
