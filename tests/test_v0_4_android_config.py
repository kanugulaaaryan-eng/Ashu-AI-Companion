"""v0.4 tests: Android build-configuration verification, done *statically*.

This sandbox has no Android SDK/Gradle and no access to Google's Maven
repositories, so an APK cannot be compiled here. These tests therefore verify
the build configuration and the cross-language contracts that a real build
would otherwise catch, and nothing more. They do NOT claim the APK builds.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android"
APP = ANDROID / "app"
KOTLIN = APP / "src" / "main" / "java" / "com" / "ashu" / "app"
MANIFEST = APP / "src" / "main" / "AndroidManifest.xml"
GRADLE = APP / "build.gradle.kts"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --- build files -----------------------------------------------------------

def test_gradle_version_matches_current_release():
    # v0.8 bumped the app to 0.8.0 / versionCode 8. This previously pinned
    # 0.4.0/4 and was left stale by the v0.6 build fix, so it failed.
    text = read(GRADLE)
    assert 'versionName = "0.8.0"' in text
    assert "versionCode = 8" in text


def test_gradle_sdks_are_sane():
    # v0.6 corrected these from the non-existent platform 37 to the real,
    # widely-installed platform 35 (compileSdk >= targetSdk).
    text = read(GRADLE)
    assert "compileSdk = 35" in text
    assert "minSdk = 26" in text
    assert "targetSdk = 35" in text


def test_root_gradle_has_required_plugins():
    text = read(ANDROID / "build.gradle.kts")
    for plugin in (
        "com.android.application",
        "org.jetbrains.kotlin.android",
        "org.jetbrains.kotlin.plugin.compose",
    ):
        assert plugin in text


def test_manifest_declares_core_permissions():
    text = read(MANIFEST)
    for permission in (
        "android.permission.INTERNET",
        "android.permission.CAMERA",
        "android.permission.RECORD_AUDIO",
        "android.permission.POST_NOTIFICATIONS",
    ):
        assert permission in text, permission


def test_manifest_declares_notification_listener_service():
    text = read(MANIFEST)
    assert "android.service.notification.NotificationListenerService" in text
    assert "BIND_NOTIFICATION_LISTENER_SERVICE" in text
    assert ".AshuNotificationListener" in text


def test_manifest_has_speech_recognition_queries():
    text = read(MANIFEST)
    assert "android.speech.RecognitionService" in text


# --- Kotlin source contracts ----------------------------------------------

def test_all_expected_kotlin_files_exist():
    for name in (
        "AshuApp.kt", "AshuApi.kt", "AshuVoice.kt", "ChibiAshu.kt",
        "DeviceTools.kt", "PhonePermissions.kt", "MainActivity.kt",
    ):
        assert (KOTLIN / name).is_file(), name


def _kotlin_action_set() -> set:
    text = read(KOTLIN / "ChibiAshu.kt")
    match = re.search(r"ASHU_ACTIONS: Set<String> = setOf\((.*?)\)", text, re.S)
    assert match, "ASHU_ACTIONS set not found in ChibiAshu.kt"
    return set(re.findall(r'"([a-z_]+)"', match.group(1)))


def test_python_and_kotlin_action_libraries_match():
    # The brain picks an action by name; the renderer must know every name.
    from personality.animation import ANIMATION_ACTIONS
    kotlin = _kotlin_action_set()
    python = set(ANIMATION_ACTIONS)
    missing = python - kotlin
    assert not missing, f"Kotlin renderer is missing actions: {sorted(missing)}"


def test_kotlin_renderer_has_v0_4_state_actions():
    kotlin = _kotlin_action_set()
    for action in ("listening", "speaking", "waiting"):
        assert action in kotlin, action


def test_kotlin_renderer_supports_reduced_motion():
    text = read(KOTLIN / "ChibiAshu.kt")
    assert "reducedMotion" in text
    assert "AshuAnimationController" in text


def test_animation_controller_has_priority_and_interruptibility():
    text = read(KOTLIN / "ChibiAshu.kt")
    assert "priority" in text
    assert "interruptible" in text
    assert "ACTION_SPECS" in text


def test_voice_layer_has_stt_tts_and_interrupt():
    text = read(KOTLIN / "AshuVoice.kt")
    assert "SpeechRecognizer" in text
    assert "TextToSpeech" in text
    assert "fun interrupt()" in text
    assert "VoiceState" in text


def test_voice_layer_wake_word_is_honestly_unavailable():
    text = read(KOTLIN / "AshuVoice.kt")
    # Wake word must be reported unavailable until a real model exists.
    assert '"available" to false' in text


def test_ui_handles_confirmation_flow():
    text = read(KOTLIN / "AshuApp.kt")
    assert "pendingActionId" in text
    assert "Confirm" in text and "Cancel" in text


def test_ui_has_privacy_and_data_deletion():
    text = read(KOTLIN / "AshuApp.kt")
    assert "PrivacyScreen" in text
    assert "delete" in text.lower()
    assert "wipeData" in text


def test_ui_shows_model_origin_honestly():
    text = read(KOTLIN / "AshuApp.kt")
    assert "modelNotice" in text
    assert "offline fallback" in text.lower()


def test_no_flirty_ui_affordance():
    # v0.4 removes flirty. The onboarding still shows flirtyEnabled=false.
    app = read(KOTLIN / "AshuApp.kt")
    assert "flirtyEnabled = false" in app
    voice = read(KOTLIN / "AshuVoice.kt")
    assert "flirty" not in voice.lower()


def test_kotlin_hairstyle_param_is_documented_noop():
    # v0.5: ChibiAshu.kt swapped its procedural Canvas renderer (which had a
    # rendering branch per Python HAIRSTYLES value) for real, fixed character
    # art with only one hairstyle. `hairstyle` is kept on the composable's
    # signature for source compatibility with existing callers, but is no
    # longer expected to visually vary -- so, unlike v0.4, this test does not
    # assert Python/Kotlin hairstyle-name parity. It instead guards against
    # silent regression: the param must still exist, and the file must still
    # say plainly that it's inert, so nobody re-adds hairstyle branching
    # without also updating this comment.
    text = read(KOTLIN / "ChibiAshu.kt")
    assert "hairstyle: String" in text
    assert "not visually applied" in text


def test_kotlin_action_assets_cover_all_actions():
    # Every action in the shared Python/Kotlin action library must resolve to
    # a real drawable in ChibiAshu.kt's ACTION_ASSET table -- this is the
    # v0.5 equivalent of the old hairstyle-parity check: a cross-language
    # contract test that would catch a newly added action (on either side)
    # that the other side doesn't know how to render.
    from personality.animation import ANIMATION_ACTIONS
    text = read(KOTLIN / "ChibiAshu.kt")
    action_asset_block = text.split("private val ACTION_ASSET")[1].split("private val MOOD_ASSET")[0]
    mapped = set(re.findall(r'"([a-z_]+)" to R\.drawable\.', action_asset_block))
    missing = set(ANIMATION_ACTIONS) - mapped
    assert not missing, f"actions with no Kotlin asset mapping: {sorted(missing)}"


def test_kotlin_drawable_references_exist_on_disk():
    # Cross-check every R.drawable.* the Kotlin sources reference against the
    # PNGs actually shipped in res/ -- catches a typo'd or renamed asset
    # reference that would otherwise only surface as a real compile error.
    res = APP / "src" / "main" / "res"
    available = {p.stem for p in res.glob("drawable*/*.png")}
    for kt_file in KOTLIN.glob("*.kt"):
        for name in re.findall(r"R\.drawable\.([a-z_0-9]+)", read(kt_file)):
            assert name in available, f"{kt_file.name} references missing drawable {name}"


def test_device_tools_are_permission_gated():
    text = read(KOTLIN / "DeviceTools.kt")
    assert "hasNotificationAccess" in text
    assert "hasUsageAccess" in text
    assert "hasCameraPermission" in text
