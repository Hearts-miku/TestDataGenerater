"""
Phase 4 · 集成测试 — WebSocket 流式生成进度
覆盖任务：P4-B5（WS /ws/generate）

需要运行中的 uvicorn。
"""

import json
import os
import time
import pytest
import httpx
from websockets.sync.client import connect as ws_connect

BASE_HTTP = os.getenv("DATAFORGE_URL", "http://127.0.0.1:8000")
BASE_WS   = BASE_HTTP.replace("http://", "ws://").replace("https://", "wss://")

DDL = """
CREATE TABLE users (
    id    INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) NOT NULL UNIQUE
);
"""


@pytest.fixture(scope="module")
def schema_id():
    with httpx.Client(base_url=BASE_HTTP, timeout=15.0) as c:
        resp = c.post("/api/parse", json={"source": DDL, "type": "ddl"})
        assert resp.status_code == 200
        return resp.json()["schema_id"]


class TestWebSocketStreaming:
    def test_ws_connection_accepted(self, schema_id):
        with ws_connect(f"{BASE_WS}/ws/generate") as ws:
            ws.send(json.dumps({
                "schema_id": schema_id,
                "row_counts": {"users": 20},
                "ai_enabled": False,
            }))
            msg = json.loads(ws.recv(timeout=30))
            assert "type" in msg

    def test_receives_progress_messages(self, schema_id):
        messages = []
        with ws_connect(f"{BASE_WS}/ws/generate") as ws:
            ws.send(json.dumps({
                "schema_id": schema_id,
                "row_counts": {"users": 50},
                "ai_enabled": False,
            }))
            for _ in range(30):
                try:
                    msg = json.loads(ws.recv(timeout=15))
                    messages.append(msg)
                    if msg.get("type") in ("done", "error"):
                        break
                except Exception:
                    break
        progress_msgs = [m for m in messages if m.get("type") == "progress"]
        assert len(progress_msgs) >= 1

    def test_progress_percentage_increases(self, schema_id):
        percentages = []
        with ws_connect(f"{BASE_WS}/ws/generate") as ws:
            ws.send(json.dumps({
                "schema_id": schema_id,
                "row_counts": {"users": 100},
                "ai_enabled": False,
            }))
            for _ in range(50):
                try:
                    msg = json.loads(ws.recv(timeout=15))
                    if msg.get("type") == "progress":
                        percentages.append(msg.get("percent", 0))
                    if msg.get("type") in ("done", "error"):
                        break
                except Exception:
                    break
        if len(percentages) >= 2:
            assert percentages[-1] >= percentages[0]

    def test_final_message_type_done(self, schema_id):
        final_msg = None
        with ws_connect(f"{BASE_WS}/ws/generate") as ws:
            ws.send(json.dumps({
                "schema_id": schema_id,
                "row_counts": {"users": 10},
                "ai_enabled": False,
            }))
            for _ in range(60):
                try:
                    msg = json.loads(ws.recv(timeout=15))
                    if msg.get("type") in ("done", "error"):
                        final_msg = msg
                        break
                except Exception:
                    break
        assert final_msg is not None
        assert final_msg["type"] == "done"

    def test_done_message_contains_row_counts(self, schema_id):
        final_msg = None
        with ws_connect(f"{BASE_WS}/ws/generate") as ws:
            ws.send(json.dumps({
                "schema_id": schema_id,
                "row_counts": {"users": 10},
                "ai_enabled": False,
            }))
            for _ in range(60):
                try:
                    msg = json.loads(ws.recv(timeout=15))
                    if msg.get("type") == "done":
                        final_msg = msg
                        break
                except Exception:
                    break
        assert final_msg is not None
        assert final_msg.get("tables", {}).get("users", {}).get("generated") == 10

    def test_invalid_schema_id_returns_error(self):
        with ws_connect(f"{BASE_WS}/ws/generate") as ws:
            ws.send(json.dumps({
                "schema_id": "invalid-xyz",
                "row_counts": {"users": 5},
            }))
            msg = json.loads(ws.recv(timeout=10))
        assert msg.get("type") == "error"

    def test_preview_rows_sent_mid_stream(self, schema_id):
        preview_received = False
        with ws_connect(f"{BASE_WS}/ws/generate") as ws:
            ws.send(json.dumps({
                "schema_id": schema_id,
                "row_counts": {"users": 200},
                "ai_enabled": False,
            }))
            for _ in range(60):
                try:
                    msg = json.loads(ws.recv(timeout=15))
                    if msg.get("type") == "preview":
                        preview_received = True
                    if msg.get("type") in ("done", "error"):
                        break
                except Exception:
                    break
        assert preview_received
