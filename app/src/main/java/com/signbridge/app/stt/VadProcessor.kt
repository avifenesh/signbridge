package com.signbridge.app.stt

import android.util.Log
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

/**
 * Voice Activity Detection using a simple energy-based approach.
 * Detects speech boundaries in an audio stream.
 *
 * Silero VAD model integration will replace the energy-based approach
 * once the ONNX model is available. For now, uses RMS energy thresholding
 * which is functional but less accurate.
 *
 * Input: stream of PCM 16-bit audio chunks
 * Output: stream of complete utterances (audio between silence gaps)
 */
class VadProcessor(
    private val sampleRate: Int = 16000,
    private val silenceThresholdMs: Int = 500,  // Consider speech ended after this silence
    private val energyThreshold: Float = 200f    // RMS energy below this = silence
) {
    companion object {
        private const val TAG = "VadProcessor"
    }

    private val utteranceBuffer = mutableListOf<ShortArray>()
    private var speechDetected = false
    private var silenceSamples = 0
    private val silenceSampleThreshold = (sampleRate * silenceThresholdMs) / 1000

    /**
     * Process a stream of audio chunks and emit complete utterances.
     * An utterance is audio between the start of speech and a silence gap.
     */
    fun processStream(audioChunks: Flow<ShortArray>): Flow<ShortArray> = flow {
        audioChunks.collect { chunk ->
            val rms = calculateRms(chunk)
            val isSpeech = rms > energyThreshold

            if (isSpeech) {
                if (!speechDetected) {
                    Log.d(TAG, "Speech started (RMS: $rms)")
                }
                speechDetected = true
                silenceSamples = 0
                utteranceBuffer.add(chunk)
            } else if (speechDetected) {
                silenceSamples += chunk.size

                // Still include silence chunks in case speech resumes
                utteranceBuffer.add(chunk)

                if (silenceSamples >= silenceSampleThreshold) {
                    // Silence long enough — emit the complete utterance
                    val utterance = mergeChunks(utteranceBuffer)
                    Log.d(TAG, "Utterance complete: ${utterance.size} samples (${utterance.size * 1000 / sampleRate}ms)")
                    emit(utterance)

                    utteranceBuffer.clear()
                    speechDetected = false
                    silenceSamples = 0
                }
            }
            // If no speech detected and not in an utterance, discard (silence)
        }

        // Emit any remaining buffered audio when stream ends
        if (utteranceBuffer.isNotEmpty()) {
            emit(mergeChunks(utteranceBuffer))
            utteranceBuffer.clear()
        }
    }

    private fun calculateRms(samples: ShortArray): Float {
        if (samples.isEmpty()) return 0f
        var sum = 0.0
        for (sample in samples) {
            sum += sample.toDouble() * sample.toDouble()
        }
        return kotlin.math.sqrt(sum / samples.size).toFloat()
    }

    private fun mergeChunks(chunks: List<ShortArray>): ShortArray {
        val totalSize = chunks.sumOf { it.size }
        val result = ShortArray(totalSize)
        var offset = 0
        for (chunk in chunks) {
            chunk.copyInto(result, offset)
            offset += chunk.size
        }
        return result
    }

    fun reset() {
        utteranceBuffer.clear()
        speechDetected = false
        silenceSamples = 0
    }
}
