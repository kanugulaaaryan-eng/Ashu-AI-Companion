# Ashu AI Companion — Timeline & Changelog

**Consolidated history from v0.1 → v0.9**

---

## v0.9 — "Floating & Alive" (Sep 2025)
**Focus:** True system overlay, procedural avatar, proactive nudges, design reference integration

### Android Overlay (Kotlin/Compose)
- **`FloatingCompanionService`** — Foreground service with `TYPE_APPLICATION_OVERLAY` window
  - Draggable bubble with edge-snap (left/right)
  - Tap → opens main app | Drag → follows finger
  - Foreground notification (required by Android 8+)
  - Off by default, explicit user toggle in Settings
  - `SYSTEM_ALERT_WINDOW` permission via Android's own settings screen (never silent)

- **`ProceduralAshu.kt`** — Canvas-based avatar (zero assets)
  - **Breathing:** 3.2s scale pulse (1.0 → 1.035)
  - **Blinking:** Natural 100ms close / 50ms hold / 120ms open, random 3–8s intervals
  - **Floating drift:** Perlin-noise X/Y (5–7s periods)
  - **Talking:** Mouth openness driven by `speakingVolume` (0–1 from TTS)
  - **Listening:** Subtle pulse rings around head during STT
  - **10 Moods:** neutral, happy, excited, sad, annoyed, curious, surprised, sleepy, wink, playful
  - **Smooth transitions:** 400ms blend between moods
  - **Reaction pop:** Scale bounce (1.0 → 1.08) on new message
  - **Tap interaction:** Cycles moods | **Drag:** follows finger
  - **Reduced motion:** Disables all autonomous movement instantly

- **Proactive System**
  - `showProactiveMessage(text)` — speech bubble auto-shows, auto-hides after 4s
  - `hideProactiveMessage()` — immediate dismiss
  - `setSpeaking(speaking, volume)` — TTS callback integration
  - `setListening(listening)` — STT callback integration
  - Intent API for Python bridge → overlay communication

- **`FloatingCompanion.kt`** updated:
  - Replaced static `Image` with `ProceduralAshu`
  - Added `SpeechBubble` composable with pop-in animation
  - State holders for proactive, speaking, listening, reduced motion
  - New intent actions: `SHOW_PROACTIVE`, `HIDE_PROACTIVE`, `SET_SPEAKING`, `SET_LISTENING`

### Design Reference Integration
- **Reference sheet:** `ashu_design_reference_sheet.png` (1536×1024, 4×6 grid = 24 cells)
- **Asset manifest:** `ASHU_ASSET_MANIFEST.json` — 45 assets mapped to grid positions
- **Grid extractor:** `scripts/extract_design_reference.py`
  - Extracts 24 cells as individual PNGs (`docs/design/reference_grid/grid_r*_c*.png`)
  - Verifies delivered assets against grid positions
  - Generates comparison image (reference vs delivered)
- **Documentation:**
  - `ASHU_DESIGN_REFERENCE.md` — human-readable mapping table
  - `RIVE_EDITOR_GUIDE.md` — step-by-step to build `.riv` state machine from grid

### Character State System
- **`AshuCharacterState.kt`** — 27 enum states with fallback chain
- 6 delivered v0.9 portraits (neutral, happy, excited, curious, surprised, wink)
- 2 legacy leaf assets (sad, sleepy) for art-consistency
- Fallback chain verified acyclic by unit test
- Mappers: `fromMood()` (brain emotion → state), `fromAction()` (gesture → state)
- Extension: `toProceduralMood()` for procedural renderer

### Bug Fixes
- 5 test encoding failures fixed (`encoding="utf-8"` on file I/O)
- 2 HTML element ID bugs fixed (`getElementById("input")` → `"draft"`)

### Tests
- All 162 tests pass (1 skipped)

---

## v0.8 — "Polished Prototype" (Aug 2025)
**Focus:** Web PWA, memory editing, mood-aware chibi, offline rule brain

### Web Prototype (`web/ashu_prototype.html`)
- Self-contained JavaScript port of brain (rules, dialogue banks, memory commands)
- Real character art (6 v2 portraits as WebP)
- Service Worker for offline caching
- "Add to Home Screen" → PWA install
- Connects to Python bridge for full brain

### Android App
- Memory dashboard with inline edit/pin/delete
- Mood-aware chibi states (thinking, reacting, speaking frames)
- Model management screen with import + recommendations
- Privacy screen with export/wipe
- 10-step onboarding with permissions, model path, test chat
- Reduced motion toggle respected everywhere

### Python Bridge
- `serve.py` — FastAPI bridge with health, chat, setup, memory, model endpoints
- Protocol version "3" (Android ↔ Python contract)
- Local model support (llama.cpp via subprocess)
- Cloud fallback (NIM API) with explicit origin labeling
- Offline fallback mode (rule-based) with honest `origin: "fallback"`

---

## v0.7 — "Clean Build" (Jul 2025)
**Focus:** Fix Gradle memory OOM, ship working APK

- **Gradle memory fix:** `gradle.properties` → `-Xmx1024m -XX:MaxMetaspaceSize=640m`
- **Prebuilt APK:** `ashu-v0.6.0-debug.apk` in repo root
- **Screenshots:** Verified captures of running app in `screenshots/`
- **Verified build:** `BUILD SUCCESSFUL` with JDK 17, AGP 8.7.3, Gradle 8.9, SDK 35
- **aapt/apksigner:** Confirmed package, versions, 21 character drawables

---

## v0.6 — "Actually Compiles" (Jun 2025)
**Focus:** Fix AGP/Gradle/SDK versions, resolve 4 compile errors

- **Version pins fixed:** AGP 8.7.3, Gradle 8.9, compileSdk/targetSdk 35
- **Gradle wrapper** shipped in repo (no local Gradle needed)
- **4 compile errors fixed** in Kotlin sources
- **Min SDK 26, Target SDK 35** — compatible with 95%+ devices
- **APK size:** ~12 MB debug-signed

---

## v0.5 — "Real Art Swap" (May 2025)
**Focus:** Replace procedural renderer with hand-designed character art

- **Asset pack integration:** 12 face expressions + 8 full-body poses + 1 default portrait
- **`ChibiAshu.kt`** — Compose renderer using real PNGs
- **Action system:** 31 named actions with specs (duration, priority, interruptible)
- **Animation controller:** Priority + interruptibility state machine
- **Asset lookup:** `ACTION_ASSET` map + `POSE_ACTIONS` set
- **v0.5 trade-off:** Art is flat stills — no literal blink/mouth movement
  - Solution: whole-image animation (breathing, sway, bounce, hide shift)
  - Reduced motion disables all

---

## v0.4 — "Honest Architecture" (Apr 2025)
**Focus:** Modular inference, explicit personality state, proactive scheduler, privacy

### Core Brain (`python/`)
- **`brain/inference.py` + `model_manager.py`** — Local llama.cpp → cloud fallback → offline fallback
  - Every reply carries `origin`: `local` / `cloud` / `fallback` / `mock` / `rule_based`
  - UI shows origin badge
- **`personality/state.py`** — Full character state (mood, energy, familiarity, trust, boredom, relationship stage, sleep state)
  - Persisted to JSON sidecar (survives restarts)
- **`personality/proactive.py`** — Scheduler with return greeting, check-ins, follow-ups, boredom nudges
  - User toggle, daily limit, DND, quiet hours, cooldown, anti-repeat
- **`personality/language.py`** — Telugu-English code-switching, register progression
- **`memory/memory_commands.py`** — Conversational memory ops (recall, remember, forget, topic-forget, wipe)
- **`security/privacy.py`** — Output sanitisation, confirmation gating, data export/wipe
- **`tools/confirmations.py`** — Confirmation flow for risky actions
- **`tools/device_tools.py`** — Open app, reminders, music, notifications, usage, camera (permission-gated)
- **`voice/voice_manager.py`** — TTS, STT, interrupt, wake-word architecture (honestly unavailable)
- **`vision/vision_manager.py`** — Modular provider, capture/analysis state machine, no covert capture

### Android App (Full v0.4 Client)
- 10-step onboarding
- Chat with voice controls + indicators
- Memory dashboard
- Model management
- Privacy screen
- Activity history
- Reduced motion mode

---

## v0.3 — "Personality Core" (Mar 2025)
**Focus:** Emotion engine, relationship progression, dialogue variety

- **`personality/emotion.py`** — 14 emotions with Telugu labels, intensity, triggers
- **`personality/relationship.py`** — 5 stages (stranger → best friend) with trust/familiarity
- **`personality/dialogue_library.py`** — 200+ lines across moods/contexts
- **`personality/boredom.py`** — Boredom accumulation + attention-seeking
- **`personality/variety.py`** — Anti-repetition for responses
- **`personality/sleep.py`** — Sleep/wake cycle with quiet hours
- **`personality/jealousy.py`** — Jealousy level (0–3) affecting responses

---

## v0.2 — "Local Bridge" (Feb 2025)
**Focus:** Python ↔ Android communication, basic chat

- **`protocols/`** — JSON schema for Android ↔ Python contract
- **`serve.py`** — HTTP bridge (FastAPI) on port 8765
- **`AshuApi.kt`** — Android HTTP client with retry/timeout
- Basic chat endpoint with session persistence
- Health endpoint for connectivity check

---

## v0.1 — "Hello Ashu" (Jan 2025)
**Focus:** Concept, basic chibi, offline rule-based brain

- Procedural Canvas chibi (circles, arcs — no assets)
- Rule-based Telugu/English responses
- Basic mood display (happy/sad/neutral)
- Single-screen chat UI

---

## 📊 Version Summary

| Version | Date | Key Deliverable | Lines of Code (approx) |
|---------|------|-----------------|------------------------|
| v0.9 | Sep 2025 | Floating overlay + procedural avatar + design reference | +2,500 |
| v0.8 | Aug 2025 | Web PWA + memory editing + mood chibi | +3,000 |
| v0.7 | Jul 2025 | Fixed build, shipped APK | +200 |
| v0.6 | Jun 2025 | Compiling Android project | +1,500 |
| v0.5 | May 2025 | Real character art swap | +2,000 |
| v0.4 | Apr 2025 | Honest architecture, proactive, privacy | +8,000 |
| v0.3 | Mar 2025 | Personality engine | +4,000 |
| v0.2 | Feb 2025 | Local bridge | +1,500 |
| v0.1 | Jan 2025 | Concept + procedural chibi | +500 |

**Total:** ~23,000 lines (Kotlin + Python + JS + tests + docs)

---

## 🏷️ Tags (for Git)

```bash
git tag -a v0.1 -m "Concept + procedural chibi"
git tag -a v0.2 -m "Local bridge"
git tag -a v0.3 -m "Personality core"
git tag -a v0.4 -m "Honest architecture"
git tag -a v0.5 -m "Real art swap"
git tag -a v0.6 -m "Actually compiles"
git tag -a v0.7 -m "Clean build + APK"
git tag -a v0.8 -m "Polished prototype"
git tag -a v0.9 -m "Floating overlay + procedural avatar"
```

---

## 📝 Notes for Contributors

- **Changelog format:** Each version gets a section with subsections (Android, Python, Design, Bug Fixes, Tests)
- **Breaking changes:** Marked with ⚠️
- **Deprecations:** Marked with 📛
- **Security fixes:** Marked with 🔒
- **Performance:** Marked with ⚡