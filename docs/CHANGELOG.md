# Ashu v0.9 — new character, state-driven renderer

This release swaps in the new Ashu character design and replaces the old
"pick a still image for this mood string" avatar logic with a single,
documented state machine (`AshuCharacterState`) that both the Android app
and the web prototype now share, plus real event-driven expressions
(listening / thinking / reacting / speaking) instead of guesses.

Everything below was built **on top of** the existing v0.8.1 app — nothing
was rebuilt from scratch, and no existing chat, memory, voice, or
reduced-motion functionality was removed.

## Asset pack reality check (read this first)

`ASHU_ASSET_MANIFEST.json` plans **45** pieces of art across 27 chat-portrait
states. This delivery shipped **6**: `neutral`, `happy`, `excited`,
`curious`, `surprised`, `wink`. The other 39 are `pending_credits` in the
manifest itself — not missing by accident.

That shaped almost every decision below: the whole point of Part 2/12 was
to make sure the app looks intentional today, with only 6 stills, *and*
needs zero code changes when the other 39 arrive later (just fill in
`AshuCharacterState.DIRECT_ASSET`).

## Part 1 — Asset installation

- Installed the 6 delivered portraits into
  `android/app/src/main/res/drawable-nodpi/ashu_v2_<state>.png` — a new,
  distinct naming lane from the v0.5-era `ashu_emo_*` / `ashu_pose_*`
  assets, so nothing old was overwritten and the two "generations" of art
  are easy to tell apart in the resource browser.
- Installed web-optimized copies at `web/assets/ashu/portraits/ashu_v2_<state>.webp`.
- Old v0.5 assets (`ashu_emo_*`, `ashu_pose_*`) were **kept**, not deleted —
  they're still used for full-body gesture poses (wave, celebrate, thumbs
  up, …) that have no equivalent in the new face-only pack, and as the
  deliberate legacy leaves for SAD/SLEEPY (see Part 2).

## Part 2 — Character state system

New file: `android/app/src/main/java/com/ashu/app/AshuCharacterState.kt`.

- One enum, all 27 states from the brief.
- `assetFor(state)` is the single place that turns a state into a drawable.
  It **never** returns nothing — every state resolves via a documented,
  acyclic fallback chain down to one of the 6 shipped portraits, with two
  intentional exceptions:
  - `SAD` → the old `ashu_emo_sad` still, and
  - `SLEEPY` → the old `ashu_emo_sleepy` still,

  both because showing Ashu smiling while the user is sad felt worse than
  a brief art-style seam. Flagged here as the first two pieces of pending
  art worth prioritizing — once they land, deleting these two lines from
  `LEGACY_LEAF_ASSET` finishes the job.
- `fromMood(mood)` covers **every** value of `personality/emotion.py`'s
  `Emotion` enum (test-enforced — see Part 13).
- `fromAction(action)` covers the subset of `ChibiAshu`'s gesture actions
  that are really just a facial expression (wink, laugh, blush, thinking,
  sleep, listening, speaking) so those get the new art too; full-body pose
  actions (wave, celebrate, jump, …) intentionally fall through to the old
  pose art — see `ChibiAshu.kt`'s new `POSE_ACTIONS` set.
- `ChibiAshu.kt`'s `resolveAsset()` was rewritten around this; the old,
  now-fully-superseded `MOOD_ASSET` static lookup table was deleted rather
  than left as dead code.

## Part 3 — Brain → character state

`AshuCharacterState.fromMood()` is the mapping. It's test-enforced
(`tests/test_v0_9_character.py::test_every_brain_emotion_has_a_kotlin_mood_mapping`)
to cover every `Emotion` member so a future emotion added to the brain
can't silently go unmapped. No random mood churn was added — the mapping
is a pure function of whatever mood the brain already reports.

## Part 4 — Chat behavior tied to real events

- **Listening**: `ChatScreen`'s call to `ChibiAshu(...)` was missing
  `listening = listening` entirely — the parameter existed on both sides
  but was never wired, so the avatar never actually showed a listening
  face. Fixed.
- **Thinking**: `sendDraft()` now sets `animation = "thinking"` for the
  real span between sending the message and getting a reply, instead of
  only using `thinking` for the text-bubble typing dots.
- **Reacting → conversational expression**: unchanged wiring, kept.
- **Speaking**: unchanged — already driven by `AshuVoice`'s real
  `UtteranceProgressListener` callbacks (`onStart`/`onDone`/`onError`),
  not a timer.
- Web prototype: `S.thinking` existed and was read by the typing-indicator
  code, but nothing ever *set* it, so the indicator was dead code.
  `sendDraft()` now sets/clears it around the real `await bridgeChat(...)`
  call and pushes an explicit `updateChibi()` so the avatar reflects it.
  `toggleMic()` now also calls `updateChibi()` so the listening face
  actually shows during speech recognition (previously the mic button
  changed state but the avatar didn't).

## Part 5 — Speaking animation

- Android: while `speaking` is true, `ChibiAshu` now alternates between the
  SPEAKING asset and a second compatible frame (HAPPY) every 420ms, adds a
  small head-wobble (`rotationZ`) and a slightly bigger breathing pulse on
  the alternating frame, and stops the instant `speaking` flips false —
  driven by the same state, no separate timer pretending audio is still
  playing. All of it is skipped under Reduced Motion.
- Web: unchanged CSS pulse (`speakingPulse` keyframe), still driven by the
  real `SpeechSynthesisUtterance.onstart/onend`.

## Part 6 — Idle life

Mostly already present in v0.8.1 (breathing scale, sway, periodic
look-left/look-right) and left as-is — it already satisfied the brief's
"mostly still → tiny movement → still again" cadence and already disables
under Reduced Motion. **Not implemented**: a literal eye blink. The asset
pack is stills, not a rig, and none of the 6 delivered portraits include a
closed-eye variant — faking a blink by flickering opacity would look like
a glitch, not a blink, so it was left out rather than shipped badly. Worth
revisiting once (or if) a blink frame is in the asset pack.

## Part 7 — Reaction animation

Already existed; changed to **randomize** the hold duration to 300–600ms
(previously a fixed 480ms) so replies don't all animate identically, per
the brief. Mirrored in both Android (`(300..600).random()`) and web
(`300+Math.floor(Math.random()*300)`); both are test-enforced.

## Part 8 — Floating companion (infrastructure)

New file: `android/app/src/main/java/com/ashu/app/FloatingCompanion.kt`,
its own `Service`, not hacked into `ChatScreen`.

Implemented:
- `FloatingCompanionPermission` — `SYSTEM_ALERT_WINDOW` is **only** ever
  requested by sending the user to Android's own "Draw over other apps"
  settings screen (`ACTION_MANAGE_OVERLAY_PERMISSION`); there is no
  silent/runtime-dialog grant path anywhere in this code.
- `FloatingCompanionService` — a foreground `Service` (required on modern
  Android for a `WindowManager` overlay to survive) hosting a
  `ComposeView` bubble: draggable, snaps to the nearest left/right edge on
  release, tap-to-open launches `MainActivity`.
- Settings screen: new "Floating Ashu" switch, **off by default**,
  persisted in `ashu_prefs`. Turning it on requests the permission if not
  already granted and shows an inline note; a `LifecycleEventObserver`
  catches the grant on `ON_RESUME` (returning from the settings screen)
  and starts the service then, rather than requiring the user to flip the
  switch twice.
- `AndroidManifest.xml`: `SYSTEM_ALERT_WINDOW`, `FOREGROUND_SERVICE`,
  `FOREGROUND_SERVICE_SPECIAL_USE` permissions and the service
  declaration, with a `PROPERTY_SPECIAL_USE_FGS_SUBTYPE` explaining why.
- `build.gradle.kts`: added `lifecycle-runtime-ktx`, `lifecycle-viewmodel-ktx`,
  `savedstate-ktx` — needed for a `Service` (which isn't itself a
  `LifecycleOwner`/`ViewModelStoreOwner`/`SavedStateRegistryOwner`) to host
  a `ComposeView`.

**Not implemented** (flagged in the file's own doc comment, not silently
dropped): a "she noticed something" attention trigger tied to the brain's
boredom/proactive system, and a speech-bubble view for proactive
messages. `FloatingCompanionService.setState()` is the extension point —
it's a public method that already exists and already updates the bubble's
expression; it just isn't called by the proactive engine yet, because that
engine doesn't currently expose a "the floating companion should say X"
hook to call it from.

**Could not verify**: this is the single riskiest file in this release —
it wasn't compiled (see "What could not be verified" below). It's a
well-trodden pattern (Compose-in-a-Service overlay) but "well-trodden"
isn't "tested here."

## Part 9 — Chat UI overlap

Already fixed in v0.8 (dedicated avatar shelf, separate from the message
`LazyColumn`, input field, and send button). Verified still intact;
nothing in this release touches that layout.

## Part 10 — Web prototype mirror

`web/ashu_prototype.html`:
- Added the 6 new portraits as inline base64 `data:` URIs in `ASHU_ASSETS`
  (kept self-contained — no new external requests).
- Ported `AshuCharacterState` as `ashuAssetForState()` /
  `ashuStateFromMood()` / `ashuEffectiveState()` — same direct-asset table,
  same fallback chain, same two legacy-leaf exceptions. Cross-checked
  against the Kotlin file by a test that parses both and asserts the
  "has real art" sets match exactly.
- `updateChibi()` and the hero avatar's initial render now go through
  `ashuCurrentAsset()` instead of a hardcoded `'ashu_emo_'+mood` string.
- Wired real THINKING/LISTENING/REACTING/SPEAKING precedence in
  `ashuEffectiveState()`, matching `ChatScreen`'s Android ordering.
- Floating companion **demo**: new "Floating Ashu demo" toggle in
  Settings (`S.floatingDemo`, default `false`) creates a draggable,
  edge-snapping, tap-to-open bubble (`setFloatingCompanionDemo()`). This
  models the same interaction as the Android overlay; it's explicitly a
  demo, not a real always-on-top window outside the browser tab, since
  browsers don't have an equivalent of `WindowManager`.
- Reduced motion: unchanged, already applied via the `.motion-off` class;
  the floating bubble also respects it (no snap transition when on).
- Fixed a real, pre-existing bug while doing this: `S.thinking` was read
  by the typing-indicator code but nothing ever set it, so the indicator
  never showed. Now set/cleared for real around `sendDraft()`'s network
  call.

## Part 11 — Image optimization

The 6 source PNGs (2048×2048-ish, ~1.85–2.07 MB each) were:
- cropped to their opaque bounding box,
- capped at 1024px longest side for Android (still crisp for a chat/hero
  avatar) and re-saved as optimized PNG — **~900KB each, down from
  ~1.9MB** (roughly 2×, transparency preserved, `RGBA` mode verified by
  test),
- separately capped at 512px and re-encoded as WebP (quality 88) for web —
  **~48–55KB each, down from ~1.9MB (≈35–39×)**, since these travel over
  HTTP on every page load and the page is otherwise self-contained.

No transparent PNG was converted to JPEG.

## Part 12 — Fallbacks

Covered above (Part 2) and enforced by `tests/test_v0_9_character.py`:
every one of the 27 states resolves to a real, existing asset key in both
renderers, the fallback graph is acyclic, and the four fallbacks the brief
specifies explicitly (`TEASING→PLAYFUL`, `CONCERNED→CARING`,
`BORED→NEUTRAL`, `ATTENTION→CURIOUS`) are asserted to hold.

## Part 13 — Tests

New file: `tests/test_v0_9_character.py`, 19 tests, all passing. Covers:
asset installation and sizes (Part 1/11), transparency preservation,
mood→state coverage against the real `Emotion` enum (Part 3), the web
fallback chain **executed for real via `node`** (not reimplemented in
Python — Part 12), Kotlin/web agreement on which states have real art,
acyclicity of the Kotlin fallback map (static analysis), floating
companion off-by-default + permission-flow markers (Part 8), the v0.8
avatar-shelf regression guard (Part 9), reaction-duration randomization in
both renderers (Part 7), and — found and fixed in the process —
`AndroidManifest.xml` well-formedness (see below).

**Not written, and why**: Android instrumented/unit tests
(`androidTest`/`test` source sets) for `AshuCharacterState.kt` and
`FloatingCompanion.kt` directly in Kotlin. This sandbox has no Android
SDK, no `kotlinc`, and no network route to Google's/Maven's repos (the
egress allowlist covers pypi/npm/github, not `dl.google.com` or
`repo.maven.apache.org`), so nothing Kotlin can be compiled or run here.
The equivalent logic is instead exercised from Python by parsing the
Kotlin source and cross-checking it against the (real, `node`-executed)
web implementation — real coverage of the *logic*, not a substitute for
`./gradlew test`.

## Part 14 — Verification

- `python -m pytest tests -q` → **162 passed, 1 failed** (full suite,
  including all pre-existing v0.3–v0.8 tests plus the new 19).
  - The one failure, `test_v0_4_proactive.py::test_engine_maybe_proactive_returns_message_object`,
    is **pre-existing and unrelated** to this release — it never touches
    any file changed here. It fails because `PersonalityEngine`'s
    proactive-message gate checks real wall-clock quiet hours
    (`ProactiveEngine.in_dnd`) and the container's current time happens to
    fall inside the default DND window, regardless of
    `proactive_probability = 1.0`. Reproduced 3× in a row (not flaky-random),
    confirmed by checking `personality/proactive.py`, a file this release
    never edited. Left as-is rather than "fixed" to stay in scope, since
    changing quiet-hours logic wasn't part of this brief and could have
    side effects I haven't reasoned through. Flagging it here rather than
    silently working around it.
- Web prototype: the inline `<script>` block round-trips through
  `node --check` (syntax) and through a full `node` execution harness (with
  minimal `document`/`window`/`localStorage`/`fetch` stubs) that calls the
  real `ashuAssetForState`/`ashuStateFromMood`/`ASHU_ASSETS` functions —
  this is real code execution, not a re-implementation. **Not verified**:
  actually opening the page in a browser (no browser/display in this
  sandbox) — no visual regression check, no manual click-through of the
  chat/settings/floating-demo flow.
- Android: **could not run `./gradlew build` or any Gradle task.** This
  sandbox has no Android SDK, no `kotlinc`, and the network egress
  allowlist does not include `dl.google.com` / Google's Maven repo /
  `repo.maven.apache.org`, which the Android Gradle Plugin and AndroidX
  dependencies require. Exact command that would need to run:
  `cd android && ./gradlew assembleDebug` (or `testDebugUnitTest`) — not
  attempted with a fake pass; genuinely not run. What *was* done instead,
  as a partial substitute: every edited/added Kotlin file was checked for
  balanced braces/parens, the new dependencies were checked against known
  real Maven coordinates (`androidx.lifecycle:lifecycle-runtime-ktx:2.8.7`,
  `androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.7`,
  `androidx.savedstate:savedstate-ktx:1.2.1`), and `AndroidManifest.xml`
  is now verified well-formed XML (see below — this caught a real bug).
  None of this is a substitute for an actual compile; `FloatingCompanion.kt`
  in particular (Compose hosted inside a bare `Service`) is exactly the
  kind of file that looks right and fails to compile over an import or API
  mismatch, and that class of bug would only surface in a real build.
- Found and fixed during verification: the Part 8 manifest edit put a
  literal `--` inside an XML comment ("v0.9 Part 8 -- floating
  companion..."), which is illegal in XML and broke `AndroidManifest.xml`
  parsing entirely. Caught by writing an XML well-formedness check
  (now a permanent regression test), not by a build (which wasn't
  available) — a good example of why "no build available" doesn't mean
  "no verification happened."

## Part 15 — This file

## Summary of what's genuinely new vs. what's pending

**Shipped and verified (to the extent this sandbox allows):** asset
install + optimization, the state/fallback system in both renderers with
19 passing tests, real event-driven listening/thinking/reacting/speaking
in both Android and web, randomized reaction timing, floating companion
infrastructure (service, permission flow, settings toggle) on Android plus
a working interactive demo on web, and a `AndroidManifest.xml` bug this
process introduced and then caught.

**Explicitly not done, not silently skipped:**
1. Blink / eye-flutter idle animation — no closed-eye asset exists yet.
2. Floating companion "attention" trigger wired to the brain's actual
   boredom/proactive signal, and its speech-bubble UI — infra exists
   (`setState()`), the brain-side hook to call it doesn't yet.
3. An actual Gradle/Android build of this app — no SDK/toolchain/network
   route available in this environment. **This is the biggest open risk**:
   `FloatingCompanion.kt` and the `AshuCharacterState.kt` integration into
   `ChibiAshu.kt` have not been compiled, only statically sanity-checked.
   Next step before shipping: run `cd android && ./gradlew assembleDebug`
   somewhere with the Android SDK and fix whatever it reports.
4. In-browser manual QA of the web prototype (no display in this
   sandbox) — only `node`-executed logic checks were possible.
5. 39 of the 45 planned character-expression assets are still
   `pending_credits` in the manifest; every state that lacks one uses the
   documented fallback chain today.
