from personality.personality_engine import PersonalityEngine, PersonalityConfig
from personality.dialogue_library import NATURAL_CHAT, EMOJI_PROBABILITY


def test_natural_chat_bank_has_variety():
    assert len(NATURAL_CHAT["check_in"]) >= 8
    assert len(NATURAL_CHAT["ack"]) >= 6
    assert len(set(NATURAL_CHAT["check_in"])) == len(NATURAL_CHAT["check_in"])


def test_emoji_policy_is_probability_based():
    assert 0 < EMOJI_PROBABILITY["neutral"] < 0.2
    assert EMOJI_PROBABILITY["excited"] > EMOJI_PROBABILITY["neutral"]


def test_personality_is_non_flirty_by_default():
    assert PersonalityConfig().flirty_enabled is False
    assert PersonalityEngine().config.flirty_enabled is False


def test_natural_chat_picker_returns_known_line():
    assert PersonalityEngine().natural_chat_line("check_in") in NATURAL_CHAT["check_in"]
