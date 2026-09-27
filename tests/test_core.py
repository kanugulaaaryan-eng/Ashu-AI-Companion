import asyncio
import tempfile
import unittest
from pathlib import Path

from brain.agent import AshuAgent
from brain.llm_interface import MockLLM, ModelConfig
from memory.models import UsefulFact, UserProfile
from memory.sqlite_memory import SQLiteMemory
from personality.personality_engine import PersonalityEngine
from protocols.local_server import _jsonable
from tools.permissions import PermissionManager, PermissionLevel
from tools.tool_system import ToolSystem


class AshuCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "memory.db"
        self.memory = SQLiteMemory(str(self.db))

    def tearDown(self):
        self.tmp.cleanup()

    def test_memory_roundtrip(self):
        self.memory.update_user_profile(name="Aaryan", nickname="Aaryan")
        self.memory.save_fact(UsefulFact(category="goal", fact="Build Ashu", source="test"))
        self.assertEqual(self.memory.get_user_profile().nickname, "Aaryan")
        self.assertEqual(self.memory.search_facts("Ashu")[0].fact, "Build Ashu")

    def test_permissions_default_safe(self):
        permissions = PermissionManager()
        self.assertFalse(permissions.check_permission("writefile"))
        permissions.grant_permission("writefile", PermissionLevel.SESSION)
        self.assertTrue(permissions.check_permission("writefile"))

    def test_mock_agent_onboarding_is_conversational(self):
        agent = AshuAgent(
            memory=self.memory,
            personality=PersonalityEngine(),
            llm=MockLLM(["Nice ra 😌"]),
            tool_system=ToolSystem(self.memory),
        )
        r1 = asyncio.run(agent.process_message("Aaryan"))
        self.assertIn("pilavali", r1.text.lower())
        r2 = asyncio.run(agent.process_message("Ashu"))
        self.assertIn("interests", r2.text.lower())
        r3 = asyncio.run(agent.process_message("coding, ML, games"))
        self.assertFalse(agent.is_onboarding)

    def test_protocol_jsonable(self):
        profile = UserProfile(name="Aaryan")
        payload = _jsonable(profile)
        self.assertEqual(payload["name"], "Aaryan")
        self.assertEqual(payload["primary_language"], "te")


if __name__ == "__main__":
    unittest.main()

def test_personality_relationship_and_boredom(tmp_path):
    from personality.personality_engine import PersonalityEngine, AshuMood
    from memory.models import UserPreferences

    engine = PersonalityEngine()
    prefs = UserPreferences(relationship_stage="best_friend", interaction_count=12)
    engine.apply_preferences(prefs)
    response = engine.boredom_response()
    assert response
    # v0.4: Ashu is explicitly non-flirty, so boredom yields only
    # bored or playful moods -- never flirty.
    assert engine.mood in {AshuMood.BORED, AshuMood.PLAYFUL}
    assert engine.config.flirty_enabled is False

def test_preferences_migrate_and_persist(tmp_path):
    from memory.sqlite_memory import SQLiteMemory
    db = SQLiteMemory(str(tmp_path / "prefs.db"))
    prefs = db.get_user_preferences()
    prefs.relationship_stage = "best_friend"
    prefs.jealousy_level = 3
    prefs.flirty_enabled = True
    prefs.sleep_start = "00:30"
    prefs.sleep_end = "07:30"
    prefs.auto_memory = True
    db.save_user_preferences(prefs)
    loaded = db.get_user_preferences()
    assert loaded.relationship_stage == "best_friend"
    assert loaded.jealousy_level == 3
    assert loaded.sleep_start == "00:30"


def test_auto_memory_skips_secrets(tmp_path):
    from brain.agent import AshuAgent
    from personality.personality_engine import PersonalityEngine
    from brain.llm_interface import MockLLM
    from memory.sqlite_memory import SQLiteMemory
    from tools.tool_system import ToolSystem

    memory = SQLiteMemory(str(tmp_path / "auto.db"))
    agent = AshuAgent(memory=memory, personality=PersonalityEngine(), llm=MockLLM(["Okay ra 😌"]), tool_system=ToolSystem(memory))
    agent.memory.update_user_preferences(auto_memory=True)
    agent._auto_capture_memory("I like SQL and building apps")
    agent._auto_capture_memory("my password is hunter2")
    facts = agent.memory.get_facts()
    assert any("SQL".lower() in f.fact.lower() for f in facts)
    assert all("password" not in f.fact.lower() for f in facts)
