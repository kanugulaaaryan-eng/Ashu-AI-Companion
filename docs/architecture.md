# Ashu architecture

## v0.4 data flow

```text
Android Jetpack Compose UI (AshuApp.kt)
  │  chat · voice (AshuVoice.kt) · chibi (ChibiAshu.kt) · memory · model · privacy
  │
  │  JSON / local HTTP  (protocol_version "3")
  ▼
Python local bridge (protocols/local_server.py)
  │
  ▼
Ashu Agent (brain/agent.py)
  ├── ContextBuilder        (brain/context.py)
  ├── DecisionEngine        (brain/decision.py)
  ├── MemoryCommands        (memory/memory_commands.py)
  ├── PersonalityEngine     (personality/personality_engine.py)
  │     ├── PersonalityState (personality/state.py)         ← persisted sidecar
  │     ├── LanguageLayer    (personality/language.py)
  │     ├── ProactiveScheduler (personality/proactive.py)
  │     ├── EmotionEngine / RelationshipEngine / JealousySystem
  │     ├── AppearanceSystem / AnimationController
  │     └── SleepSchedule
  ├── ToolSystem            (tools/tool_system.py)
  │     ├── builtin file tools (tools/builtin_tools.py, sandboxed)
  │     ├── ConfirmationManager (tools/confirmations.py)
  │     └── DeviceBridge     (tools/device_tools.py) ⇄ Android DeviceTools.kt
  ├── Security              (security/privacy.py)  ← sanitises model output
  │
  ▼
InferenceRouter (brain/inference.py)
  ├── 1. Local model     LlamaCppProvider  ─┐
  ├── 2. Cloud fallback  CloudFallbackProvider (opt-in, credential-gated)
  └── 3. Offline fallback OfflineFallbackProvider (explicitly NOT a model)
                                            │
                         ModelManager (brain/model_manager.py)
                         registry · status · storage · import · download

VoiceManager (voice/voice_manager.py)   VisionManager (vision/vision_manager.py)
  provider abstraction · TTS/STT            provider abstraction · capture
  wake-word architecture (unavailable)      no covert capture · no recognition claim
```

The LLM is deliberately an interchangeable component. Ashu's memory,
personality, permission model and tool protocols are not tied to one model.
Swapping the model runtime touches only `brain/inference.py`.

## Module boundaries (v0.4)

| Concern | Module | Responsibility |
|---|---|---|
| Character state | `personality/state.py` | one persisted state object |
| Why she speaks | `personality/proactive.py` | bounded, permitted-signal initiation |
| How she sounds | `personality/language.py` | register + code-switching |
| What she shows | `personality/animation.py` ↔ `ChibiAshu.kt` | action names + renderer |
| What she remembers | `memory/` | SQLite + conversational commands |
| What she may do | `tools/permissions.py`, `tools/confirmations.py` | gating + confirmation |
| Where text comes from | `brain/inference.py` | local/cloud/fallback + provenance |
| What is safe | `security/privacy.py` | untrusted-output sanitising |

## Mobile model strategy

Do not ship a multi-GB model inside the repository. Keep it separately
downloadable/importable and configurable; the Android app runs standalone with
an honest offline fallback and upgrades to better answers once a model is
imported. The base APK bundles no native runtime; `app/build.gradle.kts`
documents the one hook needed to add a llama.cpp Android binding.

## On-device inference (planned path)

1. Ship a llama.cpp Android (JNI) binding.
2. Implement a Kotlin `LocalModelRunner` with the same generate/stream shape as
   the bridge's `InferenceRouter`.
3. Keep the Android app's on-device path and the Python bridge contract
   identical, so either can serve the UI and the provenance rules still hold.

## v0.1–v0.3 history

v0.1 built the Python brain, SQLite memory, permissioned tools and a thin
Android client. v0.2 made it a Telugu-first companion with a chibi and device
TTS. v0.3 added the 5-stage relationship arc, the 18-emotion engine, jealousy,
boredom, sleep state machine, appearance and a 30-action animation library.
v0.4 adds explicit personality state, a real proactive scheduler, honest
inference provenance, memory review + privacy controls, confirmations, the
voice/vision abstraction and the de-flirtied, privacy-first product rules.
