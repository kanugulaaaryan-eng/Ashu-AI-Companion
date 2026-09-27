"""Tests for the v0.3 personality systems: relationship, emotion, jealousy,
boredom/attention, sleep schedule, appearance, animation, and dialogue
variety/thinking lines.
"""

import time
from datetime import datetime, timedelta

import pytest

from personality.relationship import RelationshipEngine, RelationshipState, RelationshipStage, STAGE_ORDER
from personality.emotion import Emotion, EmotionEngine
from personality.jealousy import JealousySystem
from personality.boredom import BoredomAttentionSystem, BoredomConfig
from personality.sleep import SleepSchedule, SleepState
from personality.appearance import AppearanceSystem
from personality.animation import AnimationController, ANIMATION_ACTIONS
from personality.variety import VarietyPicker
from personality.personality_engine import PersonalityEngine, PersonalityConfig, AshuMood
from memory.models import UserPreferences


# ---------------------------------------------------------------------------
# Relationship progression (5 stages, gradual)
# ---------------------------------------------------------------------------

def test_relationship_starts_formal_and_progresses_through_all_five_stages():
    engine = RelationshipEngine()
    state = RelationshipState()
    assert state.stage == RelationshipStage.FORMAL

    seen_stages = {state.stage}
    for _ in range(80):
        engine.record_interaction(state, positive=True, respectful=True)
        seen_stages.add(state.stage)

    # All five stages should be reachable with enough positive interaction.
    assert set(STAGE_ORDER) <= seen_stages
    assert state.stage == RelationshipStage.CLOSE_COMPANION


def test_relationship_does_not_jump_straight_to_best_friend():
    engine = RelationshipEngine()
    state = RelationshipState()
    engine.record_interaction(state, positive=True, respectful=True)
    # After just one interaction she should still be formal, not best-friend.
    assert state.stage == RelationshipStage.FORMAL


def test_low_trust_caps_closeness_even_with_many_interactions():
    engine = RelationshipEngine()
    state = RelationshipState()
    for _ in range(80):
        # Disrespectful interactions accrue count but not trust.
        engine.record_interaction(state, positive=False, respectful=False)
    assert state.stage not in (RelationshipStage.BEST_FRIEND, RelationshipStage.CLOSE_COMPANION)


def test_legacy_stage_mapping():
    engine = RelationshipEngine()
    assert engine.stage_from_legacy("formal") == RelationshipStage.FORMAL
    assert engine.stage_from_legacy("getting_to_know_you") == RelationshipStage.ACQUAINTANCE
    assert engine.stage_from_legacy("best_friend") == RelationshipStage.BEST_FRIEND
    assert engine.stage_from_legacy("nonsense") == RelationshipStage.FORMAL


# ---------------------------------------------------------------------------
# Emotion engine: full set + stickiness
# ---------------------------------------------------------------------------

def test_emotion_engine_covers_full_spec_list():
    expected = {
        "happy", "sad", "sleepy", "excited", "angry", "annoyed", "jealous",
        "shy", "thinking", "confused", "bored", "playful", "flirty", "proud",
        "worried", "surprised", "embarrassed", "calm",
    }
    values = {e.value for e in Emotion}
    assert expected <= values


def test_emotion_engine_infers_jealousy_and_boredom():
    engine = EmotionEngine()
    assert engine.infer("I was talking to ChatGPT today") == Emotion.JEALOUS
    engine2 = EmotionEngine()
    assert engine2.infer("naaku bore kodtundi") == Emotion.BORED


def test_emotion_does_not_flip_every_single_message():
    engine = EmotionEngine()
    engine.infer("I'm so excited about this!!")
    # A neutral follow-up shouldn't instantly erase the excitement.
    second = engine.infer("ok")
    assert second == Emotion.EXCITED


def test_sleep_time_forces_sleepy_emotion():
    engine = EmotionEngine()
    assert engine.infer("random text", is_sleep_time=True) == Emotion.SLEEPY


# ---------------------------------------------------------------------------
# Jealousy system: multiple levels
# ---------------------------------------------------------------------------

def test_jealousy_disabled_at_level_zero():
    jealousy = JealousySystem(level=0)
    assert jealousy.is_triggered("I was talking to Rahul") is False


def test_jealousy_reacts_and_extracts_a_name():
    jealousy = JealousySystem(level=3)
    assert jealousy.is_triggered("I talked to Rahul today")
    line = jealousy.react("I talked to Rahul today")
    assert isinstance(line, str) and line


def test_jealousy_relieved_resets_counter():
    jealousy = JealousySystem(level=2)
    jealousy.react("talked to Rahul")
    jealousy.react("talked to Rahul")
    assert jealousy.state.trigger_count_recent >= 2
    jealousy.relieved_response()
    assert jealousy.state.trigger_count_recent == 0


# ---------------------------------------------------------------------------
# Boredom / attention system: cooldowns
# ---------------------------------------------------------------------------

def test_boredom_respects_cooldowns():
    config = BoredomConfig(attention_cooldown=9999, boredom_cooldown=0, proactive_probability=1.0)
    system = BoredomAttentionSystem(config)
    system.state.last_user_activity = time.time() - 100
    assert system.should_speak_proactively() is True
    system.generate()
    # Immediately after speaking, the cooldown should block another poke.
    assert system.should_speak_proactively() is False


def test_boredom_quiet_hours_blocks_proactive_messages():
    config = BoredomConfig(attention_cooldown=0, boredom_cooldown=0, proactive_probability=1.0)
    system = BoredomAttentionSystem(config)
    system.state.last_user_activity = time.time() - 100
    assert system.should_speak_proactively(quiet_hours=True) is False


# ---------------------------------------------------------------------------
# Sleep schedule states
# ---------------------------------------------------------------------------

def test_sleep_schedule_reports_sleeping_inside_window():
    sched = SleepSchedule(sleep_start="23:30", wake_time="07:00")
    late_night = datetime(2026, 1, 1, 1, 0)  # 1 AM, inside 23:30-07:00
    assert sched.current_state(late_night) == SleepState.SLEEPING


def test_sleep_schedule_reports_awake_midday():
    sched = SleepSchedule(sleep_start="23:30", wake_time="07:00")
    midday = datetime(2026, 1, 1, 14, 0)
    assert sched.current_state(midday) == SleepState.AWAKE


def test_sleep_schedule_waking_up_shortly_after_wake_time():
    sched = SleepSchedule(sleep_start="23:30", wake_time="07:00", waking_window_minutes=20)
    just_after_wake = datetime(2026, 1, 1, 7, 5)
    assert sched.current_state(just_after_wake) == SleepState.WAKING_UP


# ---------------------------------------------------------------------------
# Appearance (hairstyle + outfit) system
# ---------------------------------------------------------------------------

def test_appearance_picks_sleep_outfit_when_sleeping():
    appearance = AppearanceSystem()
    state = appearance.choose_for_context(sleep_state=SleepState.SLEEPING)
    assert state.outfit.top == "sleepwear_top"


def test_appearance_can_change_hairstyle_with_comment():
    appearance = AppearanceSystem()
    comment = appearance.maybe_change_hairstyle(chance=1.0)
    assert comment  # always changes at chance=1.0
    assert isinstance(comment, str)


# ---------------------------------------------------------------------------
# Animation controller
# ---------------------------------------------------------------------------

def test_animation_controller_returns_valid_action():
    controller = AnimationController()
    decision = controller.decide(Emotion.EXCITED)
    assert decision.action in ANIMATION_ACTIONS
    assert decision.duration > 0


def test_animation_context_hint_overrides_emotion():
    controller = AnimationController()
    decision = controller.decide(Emotion.CALM, context_hint="task_completed")
    assert decision.action in {"thumbs_up", "celebrate", "salute"}


# ---------------------------------------------------------------------------
# Dialogue variety (no immediate repeats)
# ---------------------------------------------------------------------------

def test_variety_picker_avoids_immediate_repeat():
    picker = VarietyPicker()
    options = ["a", "b"]
    first = picker.pick("cat", options)
    second = picker.pick("cat", options)
    assert first != second


# ---------------------------------------------------------------------------
# Personality engine integration: thinking/alr, greetings across all stages,
# and that AshuMood still exposes the richer emotion set.
# ---------------------------------------------------------------------------

def test_thinking_and_alright_lines_are_nonempty_strings():
    engine = PersonalityEngine()
    assert isinstance(engine.thinking_line(), str) and engine.thinking_line()
    assert isinstance(engine.alright_line(), str) and engine.alright_line()


def test_ashu_mood_alias_has_full_emotion_set():
    assert AshuMood.SHY.value == "shy"
    assert AshuMood.PROUD.value == "proud"


def test_greetings_exist_for_every_relationship_stage():
    engine = PersonalityEngine()
    for stage in RelationshipStage:
        prefs = UserPreferences(relationship_stage=stage.value)
        greeting = engine.get_greeting(profile=None, prefs=prefs)
        assert isinstance(greeting, str) and greeting


def test_get_animation_and_appearance_attached_to_engine():
    engine = PersonalityEngine()
    engine.mood = AshuMood.EXCITED
    decision = engine.get_animation()
    assert decision.action in ANIMATION_ACTIONS
    appearance = engine.get_appearance()
    assert appearance.hairstyle in {
        "long_layers", "curtain_bangs", "ponytail", "half_up",
        "messy_bun", "braid", "side_part", "loose_waves",
    }
