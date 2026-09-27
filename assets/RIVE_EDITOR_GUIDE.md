# Rive Editor Guide: Building Ashu's Animated Avatar

**Goal:** Create a `.riv` file with a state machine that drives Ashu's expressions, blinking, talking, floating, and emotions — ready to drop into both Android (Kotlin/Compose) and Expo (React Native).

**Reference:** Your 4×6 design sheet (1536×1024, 24 cells = 256×256 each) at `docs/design/ashu_design_reference_sheet.png`.

---

## Step 0: Setup

1. **Download Rive Editor** — https://rive.app/editor (free, runs in browser or desktop app)
2. **Create new file** — File → New → "Character" or blank artboard
3. **Artboard size** — 512×512 (gives room for floating movement)
4. **Import assets** — Drag your 4×6 sheet in, or export the 24 cells as individual PNGs (use `scripts/extract_design_reference.py` → `docs/design/reference_grid/grid_r*_c*.png`)

---

## Step 1: Rig the Character (Bones & Mesh)

### 1.1 Create the base hierarchy
```
Root (artboard)
├── Body (group)
│   ├── Head (bone)
│   │   ├── Face (mesh)
│   │   ├── LeftEye (bone)
│   │   │   ├── LeftEyelid (mesh)
│   │   │   └── LeftPupil (mesh)
│   │   ├── RightEye (bone)
│   │   │   ├── RightEyelid (mesh)
│   │   │   └── RightPupil (mesh)
│   │   ├── Mouth (bone)
│   │   │   ├── UpperLip (mesh)
│   │   │   ├── LowerLip (mesh)
│   │   │   └── Tongue (mesh)
│   │   ├── LeftEyebrow (mesh)
│   │   │   └── LeftEyebrowBone (bone)
│   │   ├── RightEyebrow (mesh)
│   │   │   └── RightEyebrowBone (bone)
│   │   └── Hair (group)
│   │       ├── Bangs (mesh)
│   │       ├── LeftStrand (mesh)
│   │       └── RightStrand (mesh)
│   ├── Torso (bone)
│   ├── LeftArm (bone)
│   ├── RightArm (bone)
│   └── FloatOffset (bone)  ← for procedural drift
```

### 1.2 Key rigging tips for your style
- **Head** = single bone at nose bridge, controls all face follow
- **Eyes** = separate bones so pupils can gaze independently
- **Eyelids** = meshes weighted to eyelid bones (0-100% close)
- **Mouth** = 3 meshes (upper, lower, tongue) weighted to jaw bone + blend shapes for shapes
- **Eyebrows** = simple 2-point meshes with bone at inner end
- **Hair** = 3 meshes with subtle secondary motion (spring constraint on FloatOffset)
- **FloatOffset** = dummy bone at root, animated by state machine for idle drift

### 1.3 Mesh deformation for expressions
For each expression, create a **Blend Shape** (Rive calls these "Shapes") on the Face mesh:
| Shape Name | Reference Grid Cell | Key Deformations |
|------------|---------------------|------------------|
| `neutral` | r0c0 | Base |
| `happy` | r0c2 | Cheeks up, mouth corners up, eyes squint |
| `excited` | r0c4 | Wide eyes, open mouth, raised brows |
| `surprised` | r1c2 | Brows max up, eyes max open, O-mouth |
| `annoyed` | r2c0 | Brows furrowed down, eyes half-lidded, flat mouth |
| `sad` | r3c4 | Brows inner up, corners down, eyes down |
| `sleepy` | r3c0 | Lids 80% closed, mouth slightly slack |
| `curious` | r1c0 | One brow up, head tilt, slight smile |
| `wink` | r3c2 | One eye closed, other normal, smirk |
| `playful` | r1c4 | Tongue out, squint, tilted |
| `concerned` | r2c3 | Brows inner up, mouth tight |
| `proud` | r2c5 | Chin up, slight smirk, eyes confident |

**How:** Select Face mesh → Inspector → Shapes → "Create Shape" → name it → move vertices to match reference cell.

---

## Step 2: Create Inputs (State Machine Parameters)

In the **Inputs** panel (left sidebar), add:

| Input Name | Type | Default | Description |
|------------|------|---------|-------------|
| `emotion` | Number | 0 | 0=neutral, 1=happy, 2=excited, 3=surprised, 4=annoyed, 5=sad, 6=sleepy, 7=curious, 8=wink, 9=playful, 10=concerned, 11=proud |
| `blink` | Trigger | — | Fires each natural blink |
| `speaking` | Boolean | false | True while TTS is playing |
| `speakVolume` | Number | 0 | 0..1 mouth openness from TTS volume |
| `listening` | Boolean | false | True while STT active |
| `floatX` | Number | 0 | -1..1 horizontal drift |
| `floatY` | Number | 0 | -1..1 vertical drift |
| `reaction` | Trigger | — | Fires on new message (pop) |

---

## Step 3: Build the State Machine

Open **Animations** tab → "New State Machine" → name it `AshuSM`.

### 3.1 Base Layer (always playing)
```
Entry → IdleBlend
```
- **IdleBlend** = Blend State 1D (input: `emotion`)
  - 0 → Neutral animation (breathing loop)
  - 1 → Happy animation (breathing + subtle bounce)
  - 2 → Excited animation (breathing + bounce + sparkle)
  - 3 → Surprised (held pose)
  - 4 → Annoyed (breathing + arm cross)
  - 5 → Sad (slow breathing, head down)
  - 6 → Sleepy (slow blink, head nod)
  - 7 → Curious (head tilt, look around)
  - 8 → Wink (held wink + smirk)
  - 9 → Playful (bounce, tongue)
  - 10 → Concerned (brow furrow, lean forward)
  - 11 → Proud (chest out, chin up)

Each sub-state = 4-8 second looping animation with breathing + idle movement.

### 3.2 Blink Layer (additive)
```
Entry → BlinkWait → BlinkClose → BlinkHold → BlinkOpen → BlinkWait
```
- **BlinkWait** → **BlinkClose**: Transition on `blink` trigger
- **BlinkClose** (100ms): Eyelid meshes 0→100%
- **BlinkHold** (50ms): Hold closed
- **BlinkOpen** (120ms): Eyelid meshes 100%→0%
- **BlinkOpen** → **BlinkWait**: Auto-transition

**Drive from code:** Kotlin/JS sends `blink` trigger every 3-8s (random).

### 3.3 Speaking Layer (additive, overrides mouth)
```
Entry → SpeakIdle → SpeakLoop
```
- **SpeakIdle** → **SpeakLoop**: Transition when `speaking` = true
- **SpeakLoop**: Mouth openness driven by `speakVolume` input (0..1)
  - UpperLip/LowerLip meshes blend between closed/open shapes
  - Tongue mesh appears when `speakVolume` > 0.5
- **SpeakLoop** → **SpeakIdle**: Transition when `speaking` = false

### 3.4 Listening Layer (additive)
```
Entry → ListenIdle → ListenPulse
```
- Subtle ring pulse animation around head when `listening` = true
- Driven by a looping animation that plays while boolean is true

### 3.5 Reaction Layer (one-shot, high priority)
```
Entry → ReactionPop → ReactionHold → ReactionSettle → Entry
```
- **Entry** → **ReactionPop**: On `reaction` trigger (scale 0.8→1.05, -10px Y)
- **ReactionPop** (150ms) → **ReactionHold** (200ms) → **ReactionSettle** (150ms) → **Entry**
- Overrides base layer briefly for "new message" feedback

### 3.6 Float Drift (procedural, driven by inputs)
- **FloatOffset** bone X driven by `floatX` (-1..1) × 20px
- **FloatOffset** bone Y driven by `floatY` (-1..1) × 15px
- Kotlin/JS sends Perlin noise values every frame (~30fps)

---

## Step 4: Create Animations (Timeline)

For each state in IdleBlend, create a **Timeline Animation**:

| Animation | Duration | Keyframes |
|-----------|----------|-----------|
| `neutral_idle` | 4s | Breathing (scale 1.0→1.02), subtle sway (-1°→1°) |
| `happy_idle` | 4s | Neutral + cheek bounce (0.5Hz), eye squint pulse |
| `excited_idle` | 3s | Happy + body bounce (1Hz), sparkle particles |
| `surprised_idle` | 2s | Held pose (no loop) |
| `annoyed_idle` | 4s | Neutral + arm cross hold, slow head shake |
| `sad_idle` | 5s | Slow breath, head down, occasional sigh |
| `sleepy_idle` | 6s | Very slow breath, head nod, long blinks |
| `curious_idle` | 4s | Head tilt cycle (-15°→15°), gaze follow |
| `wink_idle` | 3s | Held wink, subtle smirk pulse |
| `playful_idle` | 3s | Tongue flash (0.5Hz), body wiggle |
| `concerned_idle` | 4s | Brow furrow pulse, lean forward/back |
| `proud_idle` | 4s | Chest expand, chin lift, slow rotate |

**Tip:** Make all animations loop seamlessly. Use "Loop" toggle in timeline.

---

## Step 5: Export & Integration

### 5.1 Export
- File → Export → `.riv` (binary) → save as `ashu.riv`
- Also export `.json` for debugging if needed

### 5.2 Android (Kotlin) Integration
```kotlin
// In FloatingCompanionService or ChibiAshu
@Composable
fun RiveAshu(
    riveFile: RiveFile,
    emotion: Int,
    speaking: Boolean,
    speakVolume: Float,
    listening: Boolean,
    floatX: Float,
    floatY: Float,
    onBlink: () -> Unit, // called every 3-8s
    onReaction: () -> Unit, // called on new message
) {
    val controller = rememberRiveController(riveFile)
    val sm = controller.stateMachine("AshuSM")

    // Drive inputs
    LaunchedEffect(emotion) { sm.getInput<Number>("emotion")?.value = emotion }
    LaunchedEffect(speaking) { sm.getInput<Boolean>("speaking")?.value = speaking }
    LaunchedEffect(speakVolume) { sm.getInput<Number>("speakVolume")?.value = speakVolume }
    LaunchedEffect(listening) { sm.getInput<Boolean>("listening")?.value = listening }
    LaunchedEffect(floatX) { sm.getInput<Number>("floatX")?.value = floatX }
    LaunchedEffect(floatY) { sm.getInput<Number>("floatY")?.value = floatY }

    // Blink timer
    LaunchedEffect(Unit) {
        while (true) {
            delay((3000..8000).random())
            if (!speaking) sm.getInput<Trigger>("blink")?.fire()
        }
    }

    RiveRenderer(controller, modifier = Modifier.size(112.dp))
}
```

### 5.3 Expo (React Native) Integration
```tsx
// components/RiveAshu.tsx
import { Rive } from '@rive-app/react-canvas';

export function RiveAshu({
  emotion, speaking, speakVolume, listening, floatX, floatY, onReaction
}: Props) {
  const rive = useRive({ src: 'ashu.riv', stateMachines: 'AshuSM', autoPlay: true });
  const [inputs, setInputs] = useState({ emotion: 0, speaking: false, ... });

  useEffect(() => { setInputs(s => ({ ...s, emotion })); }, [emotion]);
  useEffect(() => { setInputs(s => ({ ...s, speaking, speakVolume })); }, [speaking, speakVolume]);
  // ... etc

  // Blink timer
  useEffect(() => {
    const id = setInterval(() => {
      if (!speaking) rive.stateMachineInputs.get('blink')?.fire();
    }, Math.random() * 5000 + 3000);
    return () => clearInterval(id);
  }, [speaking]);

  return <Rive.Canvas rive={rive} style={{ width: 112, height: 112 }} />;
}
```

---

## Step 6: Swap in Your App

When `.riv` is ready:
1. **Android:** Drop `ashu.riv` in `app/src/main/assets/` → replace `ProceduralAshu` with `RiveAshu` in `FloatingCompanion.kt` and `ChibiAshu.kt`
2. **Expo:** Drop `ashu.riv` in `assets/` → use `RiveAshu` component in chat screen

The procedural avatar (`ProceduralAshu.kt`) stays as fallback — zero asset dependency, works instantly.

---

## Quick Reference: Grid Cell → Expression Map

| Grid | Expression | Emotion Input |
|------|------------|---------------|
| r0c0 | Neutral | 0 |
| r0c2 | Happy | 1 |
| r0c4 | Excited | 2 |
| r1c2 | Surprised | 3 |
| r2c0 | Annoyed | 4 |
| r3c4 | Sad | 5 |
| r3c0 | Sleepy | 6 |
| r1c0 | Curious | 7 |
| r3c2 | Wink | 8 |
| r1c4 | Playful | 9 |
| r2c3 | Concerned | 10 |
| r2c5 | Proud | 11 |

---

## Files to Create
- `android/app/src/main/assets/ashu.riv` (Android)
- `expo-app/assets/ashu.riv` (Expo)
- `docs/design/rive_state_machine.md` (this guide)

---

**Next:** When you have the `.riv` file, I'll help you wire it into both platforms. The procedural avatar is already live in your overlay — test it now!