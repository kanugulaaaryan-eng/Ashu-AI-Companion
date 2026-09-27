"""v0.4 tests: explicit personality state (mood, energy, familiarity, trust,
boredom, last interaction, conversation context, relationship stage) plus the
new waiting / silence / emotional-reaction behaviour.
"""

import time

import pytest

from personality.state import (
    PersonalityState, InMemoryStateStore, JSONStateStore,
)
from personality.personality_engine import PersonalityEngine, PersonalityConfig
from personality.emotion import Emotion
from personality.relationship import RelationshipStage
from memory.models import UserPreferences


def test_state_has_every_required_field():
    state = PersonalityState()
    for field in ("mood", "energy", "familiarity", "trust", "boredom",
                  "last_interaction_at", "conversation_context",
                  "relationship_stage", "waiting_for_user", "pending_question"):
        assert hasattr(state, field), field


def test_state_round_trips_through_json_store(tmp_path):
    store = JSONStateStore(str(tmp_path / "state.json"))
    state = PersonalityState(mood="happy", energy=0.4, familiarity=0.5,
                             trust=0.3, conversation_context="project",
                             waiting_for_user=True, pending_question="ela?")
    store.save(state)
    loaded = store.load()
    assert loaded.mood == "happy"
    assert abs(loaded.familiarity - 0.5) < 1e-6
    assert loaded.waiting_for_user is True
    assert loaded.pending_question == "ela?"


def test_missing_state_file_is_safe(tmp_path):
    store = JSONStateStore(str(tmp_path / "nope.json"))
    assert store.load().mood == Emotion.CALM.value


def test_waiting_state_set_and_cleared():
    engine = PersonalityEngine(state_store=InMemoryStateStore())
    engine.mark_waiting("Nuvvu em chestunav?")
    assert engine.is_waiting() is True
    assert engine.get_state().pending_question.endswith("?")
    engine.clear_waiting()
    assert engine.is_waiting() is False


def test_relationship_progression_updates_state_and_persists():
    store = InMemoryStateStore()
    engine = PersonalityEngine(state_store=store)
    for _ in range(80):
        engine.advance_relationship(positive=True, respectful=True)
    assert engine.relationship_state.stage == RelationshipStage.CLOSE_COMPANION
    assert engine.get_state().familiarity > 0.5
    assert engine.get_state().trust > 0.5
    # persist() pushes live values into the store.
    engine.persist_state()
    assert store.load().relationship_stage == RelationshipStage.CLOSE_COMPANION.value


def test_energy_stays_bounded():
    engine = PersonalityEngine(state_store=InMemoryStateStore())
    engine.state.energy = 5.0
    engine.persist_state()
    assert 0.0 <= engine.get_state().energy <= 1.0


def test_emotional_reaction_reacts_to_words():
    engine = PersonalityEngine(state_store=InMemoryStateStore())
    engine.emotional_reaction_to("Naku chala tension ga undi")
    # caring is inferred from "tension"
    assert engine.mood in (Emotion.CARING, Emotion.WORRIED)


def test_engine_never_flirty_even_if_preference_set():
    engine = PersonalityEngine(state_store=InMemoryStateStore())
    prefs = UserPreferences(flirty_enabled=True, attention_enabled=True)
    engine.apply_preferences(prefs)
    assert engine.config.flirty_enabled is False
    for _ in range(20):
        engine.boredom_response()
        assert engine.mood != Emotion.FLIRTY


def test_silence_is_occasional_and_bounded():
    engine = PersonalityEngine(state_store=InMemoryStateStore())
    engine.config.intensity = "balanced"
    hits = sum(1 for _ in range(400) if engine.maybe_silence())
    # Deliberate-but-rare: not never, not constant.
    assert 0 < hits < 120


def test_register_progresses_with_stage():
    engine = PersonalityEngine(state_store=InMemoryStateStore())
    assert engine._language.register("formal") == "polite"
    assert engine._language.register("best_friend") == "bestie"
