"""Tests for terminal session persistence (Phase 8)

Verifies:
1. Server announces session id on connect: [Session: <id>]
2. Same session_id reuses same PTY PID
3. Different session_ids get separate PTY PIDs
4. Disconnect does NOT kill PTY (session persists)
5. No session_id creates a new random session each time
6. Reconnect shows '✓ 会话已恢复'
"""

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
            break
    return messages


@pytest.fixture
def client():
    """Synchronous test client with WebSocket support."""
    with TestClient(app) as c:
        yield c


class TestTerminalSessionPersistence:
    """Test terminal session store and routing."""

    def test_session_info_broadcast_on_connect(self, client):
        """Server should broadcast [Session: <session_id>] on connect."""
        session_id = str(uuid.uuid4())[:8]
        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws:
            msg = receive_text_with_timeout(ws, timeout=5.0)
            assert msg.startswith("[Session:"), f"Expected session announcement, got: {msg!r}"

    def test_same_session_id_reuses_pty(self, client):
        """Two connections with same session_id should share one PTY process."""
        import tempfile, os
        session_id = str(uuid.uuid4())[:8]
        tmp = os.path.join(tempfile.gettempdir(), f"hermes_test_{session_id}")

        # Connection 1: create session and write PID to temp file
        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws1:
            receive_text_with_timeout(ws1, timeout=5.0)
            # Write PID directly to file (no bash echo/parsing needed)
            ws1.send_text(f"echo $$ > {tmp}\r")
            # Wait for bash prompt to return (signals command completed)
            for _ in range(30):
                try:
                    receive_text_with_timeout(ws1, timeout=2.0)
                except TimeoutError:
                    break

        # Read PID from file
        pid1 = open(tmp).read().strip() if os.path.exists(tmp) else ""

        # Connection 2: same session_id — should reuse PTY
        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws2:
            msg2 = receive_text_with_timeout(ws2, timeout=5.0)
            assert msg2.startswith("[Session:")
            # Write PID again
            ws2.send_text(f"echo $$ > {tmp}2\r")
            for _ in range(30):
                try:
                    receive_text_with_timeout(ws2, timeout=2.0)
                except TimeoutError:
                    break

        pid2 = open(f"{tmp}2").read().strip() if os.path.exists(f"{tmp}2") else ""
        assert pid1 == pid2, f"PTY PID should be same: {pid1} vs {pid2}"

    def test_different_session_ids_get_separate_ptys(self, client):
        """Different session_ids should get separate PTY processes."""
        import tempfile, os
        session1 = str(uuid.uuid4())[:8]
        session2 = str(uuid.uuid4())[:8]
        tmp1 = os.path.join(tempfile.gettempdir(), f"hermes_test_{session1}")
        tmp2 = os.path.join(tempfile.gettempdir(), f"hermes_test_{session2}")

        with client.websocket_connect(f"/ws/terminal?session_id={session1}") as ws1:
            receive_text_with_timeout(ws1, timeout=5.0)
            ws1.send_text(f"echo $$ > {tmp1}\r")
            for _ in range(30):
                try:
                    receive_text_with_timeout(ws1, timeout=2.0)
                except TimeoutError:
                    break

        with client.websocket_connect(f"/ws/terminal?session_id={session2}") as ws2:
            receive_text_with_timeout(ws2, timeout=5.0)
            ws2.send_text(f"echo $$ > {tmp2}\r")
            for _ in range(30):
                try:
                    receive_text_with_timeout(ws2, timeout=2.0)
                except TimeoutError:
                    break

        pid1 = open(tmp1).read().strip() if os.path.exists(tmp1) else ""
        pid2 = open(tmp2).read().strip() if os.path.exists(tmp2) else ""
        assert pid1 and pid2, f"Should get PIDs for both sessions: pid1={pid1!r}, pid2={pid2!r}"
        assert pid1 != pid2, f"Different sessions should have different PTY PIDs: {pid1} == {pid2}"

    def test_disconnect_does_not_kill_pty(self, client):
        """Disconnecting a client should NOT kill the PTY — session stays alive."""
        session_id = str(uuid.uuid4())[:8]

        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws:
            receive_text_with_timeout(ws, timeout=5.0)  # session announcement
            ws.send_text("echo KEEPAlive\r")
            receive_text_with_timeout(ws, timeout=3.0)

        # Short delay
        time.sleep(0.5)

        # Reconnect: PTY should still be alive
        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws2:
            receive_text_with_timeout(ws2, timeout=5.0)  # session announcement
            ws2.send_text("echo STILL_ALIVE\r")
            msgs = receive_until(ws2, lambda m: "STILL_ALIVE" in m, timeout=5.0)
            assert any("STILL_ALIVE" in m for m in msgs), \
                f"PTY should be alive after disconnect-reconnect, got: {msgs}"

    def test_no_session_id_creates_new_session(self, client):
        """Connecting without session_id should create a new session each time."""
        with client.websocket_connect("/ws/terminal") as ws1:
            msg1 = receive_text_with_timeout(ws1, timeout=5.0)
            assert msg1.startswith("[Session:")

        with client.websocket_connect("/ws/terminal") as ws2:
            msg2 = receive_text_with_timeout(ws2, timeout=5.0)
            assert msg2.startswith("[Session:")

        assert msg1 != msg2, "No session_id should create separate sessions"

    def test_reconnect_shows_session_restored_message(self, client):
        """Reconnecting to an existing session should receive '✓ 会话已恢复'."""
        session_id = str(uuid.uuid4())[:8]

        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws:
            receive_text_with_timeout(ws, timeout=5.0)
            ws.send_text("echo HELLO\r")
            receive_text_with_timeout(ws, timeout=3.0)

        # Reconnect
        with client.websocket_connect(f"/ws/terminal?session_id={session_id}") as ws2:
            receive_text_with_timeout(ws2, timeout=5.0)  # session announcement
            msgs = receive_until(ws2, lambda m: "会话已恢复" in m, timeout=5.0)
            assert any("会话已恢复" in m for m in msgs), \
                f"Expected '✓ 会话已恢复' in reconnect messages, got: {msgs}"
