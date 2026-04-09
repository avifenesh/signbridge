package com.signbridge.app.model

import org.junit.Assert.*
import org.junit.Test

class SignEntryTest {

    @Test
    fun `Sign entry has correct properties`() {
        val sign = SignEntry.Sign(gloss = "HELLO", signId = "hello", durationMs = 400)
        assertEquals("HELLO", sign.gloss)
        assertEquals("hello", sign.signId)
        assertEquals(400, sign.durationMs)
    }

    @Test
    fun `Fingerspell entry has letters`() {
        val fs = SignEntry.Fingerspell(gloss = "SARAH", letters = listOf('S', 'A', 'R', 'A', 'H'), durationMs = 1500)
        assertEquals(5, fs.letters.size)
        assertEquals('S', fs.letters[0])
        assertEquals(1500, fs.durationMs)
    }
}

class SignSequenceTest {

    @Test
    fun `sequence with mixed signs and fingerspelling`() {
        val seq = SignSequence(
            english = "hello Sarah",
            pipelineConfidence = 0.85f,
            entries = listOf(
                SignEntry.Sign("HELLO", "hello", 400),
                SignEntry.Fingerspell("SARAH", listOf('S', 'A', 'R', 'A', 'H'), 1500)
            )
        )
        assertEquals(2, seq.entries.size)
        assertEquals(0.85f, seq.pipelineConfidence)
        assertTrue(seq.entries[0] is SignEntry.Sign)
        assertTrue(seq.entries[1] is SignEntry.Fingerspell)
    }
}

class PipelineStatusTest {

    @Test
    fun `Listening status`() {
        val status = PipelineStatus.Listening
        assertTrue(status is PipelineStatus.Listening)
    }

    @Test
    fun `Signing status has confidence`() {
        val status = PipelineStatus.Signing(0.85f)
        assertEquals(0.85f, status.confidence)
    }

    @Test
    fun `Error status has fallback text`() {
        val status = PipelineStatus.Error("hello world")
        assertEquals("hello world", status.fallbackText)
    }
}

class AslTranslationTest {

    @Test
    fun `translation with pattern hash method`() {
        val t = AslTranslation(
            glossTokens = listOf("HELLO"),
            method = TranslationMethod.PATTERN_HASH,
            confidence = 1.0f,
            pattern = "hello"
        )
        assertEquals(TranslationMethod.PATTERN_HASH, t.method)
        assertEquals(1.0f, t.confidence)
        assertEquals(listOf("HELLO"), t.glossTokens)
    }

    @Test
    fun `translation with vector similarity`() {
        val t = AslTranslation(
            glossTokens = listOf("WEATHER", "NICE"),
            method = TranslationMethod.VECTOR_SIMILARITY,
            confidence = 0.82f
        )
        assertEquals(TranslationMethod.VECTOR_SIMILARITY, t.method)
        assertNull(t.pattern)
    }

    @Test
    fun `fingerspell fallback has low confidence`() {
        val t = AslTranslation(
            glossTokens = listOf("SUPERCALIFRAGILISTIC"),
            method = TranslationMethod.FINGERSPELL_ONLY,
            confidence = 0.3f
        )
        assertTrue(t.confidence < 0.5f)
    }
}
