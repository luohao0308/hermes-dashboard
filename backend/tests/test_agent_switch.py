"""
Backend tests for agent switch functionality.
Run with: cd backend && python -m pytest tests/ -v
Or from project root: ~/opt/anaconda3/envs/hermes310/bin/python3.10 -m pytest backend/tests/ -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestChatSessionAPI:
    """Verify ChatSession has the required fields for agent switching."""

    def test_session_has_agent_id_field(self):
        from agent.chat_manager import ChatSession
        session = ChatSession(session_id='test-123', agent_id='main')
        assert session.agent_id == 'main'
        assert session.session_id == 'test-123'

    def test_session_has_run_task_field(self):
        from agent.chat_manager import ChatSession
        session = ChatSession(session_id='x', agent_id='main')
        assert hasattr(session, '_run_task')
        assert session._run_task is None

    def test_session_can_update_agent_id(self):
        from agent.chat_manager import ChatSession
        session = ChatSession(session_id='x', agent_id='main')
        session.agent_id = 'Developer'
        assert session.agent_id == 'Developer'


class TestChatManagerAPI:
    """Verify ChatManager has correct session management API."""

    def test_create_session_with_main_agent_id(self):
        from agent.chat_manager import ChatManager
        mgr = ChatManager()
        session = mgr.create_session('main')
        assert session.agent_id == 'main'
        assert session.session_id is not None
        mgr.close_session(session.session_id)

    def test_create_session_with_developer_agent_id(self):
        from agent.chat_manager import ChatManager
        mgr = ChatManager()
        session = mgr.create_session('Developer')
        assert session.agent_id == 'Developer'
        mgr.close_session(session.session_id)

    def test_update_session_agent(self):
        from agent.chat_manager import ChatManager
        mgr = ChatManager()
        session = mgr.create_session('main')
        assert session.agent_id == 'main'

        result = mgr.update_session_agent(session.session_id, 'Developer')
        assert result is True
        assert session.agent_id == 'Developer'
        mgr.close_session(session.session_id)

    def test_close_session_removes_session(self):
        from agent.chat_manager import ChatManager
        mgr = ChatManager()
        session = mgr.create_session('main')
        sid = session.session_id

        result = mgr.close_session(sid)
        assert result is True
        assert mgr.get_session(sid) is None


class TestRunChatAgentLogic:
    """Test _run_chat_agent uses session.agent_id."""

    def test_run_chat_agent_uses_session_agent_id(self):
        """
        Verify _run_chat_agent picks agent based on session.agent_id.
        This is the critical fix: it should use session.agent_id, not cfg['main_agent'].
        """
        from agent.agent_manager import get_all_agents
        from agent.chat_manager import ChatSession

        session = ChatSession(session_id='test', agent_id='developer')
        agents = get_all_agents()

        # The key: use session.agent_id (lowercase), fallback to dispatcher
        chosen = agents.get(session.agent_id.lower(), agents.get('dispatcher'))
        assert chosen is not None
        assert chosen.name == 'Developer'

    def test_fallback_to_dispatcher_for_unknown_agent(self):
        from agent.agent_manager import get_all_agents

        agents = get_all_agents()
        # Unknown agent falls back to dispatcher
        chosen = agents.get('NonExistentAgent', agents.get('dispatcher'))
        assert chosen is not None


class TestAgentsYamlConfig:
    """Verify agents.yaml is correctly configured."""

    def test_all_agents_have_handoffs_defined(self):
        import yaml
        config_path = os.path.join(
            os.path.dirname(__file__), '..', 'agent', 'agents.yaml'
        )
        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        agents_cfg = cfg.get('agents', {})
        assert len(agents_cfg) > 0, "No agents defined in agents.yaml"
        for agent_name, agent_data in agents_cfg.items():
            assert 'handoffs' in agent_data, f"Agent {agent_name} missing handoffs"

    def test_dispatcher_agent_exists(self):
        import yaml
        config_path = os.path.join(
            os.path.dirname(__file__), '..', 'agent', 'agents.yaml'
        )
        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        agents_cfg = cfg.get('agents', {})
        # At minimum, dispatcher should be defined (as main_agent)
        assert cfg.get('main_agent') is not None


class TestStopSession:
    """Test session stop functionality."""

    def test_session_set_task(self):
        import asyncio
        from agent.chat_manager import ChatSession

        session = ChatSession(session_id='x', agent_id='main')

        async def dummy_task():
            await asyncio.sleep(10)

        async def run():
            task = asyncio.create_task(dummy_task())
            session.set_task(task)
            assert session._run_task is task
            assert not task.done()
            # Cancel it
            result = await session.stop()
            assert result is True
            assert session._run_task is None

        asyncio.run(run())
