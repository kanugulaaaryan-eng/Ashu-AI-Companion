package com.ashu.app

import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.media.AudioManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import androidx.core.content.ContextCompat
import android.Manifest
import android.content.pm.PackageManager

/**
 * Real Android implementations of Ashu's permission-gated phone capabilities.
 *
 * Every capability is individually permission-checked and returns an explicit
 * result rather than silently doing nothing. Nothing here runs without an
 * explicit user action upstream (the chat UI shows a confirmation first when
 * `tool_confirmation_required` is on).
 *
 * Implemented with platform APIs + Intents only — no extra dependencies.
 */
object DeviceTools {

    data class Result(val ok: Boolean, val detail: String = "", val needsPermission: String = "")

    // ------------------------------------------------------------- open app
    fun openApp(context: Context, packageName: String): Result {
        val intent = context.packageManager.getLaunchIntentForPackage(packageName)
            ?: return Result(false, "App '$packageName' is not installed.")
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return try {
            context.startActivity(intent)
            Result(true, "Opened $packageName")
        } catch (e: Exception) {
            Result(false, "Could not open app: ${e.message}")
        }
    }

    // ----------------------------------------------------------- reminders
    fun setReminder(context: Context, message: String, minutes: Int): Result {
        // Opens the user's calendar/reminder app pre-filled; Ashu never writes
        // to the calendar silently.
        val start = System.currentTimeMillis() + minutes.coerceAtLeast(1) * 60_000L
        val intent = Intent(Intent.ACTION_INSERT).apply {
            data = Uri.parse("content://com.android.calendar/events")
            putExtra("title", message)
            putExtra("beginTime", start)
            putExtra("endTime", start + 60_000L)
            putExtra("hasAlarm", 1)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        return try {
            context.startActivity(intent)
            Result(true, "Reminder form opened")
        } catch (e: Exception) {
            Result(false, "No calendar/reminder app available.")
        }
    }

    // --------------------------------------------------------------- music
    fun controlMusic(context: Context, command: String): Result {
        val audio = ContextCompat.getSystemService(context, AudioManager::class.java)
            ?: return Result(false, "Audio service unavailable.")
        val key = when (command.lowercase()) {
            "play", "play_pause", "pause", "toggle" -> android.view.KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE
            "next", "skip" -> android.view.KeyEvent.KEYCODE_MEDIA_NEXT
            "previous", "prev" -> android.view.KeyEvent.KEYCODE_MEDIA_PREVIOUS
            "stop" -> android.view.KeyEvent.KEYCODE_MEDIA_STOP
            else -> return Result(false, "Unknown command: $command")
        }
        return try {
            audio.dispatchMediaKeyEvent(android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN, key))
            audio.dispatchMediaKeyEvent(android.view.KeyEvent(android.view.KeyEvent.ACTION_UP, key))
            Result(true, "Sent $command to the active media session")
        } catch (e: Exception) {
            Result(false, "Could not control media: ${e.message}")
        }
    }

    // -------------------------------------------------------- notifications
    fun hasNotificationAccess(context: Context): Boolean {
        val enabled = Settings.Secure.getString(
            context.contentResolver, "enabled_notification_listeners"
        ) ?: return false
        return enabled.contains(context.packageName)
    }

    fun readNotifications(limit: Int = 10): List<Map<String, String>> =
        AshuNotificationListener.recent(limit)

    // ----------------------------------------------------------- usage access
    fun hasUsageAccess(context: Context): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as? android.app.AppOpsManager
            val mode = try {
                appOps?.checkOpNoThrow(
                    android.app.AppOpsManager.OPSTR_GET_USAGE_STATS,
                    android.os.Process.myUid(), context.packageName
                )
            } catch (_: Exception) { null }
            mode == android.app.AppOpsManager.MODE_ALLOWED
        } else false
    }

    fun openUsageAccessSettings(context: Context) {
        val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        runCatching { context.startActivity(intent) }
    }

    fun queryUsage(context: Context, limit: Int = 10): List<Map<String, String>> {
        if (!hasUsageAccess(context)) return emptyList()
        val manager = context.getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager ?: return emptyList()
        val end = System.currentTimeMillis()
        val start = end - 24 * 60 * 60 * 1000L
        return try {
            manager.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, start, end)
                ?.sortedByDescending { it.totalTimeInForeground }
                ?.take(limit)
                ?.map { mapOf("package" to it.packageName, "foreground_ms" to it.totalTimeInForeground.toString()) }
                ?: emptyList()
        } catch (_: Exception) { emptyList() }
    }

    // ---------------------------------------------------------------- camera
    fun hasCameraPermission(context: Context): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED

    // ------------------------------------------------------------- capability
    fun capabilities(context: Context): Map<String, Any> = mapOf(
        "open_app" to true,
        "set_reminder" to true,
        "control_music" to true,
        "read_notifications" to hasNotificationAccess(context),
        "usage_access" to hasUsageAccess(context),
        "camera" to hasCameraPermission(context),
        "covert_capture" to false,
    )
}

/**
 * Notification listener the user must explicitly enable in Android settings.
 * It only holds a short in-memory ring buffer — nothing is persisted or sent.
 */
class AshuNotificationListener : NotificationListenerService() {

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        val notification = sbn ?: return
        val extras = notification.notification?.extras ?: return
        val title = extras.getCharSequence("android.title")?.toString().orEmpty()
        val text = extras.getCharSequence("android.text")?.toString().orEmpty()
        if (title.isBlank() && text.isBlank()) return
        synchronized(RECENT) {
            RECENT.add(0, mapOf("package" to notification.packageName, "title" to title, "text" to text))
            while (RECENT.size > 30) RECENT.removeAt(RECENT.size - 1)
        }
    }

    companion object {
        private val RECENT = mutableListOf<Map<String, String>>()
        fun recent(limit: Int): List<Map<String, String>> = synchronized(RECENT) {
            RECENT.take(limit).toList()
        }
    }
}
