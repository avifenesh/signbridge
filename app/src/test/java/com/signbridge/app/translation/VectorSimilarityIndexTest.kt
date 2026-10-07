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

    // ── Template-aware candidate selection (mirrors translation/tier2/query.py) ──

    // Axes: [pizza, coffee, like, want]. The filler dominates, as with MiniLM.
    private fun fillerEmbed(text: String): FloatArray {
        val v = floatArrayOf(0.01f, 0.01f, 0.01f, 0.01f)
        for (w in text.split(" ")) when (w) {
            "pizza" -> v[0] += 3f
            "coffee" -> v[1] += 3f
            "like" -> v[2] += 1f
            "want" -> v[3] += 1f
        }
        return v
    }

    private val rerankEntries = listOf(
        "i like pizza" to "{FOOD} I LIKE",
        "i want {THING}" to "{THING} I WANT",
        "i want coffee" to "{THING} I WANT",
    ).map { (pattern, asl) -> VectorEntry(pattern, asl, fillerEmbed(pattern)) }

    @Test
    fun `template match beats shared-filler nearest neighbour`() {
        val input = "i want pizza"
        val emb = fillerEmbed(input)
        // Raw nearest neighbour is the wrong template
        assertTrue(cosineSimilarity(emb, rerankEntries[0].embedding) > cosineSimilarity(emb, rerankEntries[1].embedding))

        val (idx, sim) = selectCandidate(input, emb, rerankEntries, ::fillerEmbed)
        assertEquals(1, idx)
        assertEquals(1.0f, sim, 0.001f)
        assertEquals(listOf("PIZZA", "I", "WANT"), adaptTemplate("{THING} I WANT", "i want {THING}", input))
    }

    @Test
    fun `no template match keeps raw nearest neighbour`() {
        val input = "i love pizza"
        val emb = fillerEmbed(input)
        val (idx, sim) = selectCandidate(input, emb, rerankEntries, ::fillerEmbed)
        assertEquals(0, idx)
        assertEquals(cosineSimilarity(emb, rerankEntries[0].embedding), sim, 0.0001f)
    }

    @Test
    fun `unfillable example entry does not win the rerank`() {
        // "i want coffee" fully matches its own example entry, but that entry's
        // template cannot be filled from it; the template entry must win.
        val input = "i want coffee"
        val (idx, _) = selectCandidate(input, fillerEmbed(input), rerankEntries, ::fillerEmbed)
        assertEquals(1, idx)
    }

    @Test
    fun `adaptTemplate fills slots from pattern`() {
        assertEquals(
            listOf("BOOK", "I", "GIVE-JOHN"),
            adaptTemplate("{OBJECT} I GIVE-{PERSON}", "i gave {PERSON} the {OBJECT}", "i gave john the book")
        )
    }

    @Test
    fun `adaptTemplate strips slots when pattern does not match`() {
        assertEquals(listOf("I", "LIKE"), adaptTemplate("{FOOD} I LIKE", "i like {FOOD}", "i want pizza"))
        // Example entries carry no slots in the pattern: never leak a raw {SLOT}
        assertEquals(listOf("I", "WANT"), adaptTemplate("{THING} I WANT", "i want coffee", "i want coffee"))
    }

    @Test
    fun `selectCandidate on empty index`() {
        assertEquals(-1, selectCandidate("hi", floatArrayOf(1f), emptyList()) { floatArrayOf(1f) }.first)
    }

    @Test
    fun `underscore slot names compile and match`() {
        // Java named groups reject underscores; bundled assets use {FAMILY_MEMBER}
        val sp = SlotPattern("my {FAMILY_MEMBER}'s name is {NAME}")
        assertEquals(mapOf("FAMILY_MEMBER" to "sister", "NAME" to "dana"), sp.match("my sister's name is dana"))
        assertEquals(
            listOf("MY", "MOTHER", "MISS", "I"),
            adaptTemplate("MY {FAMILY_MEMBER} MISS I", "i miss my {FAMILY_MEMBER}", "i miss my mother")
        )
        val entries = listOf(VectorEntry("i miss my {FAMILY_MEMBER}", "MY {FAMILY_MEMBER} MISS I", floatArrayOf(1f, 0f)))
        assertEquals(0, selectCandidate("i miss my mother", floatArrayOf(1f, 0f), entries) { floatArrayOf(1f, 0f) }.first)
    }

    @Test
    fun `every bundled pattern compiles`() {
        val english = Regex("\"(?:english|pattern)\":\\s*\"((?:[^\"\\\\]|\\\\.)*)\"")
        for (asset in listOf("patterns.json", "vector_index.json")) {
            val text = java.io.File("src/main/assets/translation/$asset").readText()
            val patterns = english.findAll(text).map { it.groupValues[1] }.toSet()
            assertTrue("no patterns read from $asset", patterns.size > 100)
            for (pattern in patterns) {
                val sp = SlotPattern(pattern)
                val sample = sp.slots.fold(pattern) { acc, slot -> acc.replace("{$slot}", "x") }
                assertNotNull("$asset: $pattern", sp.match(sample))
            }
        }
    }
}
