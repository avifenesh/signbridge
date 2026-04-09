package com.signbridge.app.stt

import android.content.Context
import android.util.Log
import com.signbridge.app.model.SttResult
import com.signbridge.app.model.SttSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * On-device speech-to-text using Vosk.
 * Default STT engine — free, no API key, works offline.
 *
 * Vosk model is downloaded on first launch (~50MB).
 */
class VoskSttEngine(private val context: Context) {

    companion object {
        private const val TAG = "VoskSTT"
        private const val MODEL_DIR = "vosk-model"
        private const val SAMPLE_RATE = 16000f
    }

    private var model: Model? = null
    private var recognizer: Recognizer? = null

    val isReady: Boolean get() = model != null

    /**
     * Initialize the Vosk model from the downloaded model directory.
     * Must be called before recognizing.
     */
    suspend fun initialize(): Boolean = withContext(Dispatchers.IO) {
        try {
            val modelPath = File(context.filesDir, MODEL_DIR)
            if (!modelPath.exists() || !modelPath.isDirectory) {
                Log.e(TAG, "Model not found at ${modelPath.absolutePath}. Download it first.")
                return@withContext false
            }

            model = Model(modelPath.absolutePath)
            recognizer = Recognizer(model, SAMPLE_RATE)
            Log.i(TAG, "Vosk model loaded successfully")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to load Vosk model", e)
            false
        }
    }

    /**
     * Recognize a complete utterance (from VAD) and return the result.
     * This processes a batch of audio — Vosk handles it fast for short utterances.
     */
    suspend fun recognize(audioSamples: ShortArray): SttResult? = withContext(Dispatchers.IO) {
        val rec = recognizer ?: run {
            Log.e(TAG, "Recognizer not initialized")
            return@withContext null
        }

        try {
            // Convert short array to byte array (PCM 16-bit little-endian)
            val byteBuffer = ByteBuffer.allocate(audioSamples.size * 2)
                .order(ByteOrder.LITTLE_ENDIAN)
            for (sample in audioSamples) {
                byteBuffer.putShort(sample)
            }
            val bytes = byteBuffer.array()

            // Feed audio to recognizer
            rec.acceptWaveForm(bytes, bytes.size)
            val resultJson = rec.finalResult

            // Parse result
            val json = JSONObject(resultJson)
            val text = json.optString("text", "").trim()

            if (text.isEmpty()) {
                return@withContext null
            }

            // Vosk doesn't provide sentence-level confidence in the simple API,
            // but we can get word-level confidence from the alternatives.
            // For now, use a fixed moderate confidence that the pipeline can refine.
            val confidence = estimateConfidence(json)

            Log.d(TAG, "Recognized: \"$text\" (confidence: $confidence)")

            SttResult(
                sentence = text,
                confidence = confidence,
                source = SttSource.VOSK
            )
        } catch (e: Exception) {
            Log.e(TAG, "Recognition error", e)
            null
        }
    }

    private fun estimateConfidence(json: JSONObject): Float {
        // If Vosk returns word-level results with confidence, average them.
        // Otherwise return a moderate default.
        val result = json.optJSONArray("result") ?: return 0.7f
        if (result.length() == 0) return 0.7f

        var totalConf = 0.0
        for (i in 0 until result.length()) {
            totalConf += result.getJSONObject(i).optDouble("conf", 0.7)
        }
        return (totalConf / result.length()).toFloat()
    }

    fun release() {
        recognizer?.close()
        recognizer = null
        model?.close()
        model = null
    }
}
