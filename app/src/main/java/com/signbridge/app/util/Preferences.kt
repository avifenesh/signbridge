package com.signbridge.app.util

import android.content.Context
import android.content.SharedPreferences

/**
 * Simple SharedPreferences wrapper for app settings.
 * No account — all data stored locally on device.
 */
class Preferences(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("signbridge_prefs", Context.MODE_PRIVATE)

    var isSetupComplete: Boolean
        get() = prefs.getBoolean(KEY_SETUP_COMPLETE, false)
        set(value) = prefs.edit().putBoolean(KEY_SETUP_COMPLETE, value).apply()

    var isModelsDownloaded: Boolean
        get() = prefs.getBoolean(KEY_MODELS_DOWNLOADED, false)
        set(value) = prefs.edit().putBoolean(KEY_MODELS_DOWNLOADED, value).apply()

    var sttProvider: String
        get() = prefs.getString(KEY_STT_PROVIDER, STT_VOSK) ?: STT_VOSK
        set(value) = prefs.edit().putString(KEY_STT_PROVIDER, value).apply()

    var cloudSttApiKey: String
        get() = prefs.getString(KEY_CLOUD_STT_KEY, "") ?: ""
        set(value) = prefs.edit().putString(KEY_CLOUD_STT_KEY, value).apply()

    var avatarSizePercent: Int
        get() = prefs.getInt(KEY_AVATAR_SIZE, 80)
        set(value) = prefs.edit().putInt(KEY_AVATAR_SIZE, value).apply()

    var subtitleFontSizeSp: Int
        get() = prefs.getInt(KEY_SUBTITLE_FONT_SIZE, 16)
        set(value) = prefs.edit().putInt(KEY_SUBTITLE_FONT_SIZE, value).apply()

    var showConfidenceIndicator: Boolean
        get() = prefs.getBoolean(KEY_SHOW_CONFIDENCE, true)
        set(value) = prefs.edit().putBoolean(KEY_SHOW_CONFIDENCE, value).apply()

    var fallbackMode: String
        get() = prefs.getString(KEY_FALLBACK_MODE, FALLBACK_AUTO) ?: FALLBACK_AUTO
        set(value) = prefs.edit().putString(KEY_FALLBACK_MODE, value).apply()

    var isBatterySaver: Boolean
        get() = prefs.getBoolean(KEY_BATTERY_SAVER, false)
        set(value) = prefs.edit().putBoolean(KEY_BATTERY_SAVER, value).apply()

    var alwaysReadyEnabled: Boolean
        get() = prefs.getBoolean(KEY_ALWAYS_READY, false)
        set(value) = prefs.edit().putBoolean(KEY_ALWAYS_READY, value).apply()

    /** Path B relay server URL (e.g., "http://192.168.1.100:8080") */
    var relayUrl: String
        get() = prefs.getString(KEY_RELAY_URL, "") ?: ""
        set(value) = prefs.edit().putString(KEY_RELAY_URL, value).apply()

    /** Use Path B relay — default true since AudioPlaybackCapture cannot capture voice calls */
    var useRelay: Boolean
        get() = prefs.getBoolean(KEY_USE_RELAY, true)
        set(value) = prefs.edit().putBoolean(KEY_USE_RELAY, value).apply()

    var quickPhrases: List<String>
        get() {
            val raw = prefs.getString(KEY_QUICK_PHRASES, null) ?: return DEFAULT_QUICK_PHRASES
            return raw.split(PHRASE_SEPARATOR)
        }
        set(value) = prefs.edit()
            .putString(KEY_QUICK_PHRASES, value.joinToString(PHRASE_SEPARATOR))
            .apply()

    companion object {
        private const val KEY_SETUP_COMPLETE = "setup_complete"
        private const val KEY_MODELS_DOWNLOADED = "models_downloaded"
        private const val KEY_STT_PROVIDER = "stt_provider"
        private const val KEY_CLOUD_STT_KEY = "cloud_stt_key"
        private const val KEY_AVATAR_SIZE = "avatar_size"
        private const val KEY_SUBTITLE_FONT_SIZE = "subtitle_font_size"
        private const val KEY_SHOW_CONFIDENCE = "show_confidence"
        private const val KEY_FALLBACK_MODE = "fallback_mode"
        private const val KEY_BATTERY_SAVER = "battery_saver"
        private const val KEY_ALWAYS_READY = "always_ready"
        private const val KEY_RELAY_URL = "relay_url"
        private const val KEY_USE_RELAY = "use_relay"
        private const val KEY_QUICK_PHRASES = "quick_phrases"

        const val STT_VOSK = "vosk"
        const val STT_GROQ = "groq"
        const val STT_DEEPGRAM = "deepgram"
        const val STT_GOOGLE = "google"

        const val FALLBACK_AUTO = "auto"
        const val FALLBACK_ALWAYS_CAPTIONS = "always_captions"
        const val FALLBACK_ALWAYS_AVATAR = "always_avatar"

        private const val PHRASE_SEPARATOR = "|||"

        val DEFAULT_QUICK_PHRASES = listOf(
            "Yes",
            "No",
            "One moment",
            "Can you repeat that?",
            "I'll text you"
        )
    }
}
