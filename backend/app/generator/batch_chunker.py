"""BatchChunker — splits large row-count dicts into memory-safe chunks."""

from __future__ import annotations

from typing import Callable, Generator


class BatchChunker:
    """Yields successive per-table chunk dicts that together sum to the requested totals.

    Each yielded dict has the same keys as ``row_counts`` but with at most
    ``chunk_size`` rows per table per chunk.  Tables whose requested count
    doesn't divide evenly get a smaller final chunk.

    Example::

        chunker = BatchChunker(chunk_size=1_000)
        for chunk in chunker.split_counts({"users": 2_500, "orders": 800}):
            # chunk == {"users": 1000, "orders": 800} on first pass
            #         {"users": 1000, "orders": 0}    on second pass (orders done)
            #         {"users": 500,  "orders": 0}    on third pass
            generate_and_write(chunk)
    """

    def __init__(self, chunk_size: int = 10_000) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.chunk_size = chunk_size

    def split_counts(
        self,
        row_counts: dict[str, int],
        on_chunk: Callable[[int, int], None] | None = None,
    ) -> Generator[dict[str, int], None, None]:
        """Yield chunk dicts.

        Args:
            row_counts: Mapping of table name → total rows to generate.
            on_chunk:   Optional callback called as ``on_chunk(chunk_index, total_chunks)``
                        (1-based) before each chunk is yielded.
        """
        # Filter out tables with zero or negative counts
        active = {t: n for t, n in row_counts.items() if n > 0}
        if not active:
            return

        # Number of chunks needed = max over all tables
        n_chunks = max(
            (n + self.chunk_size - 1) // self.chunk_size
            for n in active.values()
        )

        remaining = dict(active)

        for chunk_idx in range(1, n_chunks + 1):
            if on_chunk is not None:
                on_chunk(chunk_idx, n_chunks)

            chunk: dict[str, int] = {}
            for table, left in remaining.items():
                take = min(left, self.chunk_size)
                chunk[table] = take
                remaining[table] = left - take

            yield chunk
