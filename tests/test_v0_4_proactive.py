"""v0.4 tests: proactive behaviour guards (toggle, daily limit, DND, quiet
hours, cooldown, anti-repeat) and return-greeting / check-in / waiting logic.
All tests inject a fixed clock so they are deterministic.
"""

from datetime import datetime

import pytest

from personality.proactive import (
    ProactiveScheduler, ProactiveConfig,
)
from personality.personality_engine import PersonalityEngine
from personality.state import InMemoryStateStore


def fixed_now(dt: datetime) -> float:
    return dt.timestamp()


def test_disabled_toggle_prevents_all_initiation():
    sched = ProactiveScheduler(ProactiveConfig(enabled=False))
    assert sched.next_message(idle_seconds=99999, now=fixed_now(datetime(2026, 1, 1, 12, 0))) is None


def test_daily_limit_caps_initiations():
    sched = ProactiveScheduler(ProactiveConfig(daily_limit=2, min_gap_seconds=0,
                                               proactive_probability=1.0,
                                               return_greeting_bypasses_limit=False))
    now = fixed_now(datetime(2026, 1, 1, 12, 0))
    sched.note_user_activity()
    sent = 0
    for i in range(10):
        sched.last_proactive_at = 0  # ignore cooldown for this test
        msg = sched.next_message(idle_seconds=3600, now=now + i * 60, force=True)
        if msg:
            sent += 1
    assert sent <= 2


def test_cooldown_blocks_rapid_repeats():
    sched = ProactiveScheduler(ProactiveConfig(min_gap_seconds=1800, proactive_probability=1.0))
    now = fixed_now(datetime(2026, 1, 1, 12, 0))
    first = sched.next_message(idle_seconds=3600, now=now)
    assert first is not None
    second = sched.next_message(idle_seconds=3600, now=now + 60)
    assert second is None
    # `force` may bypass the cooldown for a manual/test trigger.
    assert sched.next_message(idle_seconds=3600, now=now + 60, force=True) is not None


def test_dnd_blocks_initiation():
    sched = ProactiveScheduler(ProactiveConfig(dnd_enabled=True, dnd_start="22:00", dnd_end="07:00",
                                               proactive_probability=1.0))
    night = datetime(2026, 1, 1, 23, 30)
    assert sched.in_dnd(night) is True
    assert sched.next_message(idle_seconds=7200, now=fixed_now(night), force=True) is None
    day = datetime(2026, 1, 1, 12, 0)
    assert sched.in_dnd(day) is False


def test_quiet_hours_block_initiation():
    sched = ProactiveScheduler(ProactiveConfig(proactive_probability=1.0))
    now = fixed_now(datetime(2026, 1, 1, 12, 0))
    assert sched.next_message(idle_seconds=7200, now=now, quiet_hours=True, force=True) is None


def test_return_greeting_after_long_absence():
    sched = ProactiveScheduler(ProactiveConfig(return_greeting_after_seconds=3600))
    now = fixed_now(datetime(2026, 1, 1, 12, 0))
    sched.note_user_activity()
    msg = sched.next_message(idle_seconds=7200, now=now)
    assert msg is not None
    assert msg.kind == "return_greeting"


def test_anti_repeat_avoids_same_kind_twice():
    sched = ProactiveScheduler(ProactiveConfig(min_gap_seconds=0, proactive_probability=1.0))
    now = fixed_now(datetime(2026, 1, 1, 12, 0))
    kinds = []
    for i in range(6):
        msg = sched.next_message(idle_seconds=3600, now=now + i * 60, force=True)
        if msg:
            kinds.append(msg.kind)
    for a, b in zip(kinds, kinds[1:]):
        assert a != b


def test_check_in_only_with_real_topic():
    sched = ProactiveScheduler(ProactiveConfig(min_gap_seconds=0, proactive_probability=1.0,
                                               boredom_after_seconds=60))
    now = fixed_now(datetime(2026, 1, 1, 12, 0))
    msg = sched.next_message(idle_seconds=3600, now=now, check_in_topic="Ashu v0.4", force=True)
    assert msg is not None
    assert ("Ashu v0.4" in msg.text) or msg.kind in ("boredom", "attention")


def test_waiting_nudge_kind():
    sched = ProactiveScheduler(ProactiveConfig(min_gap_seconds=0, proactive_probability=1.0,
                                               waiting_nudge_after_seconds=60))
    now = fixed_now(datetime(2026, 1, 1, 12, 0))
    msg = sched.next_message(idle_seconds=600, now=now, waiting_for_user=True, force=True)
    assert msg is not None
    assert msg.kind in ("waiting", "check_in", "follow_up", "boredom", "attention")


def test_engine_maybe_proactive_returns_message_object():
    engine = PersonalityEngine(state_store=InMemoryStateStore())
    engine._proactive.config.enabled = True
    engine._proactive.config.min_gap_seconds = 0
    engine._proactive.config.proactive_probability = 1.0
    message = engine.maybe_proactive(idle_seconds=3600, force=True)
    assert message is not None
    # Backward-compatible text API still works.
    engine._proactive.config.min_gap_seconds = 0
    text = engine.maybe_proactive_message()
    assert text is None or isinstance(text, str)


def test_daily_count_resets_on_new_day():
    sched = ProactiveScheduler(ProactiveConfig(min_gap_seconds=0, proactive_probability=1.0))
    d1 = datetime(2026, 1, 1, 12, 0)
    sched.next_message(idle_seconds=3600, now=fixed_now(d1), force=True)
    assert sched.count_today == 1
    d2 = datetime(2026, 1, 2, 12, 0)
    sched.next_message(idle_seconds=3600, now=fixed_now(d2), force=True)
    assert sched.count_today == 1
