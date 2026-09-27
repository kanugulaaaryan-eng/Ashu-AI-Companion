package com.ashu.app

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import java.util.Locale

/**
 * Ashu's voice layer (v0.4).
 *
 * Contains the three real device voice pieces:
 *   * offline text-to-speech via the platform TTS engine,
 *   * speech-to-text via [SpeechRecognizer],
 *   * explicit state reporting so the UI can show listening/speaking indicators,
 *     and an interrupt() that stops playback immediately.
 *
 * Wake word is deliberately NOT claimed to work: [wakeWordStatus] reports
 * `available = false` until a real on-device keyword spotter is bundled.
 * See docs/LIMITATIONS_v0.4.md.
 *
 * The voice is an original warm/youthful Indian-female direction (rate/pitch
 * tuned), never a clone of any real person's voice.
 */
class AshuVoice(private val context: Context) : TextToSpeech.OnInitListener {

    enum class VoiceState { IDLE, LISTENING, THINKING, SPEAKING, ERROR }

    interface SttListener {
        fun onPartial(text: String)
        fun onFinal(text: String)
        fun onError(message: String)
        fun onState(state: VoiceState)
    }

    private val tts = TextToSpeech(context.applicationContext, this)
    private var ttsReady = false
    private var recognizer: SpeechRecognizer? = null

    var state: VoiceState = VoiceState.IDLE
        private set
    var lastError: String = ""
        private set

    var autoSpeak: Boolean = true
    var voiceLanguage: String = "te-IN"
    var volume: Float = 1.0f
        set(value) { field = value.coerceIn(0f, 1f) }

    override fun onInit(status: Int) {
        ttsReady = status == TextToSpeech.SUCCESS
        if (ttsReady) {
            tts.setSpeechRate(0.97f)
            tts.setPitch(1.06f)
            applyLocale(voiceLanguage)
            tts.setOnUtteranceProgressListener(object : android.speech.tts.UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) { state = VoiceState.SPEAKING }
                override fun onDone(utteranceId: String?) { state = VoiceState.IDLE }
                @Deprecated("Deprecated in API 21")
                override fun onError(utteranceId: String?) { state = VoiceState.IDLE }
                override fun onError(utteranceId: String?, errorCode: Int) { state = VoiceState.IDLE }
            })
        }
    }

    // ------------------------------------------------------------------ TTS
    fun isTtsAvailable(): Boolean = ttsReady

    fun speak(text: String) {
        if (!ttsReady || text.isBlank()) {
            if (!ttsReady) { state = VoiceState.ERROR; lastError = "Text-to-speech is unavailable on this device." }
            return
        }
        applyLocale(detectLocale(text))
        state = VoiceState.SPEAKING
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "ashu_${System.currentTimeMillis()}")
    }

    /** Interrupting playback: stops her mid-sentence. */
    fun interrupt() {
        if (ttsReady) tts.stop()
        state = VoiceState.IDLE
    }

    private fun applyLocale(localeCode: String) {
        val result = tts.setLanguage(parseLocale(localeCode))
        if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
            // Fall back to Telugu, then to the device default.
            val telugu = tts.setLanguage(Locale("te", "IN"))
            if (telugu == TextToSpeech.LANG_MISSING_DATA || telugu == TextToSpeech.LANG_NOT_SUPPORTED) {
                state = VoiceState.ERROR
                lastError = "No Telugu/Indian TTS voice is installed on this device."
            }
        }
    }

    // ------------------------------------------------------------------ STT
    fun isSttAvailable(): Boolean = SpeechRecognizer.isRecognitionAvailable(context)

    fun startListening(listener: SttListener) {
        if (!isSttAvailable()) {
            state = VoiceState.ERROR
            lastError = "Speech recognition is not available on this device."
            listener.onError(lastError)
            return
        }
        if (recognizer == null) {
            recognizer = SpeechRecognizer.createSpeechRecognizer(context).apply {
                setRecognitionListener(object : RecognitionListener {
                    override fun onReadyForSpeech(params: Bundle?) { state = VoiceState.LISTENING; listener.onState(state) }
                    override fun onBeginningOfSpeech() {}
                    override fun onRmsChanged(rmsdB: Float) {}
                    override fun onBufferReceived(buffer: ByteArray?) {}
                    override fun onEndOfSpeech() { state = VoiceState.THINKING; listener.onState(state) }
                    override fun onError(error: Int) {
                        state = VoiceState.ERROR
                        lastError = errorMessage(error)
                        listener.onError(lastError)
                        listener.onState(state)
                    }
                    override fun onResults(results: Bundle?) {
                        val text = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
                        state = VoiceState.IDLE
                        listener.onFinal(text)
                        listener.onState(state)
                    }
                    override fun onPartialResults(partialResults: Bundle?) {
                        val text = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
                        if (text.isNotBlank()) listener.onPartial(text)
                    }
                    override fun onEvent(eventType: Int, params: Bundle?) {}
                })
            }
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, voiceLanguage)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, voiceLanguage)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        state = VoiceState.LISTENING
        listener.onState(state)
        recognizer?.startListening(intent)
    }

    fun stopListening() {
        recognizer?.stopListening()
        state = VoiceState.IDLE
    }

    private fun errorMessage(code: Int): String = when (code) {
        SpeechRecognizer.ERROR_AUDIO -> "Audio recording error."
        SpeechRecognizer.ERROR_CLIENT -> "Speech recognizer client error."
        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Microphone permission not granted."
        SpeechRecognizer.ERROR_NETWORK -> "Speech recognition needs a network connection on this device."
        SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Speech recognition timed out."
        SpeechRecognizer.ERROR_NO_MATCH -> "Didn't catch that — try again."
        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Speech recognizer is busy."
        SpeechRecognizer.ERROR_SERVER -> "Speech recognition server error."
        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech detected."
        else -> "Speech recognition failed."
    }

    // ------------------------------------------------------------ wake word
    /**
     * Wake-word architecture. The intended pipeline is:
     *   always-on lightweight VAD -> small TFLite/ONNX keyword spotter
     *   -> wake event -> startListening().
     * Until that model is bundled, this reports unavailable and never listens,
     * so the app never claims a wake word it does not have.
     */
    fun wakeWordStatus(): Map<String, Any> = mapOf(
        "available" to false,
        "enabled" to false,
        "wake_word" to "hey ashu",
        "reason" to "No on-device keyword-spotter model is bundled yet.",
    )

    fun capabilities(): Map<String, Any> = mapOf(
        "tts" to isTtsAvailable(),
        "stt" to isSttAvailable(),
        "state" to state.name.lowercase(),
        "language" to voiceLanguage,
        "auto_speak" to autoSpeak,
        "last_error" to lastError,
        "wake_word" to wakeWordStatus(),
    )

    fun close() {
        if (ttsReady) { tts.stop(); tts.shutdown() }
        recognizer?.destroy()
        recognizer = null
    }

    // --------------------------------------------------------------- locale
    companion object {
        fun detectLocale(text: String): String = when {
            text.any { it in '\u0900'..'\u097F' } -> "hi-IN"
            text.any { it in '\u0C00'..'\u0C7F' } -> "te-IN"
            else -> romanTelugu(text) ?: "en-IN"
        }

        private val ROMAN_TE = setOf(
            "em", "enti", "ela", "enduku", "ekkada", "eppudu", "sare", "cheppu",
            "ra", "babu", "nuvvu", "nenu", "kada", "ledu", "undi", "avunu",
            "chala", "baga", "inka", "ayyo", "abba", "matladu", "chestunav",
        )

        private fun romanTelugu(text: String): String? {
            val words = Regex("[a-zA-Z']+").findAll(text.lowercase()).map { it.value }.toSet()
            return if (words.any { it in ROMAN_TE }) "te-IN" else null
        }

        private fun parseLocale(code: String): Locale {
            val parts = code.split("-")
            return when (parts.size) {
                1 -> Locale(parts[0])
                else -> Locale(parts[0], parts[1])
            }
        }
    }
}
