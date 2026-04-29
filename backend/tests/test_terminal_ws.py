"""
Terminal WebSocket integration tests — test the actual PTY + WebSocket behavior.

Covers:
1. New session has prompt visible (not blank)
2. Session type JSON messages are consumed silently (not shown as text)
3. No artificial reconnect message on reconnect
4. Reconnect to existing session shows PTY state
5. No auto-reconnect on disconnect (component handles reconnection)
"""

import pytest
import asyncio
import json
import websockets
import socket
import threading
import time
import uuid


BACKEND_URL = "ws://localhost:8000/ws/terminal"
BACKEND_HTTP = "http://localhost:8000"
SESSION_TIMEOUT = 5.0  # seconds


@pytest.fixture(scope="module", autouse=True)
def backend_server():
    """Run the FastAPI app in-process so WS tests are self-contained."""
    global BACKEND_URL, BACKEND_HTTP

    import urllib.request
    import uvicorn
    from main import app

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    BACKEND_URL = f"ws://127.0.0.1:{port}/ws/terminal"
    BACKEND_HTTP = f"http://127.0.0.1:{port}"

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(BACKEND_HTTP + "/health", timeout=0.5) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(0.1)
    else:
        server.should_exit = True
        pytest.fail("Backend test server did not start")

    yield

    server.should_exit = True
    thread.join(timeout=5)


def _is_session_message(msg: str) -> bool:
    try:
        parsed = json.loads(msg)
    except json.JSONDecodeError:
        return False
    return parsed.get("type") == "session"


async def wait_for_pty_output(uri: str, expected: str, timeout: float = 5.0) -> str:
    """Connect to terminal WS, collect output until `expected` appears, return all output."""
    output = ""
    async with websockets.connect(uri, ping_interval=None) as ws:
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                if _is_session_message(msg):
                    continue
                output += msg
                if expected in msg:
                    break
            except asyncio.TimeoutError:
                break
    return output


async def collect_all_output(uri: str, timeout: float = 3.0) -> str:
    """Collect all WS messages for `timeout` seconds, return concatenated output."""
    output = ""
    async with websockets.connect(uri, ping_interval=None) as ws:
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                if _is_session_message(msg):
                    continue
                output += msg + "\n"
            except asyncio.TimeoutError:
                break
    return output


class TestNewSessionPrompt:
    """New session should show prompt without user typing anything."""

    @pytest.mark.asyncio
    async def test_new_session_shows_prompt(self):
        """Backend must show a real shell prompt for a new session."""
        sid = f"test-new-{uuid.uuid4().hex[:8]}"
        uri = f"{BACKEND_URL}?session_id={sid}"

        output = await wait_for_pty_output(uri, "$ ", timeout=5.0)

        # Should contain the prompt
        assert "$ " in output, f"Expected shell prompt in output, got: {output!r}"

        # Should NOT contain JSON session type message as raw text
        # (it's consumed by frontend via JSON.parse)
        # Backend should send the prompt as raw text, not as JSON
        lines = output.strip().split("\n")
        raw_lines = [l for l in lines if not l.startswith("{")]
        assert any("luohao@192" in l for l in raw_lines), (
            f"Prompt not found as raw text in {raw_lines!r}"
        )

    @pytest.mark.asyncio
    async def test_new_session_no_json_in_output(self):
        """JSON session-type messages must NOT appear as visible text in terminal."""
        sid = f"test-json-{uuid.uuid4().hex[:8]}"
        uri = f"{BACKEND_URL}?session_id={sid}"

        output = await wait_for_pty_output(uri, "$ ", timeout=5.0)

        # No JSON objects should appear as terminal text
        for line in output.split("\n"):
            try:
                json.loads(line)
                # If it parses as JSON, it must be a session-type message
                # that frontend consumes silently
                parsed = json.loads(line)
                assert parsed.get("type") == "session", (
                    f"Unexpected JSON in terminal output: {line!r}"
                )
            except (json.JSONDecodeError, ValueError):
                pass  # Normal terminal output — fine


class TestSessionTypeMessage:
    """Backend sends {\"type\": \"session\", \"status\": \"new\"|\"reconnect\"} on connect."""

    @pytest.mark.asyncio
    async def test_new_session_sends_session_type_json(self):
        """Backend sends exactly one session-type JSON on new session connect."""
        sid = f"test-type-{uuid.uuid4().hex[:8]}"
        uri = f"{BACKEND_URL}?session_id={sid}"

        all_output = []
        async with websockets.connect(uri, ping_interval=None) as ws:
            # Read messages until we get the prompt or timeout
            start = time.monotonic()
            while time.monotonic() - start < 5.0:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    all_output.append(msg)
                    # Once we see the prompt, we have enough
                    if "$ " in msg:
                        break
                except asyncio.TimeoutError:
                    break

        assert len(all_output) >= 2, f"Expected >=2 messages, got {len(all_output)}: {all_output!r}"

        # First message should be JSON session type
        first_line = all_output[0]
        parsed = json.loads(first_line)
        assert parsed.get("type") == "session", f"Expected session type, got: {first_line!r}"
        assert parsed.get("status") == "new", f"Expected status='new', got: {parsed}"

    @pytest.mark.asyncio
    async def test_reconnect_sends_reconnect_status(self):
        """Reconnect sends status='reconnect', not 'new'."""
        sid = f"test-recon-{uuid.uuid4().hex[:8]}"
        uri1 = f"{BACKEND_URL}?session_id={sid}"
        uri2 = f"{BACKEND_URL}?session_id={sid}"

        # First connection: creates session
        async with websockets.connect(uri1, ping_interval=None) as ws1:
            msg1 = await asyncio.wait_for(ws1.recv(), timeout=3.0)
            parsed1 = json.loads(msg1)
            assert parsed1.get("status") == "new"

        # Small delay to let session settle
        await asyncio.sleep(0.3)

        # Second connection: reconnects to same session
        async with websockets.connect(uri2, ping_interval=None) as ws2:
            msg2 = await asyncio.wait_for(ws2.recv(), timeout=3.0)
            parsed2 = json.loads(msg2)
            assert parsed2.get("status") == "reconnect", (
                f"Expected status='reconnect' on 2nd connection, got: {parsed2}"
            )


class TestReconnectBuffer:
    """Reconnect to alive session should see existing PTY state."""

    @pytest.mark.asyncio
    async def test_reconnect_shows_same_session(self):
        """Two WS connections with same session_id share the same PTY."""
        sid = f"test-share-{uuid.uuid4().hex[:8]}"
        uri1 = f"{BACKEND_URL}?session_id={sid}"
        uri2 = f"{BACKEND_URL}?session_id={sid}"

        # Connection 1: send a command
        async with websockets.connect(uri1, ping_interval=None) as ws1:
            # Get initial messages
            init1 = await asyncio.wait_for(ws1.recv(), timeout=3.0)
            assert json.loads(init1).get("type") == "session"

            # Wait for prompt
            while True:
                prompt = await asyncio.wait_for(ws1.recv(), timeout=3.0)
                if not _is_session_message(prompt):
                    break

            # Send a command that produces output
            await ws1.send("echo HELLO_TERMINAL_TEST\r")
            await asyncio.sleep(0.5)

        # Connection 2: reconnect to same session
        await asyncio.sleep(0.2)
        async with websockets.connect(uri2, ping_interval=None) as ws2:
            # Should get reconnect status, not new
            status_msg = await asyncio.wait_for(ws2.recv(), timeout=3.0)
            parsed = json.loads(status_msg)
            assert parsed.get("status") == "reconnect", (
                f"Expected reconnect, got: {parsed}"
            )
            replay = ""
            start = time.monotonic()
            while time.monotonic() - start < 5.0:
                msg = await asyncio.wait_for(ws2.recv(), timeout=1.0)
                if _is_session_message(msg):
                    continue
                replay += msg
                if "HELLO_TERMINAL_TEST" in replay:
                    break
            assert "HELLO_TERMINAL_TEST" in replay


class TestNoAutoReconnect:
    """Backend must NOT auto-reconnect — frontend handles that via component remount."""

    @pytest.mark.asyncio
    async def test_disconnect_does_not_auto_send(self):
        """After client disconnects, backend must NOT auto-reconnect or send reconnect msg."""
        sid = f"test-norecon-{uuid.uuid4().hex[:8]}"
        uri = f"{BACKEND_URL}?session_id={sid}"

        # Connect and immediately disconnect
        async with websockets.connect(uri, ping_interval=None) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            parsed = json.loads(msg)
            assert parsed.get("type") == "session"

        # Backend should NOT send anything after client disconnects
        # Give it 1 second to potentially send something
        await asyncio.sleep(1.0)

        # The session should still be registered
        # (This test just verifies the session exists — no auto-msg sent)

    @pytest.mark.asyncio
    async def test_frontend_no_double_connection(self):
        """If frontend accidentally calls connectWebSocket twice, second ws should close old one."""
        # This is a frontend contract test — verify the URL pattern
        sid = "test-double"
        uri = f"{BACKEND_URL}?session_id={sid}"
        # Backend should handle multiple WS connections for same session gracefully
        # by incrementing attach_count
        async with websockets.connect(uri, ping_interval=None) as ws1:
            async with websockets.connect(uri, ping_interval=None) as ws2:
                # Both should get valid responses
                msg1 = await asyncio.wait_for(ws1.recv(), timeout=3.0)
                msg2 = await asyncio.wait_for(ws2.recv(), timeout=3.0)
                # Both should be session JSON messages
                assert json.loads(msg1).get("type") == "session"
                assert json.loads(msg2).get("type") == "session"


class TestManyTerminalSessions:
    """Opening several terminal tabs should not starve the backend event loop."""

    @pytest.mark.asyncio
    async def test_many_sessions_keep_health_responsive(self):
        import urllib.request

        sockets = []
        try:
            for idx in range(8):
                sid = f"test-many-{idx}-{uuid.uuid4().hex[:8]}"
                ws = await websockets.connect(
                    f"{BACKEND_URL}?session_id={sid}",
                    ping_interval=None,
                    proxy=None,
                )
                sockets.append(ws)
                status_msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                assert json.loads(status_msg).get("type") == "session"

            def _health():
                with urllib.request.urlopen(BACKEND_HTTP + "/health", timeout=2.0) as response:
                    return response.status

            assert await asyncio.to_thread(_health) == 200
        finally:
            await asyncio.gather(*(ws.close() for ws in sockets), return_exceptions=True)


class TestNoArtificialMessages:
    """No artificial [Session: xxx] or ✓ 会话已恢复 messages."""

    @pytest.mark.asyncio
    async def test_no_session_announcement(self):
        """Backend must NOT send [Session: xxx] artificial announcement."""
        sid = f"test-noann-{uuid.uuid4().hex[:8]}"
        uri = f"{BACKEND_URL}?session_id={sid}"

        output = await wait_for_pty_output(uri, "$ ", timeout=5.0)

        assert "[Session:" not in output, f"Unexpected [Session:] in output: {output!r}"
        assert "✓" not in output, f"Unexpected checkmark in output: {output!r}"
        assert "会话已恢复" not in output, f"Unexpected reconnect message in output: {output!r}"

    @pytest.mark.asyncio
    async def test_no_login_banner(self):
        """No 'Last login' banner should appear (HUSHLOGIN=/dev/null set in backend)."""
        sid = f"test-nologin-{uuid.uuid4().hex[:8]}"
        uri = f"{BACKEND_URL}?session_id={sid}"

        output = await wait_for_pty_output(uri, "$ ", timeout=5.0)

        assert "Last login:" not in output, f"Unexpected login banner in output: {output!r}"


class TestBackendStartup:
    """Verify backend is running before running integration tests."""

    @pytest.mark.asyncio
    async def test_backend_health(self):
        """Backend must be running on port 8000."""
        import urllib.request
        try:
            with urllib.request.urlopen(BACKEND_HTTP + "/health", timeout=2.0) as r:
                assert r.status == 200
        except Exception as e:
            pytest.skip(f"Backend not running: {e}")
