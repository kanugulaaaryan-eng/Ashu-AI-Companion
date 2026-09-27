"""v0.4 tests: memory CRUD, provenance, review dashboard support, privacy
deletion and conversational memory commands.
"""

import tempfile
from pathlib import Path

import pytest

from memory.sqlite_memory import SQLiteMemory
from memory.models import UsefulFact, MemoryType
from memory.memory_commands import handle_memory_command
from security.privacy import is_sensitive, redact


@pytest.fixture()
def memory(tmp_path):
    return SQLiteMemory(str(tmp_path / "mem.db"))


def test_create_read_update_delete(memory):
    saved = memory.save_fact(UsefulFact(category="preference", fact="likes dosa", source="auto"))
    assert saved.id is not None
    assert memory.get_fact(saved.id).fact == "likes dosa"

    memory.update_fact(saved.id, fact="likes masala dosa", category="food")
    updated = memory.get_fact(saved.id)
    assert updated.fact == "likes masala dosa"
    assert updated.category == "food"

    assert memory.delete_fact(saved.id) is True
    assert memory.get_fact(saved.id) is None


def test_fact_provenance_and_review_fields(memory):
    saved = memory.save_fact(UsefulFact(
        category="project", fact="building Ashu v0.4", source="auto",
        session_id="sess1", source_message="I am building Ashu v0.4",
        memory_type=MemoryType.AUTO.value, confidence=0.9,
    ))
    fetched = memory.get_fact(saved.id)
    assert fetched.session_id == "sess1"
    assert "Ashu v0.4" in fetched.source_message
    assert fetched.memory_type == "auto"
    assert fetched.pinned is False


def test_pinned_memories_sort_first(memory):
    memory.save_fact(UsefulFact(category="a", fact="normal one"))
    pinned = memory.save_fact(UsefulFact(category="b", fact="important one", pinned=True))
    results = memory.get_all_memories()
    assert results[0].id == pinned.id


def test_search_all_with_empty_query_returns_everything(memory):
    memory.save_fact(UsefulFact(category="a", fact="alpha"))
    memory.save_fact(UsefulFact(category="b", fact="beta"))
    assert len(memory.search_all("")) == 2
    assert len(memory.search_all("alpha")) == 1


def test_delete_all_and_wipe(memory):
    memory.save_fact(UsefulFact(category="a", fact="x"))
    memory.log_activity("tool", "get_time", "ran")
    assert memory.delete_all_memories() == 1
    assert memory.get_all_memories() == []

    memory.save_fact(UsefulFact(category="a", fact="y"))
    memory.wipe_all()
    assert memory.get_all_memories() == []
    assert memory.get_activity_log() == []
    assert memory.get_user_profile().name == ""


def test_activity_log_roundtrip_and_clear(memory):
    memory.log_activity("tool", "write_file", "success", {"path": "a.txt"}, confirmed=True)
    log = memory.get_activity_log()
    assert len(log) == 1
    assert log[0].name == "write_file"
    assert log[0].confirmed is True
    assert memory.clear_activity_log() == 1
    assert memory.get_activity_log() == []


def test_export_contains_all_sections(memory):
    memory.save_fact(UsefulFact(category="a", fact="z"))
    snapshot = memory.export_all()
    for section in ("profile", "preferences", "facts", "people", "goals", "projects", "activity"):
        assert section in snapshot
    assert len(snapshot["facts"]) == 1


# --- conversational memory commands ---------------------------------------

def test_recall_command(memory):
    memory.save_fact(UsefulFact(category="project", fact="building Ashu"))
    result = handle_memory_command("What do you remember about me?", memory)
    assert result.handled and result.action == "recall"
    assert "Ashu" in result.text


def test_remember_command_stores_explicit_memory(memory):
    result = handle_memory_command("Remember that I like filter coffee", memory)
    assert result.handled and result.action == "remember"
    facts = memory.get_all_memories()
    assert any("filter coffee" in f.fact for f in facts)
    assert facts[0].memory_type == "explicit"


def test_remember_command_refuses_secrets(memory):
    result = handle_memory_command("Remember that my password is hunter2", memory)
    assert result.handled
    assert result.data.get("blocked") is True
    assert memory.get_all_memories() == []


def test_forget_last_command(memory):
    memory.save_fact(UsefulFact(category="a", fact="temporary thing"))
    result = handle_memory_command("Forget what I just told you", memory)
    assert result.handled and result.action == "forget"
    assert memory.get_all_memories() == []


def test_forget_topic_command(memory):
    memory.save_fact(UsefulFact(category="a", fact="likes cricket"))
    memory.save_fact(UsefulFact(category="a", fact="likes dosa"))
    result = handle_memory_command("forget about cricket", memory)
    assert result.handled
    remaining = [f.fact for f in memory.get_all_memories()]
    assert remaining == ["likes dosa"]


def test_delete_everything_requires_confirmation_then_wipes(memory):
    memory.save_fact(UsefulFact(category="a", fact="something"))
    first = handle_memory_command("delete everything you know about me", memory)
    assert first.handled and first.requires_confirmation is True
    # Not deleted yet.
    assert len(memory.get_all_memories()) == 1
    second = handle_memory_command("delete everything you know about me", memory, confirmed=True)
    assert second.handled and not second.requires_confirmation
    assert memory.get_all_memories() == []


def test_wipe_confirmation_phrase_actually_wipes(memory):
    """Regression: the prompt asks the user to reply 'yes, delete everything',
    but that phrase matches no wipe regex. The confirmed=True path must wipe
    regardless of the wording, or the confirmation flow dead-ends."""
    memory.save_fact(UsefulFact(category="a", fact="something"))
    first = handle_memory_command("delete everything you know about me", memory)
    assert first.handled and first.requires_confirmation is True
    second = handle_memory_command("yes, delete everything", memory, confirmed=True)
    assert second.handled and second.action == "wipe"
    assert not second.requires_confirmation
    assert memory.get_all_memories() == []


def test_non_memory_message_is_not_handled(memory):
    assert handle_memory_command("em chestunav ra", memory).handled is False


def test_sensitive_detector():
    assert is_sensitive("my password is hunter2")
    assert is_sensitive("here is the OTP 123456")
    assert not is_sensitive("I like filter coffee")
    assert "[REDACTED]" in redact("password: hunter2")
