# Ashu web prototype (v0.6)

A single self-contained file: `ashu_prototype.html`. No server, no build
step, no dependencies. Open it in any modern browser.

## What you can test immediately

- **10-step onboarding** — name, capabilities, language, voice, cloud,
  proactive limits, permissions, model, test-chat, done.
- **Chat with Ashu** — Telugu-first replies from a faithful JavaScript port of
  her Python rules: greetings by relationship stage, mood inference, caring /
  teasing / celebration / boredom lines, jokes, time & date.
- **Memory** — say *"remember that I like biryani"*, *"what do you remember
  about me"*, *"forget that"*, or *"delete everything you know about me"*
  (which asks you to confirm first). Auto-memory captures "I like…", "I'm
  working on…", "X is my friend". Add / pin / delete / search in the Memory
  screen. Everything persists in `localStorage`.
- **Chibi character** — the 21 real character-art PNGs, chosen per
  `(mood, action)` exactly like `ChibiAshu.kt`, with breathing / sway /
  bounce / spin / hide animations that respect Reduced-motion.
- **Voice** — TTS via the Web Speech API (picks a `te-IN` voice when
  available) and STT via `webkitSpeechRecognition` when the browser supports
  it, with an honest error if it does not.
- **Privacy** — export all data as JSON, or delete everything with a
  confirm-first flow.
- **Honest provenance** — every reply shows whether it came from the rules
  brain, a local model, the cloud, or the offline fallback.

## Optional: connect the real Python brain

```bash
cd <repo>
pip install pytest                # only needed for the test suite
python serve.py --host 0.0.0.0 --port 8765            # rules/offline brain
python serve.py --cloud                               # + Gemini cloud brain
```

Then either:

- open `http://localhost:8765/` directly (the bridge serves this same page), or
- open the standalone file and set **Settings → Live bridge URL** to
  `http://localhost:8765`.

Connecting the bridge unlocks the **real** Python agent: SQLite memory,
personality state, proactive messages, confirmations and device tools. The
chat chips switch from *offline companion* to *live bridge*, and replies show
their real `origin`.

For a physical phone on the same Wi-Fi, use `http://<your-LAN-IP>:8765`.

## Notes

- Cloud fallback is **off by default** and clearly labelled when used. It
  never includes memories unless you separately allow it.
- Ashu is not flirty by design, and never claims a local model is running
  when it isn't.
