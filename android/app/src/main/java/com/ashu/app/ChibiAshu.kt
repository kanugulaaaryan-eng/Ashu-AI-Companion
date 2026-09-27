package com.ashu.app

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay

/**
 * Ashu's chibi renderer (v0.5).
 *
 * v0.4 drew Ashu procedurally with Canvas primitives. v0.5 replaces that with
 * the real, hand-designed character art (model C "Warm Elegant" -- see
 * /android/app/src/main/res/drawable-nodpi/ashu_*.png, sourced from the
 * ashu-character-assets pack). This is a full swap, not a hybrid: nothing in
 * this file draws Ashu with Canvas anymore.
 *
 * Trade-off worth knowing: the art is flat stills (12 face expressions + 8
 * full-body poses + 1 default portrait), not a rig or a sprite sheet -- the
 * asset pack's own manifest says so explicitly. So there is no literal eye
 * blink or mouth movement on a still image. What v0.5 does instead:
 *   * picks the single best-matching still for the current (mood, action)
 *     pair (see ACTION_ASSET below and AshuCharacterState.kt's mood/action mapping),
 *   * animates that still as a whole -- gentle breathing scale, idle sway,
 *     a bounce/jump/spin offset for celebratory actions, a hide-to-the-edge
 *     shift for "hide"/"shy_hide" -- using the same Compose transition
 *     infrastructure v0.4 used for its procedural bob/pulse values,
 *   * still fully disables all of that under reducedMotion.
 *
 * `hairstyle` and `outfitTop` are kept as parameters for source
 * compatibility with existing callers (AshuApp.kt's onboarding lets people
 * pick both), but the shipped art is a single fixed design, so -- unlike
 * v0.4's procedural renderer -- they are not visually applied here. If
 * hairstyle/outfit variety matters going forward, it needs either more art
 * variants from the same artist/pipeline or a return to procedural
 * rendering for those axes.
 *
 * The action-selection state machine below (ASHU_ACTIONS, ActionSpec,
 * ACTION_SPECS, AshuAnimationController) is unchanged from v0.4 -- the Python
 * brain still picks the action name (personality/animation.py) and this
 * renderer still just plays whatever it's told, only the drawing changed.
 */

/** The reusable action library -- names are shared with the Python brain. */
val ASHU_ACTIONS: Set<String> = setOf(
    "peek", "hide", "wave", "nod", "shake_head", "thumbs_up", "thumbs_down",
    "salute", "shrug", "cross_arms", "facepalm", "blush", "wink", "laugh",
    "giggle", "yawn", "stretch", "sleep", "wake", "look_left", "look_right",
    "look_at_user", "jump", "bounce", "spin", "shy_hide", "annoyed",
    "thinking", "celebrate", "listening", "speaking", "waiting",
)

/** Per-action tuning: duration ms, priority, interruptible. */
data class ActionSpec(val durationMs: Int, val priority: Int, val interruptible: Boolean)

val ACTION_SPECS: Map<String, ActionSpec> = mapOf(
    "peek" to ActionSpec(1200, 1, true),
    "hide" to ActionSpec(800, 1, true),
    "wave" to ActionSpec(1000, 2, true),
    "nod" to ActionSpec(600, 1, true),
    "shake_head" to ActionSpec(800, 2, true),
    "thumbs_up" to ActionSpec(1000, 3, true),
    "thumbs_down" to ActionSpec(1000, 3, true),
    "salute" to ActionSpec(1000, 2, true),
    "shrug" to ActionSpec(900, 1, true),
    "cross_arms" to ActionSpec(1200, 3, false),
    "facepalm" to ActionSpec(1000, 3, false),
    "blush" to ActionSpec(1000, 2, true),
    "wink" to ActionSpec(600, 2, true),
    "laugh" to ActionSpec(1400, 3, false),
    "giggle" to ActionSpec(1000, 2, true),
    "yawn" to ActionSpec(1400, 1, true),
    "stretch" to ActionSpec(1600, 1, true),
    "sleep" to ActionSpec(2000, 4, false),
    "wake" to ActionSpec(1400, 4, false),
    "look_left" to ActionSpec(700, 1, true),
    "look_right" to ActionSpec(700, 1, true),
    "look_at_user" to ActionSpec(800, 1, true),
    "jump" to ActionSpec(800, 3, false),
    "bounce" to ActionSpec(1000, 2, true),
    "spin" to ActionSpec(1200, 3, false),
    "shy_hide" to ActionSpec(1200, 2, true),
    "annoyed" to ActionSpec(1000, 2, true),
    "thinking" to ActionSpec(1000, 1, true),
    "celebrate" to ActionSpec(1600, 4, false),
    "listening" to ActionSpec(1200, 2, true),
    "speaking" to ActionSpec(1200, 2, true),
    "waiting" to ActionSpec(1200, 1, true),
)

/**
 * Priority + interruptibility + one-shot state machine.
 *
 * A higher-priority action can interrupt a lower-priority one; an
 * uninterruptible action (sleep, celebrate, facepalm) blocks lower-priority
 * actions until it finishes. When no one-shot is active the renderer falls
 * back to the idle animation.
 */
class AshuAnimationController {
    var currentAction: String = "idle"
        private set
    var isOneShot: Boolean = false
        private set

    fun play(action: String): Boolean {
        if (action !in ASHU_ACTIONS) return false
        val spec = ACTION_SPECS[action] ?: return false
        val currentSpec = ACTION_SPECS[currentAction]
        if (isOneShot && currentSpec != null && !currentSpec.interruptible && currentSpec.priority > spec.priority) {
            return false // uninterruptible action in progress
        }
        currentAction = action
        isOneShot = true
        return true
    }

    fun idle() {
        currentAction = "idle"
        isOneShot = false
    }

    fun durationFor(action: String): Int = ACTION_SPECS[action]?.durationMs ?: 1000
}

// ---------------------------------------------------------------------------
// Art lookup -- every ASHU_ACTIONS entry resolves to a real drawable.
// ---------------------------------------------------------------------------
//
// Source of truth for the "documented" half of this table is
// ashu-character-assets/manifest.json's expression_to_action_map and
// pose_to_action_map (reversed here). Where the manifest maps one
// expression/pose to *two* actions and both actions need a home in this
// 1-action-to-1-asset table, the pose (full body, more dynamic) wins over
// the expression for the shared action.
//
// The remaining actions (peek, hide, shake_head, thumbs_down, salute, shrug,
// facepalm, look_right, spin, listening, speaking, waiting) have no asset in
// the pack at all -- these are this file's own nearest-fit choices, not
// something the manifest specifies. They're called out here so a future
// pass can replace them with purpose-drawn art instead of a stand-in.
private val ACTION_ASSET: Map<String, Int> = mapOf(
    // -- documented in manifest.json ----------------------------------
    "idle" to R.drawable.ashu_pose_idle,
    "wave" to R.drawable.ashu_pose_wave,
    "thumbs_up" to R.drawable.ashu_pose_thumbs_up,
    "cross_arms" to R.drawable.ashu_pose_arms_crossed,
    "thinking" to R.drawable.ashu_pose_thinking,
    "celebrate" to R.drawable.ashu_pose_celebrate,
    "jump" to R.drawable.ashu_pose_celebrate,       // manifest: celebrate -> celebrate/jump
    "stretch" to R.drawable.ashu_pose_stretch,
    "wake" to R.drawable.ashu_pose_stretch,          // manifest: stretch -> stretch/wake
    "look_at_user" to R.drawable.ashu_emo_calm,      // manifest: calm -> idle/look_at_user
    "nod" to R.drawable.ashu_emo_happy,               // manifest: happy -> nod/bounce
    "bounce" to R.drawable.ashu_emo_happy,
    "laugh" to R.drawable.ashu_emo_laughing,          // manifest: laughing -> laugh/giggle
    "giggle" to R.drawable.ashu_emo_laughing,
    "blush" to R.drawable.ashu_emo_shy,               // manifest: shy -> blush/shy_hide
    "shy_hide" to R.drawable.ashu_emo_shy,
    "wink" to R.drawable.ashu_emo_wink,
    "annoyed" to R.drawable.ashu_emo_annoyed,         // manifest: annoyed -> annoyed/cross_arms
    "look_left" to R.drawable.ashu_emo_sad,           // manifest: sad -> look_left
    "yawn" to R.drawable.ashu_emo_sleepy,             // manifest: sleepy -> yawn/sleep
    "sleep" to R.drawable.ashu_emo_sleepy,
    // -- not in the manifest: nearest-fit stand-ins --------------------
    "peek" to R.drawable.ashu_emo_curious,
    "hide" to R.drawable.ashu_emo_shy,
    "shake_head" to R.drawable.ashu_emo_annoyed,
    "thumbs_down" to R.drawable.ashu_emo_annoyed,
    "salute" to R.drawable.ashu_pose_hands_on_hips,
    "shrug" to R.drawable.ashu_emo_curious,
    "facepalm" to R.drawable.ashu_emo_annoyed,
    "look_right" to R.drawable.ashu_emo_curious,
    "spin" to R.drawable.ashu_pose_celebrate,
    "listening" to R.drawable.ashu_emo_curious,
    "speaking" to R.drawable.ashu_emo_happy,
    "waiting" to R.drawable.ashu_emo_calm,
)

// v0.9: full-body gesture actions that have a real *pose* drawable (arms,
// stance, jumping, etc.) keep using that pose art -- there's no substitute
// for a full-body drawing in the face-only v0.9 pack. Everything else that
// used to fall back to a face/expression asset now routes through
// AshuCharacterState instead, so it benefits from the new art + fallback
// chain (see AshuCharacterState.kt) rather than a flat, static lookup
// table.
private val POSE_ACTIONS: Set<String> = setOf(
    "wave", "thumbs_up", "thumbs_down", "cross_arms", "celebrate", "jump",
    "stretch", "wake", "salute", "nod", "bounce", "shrug", "facepalm",
    "spin", "hide", "shy_hide", "peek",
)

private fun resolveAsset(mood: String, action: String): Int {
    val moodFirst = setOf("", "idle", "look_at_user", "waiting", "listening", "speaking")
    if (action in moodFirst) {
        // "listening"/"speaking" have dedicated v0.9 states; everything
        // else in this bucket reflects Ashu's current mood.
        val state = AshuCharacterState.fromAction(action) ?: AshuCharacterState.fromMood(mood)
        return AshuCharacterState.assetFor(state)
    }
    if (action in POSE_ACTIONS) {
        ACTION_ASSET[action]?.let { return it }
    }
    if (action.isNotBlank()) {
        AshuCharacterState.fromAction(action)?.let { return AshuCharacterState.assetFor(it) }
        ACTION_ASSET[action]?.let { return it } // remaining stand-ins (look_left/right, etc.)
    }
    return AshuCharacterState.assetFor(AshuCharacterState.fromMood(mood))
}

@Composable
fun ChibiAshu(
    mood: String,
    modifier: Modifier = Modifier.size(112.dp),
    hairstyle: String = "half_up",
    animationAction: String = "",
    outfitTop: String = "casual_top",
    reducedMotion: Boolean = false,
    listening: Boolean = false,
    speaking: Boolean = false,
    waiting: Boolean = false,
    reacting: Boolean = false,
    onTap: (() -> Unit)? = null,
) {
    // hairstyle/outfitTop are accepted for source compatibility with existing
    // callers but are not visually applied -- see the file header comment.

    // --- whole-image motion (disabled entirely under reduced-motion) ------
    val transition = rememberInfiniteTransition(label = "ashu_idle")
    val breathScale by transition.animateFloat(
        initialValue = 1f,
        targetValue = if (reducedMotion) 1f else 1.035f,
        animationSpec = infiniteRepeatable(tween(1300, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "breathe",
    )
    val sway by transition.animateFloat(
        initialValue = -1.5f,
        targetValue = if (reducedMotion) -1.5f else 1.5f,
        animationSpec = infiniteRepeatable(tween(1800, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "sway",
    )
    val gesturePulse by transition.animateFloat(
        initialValue = 0f,
        targetValue = if (reducedMotion) 0f else 1f,
        animationSpec = infiniteRepeatable(tween(600, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "gesture",
    )

    // --- derived, behaviour-driven state -----------------------------------
    var action by remember { mutableStateOf(animationAction) }
    var lookAround by remember { mutableStateOf("") }
    LaunchedEffect(animationAction) { action = animationAction }
    LaunchedEffect(action, mood, listening, speaking, waiting) {
        if (listening) action = "listening"
        else if (speaking) action = "speaking"
        else if (waiting) action = "waiting"
    }
    LaunchedEffect(reducedMotion) {
        if (reducedMotion) { lookAround = ""; return@LaunchedEffect }
        while (true) {
            delay(9000)
            lookAround = if (lookAround == "look_left") "look_right" else "look_left"
            delay(1200)
            lookAround = ""
        }
    }

    val effective = when {
        action.isNotBlank() -> action
        lookAround.isNotBlank() -> lookAround
        else -> "idle"
    }

    // v0.9 Part 7: reaction beat. A brand-new message flashes the REACTING
    // expression for a short, slightly-randomized window (300-600ms, per
    // spec) before settling into the normal mood/action asset, so replies
    // don't all look like the exact same transition.
    var reactionHoldMs by remember { mutableStateOf(420) }
    var showReactionFace by remember { mutableStateOf(false) }
    LaunchedEffect(reacting) {
        if (reducedMotion) { showReactionFace = false; return@LaunchedEffect }
        if (reacting) {
            reactionHoldMs = (300..600).random()
            showReactionFace = true
            delay(reactionHoldMs.toLong())
            showReactionFace = false
        } else {
            showReactionFace = false
        }
    }

    // v0.9 Part 5: while TTS is actually speaking, alternate between the
    // SPEAKING asset and a second compatible frame (HAPPY) so the portrait
    // isn't a frozen still for the whole utterance. Stops the moment
    // `speaking` goes false (driven by the real TTS callback upstream, not
    // a timer here).
    var speakFrameAlt by remember { mutableStateOf(false) }
    LaunchedEffect(speaking, reducedMotion) {
        if (!speaking || reducedMotion) { speakFrameAlt = false; return@LaunchedEffect }
        while (speaking) {
            delay(420)
            speakFrameAlt = !speakFrameAlt
        }
        speakFrameAlt = false
    }
    val headWobbleDeg = if (!reducedMotion && speaking) {
        (if (speakFrameAlt) 1.6f else -1.6f)
    } else 0f

    val assetId = when {
        showReactionFace -> AshuCharacterState.assetFor(AshuCharacterState.REACTING)
        speaking && speakFrameAlt -> AshuCharacterState.assetFor(AshuCharacterState.HAPPY)
        else -> resolveAsset(mood, effective)
    }

    val jumpOffset = if (!reducedMotion && effective in setOf("jump", "bounce", "celebrate", "spin")) {
        -gesturePulse * 10f
    } else 0f
    val spinDeg = if (!reducedMotion && effective == "spin") gesturePulse * 360f else 0f
    val hideShiftPx = if (!reducedMotion && (effective == "hide" || effective == "shy_hide")) 60f else 0f
    val swayDeg = if (reducedMotion) 0f else sway
    val speakPulse = if (!reducedMotion && speaking) (if (speakFrameAlt) 1.045f else 1.015f) else 1f
    val reactScale = if (!reducedMotion && showReactionFace) 1.045f else 1f
    val reactShift = if (!reducedMotion && showReactionFace) (-5).dp else 0.dp
    val scale = if (reducedMotion) 1f else breathScale * speakPulse * reactScale

    Image(
        painter = painterResource(id = assetId),
        contentDescription = "Ashu -- $mood",
        contentScale = ContentScale.Fit,
        modifier = modifier
            .offset(y = reactShift)
            .then(if (onTap != null) Modifier.clickable { onTap() } else Modifier)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
                rotationZ = swayDeg + spinDeg + headWobbleDeg
                translationY = jumpOffset
                translationX = hideShiftPx
            },
    )
}
