package com.signbridge.app.settings

import android.os.Bundle
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import com.signbridge.app.util.Preferences

/**
 * Settings screen.
 *
 * - STT provider: on-device (Vosk) or cloud (Groq/Deepgram/Google + API key)
 * - Quick phrase editor
 * - Avatar size
 * - Subtitle font size
 * - Confidence indicator toggle
 * - Fallback mode
 * - Battery saver
 * - Path A/B toggle (if both available)
 */
class SettingsActivity : AppCompatActivity() {

    private lateinit var preferences: Preferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        preferences = Preferences(this)
        buildUI()
    }

    private fun buildUI() {
        val scrollView = ScrollView(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 48, 48, 48)
        }

        root.addView(sectionHeader("Speech-to-Text"))

        // STT provider selector
        val sttSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(
                this@SettingsActivity,
                android.R.layout.simple_spinner_dropdown_item,
                listOf("On-device (Vosk)", "Groq", "Deepgram", "Google")
            )
            setSelection(when (preferences.sttProvider) {
                Preferences.STT_GROQ -> 1
                Preferences.STT_DEEPGRAM -> 2
                Preferences.STT_GOOGLE -> 3
                else -> 0
            })
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>?, view: android.view.View?, pos: Int, id: Long) {
                    preferences.sttProvider = when (pos) {
                        1 -> Preferences.STT_GROQ
                        2 -> Preferences.STT_DEEPGRAM
                        3 -> Preferences.STT_GOOGLE
                        else -> Preferences.STT_VOSK
                    }
                }
                override fun onNothingSelected(parent: AdapterView<*>?) {}
            }
        }
        root.addView(sttSpinner, fieldParams())

        // Cloud API key
        val apiKeyField = EditText(this).apply {
            hint = "Cloud STT API Key (optional)"
            setText(preferences.cloudSttApiKey)
            setOnFocusChangeListener { _, hasFocus ->
                if (!hasFocus) preferences.cloudSttApiKey = text.toString()
            }
        }
        root.addView(apiKeyField, fieldParams())

        root.addView(sectionHeader("Display"))

        // Subtitle font size
        root.addView(labeledSeekBar("Subtitle font size", 10, 30, preferences.subtitleFontSizeSp) {
            preferences.subtitleFontSizeSp = it
        })

        // Avatar size
        root.addView(labeledSeekBar("Avatar size %", 40, 100, preferences.avatarSizePercent) {
            preferences.avatarSizePercent = it
        })

        // Confidence indicator
        root.addView(labeledSwitch("Show confidence indicator", preferences.showConfidenceIndicator) {
            preferences.showConfidenceIndicator = it
        })

        root.addView(sectionHeader("Performance"))

        // Battery saver
        root.addView(labeledSwitch("Battery saver (15fps)", preferences.isBatterySaver) {
            preferences.isBatterySaver = it
        })

        root.addView(sectionHeader("Fallback"))

        // Fallback mode
        val fallbackSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(
                this@SettingsActivity,
                android.R.layout.simple_spinner_dropdown_item,
                listOf("Auto", "Always captions", "Always avatar")
            )
            setSelection(when (preferences.fallbackMode) {
                Preferences.FALLBACK_ALWAYS_CAPTIONS -> 1
                Preferences.FALLBACK_ALWAYS_AVATAR -> 2
                else -> 0
            })
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>?, view: android.view.View?, pos: Int, id: Long) {
                    preferences.fallbackMode = when (pos) {
                        1 -> Preferences.FALLBACK_ALWAYS_CAPTIONS
                        2 -> Preferences.FALLBACK_ALWAYS_AVATAR
                        else -> Preferences.FALLBACK_AUTO
                    }
                }
                override fun onNothingSelected(parent: AdapterView<*>?) {}
            }
        }
        root.addView(fallbackSpinner, fieldParams())

        root.addView(sectionHeader("Path B — Relay Server"))

        // Use relay toggle
        root.addView(labeledSwitch("Use relay (Path B)", preferences.useRelay) {
            preferences.useRelay = it
        })

        // Relay URL
        val relayUrlField = EditText(this).apply {
            hint = "Relay server URL (e.g., http://192.168.1.100:8080)"
            setText(preferences.relayUrl)
            setOnFocusChangeListener { _, hasFocus ->
                if (!hasFocus) preferences.relayUrl = text.toString().trimEnd('/')
            }
        }
        root.addView(relayUrlField, fieldParams())

        scrollView.addView(root)
        setContentView(scrollView)
    }

    private fun sectionHeader(text: String) = TextView(this).apply {
        this.text = text
        textSize = 18f
        setPadding(0, 32, 0, 8)
    }

    private fun fieldParams() = LinearLayout.LayoutParams(
        LinearLayout.LayoutParams.MATCH_PARENT,
        LinearLayout.LayoutParams.WRAP_CONTENT
    ).apply { bottomMargin = 16 }

    private fun labeledSeekBar(
        label: String, min: Int, max: Int, current: Int,
        onChange: (Int) -> Unit
    ): LinearLayout {
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 8, 0, 16)
        }
        val labelView = TextView(this).apply {
            text = "$label: $current"
        }
        container.addView(labelView)

        val seekBar = SeekBar(this).apply {
            this.max = max - min
            progress = current - min
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                    val value = progress + min
                    labelView.text = "$label: $value"
                    onChange(value)
                }
                override fun onStartTrackingTouch(sb: SeekBar?) {}
                override fun onStopTrackingTouch(sb: SeekBar?) {}
            })
        }
        container.addView(seekBar)
        return container
    }

    private fun labeledSwitch(
        label: String, checked: Boolean,
        onChange: (Boolean) -> Unit
    ): Switch {
        return Switch(this).apply {
            text = label
            isChecked = checked
            setPadding(0, 8, 0, 16)
            setOnCheckedChangeListener { _, isChecked -> onChange(isChecked) }
        }
    }
}
