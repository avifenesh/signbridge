package com.signbridge.app.translation

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * Tests for the BoW embedding and cosine similarity logic in VectorSimilarityIndex.
 * Can't test full index loading (needs Android Context) but can test the math.
 */
class VectorSimilarityIndexTest {

    // Replicating the BoW embed logic for testing
    private fun bowEmbed(text: String, dims: Int = 384): FloatArray {
        val vec = FloatArray(dims)
        for (word in text.lowercase().split("\\s+".toRegex())) {
            if (word.isBlank()) continue
            val idx = fnv32a(word) % dims
            vec[idx] += 1f
        }
        var norm = 0f
        for (v in vec) norm += v * v
        norm = sqrt(norm)
        if (norm > 0) for (i in vec.indices) vec[i] /= norm
        return vec
    }

    private fun fnv32a(s: String): Int {
        var h = 0x811c9dc5.toInt()
        for (b in s.toByteArray()) {
            h = h xor b.toInt()
            h = (h * 16777619)
        }
        return h and 0x7FFFFFFF
    }

    private fun cosine(a: FloatArray, b: FloatArray): Float {
        var dot = 0f; var na = 0f; var nb = 0f
        for (i in a.indices) { dot += a[i]*b[i]; na += a[i]*a[i]; nb += b[i]*b[i] }
        val d = sqrt(na) * sqrt(nb)
        return if (d > 0) dot / d else 0f
    }

    @Test
    fun `identical sentences have similarity 1`() {
        val a = bowEmbed("how are you")
        val b = bowEmbed("how are you")
        assertEquals(1.0f, cosine(a, b), 0.001f)
    }

    @Test
    fun `similar sentences have high similarity`() {
        val a = bowEmbed("how are you doing")
        val b = bowEmbed("how are you today")
        // Share 3 of 4 words
        assertTrue(cosine(a, b) > 0.5f)
    }

    @Test
    fun `unrelated sentences have low similarity`() {
        val a = bowEmbed("how are you")
        val b = bowEmbed("the weather is nice")
        assertTrue(cosine(a, b) < 0.3f)
    }

    @Test
    fun `embedding is normalized`() {
        val vec = bowEmbed("hello world")
        var norm = 0f
        for (v in vec) norm += v * v
        norm = sqrt(norm)
        assertEquals(1.0f, norm, 0.01f)
    }

    @Test
    fun `empty string produces zero vector`() {
        val vec = bowEmbed("")
        assertTrue(vec.all { it == 0f })
    }

    @Test
    fun `fnv32a produces consistent hashes`() {
        assertEquals(fnv32a("hello"), fnv32a("hello"))
        assertNotEquals(fnv32a("hello"), fnv32a("world"))
    }

    @Test
    fun `word order does not affect BoW embedding`() {
        val a = bowEmbed("i want pizza")
        val b = bowEmbed("pizza want i")
        assertEquals(1.0f, cosine(a, b), 0.001f)
    }
}
