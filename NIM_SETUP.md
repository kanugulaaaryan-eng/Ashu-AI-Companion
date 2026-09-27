# NVIDIA NIM Setup for Ashu AI Companion

This guide shows how to use your NVIDIA NIM API key with Ashu for a free, high-quality cloud brain.

---

## Your API Key

```
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
```

**Already configured in `serve.py`** — just run with `--nim` flag.

---

## Quick Start

```bash
cd "C:/Users/AARYAN/Downloads/Ashu AI companion"

# Start bridge with NIM cloud
python serve.py --nim --host 0.0.0.0 --port 8765
```

**Output:**
```
[NIM] NVIDIA NIM configured: nvidia/nemotron-3-ultra-550b-a55b
[Ashu] Bridge starting...
   Host: 0.0.0.0:8765
   DB: ashu_memory.db
   Local model: Not installed
   Cloud: nim / nvidia/nemotron-3-ultra-550b-a55b [OK]

[Endpoints]
   GET  http://0.0.0.0:8765/v1/health
   POST http://0.0.0.0:8765/v1/chat
   GET  http://0.0.0.0:8765/v1/memory
   POST http://0.0.0.0:8765/v1/setup

[Android] Set bridge URL to http://<YOUR_LAN_IP>:8765
[Web] Open web/ashu_prototype.html and connect to bridge
```

---

## Model Used

**`nvidia/nemotron-3-ultra-550b-a55b`** — Nemotron 3 Ultra (550B params, free tier on NIM)

- High quality, multilingual
- Works well with Telugu + English
- Fast response times (~1-2s)

---

## Android App Setup

1. **Build APK:**
   ```bash
   cd android && ./gradlew assembleDebug
   ```

2. **Install on phone** → Open Ashu → Complete onboarding

3. **Settings → Bridge URL** → Enter your PC's LAN IP:
   ```
   http://192.168.1.xxx:8765
   ```
   (Run `ipconfig` on Windows to find your LAN IP)

4. **Settings → Floating Ashu ON** → Grant "Display over other apps"

---

## Web PWA (No Install)

```bash
# Serve web PWA
cd web && python -m http.server 8080
# Open http://localhost:8080/ashu_prototype.html
```

- Click "Connect to Bridge" → enter `http://<PC_IP>:8765`
- "Add to Home Screen" → installs as PWA
- Works offline (Service Worker)

---

## API Testing

```bash
# Health check
curl http://<PC_IP>:8765/v1/health

# Chat
curl -X POST http://<PC_IP>:8765/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hey Ashu, em chestunav?"}'

# Memory
curl http://<PC_IP>:8765/v1/memory/all
```

---

## Hybrid Mode (Local + Cloud)

If you have a local GGUF model, use both:

```bash
python serve.py --nim --model-path ~/models/qwen3-4b-q4.gguf
```

Priority: Local model → NIM cloud → Offline fallback

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Module not found: brain" | Run from project root: `cd "C:/Users/AARYAN/Downloads/Ashu AI companion"` |
| Port 8765 in use | Change port: `--port 8766` |
| Cloud 404 errors | Model retired — update `NIM_MODEL` in `serve.py` |
| Android can't connect | Check Windows Firewall → Allow port 8765 |
| Telugu not working | NIM model may need Telugu fine-tuning |

---

## Free Tier Limits

NVIDIA NIM free tier:
- **Rate limits:** ~60 req/min (varies)
- **Models:** Rotating selection (some retire)
- **No cost** for personal use

**Check available models:**
```bash
curl -H "Authorization: Bearer $NIM_API_KEY" https://integrate.api.nvidia.com/v1/models
```

---

## Switching Models

Edit `serve.py`:
```python
NIM_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"  # Current working
# Or via CLI:
python serve.py --nim --nim-model nvidia/nemotron-3-ultra-550b-a55b
```

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  Android App    │────▶│  Python Bridge   │────▶│  NVIDIA NIM Cloud  │
│  (Kotlin/Compose)│     │  (serve.py)      │     │  Nemotron 3 Ultra  │
│  Floating Overlay│     │  FastAPI + SQLite │     │  Free Tier         │
└─────────────────┘     └──────────────────┘     └────────────────────┘
         ▲                       ▲
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│  Web PWA        │     │  Local GGUF      │
│  (Offline OK)   │     │  (Optional)      │
└─────────────────┘     └──────────────────┘
```

---

## Next Steps

1. **Test on phone** — Install APK, enable Floating Ashu
2. **Build Rive avatar** — Follow `assets/RIVE_EDITOR_GUIDE.md`
3. **Wire overlay intents** — Python bridge → `FloatingCompanionService` intents
4. **Expo app** — Cross-platform chat UI

---

**Made with 💜 for Telugu speakers who want a companion, not a product.**