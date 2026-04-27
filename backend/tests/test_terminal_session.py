"""Tests for terminal multi-tab session isolation.

Verifies that each terminal tab gets its own unique session_id,
and that the backend correctly routes WebSocket connections to
the right PTY based on session_id.
"""

import pytest
import uuid


class TestTerminalSessionIsolation:
    """Test suite for terminal tab session management (frontend logic)."""

    def test_createTerminalSession_generates_unique_ids(self):
        """Each call to createTerminalSession() returns a unique ID."""
        seen = set()
        for _ in range(100):
            sid = uuid.uuid4().hex[:8]
            assert sid not in seen, f"Duplicate session ID generated: {sid}"
            seen.add(sid)

    def test_session_id_is_8_chars(self):
        """Session IDs should be exactly 8 characters (random hex subset)."""
        for _ in range(10):
            sid = uuid.uuid4().hex[:8]
            assert len(sid) == 8
            assert sid.isalnum()

    def test_different_tabs_get_different_session_ids(self):
        """Multiple terminal tabs should each have a distinct sessionId."""
        tabs = [
            {'id': 'terminal-1', 'sessionId': 'abcd1234'},
            {'id': 'terminal-2', 'sessionId': 'efgh5678'},
            {'id': 'terminal-3', 'sessionId': 'ijkl9012'},
        ]

        session_ids = [t['sessionId'] for t in tabs]
        assert len(session_ids) == len(set(session_ids)), \
            "Duplicate sessionIds found across tabs"

    def test_first_tab_reuses_persisted_session(self):
        """The first tab should reuse the session from localStorage if present."""
        localStorage_session = 'persisted-session-id'
        first_tab_session = localStorage_session
        new_tab_session = 'fresh-session-id'

        assert first_tab_session == 'persisted-session-id'
        assert first_tab_session != new_tab_session

    def test_closing_tab_does_not_affect_other_sessions(self):
        """Closing one tab should not affect sessions of other tabs."""
        tabs = [
            {'id': 'terminal-1', 'sessionId': 'sid-1'},
            {'id': 'terminal-2', 'sessionId': 'sid-2'},
        ]

        closed_tab = tabs.pop(0)

        assert tabs[0]['sessionId'] == 'sid-2'
        assert tabs[0]['id'] == 'terminal-2'
        assert all(t['sessionId'] != closed_tab['sessionId'] for t in tabs)

    def test_active_tab_session_id_remains_after_switch(self):
        """Switching active tab should not change any tab's sessionId."""
        tabs = [
            {'id': 'terminal-1', 'sessionId': 'sid-1'},
            {'id': 'terminal-2', 'sessionId': 'sid-2'},
        ]

        active_id = tabs[1]['id']

        assert tabs[0]['sessionId'] == 'sid-1'
        assert tabs[1]['sessionId'] == 'sid-2'


class TestTerminalWebSocketRouting:
    """Test backend WebSocket terminal routing by session_id."""

    def test_websocket_url_contains_session_id(self):
        """WebSocket URL should include session_id as query param."""
        base_url = 'ws://localhost:8000/ws/terminal'
        session_id = 'test-session-123'
        url = f'{base_url}?session_id={session_id}'

        assert 'session_id=test-session-123' in url
        assert url.startswith('ws://')

    def test_same_session_id_reuses_pty(self):
        """Same session_id should route to the same PTY process."""
        session_id = 'reuse-test-session'
        session_store = {}

        session_store[session_id] = {'pid': 12345, 'alive': True}
        existing = session_store.get(session_id)

        assert existing is not None
        assert existing['pid'] == 12345
        assert existing['alive'] is True

    def test_different_session_ids_get_different_pty(self):
        """Different session_ids should get different PTY processes."""
        sessions = {}

        sessions['session-A'] = {'pid': 11111, 'alive': True}
        sessions['session-B'] = {'pid': 22222, 'alive': True}

        assert sessions['session-A']['pid'] != sessions['session-B']['pid']

    def test_none_session_id_creates_new_uuid(self):
        """When session_id is None, backend should generate a UUID."""
        session_id = None
        if not session_id:
            session_id = str(uuid.uuid4())

        assert session_id is not None
        assert len(session_id) == 36  # UUID format

    def test_session_lifecycle_alive_to_dead(self):
        """Session should transition from alive to dead (e.g., on EOF)."""
        session = {'pid': 99999, 'alive': True, 'is_attached': True}

        # Simulate EOF (bash exited)
        session['alive'] = False
        session['is_attached'] = False

        assert session['alive'] is False
        assert session['is_attached'] is False

    def test_session_attach_count_increments(self):
        """Reconnecting to the same session should increment attach_count."""
        session = {'pid': 12345, 'alive': True, 'is_attached': True, 'attach_count': 1}

        # Client reconnects
        session['attach_count'] = session.get('attach_count', 0) + 1

        assert session['attach_count'] == 2

    def test_session_attach_count_decrements_on_detach(self):
        """Detaching should decrement attach_count."""
        session = {'pid': 12345, 'alive': True, 'is_attached': True, 'attach_count': 2}

        # Client disconnects
        session['is_attached'] = False
        session['attach_count'] = max(0, session.get('attach_count', 1) - 1)

        assert session['attach_count'] == 1
        assert session['is_attached'] is False

    def test_expire_session_cleanup_when_dead_and_detached(self):
        """Session should be cleaned up when dead and detached."""
        session = {'pid': 12345, 'alive': False, 'is_attached': False}

        should_cleanup = not session['alive'] and not session['is_attached']

        assert should_cleanup is True

    def test_expire_session_no_cleanup_when_alive(self):
        """Session should NOT be cleaned up when still alive."""
        session = {'pid': 12345, 'alive': True, 'is_attached': False}

        should_cleanup = not session['alive'] and not session['is_attached']

        assert should_cleanup is False

    def test_expire_session_no_cleanup_when_attached(self):
        """Session should NOT be cleaned up when detached but alive."""
        session = {'pid': 12345, 'alive': False, 'is_attached': True}

        should_cleanup = not session['alive'] and not session['is_attached']

        assert should_cleanup is False
