"""Phase 3 integration test helpers.

Restores the canonical graph fixture state before each test in
TestGraphGenerateAPI and TestGraphQueryAPI, so that each test starts
with the same KuzuClient state regardless of what the previous test did.
"""

import pytest

_RESTORE_CLASSES = {"TestGraphGenerateAPI", "TestGraphQueryAPI"}

_FULL_COUNTS = {
    "User": 20,
    "Post": 40,
    "Tag": 10,
    "FOLLOWS": 30,
    "AUTHORED": 40,
    "TAGGED_WITH": 25,
}


@pytest.fixture(autouse=True)
def restore_graph_state(request):
    cls = request.node.cls
    if cls is None or cls.__name__ not in _RESTORE_CLASSES:
        yield
        return

    try:
        schema_id = request.getfixturevalue("schema_id")
        client = request.getfixturevalue("client")
    except Exception:
        yield
        return

    resp = client.post(
        "/api/generate",
        json={"schema_id": schema_id, "row_counts": _FULL_COUNTS},
    )
    assert resp.status_code == 200, f"restore failed: {resp.text}"
    yield
