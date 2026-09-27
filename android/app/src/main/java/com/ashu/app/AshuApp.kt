@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.ashu.app

import android.Manifest
import android.content.Context
import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.Brain
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.KeyboardVoice
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MicOff
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Pin
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

// ---------------------------------------------------------------------------
// Professional Ashu Color Palette (Material3)
// ---------------------------------------------------------------------------
private val AshuPrimary = Color(0xFF0F172A)        // Deep Navy
private val AshuPrimaryLight = Color(0xFF1E293B)
private val AshuPrimaryDark = Color(0xFF020617)
private val AshuPrimaryContainer = Color(0xFFE0E7FF)
private val AshuOnPrimary = Color.White

private val AshuSecondary = Color(0xFF0369A1)       // Professional Blue
private val AshuSecondaryLight = Color(0xFF0EA5E9)
private val AshuSecondaryContainer = Color(0xFFDBEAFE)
private val AshuOnSecondary = Color.White

private val AshuTertiary = Color(0xFFE96586)        // Warm Coral
private val AshuTertiaryLight = Color(0xFFF472B6)
private val AshuTertiaryContainer = Color(0xFFFFF1F5)
private val AshuOnTertiary = Color.White

private val AshuBackground = Color(0xFFF8FAFC)      // Clean Off-White
private val AshuSurface = Color.White
private val AshuSurfaceVariant = Color(0xFFF1F5F9)
private val AshuSurfaceContainer = Color(0xFFE8EEF7)

private val AshuOnBackground = Color(0xFF0F172A)
private val AshuOnSurface = Color(0xFF0F172A)
private val AshuOnSurfaceVariant = Color(0xFF475569)
private val AshuTextPrimary = Color(0xFF0F172A)
private val AshuTextSecondary = Color(0xFF475569)
private val AshuTextTertiary = Color(0xFF94A3B8)
private val AshuTextDisabled = Color(0xFFCBD5E1)

private val AshuOutline = Color(0xFFE2E8F0)
private val AshuOutlineVariant = Color(0xFFCBD5E1)
private val AshuDivider = Color(0xFFE2E8F0)

private val AshuSuccess = Color(0xFF059669)
private val AshuSuccessContainer = Color(0xFFD1FAE5)
private val AshuError = Color(0xFFDC2626)
private val AshuErrorContainer = Color(0xFFFEE2E2)
private val AshuWarning = Color(0xFFD97706)
private val AshuWarningContainer = Color(0xFFFEF3C7)

private val AshuShadow = Color(0x0A000000)
private val AshuShadowElevated = Color(0x14000000)

// Mood-based accent colors
private val AshuMoodColors = mapOf(
    "happy" to AshuSuccess,
    "excited" to Color(0xFFF59E0B),
    "curious" to AshuSecondary,
    "annoyed" to AshuError,
    "sad" to Color(0xFF6366F1),
    "sleepy" to Color(0xFF8B5CF6),
    "playful" to Color(0xFFEC4899),
    "calm" to Color(0xFF0891B2),
)

// ---------------------------------------------------------------------------
// Shared model
// ---------------------------------------------------------------------------
private data class ChatMessage(
    val fromAshu: Boolean,
    val text: String,
    val origin: String = "",
    val timestamp: Long = System.currentTimeMillis()
)

private enum class Screen { CHAT, MEMORY, MODEL, SETTINGS, PRIVACY }

private fun prefs(context: Context) = context.getSharedPreferences("ashu", Context.MODE_PRIVATE)

@Composable
fun AshuApp() {
    val context = LocalContext.current
    val store = remember { prefs(context) }
    var onboardingDone by remember { mutableStateOf(store.getBoolean("onboarding_done", false)) }
    var screen by remember { mutableStateOf(Screen.CHAT) }
    var baseUrl by remember { mutableStateOf(store.getString("base_url", "http://10.0.2.2:8765") ?: "http://10.0.2.2:8765") }
    var nickname by remember { mutableStateOf(store.getString("nickname", "") ?: "") }
    var voiceEnabled by remember { mutableStateOf(store.getBoolean("voice_enabled", true)) }
    var autoSpeak by remember { mutableStateOf(store.getBoolean("auto_speak", true)) }
    var reducedMotion by remember { mutableStateOf(store.getBoolean("reduced_motion", false)) }
    var mood by remember { mutableStateOf(store.getString("mood", "calm") ?: "calm") }

    // Material3 Color Scheme
    val colorScheme = lightColorScheme(
        primary = AshuPrimary,
        primaryContainer = AshuPrimaryContainer,
        secondary = AshuSecondary,
        secondaryContainer = AshuSecondaryContainer,
        tertiary = AshuTertiary,
        tertiaryContainer = AshuTertiaryContainer,
        background = AshuBackground,
        surface = AshuSurface,
        surfaceVariant = AshuSurfaceVariant,
        surfaceContainer = AshuSurfaceContainer,
        onPrimary = AshuOnPrimary,
        onSecondary = AshuOnSecondary,
        onTertiary = AshuOnTertiary,
        onBackground = AshuOnBackground,
        onSurface = AshuOnSurface,
        onSurfaceVariant = AshuOnSurfaceVariant,
        outline = AshuOutline,
        outlineVariant = AshuOutlineVariant,
        error = AshuError,
        errorContainer = AshuErrorContainer,
        onError = AshuOnPrimary,
        onErrorContainer = AshuTextPrimary,
    )

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography(
            displayLarge = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.Bold,
                fontSize = 57.sp,
                lineHeight = 64.sp,
                letterSpacing = -0.25.sp
            ),
            displayMedium = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.Bold,
                fontSize = 45.sp,
                lineHeight = 52.sp,
                letterSpacing = 0.sp
            ),
            displaySmall = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.Bold,
                fontSize = 36.sp,
                lineHeight = 44.sp,
                letterSpacing = 0.sp
            ),
            headlineLarge = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.Bold,
                fontSize = 32.sp,
                lineHeight = 40.sp,
                letterSpacing = 0.sp
            ),
            headlineMedium = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.SemiBold,
                fontSize = 28.sp,
                lineHeight = 36.sp,
                letterSpacing = 0.sp
            ),
            headlineSmall = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.SemiBold,
                fontSize = 24.sp,
                lineHeight = 32.sp,
                letterSpacing = 0.sp
            ),
            titleLarge = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.SemiBold,
                fontSize = 22.sp,
                lineHeight = 28.sp,
                letterSpacing = 0.sp
            ),
            titleMedium = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.Medium,
                fontSize = 16.sp,
                lineHeight = 24.sp,
                letterSpacing = 0.15.sp
            ),
            titleSmall = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.Medium,
                fontSize = 14.sp,
                lineHeight = 20.sp,
                letterSpacing = 0.1.sp
            ),
            bodyLarge = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.Normal,
                fontSize = 16.sp,
                lineHeight = 24.sp,
                letterSpacing = 0.5.sp
            ),
            bodyMedium = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.Normal,
                fontSize = 14.sp,
                lineHeight = 20.sp,
                letterSpacing = 0.25.sp
            ),
            bodySmall = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.Normal,
                fontSize = 12.sp,
                lineHeight = 16.sp,
                letterSpacing = 0.4.sp
            ),
            labelLarge = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.SemiBold,
                fontSize = 14.sp,
                lineHeight = 20.sp,
                letterSpacing = 0.1.sp
            ),
            labelMedium = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.Medium,
                fontSize = 12.sp,
                lineHeight = 16.sp,
                letterSpacing = 0.5.sp
            ),
            labelSmall = TextStyle(
                fontFamily = FontFamily.Default,
                fontWeight = FontWeight.Medium,
                fontSize = 11.sp,
                lineHeight = 16.sp,
                letterSpacing = 0.5.sp
            ),
        ),
        shapes = Shapes(
            extraSmall = RoundedCornerShape(12.dp),
            small = RoundedCornerShape(16.dp),
            medium = RoundedCornerShape(24.dp),
            large = RoundedCornerShape(28.dp),
            extraLarge = RoundedCornerShape(32.dp),
        )
    ) {
        Surface(Modifier.fillMaxSize(), color = colorScheme.background) {
            if (!onboardingDone) {
                Onboarding(baseUrlDefault = baseUrl) { setup ->
                    nickname = setup.nickname.ifBlank { setup.name }
                    baseUrl = setup.baseUrl
                    voiceEnabled = setup.voiceEnabled
                    autoSpeak = setup.autoSpeak
                    reducedMotion = setup.reducedMotion
                    store.edit()
                        .putBoolean("onboarding_done", true)
                        .putString("nickname", nickname)
                        .putString("base_url", baseUrl)
                        .putBoolean("voice_enabled", voiceEnabled)
                        .putBoolean("auto_speak", autoSpeak)
                        .putBoolean("reduced_motion", reducedMotion)
                        .putString("mood", "happy").apply()
                    onboardingDone = true
                    kotlinx.coroutines.CoroutineScope(Dispatchers.IO).launch {
                        runCatching {
                            AshuApi(baseUrl).setup(
                                name = setup.name, nickname = setup.nickname,
                                interests = setup.interests.split(',').map { it.trim() }.filter { it.isNotBlank() },
                                jealousyLevel = setup.jealousyLevel, flirtyEnabled = false,
                                attentionEnabled = setup.attentionEnabled,
                                sleepStart = setup.sleepStart, sleepEnd = setup.sleepEnd,
                                voiceEnabled = setup.voiceEnabled, autoMemory = setup.autoMemory,
                                voiceLanguage = setup.voiceLanguage, autoSpeak = setup.autoSpeak,
                                cloudFallbackEnabled = setup.cloudFallbackEnabled,
                                proactiveEnabled = setup.proactiveEnabled,
                                dailyInitiationLimit = setup.dailyLimit,
                                toolConfirmationRequired = setup.toolConfirmation,
                                reducedMotion = setup.reducedMotion,
                            )
                        }
                    }
                }
            } else {
                Scaffold(
                    containerColor = colorScheme.background,
                    topBar = {
                        TopAppBar(
                            title = {
                                Column {
                                    Text("Ashu", fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
                                    Text(
                                        if (nickname.isBlank()) "nee phone lo nenu" else "$nickname tho chat",
                                        fontSize = 11.sp, color = colorScheme.onSurfaceVariant.copy(alpha = 0.8f),
                                    )
                                }
                            },
                            actions = {
                                AssistChip(onClick = { screen = Screen.MEMORY }, label = { Text("Memory") })
                                Spacer(Modifier.width(4.dp))
                                AssistChip(onClick = { screen = Screen.MODEL }, label = { Text("Model") })
                                Spacer(Modifier.width(4.dp))
                                IconButton(onClick = { screen = Screen.PRIVACY }) { Text("🔒") }
                                IconButton(onClick = { screen = Screen.SETTINGS }) { Text("⚙") }
                            },
                        )
                    },
                ) { padding ->
                    Box(Modifier.padding(padding).fillMaxSize()) {
                        when (screen) {
                            Screen.CHAT -> ChatScreen(
                                baseUrl = baseUrl, voiceEnabled = voiceEnabled, autoSpeak = autoSpeak,
                                reducedMotion = reducedMotion, nickname = nickname,
                                onMoodChange = { mood = it; store.edit().putString("mood", it).apply() },
                            )
                            Screen.MEMORY -> MemoryScreen(baseUrl)
                            Screen.MODEL -> ModelScreen(baseUrl)
                            Screen.SETTINGS -> SettingsScreen(
                                baseUrl = baseUrl, voiceEnabled = voiceEnabled,
                                autoSpeak = autoSpeak, reducedMotion = reducedMotion,
                                onSave = { url, voice, speak, rm ->
                                    baseUrl = url; voiceEnabled = voice; autoSpeak = speak; reducedMotion = rm
                                    store.edit().putString("base_url", url).putBoolean("voice_enabled", voice)
                                        .putBoolean("auto_speak", speak).putBoolean("reduced_motion", rm).apply()
                                    screen = Screen.CHAT
                                },
                            )
                            Screen.PRIVACY -> PrivacyScreen(baseUrl)
                        }
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Onboarding (10 steps)
// ---------------------------------------------------------------------------
data class SetupState(
    val name: String, val nickname: String, val interests: String,
    val jealousyLevel: Int, val flirtyEnabled: Boolean = false, val attentionEnabled: Boolean,
    val sleepStart: String, val sleepEnd: String, val voiceEnabled: Boolean, val autoMemory: Boolean,
    val baseUrl: String, val voiceLanguage: String, val autoSpeak: Boolean,
    val cloudFallbackEnabled: Boolean, val proactiveEnabled: Boolean, val dailyLimit: Int,
    val toolConfirmation: Boolean, val reducedMotion: Boolean,
)

@Composable
private fun Onboarding(baseUrlDefault: String, onFinish: (SetupState) -> Unit) {
    val context = LocalContext.current
    var step by remember { mutableIntStateOf(0) }
    var name by remember { mutableStateOf("") }
    var nick by remember { mutableStateOf("") }
    var interests by remember { mutableStateOf("") }
    var language by remember { mutableStateOf("Telugu + English") }
    var jealousy by remember { mutableFloatStateOf(2f) }
    var attention by remember { mutableStateOf(true) }
    var sleepStart by remember { mutableStateOf("23:30") }
    var sleepEnd by remember { mutableStateOf("07:00") }
    var voice by remember { mutableStateOf(true) }
    var autoSpeak by remember { mutableStateOf(true) }
    var autoMemory by remember { mutableStateOf(true) }
    var cloudFallback by remember { mutableStateOf(false) }
    var proactive by remember { mutableStateOf(true) }
    var dailyLimit by remember { mutableFloatStateOf(6f) }
    var toolConfirm by remember { mutableStateOf(true) }
    var reducedMotion by remember { mutableStateOf(false) }
    var permCamera by remember { mutableStateOf(false) }
    var permMic by remember { mutableStateOf(false) }
    var permNotif by remember { mutableStateOf(false) }
    var permFiles by remember { mutableStateOf(false) }
    var modelPath by remember { mutableStateOf("") }
    var testMessage by remember { mutableStateOf("") }
    var testReply by remember { mutableStateOf("") }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        permCamera = result[Manifest.permission.CAMERA] ?: permCamera
        permMic = result[Manifest.permission.RECORD_AUDIO] ?: permMic
    }

    val titles = listOf(
        "Hi. I'm Ashu ♡",
        "What I can and can't access",
        "Which languages?",
        "How should I sound?",
        "Cloud fallback?",
        "When should I talk first?",
        "Give me permissions — one by one",
        "Bring my local brain",
        "Let's test it",
        "All set ♡",
    )

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(22.dp),
        verticalArrangement = Arrangement.Top,
    ) {
        Box(Modifier.fillMaxWidth().height(if (step == 0) 210.dp else 150.dp), contentAlignment = Alignment.CenterEnd) {
            if (step == 0) {
                // First "meet Ashu" screen: the full front portrait, not a mood still.
                androidx.compose.foundation.Image(
                    painter = androidx.compose.ui.res.painterResource(id = R.drawable.ashu_full_front),
                    contentDescription = "Ashu",
                    modifier = Modifier.size(width = 130.dp, height = 200.dp),
                )
            } else {
                ChibiAshu(
                    mood = when (step) { 5 -> "bored"; 7 -> "thinking"; 8 -> "happy"; else -> "calm" },
                    reducedMotion = reducedMotion, modifier = Modifier.size(130.dp),
                )
            }
        }
        Text("ASHU v0.9", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = AshuTertiary)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                "Step ${step + 1} / ${titles.size}",
                fontSize = 11.sp, fontWeight = FontWeight.Bold, color = AshuTertiary,
                modifier = Modifier.background(AshuTertiaryContainer, RoundedCornerShape(999.dp))
                    .padding(horizontal = 8.dp, vertical = 4.dp),
            )
            Spacer(Modifier.width(8.dp))
            Text(
                titles[step], fontSize = 25.sp, fontWeight = FontWeight.SemiBold, color = colorScheme.onSurface,
                modifier = Modifier.weight(1f),
            )
        }
        Spacer(Modifier.height(10.dp))

        when (step) {
            0 -> {
                Text(
                    "Nenu Telugu-first companion. Local ga untanu — nee phone lo ne. Conversation, memories, voice anni nee daggare.",
                    color = colorScheme.onSurfaceVariant, lineHeight = 22.sp,
                )
                Spacer(Modifier.height(14.dp))
                OutlinedTextField(name, { name = it }, label = { Text("Your name") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(nick, { nick = it }, label = { Text("What should I call you?") }, singleLine = true, modifier = Modifier.fillMaxWidth())
            }
            1 -> {
                Card(colors = CardDefaults.cardColors(containerColor = AshuSuccessContainer), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text("Ashu CAN:", fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
                        Text("• chat in Telugu + English\n• remember things you tell her (locally)\n• speak with your phone's TTS\n• use permissions you grant, one at a time", fontSize = 13.sp, color = colorScheme.onSurfaceVariant)
                        Spacer(Modifier.height(8.dp))
                        Text("Ashu CANNOT (by design):", fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
                        Text("• secretly record audio or capture the screen\n• read notifications or app usage without explicit access\n• send messages or delete files without confirmation\n• claim to know something she hasn't actually accessed", fontSize = 13.sp, color = colorScheme.onSurfaceVariant)
                    }
                }
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(interests, { interests = it }, label = { Text("Interests: coding, cricket, movies…") }, modifier = Modifier.fillMaxWidth())
            }
            2 -> {
                Text("Telugu is primary, English second. Hindi is scaffolded for later.", color = colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(8.dp))
                listOf("Telugu + English", "Telugu only", "English first").forEach { option ->
                    Row(Modifier.fillMaxWidth().clickable { language = option }.padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected = language == option, onClick = { language = option })
                        Text(option, color = colorScheme.onSurface)
                    }
                }
            }
            3 -> {
                SwitchRow("Speak replies out loud", voice) { voice = it }
                SwitchRow("Auto-speak every reply", autoSpeak) { autoSpeak = it }
                SwitchRow("Reduce motion (no idle animation)", reducedMotion) { reducedMotion = it }
                Spacer(Modifier.height(6.dp))
                Text("Voice uses your device's own TTS. It's an original warm voice profile — not a clone of any real person.", fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
            }
            4 -> {
                SwitchRow("Allow cloud fallback for hard questions", cloudFallback) { cloudFallback = it }
                Spacer(Modifier.height(4.dp))
                Text(
                    "Off by default. If you turn it on, Ashu clearly tells you whenever a reply came from the cloud. Your memories and files are never included unless you separately allow it.",
                    fontSize = 12.sp, color = colorScheme.onSurfaceVariant,
                )
            }
            5 -> {
                SwitchRow("Ashu may start conversations sometimes", proactive) { proactive = it }
                SwitchRow("Playful attention-seeking when bored", attention) { attention = it }
                Spacer(Modifier.height(6.dp))
                Text("Daily initiation limit: ${dailyLimit.toInt()}", fontWeight = FontWeight.SemiBold, color = colorScheme.onSurface)
                Slider(dailyLimit, { dailyLimit = it }, valueRange = 0f..12f, steps = 11)
                Text("She respects a daily cap and quiet hours, so she never spams you.", fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(sleepStart, { sleepStart = it }, label = { Text("Sleep") }, modifier = Modifier.weight(1f), singleLine = true)
                    OutlinedTextField(sleepEnd, { sleepEnd = it }, label = { Text("Wake") }, modifier = Modifier.weight(1f), singleLine = true)
                }
            }
            6 -> {
                PhonePermissions.CATALOG.forEach { info ->
                    PermissionCard(info.title, info.explanation, when (info.key) {
                        "camera" -> permCamera; "microphone" -> permMic
                        "notifications" -> permNotif; "files" -> permFiles
                        else -> false
                    }) { checked ->
                        when (info.key) {
                            "camera" -> { permCamera = checked; if (checked) permissionLauncher.launch(arrayOf(Manifest.permission.CAMERA)) }
                            "microphone" -> { permMic = checked; if (checked) permissionLauncher.launch(arrayOf(Manifest.permission.RECORD_AUDIO)) }
                            "notifications" -> permNotif = checked
                            "files" -> { permFiles = checked; if (checked) PhonePermissions.openBroadFileAccess(context) }
                            "notification_listener" -> if (checked) PhonePermissions.openNotificationListenerSettings(context)
                            "usage_access" -> if (checked) DeviceTools.openUsageAccessSettings(context)
                        }
                    }
                }
                SwitchRow("Ask before risky actions (write file, open app, camera)", toolConfirm) { toolConfirm = it }
            }
            7 -> {
                Text("Ashu runs fully with an offline fallback, but a local model makes her much better.", color = colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(modelPath, { modelPath = it }, label = { Text("Path to a .gguf model on your device (optional)") }, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                Card(colors = CardDefaults.cardColors(containerColor = AshuSecondaryContainer), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp)) {
                        Text("Recommended for Telugu / on-device", fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
                        Text("Qwen3-4B Q4_K_M (~2.50 GB) · Qwen3-1.7B Q4_K_M (~1.28 GB) · Gemma 3n E2B Q8_0 (~4.79 GB)", fontSize = 13.sp, color = colorScheme.onSurfaceVariant)
                        Spacer(Modifier.height(4.dp))
                        Text("GGUF releases are available for all three. Start with Qwen3-1.7B when storage/RAM is tight.", fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
                    }
                }
            }
            8 -> {
                Text("Say something to test the local bridge (optional).", color = colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(testMessage, { testMessage = it }, label = { Text("Hey Ashu, em chestunav?") }, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                Button(onClick = {
                    kotlinx.coroutines.CoroutineScope(Dispatchers.IO).launch {
                        val reply = runCatching { AshuApi(baseUrlDefault).chat(testMessage.ifBlank { "hi" }, null).text }.getOrDefault("Bridge reachable kaadu — offline mode lo untanu.")
                        withContext(Dispatchers.Main) { testReply = reply }
                    }
                }) { Text("Test chat") }
                if (testReply.isNotBlank()) {
                    Spacer(Modifier.height(10.dp))
                    Card(colors = CardDefaults.cardColors(containerColor = AshuTertiaryContainer)) {
                        Text(testReply, Modifier.padding(14.dp), color = colorScheme.onSurface)
                    }
                }
            }
            else -> {
                Card(colors = CardDefaults.cardColors(containerColor = AshuSuccessContainer), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text("Ashu is ready.", fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
                        Text("She'll start polite, remember what matters, and slowly grow into a warm, teasing best friend. No flirting, no guilt-tripping, no spying.", fontSize = 13.sp, color = colorScheme.onSurfaceVariant)
                    }
                }
            }
        }

        Spacer(Modifier.height(20.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            if (step > 0) {
                OutlinedButton(onClick = { step-- }, modifier = Modifier.weight(1f)) { Text("Back") }
            }
            Button(
                onClick = {
                    if (step < titles.size - 1) step++
                    else onFinish(SetupState(
                        name = name.ifBlank { "friend" }, nickname = nick, interests = interests,
                        jealousyLevel = jealousy.toInt(), attentionEnabled = attention,
                        sleepStart = sleepStart, sleepEnd = sleepEnd, voiceEnabled = voice,
                        autoMemory = autoMemory, baseUrl = baseUrlDefault, voiceLanguage = "te-IN",
                        autoSpeak = autoSpeak, cloudFallbackEnabled = cloudFallback,
                        proactiveEnabled = proactive, dailyLimit = dailyLimit.toInt(),
                        toolConfirmation = toolConfirm, reducedMotion = reducedMotion,
                    ))
                },
                enabled = step != 0 || name.isNotBlank(),
                modifier = Modifier.weight(if (step > 0) 2f else 1f).height(52.dp),
                shape = RoundedCornerShape(18.dp),
                colors = ButtonDefaults.buttonColors(containerColor = AshuTertiary),
            ) { Text(if (step < titles.size - 1) "Next" else "Welcome home, Ashu") }
        }
    }
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------
@Composable
private fun ChatScreen(
    baseUrl: String,
    voiceEnabled: Boolean,
    autoSpeak: Boolean,
    reducedMotion: Boolean,
    nickname: String,
    onMoodChange: (String) -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val voice = remember { AshuVoice(context) }
    var input by remember { mutableStateOf("") }
    var sessionId by remember { mutableStateOf<String?>(null) }
    var online by remember { mutableStateOf(false) }
    var thinking by remember { mutableStateOf(false) }
    var mood by remember { mutableStateOf("calm") }
    var animation by remember { mutableStateOf("") }
    var hairstyle by remember { mutableStateOf("half_up") }
    var outfitTop by remember { mutableStateOf("casual_top") }
    var relationshipStage by remember { mutableStateOf("formal") }
    var sleepState by remember { mutableStateOf("awake") }
    var origin by remember { mutableStateOf("") }
    var modelNotice by remember { mutableStateOf("") }
    var waiting by remember { mutableStateOf(false) }
    var pendingId by remember { mutableStateOf("") }
    var pendingDescription by remember { mutableStateOf("") }
    var listening by remember { mutableStateOf(false) }
    var speaking by remember { mutableStateOf(false) }
    var reacting by remember { mutableStateOf(false) }
    var partial by remember { mutableStateOf("") }
    val messages = remember {
        mutableStateListOf(ChatMessage(true, "Hello... 😌 Nenu Ashu. Ikkade unna.", "rule_based"))
    }

    DisposableEffect(Unit) { onDispose { voice.close() } }

    LaunchedEffect(baseUrl) {
        online = withContext(Dispatchers.IO) {
            runCatching { AshuApi(baseUrl).health().optBoolean("ok", false) }.getOrDefault(false)
        }
    }

    suspend fun speakWithState(text: String) {
        if (!voiceEnabled || !autoSpeak || text.isBlank()) return
        speaking = true
        voice.speak(text)
        while (voice.state == AshuVoice.VoiceState.SPEAKING) kotlinx.coroutines.delay(80)
        speaking = false
    }

    suspend fun send(text: String) {
        val clean = text.trim()
        if (clean.isEmpty()) return
        messages += ChatMessage(false, clean)
        thinking = true
        animation = "thinking" // v0.9 Part 4: real THINKING state while awaiting the brain's reply
        val result = withContext(Dispatchers.IO) {
            runCatching { AshuApi(baseUrl).chat(clean, sessionId) }.getOrNull()
        }
        if (!result?.thinkingLine.isNullOrBlank()) kotlinx.coroutines.delay(400)
        thinking = false

        if (result != null) {
            sessionId = result.sessionId
            mood = result.mood
            onMoodChange(result.mood)
            online = true
            animation = result.animation
            hairstyle = result.hairstyle
            result.outfit["top"]?.let { outfitTop = it }
            relationshipStage = result.relationshipStage
            sleepState = result.sleepState
            origin = result.origin
            modelNotice = result.modelNotice
            waiting = result.waitingForUser
            pendingId = result.pendingActionId
            pendingDescription = result.pendingDescription
            messages += ChatMessage(true, result.text, result.origin)
            reacting = true
            animation = result.animation.ifBlank {
                if (result.waitingForUser) "waiting" else "look_at_user"
            }
            if (!reducedMotion) {
                kotlinx.coroutines.delay(480)
                reacting = false
            }
            speakWithState(result.text)
        } else {
            online = false
            val reply = fallbackReply(clean)
            mood = inferFallbackMood(clean)
            onMoodChange(mood)
            animation = "shrug"
            messages += ChatMessage(true, reply, "rule_based")
            reacting = true
            if (!reducedMotion) {
                kotlinx.coroutines.delay(480)
                reacting = false
            }
            speakWithState(reply)
        }
    }

    Column(Modifier.fillMaxSize().padding(horizontal = 14.dp, vertical = 8.dp)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Chip(if (online) "local bridge" else "offline companion", if (online) AshuSuccessContainer else AshuTertiaryContainer)
            Chip(relationshipStage.replace('_', ' '), AshuSecondaryContainer)
            Chip(
                "mood: ${mood.lowercase()}" + if (sleepState != "awake") " · $sleepState" else "",
                AshuTertiaryContainer,
            )
            Spacer(Modifier.weight(1f))
            if (origin.isNotBlank()) OriginTag(origin)
        }

        if (modelNotice.isNotBlank()) {
            Spacer(Modifier.height(6.dp))
            Surface(color = AshuWarningContainer, shape = RoundedCornerShape(12.dp)) {
                Text(modelNotice, Modifier.padding(10.dp), fontSize = 12.sp, color = AshuOnBackground.copy(alpha = 0.8f))
            }
        }
        Spacer(Modifier.height(6.dp))

        // The avatar has its own shelf. The message list starts below it, so
        // the chibi never shares a bubble's bounding box.
        Box(Modifier.fillMaxWidth().height(92.dp)) {
            ChibiAshu(
                mood = mood,
                hairstyle = hairstyle,
                animationAction = animation,
                outfitTop = outfitTop,
                reducedMotion = reducedMotion,
                waiting = waiting,
                listening = listening,
                reacting = reacting,
                speaking = speaking,
                modifier = Modifier.align(Alignment.BottomEnd).size(88.dp).alpha(0.98f),
                onTap = {
                    val states = listOf("happy", "curious", "annoyed", "thinking", "calm")
                    val next = states[(states.indexOf(mood).coerceAtLeast(0) + 1) % states.size]
                    mood = next
                    onMoodChange(next)
                },
            )
        }

        LazyColumn(
            Modifier.weight(1f).fillMaxWidth(),
            contentPadding = PaddingValues(top = 4.dp, bottom = 12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            items(messages) { message ->
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = if (message.fromAshu) Arrangement.Start else Arrangement.End,
                ) {
                    Column(horizontalAlignment = if (message.fromAshu) Alignment.Start else Alignment.End) {
                        Surface(
                            color = if (message.fromAshu) AshuTertiaryContainer else colorScheme.surface,
                            shape = RoundedCornerShape(20.dp), shadowElevation = 1.dp,
                        ) {
                            Text(message.text, Modifier.padding(horizontal = 15.dp, vertical = 11.dp), color = colorScheme.onSurface)
                        }
                        if (message.fromAshu && message.origin.isNotBlank()) OriginTag(message.origin)
                    }
                }
            }
            if (thinking) {
                item {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Start) {
                        Surface(color = AshuTertiaryContainer.copy(alpha = 0.7f), shape = RoundedCornerShape(20.dp)) {
                            Text("···", Modifier.padding(horizontal = 15.dp, vertical = 11.dp), color = colorScheme.onSurface)
                        }
                    }
                }
            }
            if (pendingId.isNotBlank()) {
                item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = AshuErrorContainer),
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Column(Modifier.padding(14.dp)) {
                            Text("Ashu wants to do something", fontWeight = FontWeight.Bold)
                            Text(pendingDescription, fontSize = 13.sp)
                            Spacer(Modifier.height(8.dp))
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Button(onClick = {
                                    scope.launch {
                                        val text = withContext(Dispatchers.IO) {
                                            runCatching { AshuApi(baseUrl).confirm(pendingId) }.getOrDefault("")
                                        }
                                        if (text.isNotBlank()) messages += ChatMessage(true, text, origin)
                                        pendingId = ""
                                        pendingDescription = ""
                                    }
                                }) { Text("Confirm") }
                                OutlinedButton(onClick = {
                                    scope.launch {
                                        val text = withContext(Dispatchers.IO) {
                                            runCatching { AshuApi(baseUrl).cancel(pendingId) }.getOrDefault("")
                                        }
                                        if (text.isNotBlank()) messages += ChatMessage(true, text, origin)
                                        pendingId = ""
                                        pendingDescription = ""
                                    }
                                }) { Text("Cancel") }
                            }
                        }
                    }
                }
            }
        }

        Row(verticalAlignment = Alignment.Bottom) {
            OutlinedTextField(
                value = if (listening && partial.isNotBlank()) partial else input,
                onValueChange = { input = it },
                placeholder = { Text(if (listening) "Listening…" else "Ashu tho matladu…") },
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(20.dp),
                maxLines = 4,
            )
            Spacer(Modifier.width(6.dp))
            FilledTonalIconButton(onClick = {
                if (!voiceEnabled) return@FilledTonalIconButton
                if (listening) {
                    voice.stopListening()
                    listening = false
                    partial = ""
                    return@FilledTonalIconButton
                }
                listening = true
                partial = ""
                voice.startListening(object : AshuVoice.SttListener {
                    override fun onPartial(text: String) { partial = text }
                    override fun onFinal(text: String) {
                        listening = false
                        partial = ""
                        if (text.isNotBlank()) scope.launch { send(text) }
                    }
                    override fun onError(message: String) {
                        listening = false
                        partial = ""
                        if (message.isNotBlank()) messages += ChatMessage(true, "$message", "rule_based")
                    }
                    override fun onState(state: AshuVoice.VoiceState) {}
                })
            }) { Text(if (listening) "■" else Icons.Default.Mic, fontSize = 16.sp) }
            Spacer(Modifier.width(6.dp))
            FilledTonalIconButton(onClick = { voice.interrupt(); speaking = false }) {
                Text(if (speaking) Icons.Default.Stop else Icons.Default.VolumeUp, fontSize = 15.sp)
            }
            Spacer(Modifier.width(6.dp))
            Button(
                onClick = {
                    scope.launch {
                        val text = input
                        input = ""
                        send(text)
                    }
                },
                modifier = Modifier.size(50.dp),
                contentPadding = PaddingValues(0.dp),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(containerColor = AshuTertiary),
            ) { Text(Icons.Default.Send, fontSize = 18.sp) }
        }
    }
}

// ---------------------------------------------------------------------------
// Memory dashboard
// ---------------------------------------------------------------------------
@Composable
private fun MemoryScreen(baseUrl: String) {
    val scope = rememberCoroutineScope()
    var memoryJson by remember { mutableStateOf(JSONArray()) }
    var activityJson by remember { mutableStateOf(JSONArray()) }
    var query by remember { mutableStateOf("") }
    var newFact by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("Loading local memory…") }
    var editingId by remember { mutableIntStateOf(-1) }
    var editingText by remember { mutableStateOf("") }

    fun reload(q: String = "") {
        scope.launch {
            withContext(Dispatchers.IO) {
                runCatching {
                    memoryJson = AshuApi(baseUrl).memoryAll(q)
                    activityJson = AshuApi(baseUrl).activity()
                    status = "Local memory connected"
                }.onFailure { status = "Bridge unavailable" }
            }
        }
    }
    LaunchedEffect(baseUrl) { reload() }

Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)) {
        Text("Ashu's memory", fontSize = 25.sp, fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
        Text("Local-first. Everything here is stored on this device.", color = colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(10.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(query, { query = it }, label = { Text("Search memories") }, modifier = Modifier.weight(1f), singleLine = true)
            Spacer(Modifier.width(6.dp))
            Button(onClick = { reload(query) }) { Text("Search") }
        }
        Spacer(Modifier.height(8.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(newFact, { newFact = it }, label = { Text("Add a memory") }, modifier = Modifier.weight(1f))
            Spacer(Modifier.width(6.dp))
            Button(onClick = {
                val fact = newFact.trim()
                if (fact.isBlank()) return@Button
                scope.launch {
                    withContext(Dispatchers.IO) { runCatching { AshuApi(baseUrl).addMemory(fact, "user_note", false) } }
                    newFact = ""
                    reload(query)
                }
            }) { Text("Add") }
        }
        Spacer(Modifier.height(10.dp))
        Text(status, fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(6.dp))

        for (i in 0 until memoryJson.length()) {
            val obj = memoryJson.optJSONObject(i) ?: continue
            val id = obj.optInt("id", -1)
            Card(Modifier.fillMaxWidth().padding(vertical = 4.dp), colors = CardDefaults.cardColors(containerColor = colorScheme.surface)) {
                Column(Modifier.padding(12.dp)) {
                    if (editingId == id) {
                        Text("Edit memory", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = AshuTertiary)
                        Spacer(Modifier.height(4.dp))
                        OutlinedTextField(editingText, { editingText = it }, modifier = Modifier.fillMaxWidth())
                    } else {
                        Text(obj.optString("fact"), fontWeight = FontWeight.SemiBold, color = colorScheme.onSurface)
                    }
                    Text(
                        "[${obj.optString("category")}] · ${obj.optString("memory_type")} · conf ${"%.2f".format(obj.optDouble("confidence", 1.0))}",
                        fontSize = 11.sp, color = colorScheme.onSurfaceVariant,
                    )
                    obj.optString("created_at").take(10).let { if (it.isNotBlank()) Text(it, fontSize = 11.sp, color = colorScheme.onSurfaceVariant) }
                    Spacer(Modifier.height(4.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        if (editingId == id) {
                            Button(onClick = {
                                val fact = editingText.trim()
                                if (fact.isBlank()) return@Button
                                scope.launch {
                                    withContext(Dispatchers.IO) {
                                        runCatching { AshuApi(baseUrl).updateMemory(id, fact, obj.optString("category"), obj.optBoolean("pinned")) }
                                    }
                                    editingId = -1
                                    reload(query)
                                }
                            }) { Text("Save") }
                            OutlinedButton(onClick = { editingId = -1 }) { Text("Cancel") }
                        } else {
                            OutlinedButton(onClick = { editingId = id; editingText = obj.optString("fact") }) { Text("Edit", fontSize = 12.sp) }
                            OutlinedButton(onClick = {
                                scope.launch {
                                    withContext(Dispatchers.IO) {
                                        runCatching { AshuApi(baseUrl).updateMemory(id, obj.optString("fact"), obj.optString("category"), !obj.optBoolean("pinned")) }
                                    }
                                    reload(query)
                                }
                            }) { Text(if (obj.optBoolean("pinned")) "Unpin" else "Pin", fontSize = 12.sp) }
                            OutlinedButton(onClick = {
                                scope.launch {
                                    withContext(Dispatchers.IO) { runCatching { AshuApi(baseUrl).deleteMemory(id) } }
                                    reload(query)
                                }
                            }) { Text("Delete", fontSize = 12.sp) }
                        }
                    }
                }
            }
        }

        Spacer(Modifier.height(12.dp))
        Button(onClick = {
            scope.launch {
                withContext(Dispatchers.IO) { runCatching { AshuApi(baseUrl).deleteAllMemories() } }
                reload(query)
            }
        }, colors = ButtonDefaults.buttonColors(containerColor = AshuError)) { Text("Delete all memories") }

        Spacer(Modifier.height(18.dp))
        Text("Activity history", fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
        Text("Everything Ashu did, transparently.", fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(6.dp))
        for (i in 0 until activityJson.length()) {
            val a = activityJson.optJSONObject(i) ?: continue
            Text("• [${a.optString("kind")}] ${a.optString("name")} — ${a.optString("detail").take(70)}", fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
        }
        Spacer(Modifier.height(10.dp))
        Text("Ashu avoids saving passwords, OTPs and API keys automatically.", fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
    }
}

// ---------------------------------------------------------------------------
// Model management
// ---------------------------------------------------------------------------
@Composable
private fun ModelScreen(baseUrl: String) {
    val scope = rememberCoroutineScope()
    var statusJson by remember { mutableStateOf(JSONObject()) }
    var registry by remember { mutableStateOf(JSONArray()) }
    var importPath by remember { mutableStateOf("") }
    var message by remember { mutableStateOf("") }

    fun reload() {
        scope.launch {
            withContext(Dispatchers.IO) {
                runCatching {
                    statusJson = AshuApi(baseUrl).modelStatus()
                    registry = AshuApi(baseUrl).modelRegistry()
                }
            }
        }
    }
    LaunchedEffect(baseUrl) { reload() }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)) {
        Text("Local model", fontSize = 25.sp, fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
        Text("Balanced quantized model, ~2–4 GB.", color = colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(10.dp))

        val usable = statusJson.optBoolean("usable", false)
        Card(colors = CardDefaults.cardColors(containerColor = if (usable) AshuSuccessContainer else AshuTertiaryContainer), modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp)) {
                Text(if (usable) "Local model ready" else "No local model installed", fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
                Text(statusJson.optString("name", "-"), fontSize = 13.sp, color = colorScheme.onSurfaceVariant)
                if (statusJson.optString("reason").isNotBlank()) Text(statusJson.optString("reason"), fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
                Text("Size: ${statusJson.optDouble("size_mb", 0.0)} MB · Free: ${statusJson.optInt("disk_free_mb", 0)} MB", fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
                Text("Active origin: ${statusJson.optString("active_origin", "fallback")}", fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
            }
        }

        Spacer(Modifier.height(10.dp))
        Text("Import your own model (.gguf)", fontWeight = FontWeight.SemiBold, color = colorScheme.onSurface)
        OutlinedTextField(importPath, { importPath = it }, label = { Text("/storage/emulated/0/Download/model.gguf") }, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(6.dp))
        Button(onClick = {
            val path = importPath.trim()
            if (path.isBlank()) { message = "Enter the full path to a .gguf file first."; return@Button }
            scope.launch {
                val result = withContext(Dispatchers.IO) {
                    runCatching { AshuApi(baseUrl).importModel(path) }.getOrNull()
                }
                message = when {
                    result == null -> "Bridge unavailable."
                    result.optBoolean("usable", false) -> "Imported ${result.optString("name")} successfully."
                    else -> result.optString("reason", "Import failed.")
                }
                reload()
            }
        }) { Text("Import") }
        if (message.isNotBlank()) Text(message, fontSize = 12.sp, color = colorScheme.onSurfaceVariant)

        Spacer(Modifier.height(14.dp))
        Text("Recommended models (current GGUF options)", fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
        if (registry.length() == 0) {
            registry = JSONArray("""[
              {"name":"Qwen3-4B Instruct (Q4_K_M)","approx_size_gb":2.50,"quant":"Q4_K_M","languages":["te","en","hi"],"notes":"Official GGUF; strong multilingual and multi-turn balance."},
              {"name":"Qwen3-1.7B (Q4_K_M)","approx_size_gb":1.28,"quant":"Q4_K_M","languages":["te","en","hi"],"notes":"Lightweight GGUF for smaller devices."},
              {"name":"Gemma 3n E2B (Q8_0)","approx_size_gb":4.79,"quant":"Q8_0","languages":["te","en","hi"],"notes":"On-device focused; heavier."}
            ]""")
        }
        for (i in 0 until registry.length()) {
            val m = registry.optJSONObject(i) ?: continue
            Card(Modifier.fillMaxWidth().padding(vertical = 4.dp), colors = CardDefaults.cardColors(containerColor = AshuSecondaryContainer)) {
                Column(Modifier.padding(12.dp)) {
                    Text(m.optString("name"), fontWeight = FontWeight.SemiBold, color = colorScheme.onSurface)
                    Text("${m.optDouble("approx_size_gb", 0.0)} GB · ${m.optString("quant")} · langs: " +
                        (m.optJSONArray("languages")?.let { arr ->
                            (0 until arr.length()).joinToString { arr.optString(it) }
                        } ?: ""), fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
                    Text(m.optString("notes"), fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
                }
            }
        }
        Spacer(Modifier.height(10.dp))
        Text("Ashu works without a model (offline fallback mode) and never pretends a model is running when it isn't.", fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
    }
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
@Composable
private fun SettingsScreen(
    baseUrl: String, voiceEnabled: Boolean, autoSpeak: Boolean, reducedMotion: Boolean,
    onSave: (String, Boolean, Boolean, Boolean) -> Unit,
) {
    val context = LocalContext.current
    var url by remember { mutableStateOf(baseUrl) }
    var voice by remember { mutableStateOf(voiceEnabled) }
    var speak by remember { mutableStateOf(autoSpeak) }
    var motion by remember { mutableStateOf(reducedMotion) }
    var proactive by remember { mutableStateOf(true) }
    var dnd by remember { mutableStateOf(false) }
    var daily by remember { mutableFloatStateOf(6f) }
    var cloud by remember { mutableStateOf(false) }
    var confirmTools by remember { mutableStateOf(true) }
    val prefs = remember { context.getSharedPreferences("ashu_prefs", Context.MODE_PRIVATE) }
    var floatingAshu by remember {
        mutableStateOf(prefs.getBoolean(FloatingCompanionPermission.PREF_ENABLED, false))
    }
    var showOverlayPermissionNote by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp)) {
        Text("Settings", fontSize = 25.sp, fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
        Spacer(Modifier.height(10.dp))
        SwitchRow("Ashu voice", voice) { voice = it }
        SwitchRow("Auto-speak replies", speak) { speak = it }
        SwitchRow("Reduced motion", motion) { motion = it }
        SwitchRow("Proactive conversation", proactive) { proactive = it }
        // v0.9 Part 8 -- Floating Ashu. Infrastructure only, off by default;
        // turning it on here is the one and only place SYSTEM_ALERT_WINDOW
        // is ever requested, and only via Android's own settings screen.
        SwitchRow("Floating Ashu (companion outside the app)", floatingAshu) { enabled ->
            floatingAshu = enabled
            prefs.edit().putBoolean(FloatingCompanionPermission.PREF_ENABLED, enabled).apply()
            if (enabled) {
                if (FloatingCompanionPermission.canDrawOverlays(context)) {
                    FloatingCompanionPermission.start(context)
                } else {
                    showOverlayPermissionNote = true
                    FloatingCompanionPermission.request(context)
                }
            } else {
                FloatingCompanionPermission.stop(context)
            }
        }
        if (showOverlayPermissionNote) {
            Text(
                "Grant \"Display over other apps\" for Ashu, then come back here -- Floating Ashu starts as soon as it's allowed.",
                fontSize = 12.sp, color = colorScheme.onSurfaceVariant, modifier = Modifier.padding(start = 4.dp, bottom = 6.dp),
            )
        }
        // Coming back from the "Display over other apps" screen doesn't
        // re-run this composable on its own -- catch the grant on resume.
        val lifecycleOwner = androidx.compose.ui.platform.LocalLifecycleOwner.current
        DisposableEffect(lifecycleOwner) {
            val observer = androidx.lifecycle.LifecycleEventObserver { _, event ->
                if (event == androidx.lifecycle.Lifecycle.Event.ON_RESUME &&
                    floatingAshu && FloatingCompanionPermission.canDrawOverlays(context)
                ) {
                    showOverlayPermissionNote = false
                    FloatingCompanionPermission.start(context)
                }
            }
            lifecycleOwner.lifecycle.addObserver(observer)
            onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
        }
        SwitchRow("Do-not-disturb window", dnd) { dnd = it }
        SwitchRow("Cloud fallback (off by default)", cloud) { cloud = it }
        SwitchRow("Ask before risky actions", confirmTools) { confirmTools = it }
        Spacer(Modifier.height(6.dp))
        Text("Daily initiation limit: ${daily.toInt()}", fontWeight = FontWeight.SemiBold, color = colorScheme.onSurface)
        Slider(daily, { daily = it }, valueRange = 0f..12f, steps = 11)

        Spacer(Modifier.height(12.dp))
        Text("Local bridge", fontWeight = FontWeight.SemiBold, color = colorScheme.onSurface)
        OutlinedTextField(url, { url = it }, singleLine = true, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(8.dp))
        Button(onClick = {
            kotlinx.coroutines.CoroutineScope(Dispatchers.IO).launch {
                runCatching {
                    AshuApi(url.trim()).preferences(mapOf(
                        "voice_enabled" to voice, "auto_speak" to speak, "reduced_motion" to motion,
                        "proactive_enabled" to proactive, "dnd_enabled" to dnd,
                        "daily_initiation_limit" to daily.toInt(),
                        "cloud_fallback_enabled" to cloud,
                        "tool_confirmation_required" to confirmTools,
                    ))
                }
            }
            onSave(url.trim(), voice, speak, motion)
            if (floatingAshu && FloatingCompanionPermission.canDrawOverlays(context)) {
                context.startService(
                    Intent(context, FloatingCompanionService::class.java)
                        .setAction(FloatingCompanionService.ACTION_SET_REDUCED_MOTION)
                        .putExtra(FloatingCompanionService.EXTRA_REDUCED_MOTION, motion),
                )
            }
        }, Modifier.fillMaxWidth()) { Text("Save") }

        Spacer(Modifier.height(12.dp))
        OutlinedButton(onClick = { PhonePermissions.openAppSettings(context) }, Modifier.fillMaxWidth()) { Text("App permissions") }
        Spacer(Modifier.height(6.dp))
        OutlinedButton(onClick = { PhonePermissions.openNotificationListenerSettings(context) }, Modifier.fillMaxWidth()) { Text("Notification access") }
        Spacer(Modifier.height(6.dp))
        OutlinedButton(onClick = { DeviceTools.openUsageAccessSettings(context) }, Modifier.fillMaxWidth()) { Text("App usage access") }
        Spacer(Modifier.height(10.dp))
        Text("Ashu is not flirty by design, never guilt-trips and never encourages unhealthy dependence.", fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
    }
}

// ---------------------------------------------------------------------------
// Privacy
// ---------------------------------------------------------------------------
@Composable
private fun PrivacyScreen(baseUrl: String) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf("") }
    var confirmWipe by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp)) {
        Text("Privacy & data", fontSize = 25.sp, fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
        Spacer(Modifier.height(8.dp))
        Card(colors = CardDefaults.cardColors(containerColor = AshuSuccessContainer), modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp)) {
                Text("Local-first by default", fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
                Text("Memories, personality state and activity history live on this device. Cloud fallback is off by default and clearly labelled when used.", fontSize = 13.sp, color = colorScheme.onSurfaceVariant)
            }
        }
        Spacer(Modifier.height(12.dp))
        Button(onClick = {
            scope.launch {
                val data = withContext(Dispatchers.IO) { runCatching { AshuApi(baseUrl).exportData() }.getOrNull() }
                status = if (data != null) "Exported ${data.optJSONArray("facts")?.length() ?: 0} memories (see bridge logs)" else "Bridge unavailable"
            }
        }, Modifier.fillMaxWidth()) { Text("Export my data") }
        Spacer(Modifier.height(8.dp))
        if (!confirmWipe) {
            OutlinedButton(onClick = { confirmWipe = true }, Modifier.fillMaxWidth()) { Text("Delete everything Ashu knows") }
        } else {
            Card(colors = CardDefaults.cardColors(containerColor = AshuErrorContainer), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp)) {
                    Text("This permanently deletes all memories, people, goals and activity history. It cannot be undone.", fontSize = 13.sp, color = colorScheme.onSurface)
                    Spacer(Modifier.height(8.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = {
                            scope.launch {
                                withContext(Dispatchers.IO) { runCatching { AshuApi(baseUrl).wipeData() } }
                                status = "All local data deleted."
                                confirmWipe = false
                            }
                        }, colors = ButtonDefaults.buttonColors(containerColor = AshuError)) { Text("Yes, delete all") }
                        OutlinedButton(onClick = { confirmWipe = false }) { Text("Cancel") }
                    }
                }
            }
        }
        if (status.isNotBlank()) {
            Spacer(Modifier.height(10.dp))
            Text(status, fontSize = 13.sp, color = colorScheme.onSurface)
        }
        Spacer(Modifier.height(14.dp))
        OutlinedButton(onClick = { PhonePermissions.openAppSettings(context) }, Modifier.fillMaxWidth()) { Text("Revoke permissions in Android settings") }
        Spacer(Modifier.height(14.dp))
        Text("Ashu never records audio secretly, never captures the screen, and never sends files or memories to a cloud provider without your explicit setting.", fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
    }
}

// ---------------------------------------------------------------------------
// Small shared components
// ---------------------------------------------------------------------------
@Composable
private fun SwitchRow(title: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(title, Modifier.weight(1f))
        Switch(checked, onChange)
    }
}

@Composable
private fun PermissionCard(title: String, subtitle: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Card(Modifier.fillMaxWidth().padding(vertical = 4.dp), colors = CardDefaults.cardColors(containerColor = colorScheme.surface)) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.SemiBold, color = colorScheme.onSurface)
                Text(subtitle, fontSize = 12.sp, color = colorScheme.onSurfaceVariant)
            }
            Switch(checked, onChange)
        }
    }
}

@Composable
private fun Chip(text: String, color: Color) {
    Surface(color = color, shape = RoundedCornerShape(50)) {
        Text(text, Modifier.padding(horizontal = 10.dp, vertical = 6.dp), fontSize = 11.sp, color = colorScheme.onSurface)
    }
}

@Composable
private fun OriginTag(origin: String) {
    Surface(
        color = if (origin == "local") AshuSuccessContainer else AshuSecondaryContainer,
        shape = RoundedCornerShape(999.dp)
    ) {
        Text("● ${originLabel(origin)}", Modifier.padding(horizontal = 8.dp, vertical = 4.dp), fontSize = 10.sp, fontWeight = FontWeight.Bold, color = colorScheme.onSurface)
    }
}

private fun originHelp(origin: String): String = when (origin) {
    "local" -> "Generated by the local model/brain on this device."
    "rule_based" -> "Generated by Ashu's offline rule brain; no language model was used."
    "cloud" -> "Generated through the optional cloud fallback you enabled."
    else -> "Reply origin: $origin"
}

private fun originLabel(origin: String): String = when (origin) {
    "local" -> "local model"
    "cloud" -> "cloud"
    "fallback" -> "offline fallback"
    "mock" -> "mock (dev)"
    "rule_based" -> "rules"
    else -> origin
}

private fun inferFallbackMood(text: String): String {
    val lower = text.lowercase()
    return when {
        lower.contains("jealous") || lower.contains("chatgpt") -> "jealous"
        lower.contains("bore") -> "playful"
        lower.contains("nidra") || lower.contains("sleep") -> "sleepy"
        lower.contains("tension") || lower.contains("sad") -> "caring"
        else -> "calm"
    }
}

private fun fallbackReply(text: String): String {
    val lower = text.lowercase()
    return when {
        lower.contains("bore") -> "Malli bore aa? 😄 Natho konchem time spend cheyyachu kada."
        lower.contains("hello") || lower.contains("hey") -> "Heyyy 😌 Nenu ikkade unna. Cheppu."
        lower.contains("em chest") || lower.contains("em chestunav") -> "Em ledu ra babu, ninnu wait chestunna 😄"
        lower.contains("ashu") -> "Cheppu ra. Full attention ikkade 👀"
        lower.contains("thank") -> "Aww sare sare, formal avvaku 😭❤️"
        else -> "Ikkada offline mode lo unna. Bridge connect chesaka inka manchi ga matladtha 😌"
    }
}
