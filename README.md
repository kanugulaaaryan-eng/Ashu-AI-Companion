# Ashu AI Companion

**A local-first, privacy-respecting AI companion that lives on your phone as a floating avatar — speaks Telugu + English, remembers what matters, notices when you're gone, and can start conversations on her own.**

> **Current version: v0.9** — Procedural floating avatar, overlay service, proactive nudges, design reference integration

---

## ✨ What Ashu Does

| Feature | Description |
|---------|-------------|
| **Floating Avatar** | System overlay (`TYPE_APPLICATION_OVERLAY`) — breathes, blinks, floats, talks, expresses emotions, reacts to taps/drags |
| **Procedural Animation** | Zero asset dependency — Canvas-based character with 10 moods, TTS-synced mouth, natural blink intervals, Perlin drift |
| **Proactive Nudges** | Speech bubbles appear when she's bored, notices notifications, or wants to check in — fully user-controlled |
| **Telugu-First Chat** | Native Telugu (Telangana/Andhra) + English code-switching, relationship progression, memory-aware replies |
| **Local-First Brain** | Python bridge runs locally (llama.cpp/Gemma/Qwen), optional NIM API + free GPT fallback — every reply labeled with origin |
| **Memory & Personality** | SQLite memory with conversational commands (`remember`, `forget`, `recall`), mood/energy/familiarity/trust state machine |
| **Voice I/O** | Android TTS + STT with speaking/listening indicators, interrupt support |
| **Privacy by Design** | No telemetry, no covert capture, explicit confirmations for risky actions, full export/wipe |
| **Cross-Platform Ready** | Android (Kotlin/Compose) + Web PWA + Expo (planned) — same brain, same protocol |

---

## 📱 Quick Start (Android)

### Prerequisites
- Android Studio (Koala+) or JDK 17 + Android SDK (platform 35, build-tools 35)
- **OR** just install the APK when released

### Build & Install
```bash
cd android
./gradlew assembleDebug
# Output: app/build/outputs/apk/debug/app-debug.apk
```

### Run on Device
1. Install APK → open Ashu
2. Complete 10-step onboarding (name, languages, voice, permissions, model path)
3. **Settings → Floating Ashu ON** → grant "Display over other apps"
4. Ashu appears as a floating companion — tap to open chat, drag to move, she snaps to edges

### Connect Python Bridge (for full brain)
```bash
# On your PC/laptop (same LAN as phone)
cd ../python
pip install -r ../../requirements.txt
python ../serve.py --host 0.0.0.0 --port 8765
```
Then in Ashu app: **Settings → Bridge URL** → `http://<PC_IP>:8765`

---

## 🌐 Quick Start (Web PWA)

```bash
cd web
# Open ashu_prototype.html directly in browser, or serve:
python -m http.server 8080
# Then open http://localhost:8080/ashu_prototype.html
```
- Works offline (Service Worker)
- "Add to Home Screen" → installs as PWA
- Connects to Python bridge for full brain
- **Note:** No floating overlay on web (browser limitation)

---

## 🧠 Python Bridge (Local Brain)

```bash
cd python
pip install -r ../../requirements.txt

# Health check
python ../serve.py --host 0.0.0.0 --port 8765

# With local model (GGUF)
python ../serve.py --host 0.0.0.0 --port 8765 --model-path ~/models/qwen3-4b-q4.gguf

# With NIM API (cloud)
export NIM_API_KEY="your_key"
python ../serve.py --host 0.0.0.0 --port 8765 --cloud
```

**Endpoints:**
- `GET  /v1/health` — bridge status, model info
- `POST /v1/chat` — chat with session, returns mood, animation, origin
- `POST /v1/setup` — configure personality, voice, proactive, memory
- `GET  /v1/memory` — list memories (with search)
- `POST /v1/memory` — add/update/delete memories
- `GET  /v1/activity` — transparent activity log
- `GET  /v1/model/status` — local model status
- `POST /v1/model/import` — import GGUF model

---

## 🏗 Project Structure

```
Ashu AI companion/
├── android/                 # Android app (Kotlin + Jetpack Compose)
│   ├── app/
│   │   └── src/main/java/com/ashu/app/
│   │       ├── AshuApp.kt              # Main app: chat, memory, model, settings, onboarding
│   │       ├── AshuCharacterState.kt   # 27 mood states → asset mapping with fallbacks
│   │       ├── ProceduralAshu.kt       # Canvas avatar: breathes, blinks, floats, talks, 10 moods
│   │       ├── FloatingCompanion.kt    # Overlay service + proactive speech bubbles
│   │       ├── ChibiAshu.kt            # In-app chibi renderer (uses character states)
│   │       ├── AshuVoice.kt            # TTS/STT bridge
│   │       ├── AshuApi.kt              # HTTP client to Python bridge
│   │       └── ... (permissions, device tools, etc.)
│   └── build.gradle.kts
│
├── python/                  # Local brain (pure Python, no framework lock-in)
│   ├── brain/               # Agent, context, decision, inference router, model manager
│   ├── personality/         # State, emotion, relationship, proactive, language, animation
│   ├── memory/              # SQLite + conversational memory commands
│   ├── tools/               # Permission-gated tools, confirmations, device bridge
│   ├── voice/               # Voice provider abstraction
│   ├── vision/              # Modular vision layer
│   ├── security/            # Output sanitising + privacy/export
│   └── protocols/           # Android ↔ Python contract (protocol_version "4")
│
├── docs/                    # Architecture, changelog, privacy, protocol
│   ├── architecture.md
│   ├── CHANGELOG.md         # Consolidated timeline
│   ├── PRIVACY.md
│   ├── PROTOCOL.md
│   └── design/              # Design reference + Rive guide
│       ├── ASHU_ASSET_MANIFEST.json
│       ├── ASHU_DESIGN_REFERENCE.md
│       ├── RIVE_EDITOR_GUIDE.md
│       └── reference_grid/  # 24 extracted grid cells
│
├── web/                     # Web PWA prototype
│   ├── ashu_prototype.html  # Self-contained JS port of brain
│   ├── manifest.webmanifest
│   ├── sw.js                # Service worker (offline)
│   └── assets/ashu/portraits/  # 6 delivered v2 portraits (WebP)
│
├── scripts/                 # Utilities
│   └── extract_design_reference.py  # Grid extractor + asset verifier
│
├── tests/                   # Unit tests (162 passing)
│   ├── test_core.py
│   ├── test_v0_9_character.py
│   └── ...
│
├── assets/                  # Design assets
│   ├── ashu_design_reference_sheet.png  # 4×6 grid (1536×1024)
│   ├── ASHU_ASSET_MANIFEST.json         # 45 assets mapped to grid
│   ├── ASHU_DESIGN_REFERENCE.md         # Human-readable mapping
│   ├── RIVE_EDITOR_GUIDE.md             # Build .riv from grid
│   └── reference_grid/                  # 24 PNG cells (256×256)
│
├── requirements.txt         # Python deps
├── serve.py                 # Bridge entrypoint
└── README.md                # This file
```

---

## 🎨 Design Reference

Your **4×6 design sheet** (`assets/ashu_design_reference_sheet.png`) maps to 45 planned assets:

| Category | Delivered (6) | Pending (39) |
|----------|---------------|--------------|
| Portraits | neutral, happy, excited, curious, surprised, wink | laughing, playful, pout, annoyed, sad, proud, ... |
| Voice | — | listening, speaking, reacting |
| Floating | — | idle, peeking, sitting, moving, sleeping, happy, excited, annoyed, curious, bored, attention |
| Chat | — | idle, happy, annoyed |
| Expressions | — | excited, laughing, surprised, annoyed, sad, proud |

**Tools:**
- `scripts/extract_design_reference.py` — extracts 24 grid cells, verifies delivered assets, generates comparison image
- `docs/design/ASHU_DESIGN_REFERENCE.md` — full mapping table
- `docs/design/RIVE_EDITOR_GUIDE.md` — step-by-step to build `.riv` state machine from grid

---

## 🔧 Configuration

### Android (Settings Screen)
- Bridge URL (default: `http://10.0.2.2:8765` for emulator)
- Voice ON/OFF, Auto-speak, Reduced motion
- Proactive ON/OFF, Daily limit, Quiet hours
- Cloud fallback ON/OFF (off by default)
- Floating Ashu ON/OFF (requires overlay permission)
- Confirm risky actions ON/OFF

### Python Bridge (`serve.py` flags)
```bash
--host HOST           # Bind address (default: 127.0.0.1)
--port PORT           # Port (default: 8765)
--model-path PATH     # Path to GGUF model
--cloud               # Enable NIM API fallback (needs NIM_API_KEY)
--no-fallback         # Disable offline fallback
```

### Environment Variables
| Variable | Purpose |
|----------|---------|
| `NIM_API_KEY` | NVIDIA NIM API key for cloud fallback |
| `OPENAI_API_KEY` | Free GPT fallback (optional) |
| `ASHU_MODEL_PATH` | Default GGUF model path |

---

## 🧪 Testing

```bash
# Python tests (162 tests, 1 skipped)
cd tests && python -m pytest -v

# Android unit tests
cd android && ./gradlew testDebugUnitTest

# Lint
cd android && ./gradlew lintDebug
```

---

## 📦 Build APK for Distribution

```bash
cd android
./gradlew assembleRelease
# Output: app/build/outputs/apk/release/app-release-unsigned.apk
# Sign with your keystore:
apksigner sign --ks your.keystore --out ashu-signed.apk app-release-unsigned.apk
```

**Min SDK:** 26 (Android 8.0)  
**Target SDK:** 35 (Android 15)  
**Permissions:** Internet, Camera, Microphone, Notifications, Overlay, Foreground Service

---

## 🛡 Privacy & Security

- **Local-first:** All memory, personality state, activity log stored on device
- **No telemetry:** Zero analytics, crash reporting, or usage tracking
- **Explicit permissions:** Each permission requested individually with plain-language explanation
- **Confirmation gating:** Risky actions (camera, file write, app open) require user confirmation
- **Sanitised output:** Model responses parsed — never execute tools or bypass permissions
- **Full control:** Export all data (JSON), delete everything, revoke permissions anytime
- **Offline fallback:** Works without internet; cloud replies explicitly labeled

See `docs/PRIVACY.md` for full details.

---

## 🗺 Roadmap

| Version | Focus |
|---------|-------|
| **v0.9** (current) | Procedural overlay, design reference integration, proactive bubbles |
| **v1.0** | Rive avatar swap, Expo app, NIM + Gemma hybrid brain, notification listener |
| **v1.1** | Widget, Quick Settings tile, backup/restore, multi-device sync (local) |
| **v1.2** | Plugin system, custom tools, community asset packs |

---

## 🤝 Contributing

1. Fork → branch → PR
2. Run tests: `pytest tests/` + `./gradlew testDebugUnitTest`
3. Follow Kotlin/Compose conventions (see `android/app/src/main/java/com/ashu/app/`)
4. Python: type hints, `ruff` format, `mypy` strict

---

## 📄 License

MIT — see `LICENSE` (to be added). Character art assets have separate licensing — see `assets/ASHU_ASSET_MANIFEST.json`.

---

## 🙏 Acknowledgements

- **Character design:** Ashu 2D Character Asset Pack (reference sheet + delivered portraits)
- **Brain architecture:** Inspired by local-first AI patterns (llama.cpp, ONNX Runtime)
- **Animation:** Procedural Canvas techniques + Rive state machine design
- **Privacy model:** Local-first principles (no telemetry, explicit consent)

---

**Made with 💜 for Telugu speakers who want a companion, not a product.**