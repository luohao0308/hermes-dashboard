"""Tests for browser terminal session persistence."""

import json
import os
import pytest
import uuid
import time
import threading
from starlette.testclient import TestClient
from main import app


def receive_text_with_timeout(ws, timeout=5.0):
    """Receive text from WebSocket with timeout using a background thread."""
    result = [None]
    error = [None]

    def _recv():
        try:
            result[0] = ws.receive_text()
        except Exception as e:
            error[0] = e

    t = threading.Thread(target=_recv, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if error[0]:
        raise error[0]
    if t.is_alive():
        raise TimeoutError(f"No message received within {timeout}s")
    return result[0]


def receive_until(ws, condition, timeout=5.0, poll_interval=0.1):
    """Keep receiving until condition is met or timeout."""
    start = time.time()
    messages = []
    while time.time() - start < timeout:
        try:
            msg = receive_text_with_timeout(ws, timeout=poll_interval)
            messages.append(msg)
            if condition(msg):
                return messages
        except TimeoutError:
            continue
    return messages


def receive_session_status(ws, expected_status=None):
    msg = receive_text_with_timeout(ws, timeout=5.0)
    parsed = json.loads(msg)
    assert parsed["type"] == "session"
    assert "session_id" in parsed
    if expected_status is not None:
        assert parsed["status"] == expected_status
    return parsed


def run_command(ws, command, expected, timeout=5.0):
    ws.send_text(f"{command}\r")
    msgs = receive_until(ws, lambda m: expected in m, timeout=timeout)
    assert any(expected in m for m in msgs), f"Expected {expected!r}, got: {msgs!r}"
    return msgs


@pytest.fixture
def client():
    """Synchronous test client with WebSocket support."""
    with TestClient(app) as c:
        yield c


class TestTerminalSessionPersistence:
    """Test terminal session store and routing."""

    def test_session_info_broadcast_on_connect(self, client):
        """Server should send structured session metadata on connect."""
        session_id = str(uuid.uuid4())[:8]
        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws:
            status = receive_session_status(ws, "new")
            assert status["session_id"] == session_id

    def test_same_session_id_reuses_pty(self, client):
        """Two connections with same session_id should share one PTY process."""
        import tempfile
        session_id = str(uuid.uuid4())[:8]
        tmp = os.path.join(tempfile.gettempdir(), f"hermes_test_{session_id}")

        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws1:
            receive_session_status(ws1, "new")
            run_command(ws1, f"echo $$ > {tmp}; echo PID_WRITTEN", "PID_WRITTEN")

        pid1 = open(tmp).read().strip() if os.path.exists(tmp) else ""
        assert pid1

        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws2:
            receive_session_status(ws2, "reconnect")
            run_command(ws2, f"echo $$ > {tmp}2; echo PID_WRITTEN_2", "PID_WRITTEN_2")

        pid2 = open(f"{tmp}2").read().strip() if os.path.exists(f"{tmp}2") else ""
        assert pid1 == pid2, f"PTY PID should be same: {pid1} vs {pid2}"

    def test_different_session_ids_get_separate_ptys(self, client):
        """Different session_ids should get separate PTY processes."""
        import tempfile
        session1 = str(uuid.uuid4())[:8]
        session2 = str(uuid.uuid4())[:8]
        tmp1 = os.path.join(tempfile.gettempdir(), f"hermes_test_{session1}")
        tmp2 = os.path.join(tempfile.gettempdir(), f"hermes_test_{session2}")

        with client.websocket_connect(f"/ws/terminal?session_id={session1}") as ws1:
            receive_session_status(ws1, "new")
            run_command(ws1, f"echo $$ > {tmp1}; echo PID1_WRITTEN", "PID1_WRITTEN")

        with client.websocket_connect(f"/ws/terminal?session_id={session2}") as ws2:
            receive_session_status(ws2, "new")
            run_command(ws2, f"echo $$ > {tmp2}; echo PID2_WRITTEN", "PID2_WRITTEN")

        pid1 = open(tmp1).read().strip() if os.path.exists(tmp1) else ""
        pid2 = open(tmp2).read().strip() if os.path.exists(tmp2) else ""
        assert pid1 and pid2, f"Should get PIDs for both sessions: pid1={pid1!r}, pid2={pid2!r}"
        assert pid1 != pid2, f"Different sessions should have different PTY PIDs: {pid1} == {pid2}"

    def test_disconnect_does_not_kill_pty(self, client):
        """Disconnecting a client should NOT kill the PTY — session stays alive."""
        session_id = str(uuid.uuid4())[:8]

        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws:
            receive_session_status(ws, "new")
            run_command(ws, "echo KEEPAlive", "KEEPAlive")

        # Short delay
        time.sleep(0.5)

        # Reconnect: PTY should still be alive
        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws2:
            receive_session_status(ws2, "reconnect")
            run_command(ws2, "echo STILL_ALIVE", "STILL_ALIVE")

    def test_no_session_id_creates_new_session(self, client):
        """Connecting without session_id should create a new session each time."""
        with client.websocket_connect("/ws/terminal") as ws1:
            status1 = receive_session_status(ws1, "new")

        with client.websocket_connect("/ws/terminal") as ws2:
            status2 = receive_session_status(ws2, "new")

        assert status1["session_id"] != status2["session_id"]

    def test_reconnect_reports_reconnect_status(self, client):
        """Reconnecting to an existing session should receive reconnect metadata."""
        session_id = str(uuid.uuid4())[:8]

        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws:
            receive_session_status(ws, "new")
            run_command(ws, "echo HELLO", "HELLO")

        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws2:
            status = receive_session_status(ws2, "reconnect")
            assert status["session_id"] == session_id
            replay = receive_until(ws2, lambda m: "HELLO" in m, timeout=5.0)
            assert any("HELLO" in m for m in replay), f"Expected replayed output, got: {replay!r}"
