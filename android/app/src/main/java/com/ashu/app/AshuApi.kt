package com.ashu.app

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets

/**
 * Ashu v0.4 HTTP client for the local bridge.
 *
 * Mirrors the Python protocol (protocol_version "3"). Every field is read with
 * a safe default so a newer/older bridge never crashes the app.
 */
class AshuApi(private val baseUrl: String) {

    // ---------------------------------------------------------------- setup
    fun setup(
        name: String, nickname: String, interests: List<String>,
        jealousyLevel: Int = 2, flirtyEnabled: Boolean = false, attentionEnabled: Boolean = true,
        sleepStart: String = "23:30", sleepEnd: String = "07:00", voiceEnabled: Boolean = true, autoMemory: Boolean = true,
        voiceLanguage: String = "te-IN", autoSpeak: Boolean = true,
        cloudFallbackEnabled: Boolean = false,
        proactiveEnabled: Boolean = true, dailyInitiationLimit: Int = 6,
        toolConfirmationRequired: Boolean = true, reducedMotion: Boolean = false,
    ): Boolean {
        val body = JSONObject().apply {
            put("name", name)
            put("nickname", nickname)
            put("interests", JSONArray(interests))
            put("primary_language", "te")
            put("secondary_languages", JSONArray(listOf("en", "hi")))
            put("jealousy_level", jealousyLevel)
            put("flirty_enabled", false) // v0.4: disabled by design
            put("attention_enabled", attentionEnabled)
            put("sleep_start", sleepStart)
            put("sleep_end", sleepEnd)
            put("voice_enabled", voiceEnabled)
            put("auto_memory", autoMemory)
            put("voice_language", voiceLanguage)
            put("auto_speak", autoSpeak)
            put("cloud_fallback_enabled", cloudFallbackEnabled)
            put("proactive_enabled", proactiveEnabled)
            put("daily_initiation_limit", dailyInitiationLimit)
            put("tool_confirmation_required", toolConfirmationRequired)
            put("reduced_motion", reducedMotion)
        }
        return post("/v1/setup", body).optBoolean("ok", false)
    }

    fun preferences(updates: Map<String, Any?>): JSONObject {
        val body = JSONObject()
        updates.forEach { (key, value) -> body.put(key, value) }
        return post("/v1/preferences", body)
    }

    // ----------------------------------------------------------------- chat
    fun chat(message: String, sessionId: String?): ChatResult {
        val body = JSONObject().apply {
            put("message", message)
            if (!sessionId.isNullOrBlank()) put("session_id", sessionId)
        }
        return post("/v1/chat", body).toChatResult()
    }

    fun proactive(): ProactiveResult {
        val json = get("/v1/proactive")
        return ProactiveResult(
            hasMessage = json.optBoolean("has_message", false),
            text = json.optString("text", ""),
            kind = json.optString("kind", ""),
            mood = json.optString("mood", "calm"),
            animation = json.optString("animation", ""),
        )
    }

    fun presence(idleSeconds: Long, appResumed: Boolean): ProactiveResult {
        val body = JSONObject().apply {
            put("idle_seconds", idleSeconds)
            put("app_resumed", appResumed)
        }
        val json = post("/v1/presence", body)
        return ProactiveResult(
            hasMessage = json.optBoolean("has_message", false),
            text = json.optString("text", ""),
            kind = json.optString("kind", ""),
            mood = json.optString("mood", "calm"),
            animation = json.optString("animation", ""),
        )
    }

    // ------------------------------------------------------------ decisions
    fun confirmations(): JSONObject = get("/v1/confirmations")

    fun confirm(id: String): String =
        post("/v1/confirm", JSONObject().put("id", id)).optString("text", "")

    fun cancel(id: String): String =
        post("/v1/cancel", JSONObject().put("id", id)).optString("text", "")

    // --------------------------------------------------------------- memory
    fun memory(): JSONObject = get("/v1/memory")

    fun memoryAll(query: String = ""): JSONArray {
        val path = if (query.isBlank()) "/v1/memory/all" else "/v1/memory/all?q=${enc(query)}"
        return get(path).optJSONArray("memories") ?: JSONArray()
    }

    fun activity(): JSONArray = get("/v1/memory/activity").optJSONArray("activity") ?: JSONArray()

    fun addMemory(fact: String, category: String, pinned: Boolean): Boolean =
        post("/v1/memory/add", JSONObject().apply {
            put("fact", fact); put("category", category); put("pinned", pinned)
        }).optBoolean("ok", false)

    fun updateMemory(id: Int, fact: String, category: String, pinned: Boolean): Boolean =
        post("/v1/memory/update", JSONObject().apply {
            put("id", id); put("fact", fact); put("category", category); put("pinned", pinned)
        }).optBoolean("ok", false)

    fun deleteMemory(id: Int): Boolean =
        post("/v1/memory/delete", JSONObject().put("id", id)).optBoolean("ok", false)

    fun deleteAllMemories(): Int =
        post("/v1/memory/delete_all", JSONObject()).optInt("removed", 0)

    // ---------------------------------------------------------------- state
    fun state(): JSONObject = get("/v1/state")

    // --------------------------------------------------------- model/voice
    fun modelStatus(): JSONObject = get("/v1/model/status")

    fun modelRegistry(): JSONArray = get("/v1/model/registry").optJSONArray("models") ?: JSONArray()

    fun importModel(sourcePath: String, destName: String? = null, sha256: String? = null): JSONObject =
        post("/v1/model/import", JSONObject().apply {
            put("source_path", sourcePath)
            if (!destName.isNullOrBlank()) put("dest_name", destName)
            if (!sha256.isNullOrBlank()) put("sha256", sha256)
        })

    fun downloadModel(specId: String): JSONObject =
        post("/v1/model/download", JSONObject().put("spec_id", specId))

    fun voiceCapabilities(): JSONObject = get("/v1/voice/capabilities")

    fun visionCapabilities(): JSONObject = get("/v1/vision/capabilities")

    fun visionCapture(granted: Boolean): JSONObject =
        post("/v1/vision/capture", JSONObject().put("granted", granted))

    fun visionAnalyze(imagePath: String, granted: Boolean): JSONObject =
        post("/v1/vision/analyze", JSONObject().apply {
            put("image_path", imagePath); put("granted", granted)
        })

    // -------------------------------------------------------------- privacy
    fun exportData(): JSONObject = post("/v1/privacy/export", JSONObject()).optJSONObject("data") ?: JSONObject()

    fun wipeData(): JSONObject = post("/v1/privacy/wipe", JSONObject())

    fun health(): JSONObject = try { get("/v1/health") } catch (_: Exception) { JSONObject() }

    // ----------------------------------------------------------- transport
    private fun post(path: String, json: JSONObject): JSONObject = request("POST", path, json.toString())

    private fun get(path: String): JSONObject = request("GET", path, null)

    private fun request(method: String, path: String, body: String?): JSONObject {
        val url = URL(baseUrl.trimEnd('/') + path)
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 3000
            readTimeout = 60000
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
            doInput = true
            if (body != null) doOutput = true
        }
        try {
            if (body != null) {
                connection.outputStream.use { it.write(body.toByteArray(StandardCharsets.UTF_8)) }
            }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader()?.use { it.readText() } ?: "{}"
            if (code !in 200..299) throw IllegalStateException(text)
            return JSONObject(text)
        } finally {
            connection.disconnect()
        }
    }

    private fun enc(value: String): String =
        java.net.URLEncoder.encode(value, "UTF-8")
}

private fun JSONObject.toChatResult(): ChatResult {
    val outfitJson = optJSONObject("outfit")
    val outfit = mutableMapOf<String, String>()
    outfitJson?.keys()?.forEach { key -> outfit[key] = outfitJson.optString(key, "") }
    val pending = optJSONObject("pending_action")
    return ChatResult(
        text = optString("text", "Em ledu ra babu 😭"),
        sessionId = optString("session_id"),
        action = optString("action_type", "answer"),
        mood = optString("mood", "calm"),
        relationshipStage = optString("relationship_stage", "formal"),
        thinkingLine = optString("thinking_line", ""),
        animation = optString("animation", ""),
        animationDuration = optDouble("animation_duration", 0.8).toFloat(),
        hairstyle = optString("hairstyle", "half_up"),
        outfit = outfit,
        sleepState = optString("sleep_state", "awake"),
        // v0.4
        origin = optString("origin", "rule_based"),
        provider = optString("provider", ""),
        isLocal = optBoolean("is_local", true),
        usedCloud = optBoolean("used_cloud", false),
        modelNotice = optString("model_notice", ""),
        waitingForUser = optBoolean("waiting_for_user", false),
        pendingActionId = pending?.optString("id", "") ?: "",
        pendingDescription = pending?.optString("description", "") ?: "",
        confidence = optDouble("confidence", 1.0).toFloat(),
    )
}

data class ChatResult(
    val text: String,
    val sessionId: String,
    val action: String,
    val mood: String = "calm",
    val relationshipStage: String = "formal",
    val thinkingLine: String = "",
    val animation: String = "",
    val animationDuration: Float = 0.8f,
    val hairstyle: String = "half_up",
    val outfit: Map<String, String> = emptyMap(),
    val sleepState: String = "awake",
    // v0.4 additions
    val origin: String = "rule_based",
    val provider: String = "",
    val isLocal: Boolean = true,
    val usedCloud: Boolean = false,
    val modelNotice: String = "",
    val waitingForUser: Boolean = false,
    val pendingActionId: String = "",
    val pendingDescription: String = "",
    val confidence: Float = 1.0f,
)

data class ProactiveResult(
    val hasMessage: Boolean,
    val text: String,
    val kind: String = "",
    val mood: String = "calm",
    val animation: String = "",
)
