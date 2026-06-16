"""
Phase 5 · 单元测试 — 批量分块生成器
覆盖任务：P5-B3（chunk_size 分块、内存控制）
"""

import pytest
from app.generator.batch_chunker import BatchChunker


@pytest.fixture
def chunker():
    return BatchChunker(chunk_size=1_000)


class TestChunkSplitting:
    def test_single_chunk_when_total_le_chunk_size(self, chunker):
        chunks = list(chunker.split_counts({"users": 500}))
        assert len(chunks) == 1
        assert chunks[0]["users"] == 500

    def test_splits_into_multiple_chunks(self, chunker):
        chunks = list(chunker.split_counts({"users": 3_500}))
        # 3500 / 1000 = 4 chunks (3×1000 + 1×500)
        assert len(chunks) == 4

    def test_chunk_sizes_sum_to_total(self, chunker):
        total = 7_777
        chunks = list(chunker.split_counts({"users": total}))
        assert sum(c["users"] for c in chunks) == total

    def test_last_chunk_is_remainder(self, chunker):
        chunks = list(chunker.split_counts({"users": 2_300}))
        assert chunks[-1]["users"] == 300

    def test_multiple_tables_split_independently(self, chunker):
        chunks = list(chunker.split_counts({"users": 2_500, "orders": 1_200}))
        total_users  = sum(c.get("users",  0) for c in chunks)
        total_orders = sum(c.get("orders", 0) for c in chunks)
        assert total_users  == 2_500
        assert total_orders == 1_200

    def test_zero_rows_produces_no_chunks(self, chunker):
        chunks = list(chunker.split_counts({"users": 0}))
        assert chunks == []

    def test_custom_chunk_size(self):
        chunker = BatchChunker(chunk_size=10_000)
        chunks = list(chunker.split_counts({"big": 100_000}))
        assert len(chunks) == 10
        assert all(c["big"] == 10_000 for c in chunks)

    def test_exactly_chunk_size(self, chunker):
        chunks = list(chunker.split_counts({"users": 1_000}))
        assert len(chunks) == 1
        assert chunks[0]["users"] == 1_000


class TestChunkerCallback:
    def test_progress_callback_called_per_chunk(self, chunker):
        calls = []
        list(chunker.split_counts(
            {"users": 3_000},
            on_chunk=lambda i, total: calls.append((i, total)),
        ))
        assert len(calls) == 3
        assert calls[0] == (1, 3)
        assert calls[-1] == (3, 3)

    def test_callback_receives_correct_total_chunks(self, chunker):
        received_totals = []
        list(chunker.split_counts(
            {"users": 4_500},
            on_chunk=lambda i, total: received_totals.append(total),
        ))
        assert all(t == 5 for t in received_totals)
