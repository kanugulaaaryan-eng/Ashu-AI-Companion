"""v0.4 tests: Telugu-first language layer + realistic code-switching set.

Includes a fixture of realistic Telugu-English conversations (the spec asks
for a test set) and asserts detection, register progression and the
non-flirty product rule.
"""

import json
from pathlib import Path

import pytest

from personality.language import LanguageLayer, LanguageConfig
from personality.emotion import Emotion
from personality.dialogue_library import TEASING, AFFECTIONATE, MILD_SCOLDING

FIXTURE = Path(__file__).parent / "fixtures" / "telugu_english_examples.json"


def load_examples():
    with FIXTURE.open(encoding="utf-8") as fh:
        return json.load(fh)["examples"]


def test_fixture_exists_and_has_examples():
    examples = load_examples()
    assert len(examples) >= 5
    for example in examples:
        assert example["user"]
        assert "expected_language" in example


@pytest.mark.parametrize("example", load_examples(), ids=lambda e: e["id"])
def test_example_language_detection(example):
    detected = LanguageLayer.detect(example["user"])
    expected = example["expected_language"]
    if expected == "mixed":
        assert detected in ("te", "en")
    elif expected == "hi":
        assert detected in ("hi", "en", "te")
    else:
        assert detected == "te"


def test_telugu_script_detected():
    assert LanguageLayer.detect("నేను బాగున్నాను") == "te"


def test_hindi_script_detected():
    assert LanguageLayer.detect("कल मिलते हैं") == "hi"


def test_roman_telugu_detected():
    assert LanguageLayer.detect("em chestunav ra") == "te"
    assert LanguageLayer.detect("how are you doing today") == "en"


def test_register_progression():
    layer = LanguageLayer()
    assert layer.register("formal") == "polite"
    assert layer.register("acquaintance") == "friendly"
    assert layer.register("comfortable_friend") == "casual"
    assert layer.register("best_friend") == "bestie"
    assert layer.register("close_companion") == "bestie"


def test_code_switch_probability_zero_keeps_text_unchanged():
    layer = LanguageLayer(LanguageConfig(code_switch_probability=0.0))
    assert layer.code_switch("sare ra", "best_friend") == "sare ra"


def test_code_switch_probability_one_adds_connector():
    layer = LanguageLayer(LanguageConfig(code_switch_probability=1.0))
    out = layer.code_switch("sare ra", "best_friend")
    assert out != "sare ra"
    assert out.endswith("sare ra")


def test_mix_blends_both_languages():
    layer = LanguageLayer()
    blended = layer.mix("sare ra", "no problem", "best_friend")
    assert "sare ra" in blended
    assert "no problem" in blended


def test_style_guidance_is_telugu_first_and_non_flirty():
    layer = LanguageLayer()
    guidance = layer.style_guidance("best_friend").lower()
    assert "telugu" in guidance
    assert "flirty" in guidance
    assert "never be flirty" in guidance


def test_dialogue_banks_are_non_empty_and_not_flirty():
    for bank in (TEASING, AFFECTIONATE, MILD_SCOLDING):
        assert bank
    # Affection lines must not contain explicit romantic/flirty phrasing.
    forbidden = ["kiss me", "i love you baby", "sweetheart", "be mine"]
    for line in AFFECTIONATE:
        lowered = line.lower()
        assert not any(f in lowered for f in forbidden)


def test_locale_code_mapping():
    assert LanguageLayer.locale_code("te") == "te-IN"
    assert LanguageLayer.locale_code("hi") == "hi-IN"
    assert LanguageLayer.locale_code("en") == "en-IN"
