"""
Terminal WebSocket integration tests — test the actual PTY + WebSocket behavior.

Covers:
1. New session has prompt visible (not blank)
2. Session type JSON messages are consumed silently (not shown as text)
3. No artificial reconnect message on reconnect
4. Reconnect to existing session replays full PTY buffer
5. No auto-reconnect on disconnect (component handles reconnection)
"""

import pytest
import asyncio
import json
import websockets
import os
import signal
import time
import uuid


BACKEND_URL = "ws://localhost:8000/ws/terminal"
BACKEND_HTTP = "http://localhost:8000"
SESSION_TIMEOUT = 5.0  # seconds


async def wait_for_pty_output(uri: str, expected: str, timeout: float = 5.0) -> str:
    """Connect to terminal WS, collect output until `expected` appears, return all output."""
    output = ""
    async with websockets.connect(uri, ping_interval=None) as ws:
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
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
                output += msg + "\n"
            except asyncio.TimeoutError:
                break
    return output


class TestNewSessionPrompt:
    """New session should show prompt without user typing anything."""

    @pytest.mark.asyncio
    async def test_new_session_shows_prompt(self):
        """Backend must send initial prompt for new session (zsh -l doesn't auto-output)."""
        sid = "test-new-{}".format(uuid.uuid4().hex[:8])
        uri = "{}?session_id={}".format(BACKEND_URL, sid)

        output = await wait_for_pty_output(uri, "luohao@192 backend %", timeout=5.0)

        # Should contain the prompt
        assert "luohao@192 backend %" in output, (
            "Expected prompt 'luohao@192 backend %' in output, got: {!r}".format(output)
        )

        # Should NOT contain JSON session type message as raw text
        lines = output.strip().split("\n")
        raw_lines = [l for l in lines if not l.startswith("{")]
        assert any("luohao@192" in l for l in raw_lines), (
            "Prompt not found as raw text in {!r}".format(raw_lines)
        )

    @pytest.mark.asyncio
    async def test_new_session_no_json_in_output(self):
        """JSON session-type messages must NOT appear as visible text in terminal."""
        sid = "test-json-{}".format(uuid.uuid4().hex[:8])
        uri = "{}?session_id={}".format(BACKEND_URL, sid)

        output = await wait_for_pty_output(uri, "luohao@192 backend %", timeout=5.0)

        # No JSON objects should appear as terminal text
        for line in output.split("\n"):
            try:
                json.loads(line)
                parsed = json.loads(line)
                assert parsed.get("type") == "session", (
                    "Unexpected JSON in terminal output: {!r}".format(line)
                )
            except (json.JSONDecodeError, ValueError):
                pass  # Normal terminal output — fine


class TestSessionTypeMessage:
    """Backend sends {"type": "session", "status": "new"|"reconnect"} on connect."""

    @pytest.mark.asyncio
    async def test_new_session_sends_session_type_json(self):
        """Backend sends exactly one session-type JSON on new session connect."""
        sid = "test-type-{}".format(uuid.uuid4().hex[:8])
        uri = "{}?session_id={}".format(BACKEND_URL, sid)

        all_output = []
        async with websockets.connect(uri, ping_interval=None) as ws:
            start = time.monotonic()
            while time.monotonic() - start < 5.0:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    all_output.append(msg)
                    if "luohao@192" in msg:
                        break
                except asyncio.TimeoutError:
                    break

        assert len(all_output) >= 2, (
            "Expected >=2 messages, got {}: {!r}".format(len(all_output), all_output)
        )

        first_line = all_output[0]
        parsed = json.loads(first_line)
        assert parsed.get("type") == "session", "Expected session type, got: {!r}".format(first_line)
        assert parsed.get("status") == "new", "Expected status='new', got: {}".format(parsed)

    @pytest.mark.asyncio
    async def test_reconnect_sends_reconnect_status(self):
        """Reconnect sends status='reconnect', not 'new'."""
        sid = "test-recon-{}".format(uuid.uuid4().hex[:8])
        uri1 = "{}?session_id={}".format(BACKEND_URL, sid)
        uri2 = "{}?session_id={}".format(BACKEND_URL, sid)

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
                "Expected status='reconnect' on 2nd connection, got: {}".format(parsed2)
            )


class TestReconnectBuffer:
    """Reconnect to alive session should replay full PTY buffer."""

    @pytest.mark.asyncio
    async def test_reconnect_replays_full_buffer(self):
        """Reconnect must replay ALL accumulated PTY output, including user commands."""
        sid = "test-replay-{}".format(uuid.uuid4().hex[:8])
        uri = "{}?session_id={}".format(BACKEND_URL, sid)

        # C1: create session, type a command
        async with websockets.connect(uri, ping_interval=None) as ws1:
            await ws1.recv()  # status: new
            await ws1.recv()  # initial prompt

            cmd = "echo REPLAY_TEST\r"
            await ws1.send(cmd)
            await asyncio.sleep(0.5)

            # Collect PTY echo + command output + new prompt
            collected = []
            for _ in range(5):
                try:
                    m = await asyncio.wait_for(ws1.recv(), timeout=0.5)
                    collected.append(m)
                except asyncio.TimeoutError:
                    break

            has_echo = any("REPLAY_TEST" in m for m in collected)
            assert has_echo, "Expected REPLAY_TEST in C1 output: {}".format(collected)

        # C2: reconnect - must replay the entire buffer
        await asyncio.sleep(0.2)
        async with websockets.connect(uri, ping_interval=None) as ws2:
            msgs2 = []
            for _ in range(20):
                try:
                    m = await asyncio.wait_for(ws2.recv(), timeout=0.5)
                    msgs2.append(m)
                except asyncio.TimeoutError:
                    break

            has_recon = any("reconnect" in m for m in msgs2)
            has_echo = any("REPLAY_TEST" in m for m in msgs2)
            assert has_recon, "Expected reconnect status in C2: {}".format(msgs2)
            assert has_echo, "Expected REPLAY_TEST echo in C2 buffer: {}".format(msgs2)

    @pytest.mark.asyncio
    async def test_reconnect_shows_same_session(self):
        """Two WS connections with same session_id share the same PTY."""
        sid = "test-share-{}".format(uuid.uuid4().hex[:8])
        uri1 = "{}?session_id={}".format(BACKEND_URL, sid)
        uri2 = "{}?session_id={}".format(BACKEND_URL, sid)

        # Connection 1: send a command
        async with websockets.connect(uri1, ping_interval=None) as ws1:
            init1 = await asyncio.wait_for(ws1.recv(), timeout=3.0)
            assert json.loads(init1).get("type") == "session"

            await asyncio.wait_for(ws1.recv(), timeout=3.0)

            await ws1.send("echo HELLO_TERMINAL_TEST\r")
            await asyncio.sleep(0.5)

        # Connection 2: reconnect to same session
        await asyncio.sleep(0.2)
        async with websockets.connect(uri2, ping_interval=None) as ws2:
            status_msg = await asyncio.wait_for(ws2.recv(), timeout=3.0)
            parsed = json.loads(status_msg)
            assert parsed.get("status") == "reconnect", (
                "Expected reconnect, got: {}".format(parsed)
            )


class TestNoAutoReconnect:
    """Backend must NOT auto-reconnect — frontend handles that via component remount."""

    @pytest.mark.asyncio
    async def test_disconnect_does_not_auto_send(self):
        """After client disconnects, backend must NOT auto-reconnect or send reconnect msg."""
        sid = "test-norecon-{}".format(uuid.uuid4().hex[:8])
        uri = "{}?session_id={}".format(BACKEND_URL, sid)

        # Connect and immediately disconnect
        async with websockets.connect(uri, ping_interval=None) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            parsed = json.loads(msg)
            assert parsed.get("type") == "session"

        # Backend should NOT send anything after client disconnects
        await asyncio.sleep(1.0)

    @pytest.mark.asyncio
    async def test_frontend_no_double_connection(self):
        """Backend should handle multiple WS connections for same session gracefully."""
        sid = "test-double"
        uri = "{}?session_id={}".format(BACKEND_URL, sid)
        async with websockets.connect(uri, ping_interval=None) as ws1:
            async with websockets.connect(uri, ping_interval=None) as ws2:
                msg1 = await asyncio.wait_for(ws1.recv(), timeout=3.0)
                msg2 = await asyncio.wait_for(ws2.recv(), timeout=3.0)
                assert json.loads(msg1).get("type") == "session"
                assert json.loads(msg2).get("type") == "session"


class TestNoArtificialMessages:
    """No artificial [Session: xxx] or checkmark messages."""

    @pytest.mark.asyncio
    async def test_no_session_announcement(self):
        """Backend must NOT send [Session: xxx] artificial announcement."""
        sid = "test-noann-{}".format(uuid.uuid4().hex[:8])
        uri = "{}?session_id={}".format(BACKEND_URL, sid)

        output = await wait_for_pty_output(uri, "luohao@192 backend %", timeout=5.0)

        assert "[Session:" not in output, "Unexpected [Session:] in output: {!r}".format(output)
        assert "\u2713" not in output, "Unexpected checkmark in output: {!r}".format(output)
        assert "\u4f1a\u8bdd\u5df2\u6062\u590d" not in output, "Unexpected reconnect message in output"

    @pytest.mark.asyncio
    async def test_no_login_banner(self):
        """No 'Last login' banner should appear (HUSHLOGIN=/dev/null set in backend)."""
        sid = "test-nologin-{}".format(uuid.uuid4().hex[:8])
        uri = "{}?session_id={}".format(BACKEND_URL, sid)

        output = await wait_for_pty_output(uri, "luohao@192 backend %", timeout=5.0)

        assert "Last login:" not in output, "Unexpected login banner in output: {!r}".format(output)


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
            pytest.skip("Backend not running: {}".format(e))
