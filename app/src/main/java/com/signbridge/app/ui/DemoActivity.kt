package com.signbridge.app.ui

import android.graphics.Color
import android.graphics.PixelFormat
import android.opengl.GLSurfaceView
import android.os.Bundle
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.signbridge.app.R
import com.signbridge.app.model.*
import com.signbridge.app.renderer.AvatarRenderer
import com.signbridge.app.translation.AslTranslationEngine
import com.signbridge.app.translation.SignDictionary
import com.signbridge.app.util.Preferences
import kotlinx.coroutines.*

/**
 * Demo mode — no relay, no Telegram, no credentials needed.
 *
 * Type any sentence → tap Sign → avatar animates ASL signs.
 * Tests the full translation → dictionary → renderer pipeline on a real device.
 */
class DemoActivity : AppCompatActivity() {

    private lateinit var glSurfaceView: GLSurfaceView
    private lateinit var avatarRenderer: AvatarRenderer
    private lateinit var translationEngine: AslTranslationEngine
    private lateinit var dictionary: SignDictionary
    private lateinit var inputField: EditText
    private lateinit var signButton: Button
    private lateinit var statusText: TextView
    private lateinit var glossText: TextView
    private lateinit var confidenceBar: View

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        translationEngine = AslTranslationEngine(this)
        dictionary = SignDictionary(this)

        // Initialize on background thread
        lifecycleScope.launch(Dispatchers.IO) {
            translationEngine.initialize()
            dictionary.load()
            withContext(Dispatchers.Main) {
                statusText.text = "Ready — type a sentence and tap Sign"
                signButton.isEnabled = true
            }
        }

        buildUI()
    }

    private fun buildUI() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(15, 15, 20))
        }

        // ── Avatar view (top 60% of screen) ──────────────────────────
        avatarRenderer = AvatarRenderer(this)
        glSurfaceView = GLSurfaceView(this).apply {
            setEGLContextClientVersion(2)
            setEGLConfigChooser(8, 8, 8, 8, 16, 0)
            holder.setFormat(PixelFormat.TRANSLUCENT)
            setZOrderOnTop(false)
            setRenderer(avatarRenderer)
            renderMode = GLSurfaceView.RENDERMODE_CONTINUOUSLY
        }
        root.addView(glSurfaceView, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 0, 6f
        ))

        // ── Info panel ────────────────────────────────────────────────
        val infoPanel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(20, 20, 30))
            setPadding(24, 16, 24, 8)
        }

        // Confidence bar
        confidenceBar = View(this).apply {
            setBackgroundColor(Color.GRAY)
        }
        infoPanel.addView(confidenceBar, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 6
        ).apply { bottomMargin = 12 })

        // ASL gloss output
        glossText = TextView(this).apply {
            text = ""
            setTextColor(Color.rgb(100, 200, 100))
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f)
            setPadding(0, 0, 0, 4)
        }
        infoPanel.addView(glossText)

        // Status
        statusText = TextView(this).apply {
            text = "Initializing..."
            setTextColor(Color.rgb(160, 160, 180))
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 12f)
        }
        infoPanel.addView(statusText)

        root.addView(infoPanel, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ))

        // ── Quick phrase chips ─────────────────────────────────────────
        val chipScroll = HorizontalScrollView(this).apply {
            setBackgroundColor(Color.rgb(15, 15, 20))
            setPadding(12, 8, 12, 8)
        }
        val chipRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        val quickPhrases = listOf(
            "hello", "how are you", "what is your name",
            "thank you", "I don't understand", "nice to meet you",
            "where is the bathroom", "I want pizza", "I gave you the book",
            "goodbye"
        )
        for (phrase in quickPhrases) {
            val chip = TextView(this).apply {
                text = phrase
                setTextColor(Color.WHITE)
                setBackgroundColor(Color.rgb(40, 60, 90))
                setPadding(20, 10, 20, 10)
                setTextSize(TypedValue.COMPLEX_UNIT_SP, 12f)
                setOnClickListener {
                    inputField.setText(phrase)
                    signSentence(phrase)
                }
            }
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { marginEnd = 8 }
            chipRow.addView(chip, params)
        }
        chipScroll.addView(chipRow)
        root.addView(chipScroll, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ))

        // ── Input row ─────────────────────────────────────────────────
        val inputRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setBackgroundColor(Color.rgb(25, 25, 35))
            setPadding(16, 12, 16, 12)
            gravity = Gravity.CENTER_VERTICAL
        }

        inputField = EditText(this).apply {
            hint = "Type a sentence..."
            setHintTextColor(Color.GRAY)
            setTextColor(Color.WHITE)
            setBackgroundColor(Color.rgb(35, 35, 50))
            setPadding(20, 16, 20, 16)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f)
            imeOptions = EditorInfo.IME_ACTION_DONE
            setSingleLine(true)
            setOnEditorActionListener { _, actionId, _ ->
                if (actionId == EditorInfo.IME_ACTION_DONE) {
                    signSentence(text.toString())
                    true
                } else false
            }
        }
        inputRow.addView(inputField, LinearLayout.LayoutParams(
            0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f
        ).apply { marginEnd = 12 })

        signButton = Button(this).apply {
            text = "Sign"
            isEnabled = false
            setBackgroundColor(Color.rgb(21, 101, 192))
            setTextColor(Color.WHITE)
            setOnClickListener { signSentence(inputField.text.toString()) }
        }
        inputRow.addView(signButton, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ))

        root.addView(inputRow, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ))

        setContentView(root)
    }

    private fun signSentence(sentence: String) {
        val trimmed = sentence.trim()
        if (trimmed.isBlank()) return

        // Hide keyboard
        val imm = getSystemService(InputMethodManager::class.java)
        imm.hideSoftInputFromWindow(inputField.windowToken, 0)

        statusText.text = "Translating..."
        signButton.isEnabled = false

        lifecycleScope.launch {
            try {
                // Translate
                val translation = withContext(Dispatchers.Default) {
                    translationEngine.translate(trimmed)
                }

                if (translation == null) {
                    statusText.text = "Translation failed"
                    signButton.isEnabled = true
                    return@launch
                }

                // Look up signs
                val signEntries = withContext(Dispatchers.Default) {
                    dictionary.lookupGloss(translation.glossTokens)
                }

                val sequence = SignSequence(
                    english = trimmed,
                    pipelineConfidence = translation.confidence,
                    entries = signEntries
                )

                // Update UI
                val glossStr = translation.glossTokens.joinToString(" → ")
                glossText.text = "ASL: $glossStr"

                val confColor = when (ConfidenceLevel.from(translation.confidence)) {
                    ConfidenceLevel.HIGH -> Color.rgb(50, 200, 50)
                    ConfidenceLevel.MEDIUM -> Color.rgb(220, 180, 0)
                    ConfidenceLevel.LOW -> Color.rgb(220, 60, 60)
                }
                confidenceBar.setBackgroundColor(confColor)

                val methodLabel = when (translation.method) {
                    com.signbridge.app.model.TranslationMethod.PATTERN_HASH -> "pattern match"
                    com.signbridge.app.model.TranslationMethod.VECTOR_SIMILARITY -> "vector similarity"
                    else -> "grammar rules"
                }
                val signsDesc = signEntries.joinToString(" · ") { entry ->
                    when (entry) {
                        is SignEntry.Sign -> entry.gloss
                        is SignEntry.Fingerspell -> "${entry.gloss}(fs)"
                    }
                }
                statusText.text = "[$methodLabel] $signsDesc"

                // Play on renderer
                glSurfaceView.queueEvent {
                    avatarRenderer.playSignSequence(sequence, dictionary)
                }

                // Re-enable button after animation completes
                val totalDuration = signEntries.sumOf { it.durationMs + 200 }.toLong()
                delay(totalDuration + 500)
                signButton.isEnabled = true

            } catch (e: Exception) {
                statusText.text = "Error: ${e.message}"
                signButton.isEnabled = true
            }
        }
    }

    override fun onResume() {
        super.onResume()
        glSurfaceView.onResume()
    }

    override fun onPause() {
        super.onPause()
        glSurfaceView.onPause()
    }

    override fun onDestroy() {
        avatarRenderer.release()
        super.onDestroy()
    }
}
