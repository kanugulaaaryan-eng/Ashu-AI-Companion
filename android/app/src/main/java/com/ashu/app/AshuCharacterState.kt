package com.ashu.app

/**
 * Ashu's v0.9 character state system.
 *
 * This is the single source of truth for "what expression is Ashu making
 * right now". Nothing else in the app should pick a drawable directly for
 * her portrait -- callers hand this a [AshuCharacterState] (or one of the
 * `from*` mappers below turns brain output into one) and [AshuCharacterState.assetFor]
 * resolves it to a real resource id, with fallbacks.
 *
 * Why fallbacks matter here: the v0.9 asset pack
 * (`ashu_assets_pack.zip` / ASHU_ASSET_MANIFEST.json) plans 45 pieces of art
 * across 27 chat-portrait states but only shipped 6 ("delivered"; the rest
 * are "pending_credits"). Every state below still resolves to *something*
 * sensible -- see [FALLBACK] -- so nothing ever renders a broken image, and
 * as more art lands, filling in [DIRECT_ASSET] for a state is the only
 * change needed.
 *
 * Art-consistency note: the fallback chain only ever lands on one of the
 * six new v0.9 portraits (neutral/happy/excited/curious/surprised/wink),
 * with two deliberate exceptions -- SAD and SLEEPY -- which fall back to
 * the *previous* character design's dedicated sad/sleepy stills rather than
 * to a smiling v0.9 face, because showing Ashu smiling while the user is
 * sad is worse than a brief art-style seam. Both are called out in
 * docs/CHANGELOG_v0.9.md as the first pieces of pending art worth
 * prioritizing.
 */
enum class AshuCharacterState {
    NEUTRAL, HAPPY, EXCITED, LAUGHING, PLAYFUL, WINK, CURIOUS, SURPRISED,
    CONFUSED, THINKING, SIDE_EYE, POUT, ANNOYED, SARCASTIC, TIRED, SLEEPY,
    CONCERNED, CARING, EMBARRASSED, PROUD, TEASING, SAD, LISTENING,
    SPEAKING, REACTING, BORED, ATTENTION;

    companion object {
        /** States with real v0.9 art shipped in this pack. */
        private val DIRECT_ASSET: Map<AshuCharacterState, Int> = mapOf(
            NEUTRAL to R.drawable.ashu_v2_neutral,
            HAPPY to R.drawable.ashu_v2_happy,
            EXCITED to R.drawable.ashu_v2_excited,
            WINK to R.drawable.ashu_v2_wink,
            CURIOUS to R.drawable.ashu_v2_curious,
            SURPRISED to R.drawable.ashu_v2_surprised,
        )

        /**
         * States with a deliberate legacy-art leaf instead of a v0.9 leaf
         * (see the class doc's "Art-consistency note").
         */
        private val LEGACY_LEAF_ASSET: Map<AshuCharacterState, Int> = mapOf(
            SAD to R.drawable.ashu_emo_sad,
            SLEEPY to R.drawable.ashu_emo_sleepy,
        )

        /**
         * Every state without its own art points at the nearest state that
         * *does* have art (directly or transitively). Must be acyclic --
         * verified by a unit test (AshuCharacterStateTest).
         */
        private val FALLBACK: Map<AshuCharacterState, AshuCharacterState> = mapOf(
            LAUGHING to EXCITED,
            PLAYFUL to WINK,
            CONFUSED to CURIOUS,
            THINKING to CURIOUS,
            SIDE_EYE to ANNOYED,
            POUT to ANNOYED,
            ANNOYED to NEUTRAL,
            SARCASTIC to ANNOYED,
            TIRED to SLEEPY,
            CONCERNED to CARING,
            CARING to NEUTRAL,
            EMBARRASSED to SURPRISED,
            PROUD to HAPPY,
            TEASING to PLAYFUL,
            LISTENING to CURIOUS,
            SPEAKING to HAPPY,
            REACTING to SURPRISED,
            BORED to NEUTRAL,
            ATTENTION to CURIOUS,
        )

        /** Resolves a state to a drawable resource id. Never returns null / broken. */
        fun assetFor(state: AshuCharacterState): Int {
            DIRECT_ASSET[state]?.let { return it }
            LEGACY_LEAF_ASSET[state]?.let { return it }
            var cursor = state
            repeat(AshuCharacterState.values().size) { // cycle guard
                val next = FALLBACK[cursor] ?: break
                DIRECT_ASSET[next]?.let { return it }
                LEGACY_LEAF_ASSET[next]?.let { return it }
                cursor = next
            }
            return R.drawable.ashu_v2_neutral // absolute last resort
        }

        /**
         * True if [state] has real, purpose-drawn v0.9 art (as opposed to
         * borrowing another state's expression).
         */
        fun hasDirectArt(state: AshuCharacterState): Boolean =
            state in DIRECT_ASSET || state in LEGACY_LEAF_ASSET

        /**
         * Brain mood string (personality/emotion.py's `Emotion`, lowercase
         * value) -> character state. Covers every `Emotion` enum member so
         * every mood the brain can report has a home.
         */
        fun fromMood(mood: String): AshuCharacterState = when (mood.lowercase()) {
            "happy" -> HAPPY
            "sad" -> SAD
            "sleepy" -> SLEEPY
            "excited" -> EXCITED
            "angry" -> ANNOYED
            "annoyed" -> ANNOYED
            "jealous" -> SIDE_EYE
            "caring" -> CARING
            "shy" -> EMBARRASSED
            "thinking" -> THINKING
            "confused" -> CONFUSED
            "bored" -> BORED
            "playful" -> PLAYFUL
            "flirty" -> WINK
            "proud" -> PROUD
            "worried" -> CONCERNED
            "surprised" -> SURPRISED
            "embarrassed" -> EMBARRASSED
            "curious" -> CURIOUS
            "calm" -> NEUTRAL
            else -> NEUTRAL
        }

        /**
         * Reusable gesture/action name (ASHU_ACTIONS in ChibiAshu.kt) ->
         * character state, for the subset of actions that are really just
         * a facial expression rather than a full-body pose. Returns null
         * for actions that should keep using ChibiAshu's existing
         * pose-based ACTION_ASSET table instead (e.g. "wave", "celebrate").
         */
        fun fromAction(action: String): AshuCharacterState? = when (action) {
            "wink" -> WINK
            "laugh", "giggle" -> LAUGHING
            "annoyed" -> ANNOYED
            "blush", "shy_hide" -> EMBARRASSED
            "thinking" -> THINKING
            "sleep", "yawn" -> SLEEPY
            "listening" -> LISTENING
            "speaking" -> SPEAKING
            "waiting" -> NEUTRAL
            else -> null
        }
    }
}
