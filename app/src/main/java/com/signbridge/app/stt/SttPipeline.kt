package com.signbridge.app.stt

import android.util.Log
import com.signbridge.app.model.PipelineStatus
import com.signbridge.app.model.SignSequence
import com.signbridge.app.model.SttResult
import com.signbridge.app.translation.AslTranslationEngine
import com.signbridge.app.translation.SignDictionary
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*

/**
 * Orchestrates the full pipeline:
 * Audio chunks → VAD → STT → ASL Translation → Sign Sequence
 *
 * Emits SignSequence and PipelineStatus for the overlay to consume.
 */
class SttPipeline(
    private val voskEngine: VoskSttEngine,
    private val translationEngine: AslTranslationEngine,
    private val dictionary: SignDictionary
) {
    companion object {
        private const val TAG = "SttPipeline"
        private const val LOW_CONFIDENCE_THRESHOLD = 0.3f
    }

    private val vad = VadProcessor()

    private val _signSequences = MutableSharedFlow<SignSequence>(extraBufferCapacity = 16)
    val signSequences: SharedFlow<SignSequence> = _signSequences

    private val _status = MutableStateFlow<PipelineStatus>(PipelineStatus.Listening)
    val status: StateFlow<PipelineStatus> = _status

    private val _subtitles = MutableSharedFlow<String>(extraBufferCapacity = 16)
    val subtitles: SharedFlow<String> = _subtitles

    /**
     * Start processing an audio stream. Runs until the flow completes or scope is cancelled.
     */
    suspend fun processAudioStream(audioChunks: Flow<ShortArray>) {
        _status.value = PipelineStatus.Listening

        vad.processStream(audioChunks).collect { utterance ->
            processUtterance(utterance)
        }
    }

    private suspend fun processUtterance(utterance: ShortArray) {
        _status.value = PipelineStatus.Processing

        // Step 1: STT
        val sttResult = voskEngine.recognize(utterance)
        if (sttResult == null) {
            _status.value = PipelineStatus.Listening
            return
        }

        // Always emit subtitle text
        _subtitles.emit(sttResult.sentence)

        // Step 2: Check confidence — if too low, fallback to captions only
        if (sttResult.confidence < LOW_CONFIDENCE_THRESHOLD) {
            Log.w(TAG, "Low STT confidence (${sttResult.confidence}), caption fallback")
            _status.value = PipelineStatus.Error(sttResult.sentence)
            return
        }

        // Step 3: ASL Translation
        val translation = translationEngine.translate(sttResult.sentence)
        if (translation == null) {
            Log.w(TAG, "Translation failed for: ${sttResult.sentence}")
            _status.value = PipelineStatus.Error(sttResult.sentence)
            return
        }

        // Step 4: Look up signs from dictionary
        val signEntries = dictionary.lookupGloss(translation.glossTokens)

        // Step 5: Build sign sequence with aggregate confidence
        val pipelineConfidence = sttResult.confidence * translation.confidence
        val sequence = SignSequence(
            english = sttResult.sentence,
            pipelineConfidence = pipelineConfidence,
            entries = signEntries
        )

        Log.d(TAG, "Pipeline complete: \"${sttResult.sentence}\" → ${translation.glossTokens} (conf: $pipelineConfidence)")

        _status.value = PipelineStatus.Signing(pipelineConfidence)
        _signSequences.emit(sequence)
    }

    fun reset() {
        vad.reset()
        _status.value = PipelineStatus.Listening
    }
}
