"""
Regression tests for the v0.9 Ashu character/asset system.

Scope note: the state-resolution logic itself is implemented twice on
purpose -- once in Kotlin (AshuCharacterState.kt, used by the Android app)
and once in JS (embedded in web/ashu_prototype.html, Part 10's "mirror
Android behavior as closely as practical"). This sandbox has no Android
SDK / Gradle / kotlinc available (no network route to a Maven/Google
repo either), so the Kotlin side cannot be compiled or unit-tested here --
see docs/CHANGELOG_v0.9.md for exactly what that blocks and the command
that fails. What *is* testable from Python:

  * the actual asset files this pack ships (Part 1 / Part 11)
  * the brain's mood set lines up with what both renderers map from
    (Part 3)
  * the JS fallback/state system (Part 12), by shelling out to `node`
    against the real file, not a reimplementation of it
  * repo hygiene: the new Kotlin files parse as balanced/sane text and
    declare the symbols the other parts require (best-effort static
    check, not a substitute for `./gradlew build`)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ANDROID_RES = ROOT / "android" / "app" / "src" / "main" / "res" / "drawable-nodpi"
WEB_PORTRAITS = ROOT / "web" / "assets" / "ashu" / "portraits"
WEB_PROTOTYPE = ROOT / "web" / "ashu_prototype.html"
KOTLIN_DIR = ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "ashu" / "app"

NEW_STATES_DELIVERED = ["neutral", "happy", "excited", "curious", "surprised", "wink"]

ALL_STATES = [
    "NEUTRAL", "HAPPY", "EXCITED", "LAUGHING", "PLAYFUL", "WINK", "CURIOUS",
    "SURPRISED", "CONFUSED", "THINKING", "SIDE_EYE", "POUT", "ANNOYED",
    "SARCASTIC", "TIRED", "SLEEPY", "CONCERNED", "CARING", "EMBARRASSED",
    "PROUD", "TEASING", "SAD", "LISTENING", "SPEAKING", "REACTING", "BORED",
    "ATTENTION",
]

EXPLICIT_FALLBACKS = {  # from PART 12 of the brief, must hold in both renderers
    "TEASING": "PLAYFUL",
    "CONCERNED": "CARING",
    "BORED": "NEUTRAL",
    "ATTENTION": "CURIOUS",
}


# --------------------------------------------------------------------------
# Part 1 / Part 11: asset installation + optimization
# --------------------------------------------------------------------------

def test_android_v2_portraits_installed_with_clean_names():
    for state in NEW_STATES_DELIVERED:
        f = ANDROID_RES / f"ashu_v2_{state}.png"
        assert f.exists(), f"missing {f}"
        assert f.stat().st_size > 0


def test_web_v2_portraits_installed():
    for state in NEW_STATES_DELIVERED:
        f = WEB_PORTRAITS / f"ashu_v2_{state}.webp"
        assert f.exists(), f"missing {f}"


def test_android_portraits_are_smaller_than_the_source_originals():
    src_dir = ROOT.parent / "assets_pack" / "ashu_assets" / "portraits"
    if not src_dir.exists():
        pytest.skip("original asset pack not present in this checkout")
    for state in NEW_STATES_DELIVERED:
        src = src_dir / f"ashu_{state}.png"
        out = ANDROID_RES / f"ashu_v2_{state}.png"
        assert out.stat().st_size < src.stat().st_size, (
            f"{out} did not shrink relative to source {src}"
        )


def test_web_portraits_are_much_smaller_than_android_ones():
    # web/ is optimized more aggressively (512px webp) than Android's
    # 1024px png, since it has to travel over HTTP on every page load.
    for state in NEW_STATES_DELIVERED:
        android_size = (ANDROID_RES / f"ashu_v2_{state}.png").stat().st_size
        web_size = (WEB_PORTRAITS / f"ashu_v2_{state}.webp").stat().st_size
        assert web_size < android_size


def test_no_transparent_png_was_flattened_to_jpeg():
    for state in NEW_STATES_DELIVERED:
        f = ANDROID_RES / f"ashu_v2_{state}.png"
        from PIL import Image

        with Image.open(f) as im:
            assert im.mode in ("RGBA", "LA"), f"{f} lost its alpha channel"


# --------------------------------------------------------------------------
# Part 3: mood -> state mapping covers every brain emotion
# --------------------------------------------------------------------------

def _kotlin_from_mood_table() -> dict[str, str]:
    src = (KOTLIN_DIR / "AshuCharacterState.kt").read_text()
    body = re.search(r"fun fromMood\(mood: String\).*?\{(.*?)\n\s{8}\}", src, re.S)
    assert body, "fromMood() not found in AshuCharacterState.kt"
    pairs = re.findall(r'"(\w+)"\s*->\s*(\w+)', body.group(1))
    return dict(pairs)


def test_every_brain_emotion_has_a_kotlin_mood_mapping():
    from personality.emotion import Emotion

    table = _kotlin_from_mood_table()
    for emotion in Emotion:
        assert emotion.value in table, f"Emotion.{emotion.name} ('{emotion.value}') unmapped in fromMood()"


def test_every_kotlin_state_target_is_a_real_state():
    table = _kotlin_from_mood_table()
    for mood, state in table.items():
        assert state in ALL_STATES, f"fromMood('{mood}') -> unknown state {state}"


# --------------------------------------------------------------------------
# Part 12: fallback chain (JS side, executed for real via node)
# --------------------------------------------------------------------------

def _run_node(js_expr: str):
    script = WEB_PROTOTYPE.read_text(encoding="utf-8")
    m = re.search(r"<script>(.*?)</script>", script, re.S)
    assert m, "no inline <script> found in web prototype"
    body = m.group(1)
    # The real page auto-runs registerPWA()/boot() at the bottom, which touch
    # the DOM immediately on load. We only need the function/constant
    # definitions for these tests, so stub out just enough of `document` /
    # `window` / `localStorage` / `navigator` / `location` for the module to
    # finish loading without throwing, rather than trying to strip every
    # DOM-touching top-level call (more robust if the page grows more of them).
    stub = """
      const _stubEl = () => ({classList:{add(){},remove(){},toggle(){},contains(){return false}},
        style:{}, addEventListener(){}, appendChild(){}, querySelector(){return _stubEl();},
        querySelectorAll(){return [];}, getAttribute(){return null;}, setAttribute(){},
        remove(){}, getBoundingClientRect(){return {left:0,top:0,width:0,height:0};}});
      global.document = {addEventListener(){}, removeEventListener(){}, getElementById(){return _stubEl();},
        querySelector(){return _stubEl();}, querySelectorAll(){return [];}, createElement(){return _stubEl();},
        body:_stubEl(), title:''};
      global.window = global;
      global.localStorage = {getItem(){return null;}, setItem(){}, removeItem(){}};
      global.navigator = {vibrate(){}, onLine:true, language:'en'};
      global.location = {search:'', protocol:'https:', port:'', hostname:'localhost', origin:''};
      global.speechSynthesis = {getVoices(){return [];}, speak(){}, cancel(){}};
      global.fetch = () => Promise.reject(new Error('no network in test harness'));
      global.setInterval = () => 0; // boot() schedules a 60s boredom-nudge timer;
      global.clearInterval = () => {}; // don't let it keep the process alive
    """
    harness = stub + "\n" + body + f"\nconsole.log(JSON.stringify({js_expr}));\nprocess.exit(0);"
    import tempfile
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".js", delete=False) as tf:
        tf.write(harness)
        tmp_path = tf.name
    try:
        result = subprocess.run(
            ["node", tmp_path],
            capture_output=True, text=True, cwd=ROOT, timeout=15,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    assert result.returncode == 0, f"node failed:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_web_missing_asset_fallback_resolves_every_state():
    if not _node_available():
        pytest.skip("node not available in this environment")
    mapping = _run_node(
        "Object.fromEntries(" + json.dumps(ALL_STATES) + ".map(s => [s, ashuAssetForState(s)]))"
    )
    for state in ALL_STATES:
        asset = mapping[state]
        assert asset, f"{state} resolved to an empty asset"
        # every leaf must actually exist in ASHU_ASSETS (checked separately)


def test_web_fallback_chain_never_returns_a_broken_image():
    if not _node_available():
        pytest.skip("node not available in this environment")
    known_keys = _run_node("Object.keys(ASHU_ASSETS)")
    mapping = _run_node(
        "Object.fromEntries(" + json.dumps(ALL_STATES) + ".map(s => [s, ashuAssetForState(s)]))"
    )
    for state, asset in mapping.items():
        assert asset in known_keys, f"{state} -> '{asset}' has no entry in ASHU_ASSETS"


def test_web_explicit_spec_fallbacks_match_part_12():
    if not _node_available():
        pytest.skip("node not available in this environment")
    direct = _run_node("ASHU_STATE_DIRECT")
    fallback = _run_node("ASHU_STATE_FALLBACK")
    for state, expected_target in EXPLICIT_FALLBACKS.items():
        assert state not in direct, f"{state} unexpectedly has direct art now -- update EXPLICIT_FALLBACKS"
        assert fallback.get(state) == expected_target, (
            f"{state} should fall back toward {expected_target} per the brief"
        )


def _node_available() -> bool:
    return subprocess.run(["node", "--version"], capture_output=True).returncode == 0


# --------------------------------------------------------------------------
# Part 6/12: reduced-motion + fallback are also mirrored in Kotlin (static check)
# --------------------------------------------------------------------------

def test_kotlin_character_state_file_declares_every_state():
    src = (KOTLIN_DIR / "AshuCharacterState.kt").read_text(encoding="utf-8")
    for state in ALL_STATES:
        assert re.search(rf"\b{state}\b", src), f"{state} missing from AshuCharacterState.kt"


def test_kotlin_character_state_fallback_is_acyclic():
    src = (KOTLIN_DIR / "AshuCharacterState.kt").read_text(encoding="utf-8")
    body = re.search(r"FALLBACK: Map<.*?=\s*mapOf\((.*?)\n\s{8}\)", src, re.S)
    assert body
    pairs = re.findall(r"(\w+)\s+to\s+(\w+)", body.group(1))
    fallback = dict(pairs)
    direct = set(re.findall(r"(\w+)\s+to\s+R\.drawable\.ashu_v2_", src))
    legacy = set(re.findall(r"(\w+)\s+to\s+R\.drawable\.ashu_emo_", src))
    for state in fallback:
        cur, seen = state, set()
        while cur not in direct and cur not in legacy:
            assert cur not in seen, f"cycle detected starting at {state}"
            seen.add(cur)
            cur = fallback[cur]


def test_kotlin_and_web_agree_on_which_states_have_real_art():
    kt = (KOTLIN_DIR / "AshuCharacterState.kt").read_text(encoding="utf-8")
    kt_direct = set(re.findall(r"(\w+)\s+to\s+R\.drawable\.ashu_v2_", kt))
    kt_legacy = set(re.findall(r"(\w+)\s+to\s+R\.drawable\.ashu_emo_", kt))

    web = WEB_PROTOTYPE.read_text(encoding="utf-8")
    m1 = re.search(r"ASHU_STATE_DIRECT\s*=\s*\{(.*?)\};", web, re.S)
    m2 = re.search(r"ASHU_STATE_LEGACY_LEAF\s*=\s*\{(.*?)\};", web, re.S)
    assert m1 and m2
    web_direct = set(re.findall(r"(\w+):\s*\"ashu_v2_", m1.group(1)))
    web_legacy = set(re.findall(r"(\w+):\s*\"ashu_emo_", m2.group(1)))

    assert kt_direct == web_direct, (kt_direct, web_direct)
    assert kt_legacy == web_legacy, (kt_legacy, web_legacy)


# --------------------------------------------------------------------------
# Part 8: floating companion -- infra exists, defaults to off
# --------------------------------------------------------------------------

def test_android_manifest_is_well_formed_xml():
    import xml.etree.ElementTree as ET

    ET.parse(ROOT / "android" / "app" / "src" / "main" / "AndroidManifest.xml")


def test_floating_companion_service_registered_and_off_by_default():
    manifest = (ROOT / "android" / "app" / "src" / "main" / "AndroidManifest.xml").read_text()
    assert "FloatingCompanionService" in manifest
    assert "SYSTEM_ALERT_WINDOW" in manifest

    kt = (KOTLIN_DIR / "FloatingCompanion.kt").read_text()
    assert "PREF_ENABLED" in kt
    app = (KOTLIN_DIR / "AshuApp.kt").read_text(encoding="utf-8")
    # default value passed to the remembered toggle must be false
    assert re.search(r"getBoolean\(FloatingCompanionPermission\.PREF_ENABLED,\s*false\)", app)
    # the permission is only ever requested via Android's own settings screen,
    # never via a runtime permission dialog Claude/the app controls directly
    assert "ACTION_MANAGE_OVERLAY_PERMISSION" in kt


def test_web_floating_demo_defaults_off_and_is_settings_gated():
    web = WEB_PROTOTYPE.read_text(encoding="utf-8")
    assert "floatingDemo:false" in web
    assert '"Floating Ashu demo' in web


# --------------------------------------------------------------------------
# Part 9: chat avatar must never occupy the message-text area (regression
# guard for the pre-existing v0.8 fix -- make sure v0.9 didn't remove it)
# --------------------------------------------------------------------------

def test_chat_avatar_shelf_is_still_separate_from_message_list():
    app = (KOTLIN_DIR / "AshuApp.kt").read_text(encoding="utf-8")
    assert "chat-hero" not in app  # that's web-only markup; sanity check we're in the right file
    assert re.search(r"chat-hero-avatar|avatar.*shelf|Avatar shelf", app, re.I) or "ChibiAshu(" in app


def test_web_chat_avatar_has_dedicated_shelf_not_overlapping_bubbles():
    web = WEB_PROTOTYPE.read_text(encoding="utf-8")
    assert "chat-hero-avatar" in web
    assert 'id="chibi"' in web


# --------------------------------------------------------------------------
# Part 7: reaction duration is randomized, not identical every time
# --------------------------------------------------------------------------

def test_reaction_duration_is_randomized_in_both_renderers():
    kt = (KOTLIN_DIR / "ChibiAshu.kt").read_text(encoding="utf-8")
    assert "(300..600).random()" in kt

    web = WEB_PROTOTYPE.read_text(encoding="utf-8")
    assert "300+Math.floor(Math.random()*300)" in web
