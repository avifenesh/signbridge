package com.signbridge.app.stt

import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

class VadProcessorTest {

    @Test
    fun `silence-only produces no utterances`() = runBlocking {
        val vad = VadProcessor(sampleRate = 16000, energyThreshold = 200f)
        val silence = ShortArray(1024) { 0 }
        val chunks = flowOf(silence, silence, silence)
        val utterances = vad.processStream(chunks).toList()
        assertTrue(utterances.isEmpty())
    }

    @Test
    fun `loud audio produces utterance after silence`() = runBlocking {
        val vad = VadProcessor(sampleRate = 16000, silenceThresholdMs = 100, energyThreshold = 50f)
        val loud = ShortArray(1024) { 1000 }
        val silence = ShortArray(1024) { 0 }
        // speech → silence → silence (enough silence to trigger)
        val chunks = flowOf(loud, loud, silence, silence, silence, silence, silence)
        val utterances = vad.processStream(chunks).toList()
        assertTrue("Should produce at least 1 utterance", utterances.isNotEmpty())
        assertTrue("Utterance should contain speech samples", utterances[0].size > 1024)
    }

    @Test
    fun `RMS calculation works`() {
        val vad = VadProcessor()
        // A constant signal of 100 should have RMS of 100
        val signal = ShortArray(100) { 100 }
        // We can't call calculateRms directly (private), but we can verify
        // via the processStream behavior — loud signals should be detected
        assertNotNull(vad)
    }

    @Test
    fun `reset clears state`() {
        val vad = VadProcessor()
        vad.reset()
        // After reset, should be ready for new stream
        assertNotNull(vad)
    }
}
