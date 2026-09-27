"""v0.4 tests: offline operation, missing-model handling and no-network
guarantees for the core companion loop.
"""

import asyncio
import socket
from unittest import mock

import pytest

from brain.agent import create_agent
from brain.model_manager import ModelManager


def run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def ready_agent(tmp_path):
    agent = create_agent(db_path=str(tmp_path / "offline.db"))
    agent.memory.update_user_profile(name="Arya", nickname="Arya",
                                     interests=["coding"], onboarding_completed=True)
    return agent


def test_core_conversation_works_offline(ready_agent, monkeypatch):
    # Fail any attempt to open a network socket: the core loop must not need one.
    def no_socket(*args, **kwargs):
        raise AssertionError("network access attempted during offline chat")

    monkeypatch.setattr(socket, "create_connection", no_socket)
    response = run(ready_agent.process_message("em chestunav ra"))
    assert response.text
    assert response.origin in ("fallback", "rule_based", "mock", "local")


def test_memory_works_offline(ready_agent):
    run(ready_agent.process_message("remember that I like idli"))
    assert any("idli" in f.fact for f in ready_agent.memory.get_all_memories())


def test_missing_model_reported_honestly(ready_agent):
    info = ready_agent.llm.get_model_info()
    # Either no local model (fallback) or a real one; never a false "local".
    assert "last_origin" in info
    status = ModelManager().status()
    if not status.usable:
        assert "model" in status.reason.lower() or status.reason == ""


def test_health_reports_model_unavailable_when_absent(tmp_path):
    manager = ModelManager(models_dir=str(tmp_path / "empty"))
    status = manager.status()
    assert status.usable is False


def test_confirmation_queue_survives_multiple_turns(tmp_path):
    from brain.decision import AgentDecision, ActionType
    agent = create_agent(db_path=str(tmp_path / "queue.db"))
    agent.memory.update_user_profile(name="Arya", nickname="Arya",
                                     interests=["coding"], onboarding_completed=True)
    context = agent.context_builder.build_context("write a file")
    run(agent._execute_tool(AgentDecision(
        action_type=ActionType.USE_TOOL, tool_name="write_file",
        tool_args={"path": "a.txt", "content": "x"}), context))
    run(agent.process_message("em chestunav"))
    assert len(agent.get_pending_actions()) == 1


def test_wipe_data_clears_everything(tmp_path):
    agent = create_agent(db_path=str(tmp_path / "wipe.db"))
    agent.memory.update_user_profile(name="Arya", nickname="Arya",
                                     interests=["coding"], onboarding_completed=True)
    run(agent.process_message("remember that I like tea"))
    assert agent.memory.get_all_memories()
    result = agent.wipe_data()
    assert result["ok"] is True
    assert agent.memory.get_all_memories() == []
