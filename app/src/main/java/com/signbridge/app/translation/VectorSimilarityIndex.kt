package com.signbridge.app.translation

import android.content.Context
import android.util.Log
import com.signbridge.app.model.AslTranslation
import com.signbridge.app.model.TranslationMethod
import org.json.JSONObject
import kotlin.math.sqrt

/**
 * Tier 2: Vector similarity search for ASL translation.
 *
 * Pre-computed embeddings for all patterns are loaded from an asset file.
 * At runtime, the input sentence is embedded with the same method (BoW or MiniLM)
 * and compared to all pattern embeddings via cosine similarity.
 *
 * When MiniLM ONNX is available, it replaces the BoW embedder for higher accuracy.
 * The index file must be regenerated with matching embeddings.
 *
 * Brute-force cosine over ~400 vectors takes < 1ms — no FAISS needed.
 */
class VectorSimilarityIndex(private val context: Context) {

    companion object {
        private const val TAG = "VectorSimilarity"
        private const val INDEX_ASSET = "translation/vector_index.json"
    }

    private var miniLmEmbedder: MiniLmEmbedder? = null

    private val entries = mutableListOf<VectorEntry>()
    private var dims = 384
    private var embedderType = "bow"
    var vectorCount: Int = 0
        private set

    /**
     * Load the pre-computed vector index from assets.
     * @return true if loaded successfully.
     */
    fun load(): Boolean {
        return try {
            val stream = context.assets.open(INDEX_ASSET)
            val jsonText = stream.bufferedReader().readText()
            stream.close()

            val json = JSONObject(jsonText)
            dims = json.optInt("dims", 384)
            embedderType = json.optString("embedder", "bow")
            val entriesArray = json.getJSONArray("entries")

            for (i in 0 until entriesArray.length()) {
                val obj = entriesArray.getJSONObject(i)
                val pattern = obj.getString("pattern")
                val aslTemplate = obj.getString("asl_template")
                val embArray = obj.getJSONArray("embedding")
                val embedding = FloatArray(embArray.length()) { embArray.getDouble(it).toFloat() }

                entries.add(VectorEntry(pattern, aslTemplate, embedding))
            }

            vectorCount = entries.size

            // Try to load MiniLM for runtime embedding (matches MiniLM-built index)
            if (embedderType == "minilm") {
                miniLmEmbedder = MiniLmEmbedder(context)
                if (miniLmEmbedder!!.load()) {
                    Log.i(TAG, "MiniLM embedder loaded for runtime queries")
                } else {
                    Log.w(TAG, "MiniLM not available — falling back to BoW (reduced accuracy)")
                    miniLmEmbedder = null
                }
            }

            Log.i(TAG, "Loaded $vectorCount vectors (dims=$dims, embedder=$embedderType)")
            true
        } catch (e: Exception) {
            Log.w(TAG, "Failed to load vector index: ${e.message}")
            false
        }
    }

    /**
     * Find the most similar pattern to the input sentence.
     * Returns null if no match exceeds the confidence threshold.
     */
    fun findSimilar(sentence: String, threshold: Float): AslTranslation? {
        if (entries.isEmpty()) return null

        val inputEmb = embed(sentence)
        val (bestIdx, bestSim) = selectCandidate(sentence, inputEmb, entries, ::embed)

        if (bestIdx < 0 || bestSim < threshold) return null

        val best = entries[bestIdx]
        val glossTokens = adaptTemplate(best.aslTemplate, best.pattern, sentence)

        Log.d(TAG, "Match: \"$sentence\" → \"${best.pattern}\" (sim=$bestSim)")

        return AslTranslation(
            glossTokens = glossTokens,
            method = TranslationMethod.VECTOR_SIMILARITY,
            confidence = bestSim,
            pattern = best.pattern
        )
    }

    /**
     * Embed a sentence using the same method as the index was built with.
     * Uses MiniLM ONNX when available (matches MiniLM-built index).
     * Falls back to BoW if MiniLM not loaded.
     */
    private fun embed(text: String): FloatArray {
        // Use MiniLM if available (handles its own BoW fallback internally)
        miniLmEmbedder?.let { return it.embed(text) }

        // BoW fallback
        val vec = FloatArray(dims)
        for (word in text.lowercase().split("\\s+".toRegex())) {
            if (word.isBlank()) continue
            val idx = fnv32a(word) % dims
            vec[idx] += 1f
        }
        var norm = 0f
        for (v in vec) norm += v * v
        norm = sqrt(norm)
        if (norm > 0f) {
            for (i in vec.indices) vec[i] /= norm
        }
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
}

/** Number of nearest neighbours checked for a full template match. */
internal const val TEMPLATE_RERANK_TOP_K = 10

private val SLOT_REGEX = Regex("\\{(\\w+)\\}")

internal class VectorEntry(
    val pattern: String,
    val aslTemplate: String,
    val embedding: FloatArray
) {
    /** Compiled once; used for reranking. */
    val slotPattern: SlotPattern by lazy { SlotPattern(pattern) }

    /** True when every slot in the ASL template can be filled from the pattern. */
    val fillable: Boolean by lazy {
        val patternSlots = SLOT_REGEX.findAll(pattern).map { it.groupValues[1] }.toSet()
        SLOT_REGEX.findAll(aslTemplate).all { it.groupValues[1] in patternSlots }
    }
}

/**
 * An English pattern like "i want {THING}" compiled into an anchored regex with
 * one lazy capture group per slot and an optional trailing [.?!]. Same shape as
 * the Python `_pattern_regex`.
 *
 * Groups are positional, not named: bundled slot names such as FAMILY_MEMBER
 * contain underscores, which Java/Android named groups reject.
 */
internal class SlotPattern(pattern: String) {
    val slots: List<String> = SLOT_REGEX.findAll(pattern).map { it.groupValues[1] }.toList()

    val regex: Regex = run {
        val parts = SLOT_REGEX.split(pattern)
        val sb = StringBuilder("^")
        for (i in parts.indices) {
            sb.append(Regex.escape(parts[i]))
            if (i < slots.size) sb.append("(.+?)")
        }
        sb.append("[.?!]?\$")
        Regex(sb.toString(), RegexOption.IGNORE_CASE)
    }

    /** Slot name to captured value, or null if [input] does not match. */
    fun match(input: String): Map<String, String>? {
        val m = regex.find(input) ?: return null
        return slots.withIndex().associate { (i, slot) -> slot to m.groupValues[i + 1] }
    }
}

internal fun cosineSimilarity(a: FloatArray, b: FloatArray): Float {
    if (a.size != b.size) return 0f
    var dot = 0f
    var normA = 0f
    var normB = 0f
    for (i in a.indices) {
        dot += a[i] * b[i]
        normA += a[i] * a[i]
        normB += b[i] * b[i]
    }
    val denom = sqrt(normA) * sqrt(normB)
    return if (denom > 0f) dot / denom else 0f
}

/**
 * Pick the index entry to translate [input] with. Returns (index, similarity),
 * index -1 when [entries] is empty.
 *
 * Index vectors are slot-filled examples, and the sentence embedding weights
 * the slot filler heavily: "i want pizza" lands nearer "i like pizza" than
 * "i want coffee". So among the [TEMPLATE_RERANK_TOP_K] nearest entries, the
 * first (by cosine) whose pattern fully matches [input] and whose ASL template
 * can be completely filled from that pattern wins over the raw nearest
 * neighbour. Its similarity is the cosine between [input] and the pattern
 * re-filled with the input's own slot values. Mirrors `VectorIndex.query` in
 * translation/tier2/query.py.
 */
internal fun selectCandidate(
    input: String,
    inputEmb: FloatArray,
    entries: List<VectorEntry>,
    embed: (String) -> FloatArray,
): Pair<Int, Float> {
    if (entries.isEmpty()) return -1 to -1f
    val sims = FloatArray(entries.size) { cosineSimilarity(inputEmb, entries[it].embedding) }
    val ranked = entries.indices.sortedByDescending { sims[it] }
    val lowered = input.lowercase()

    for (i in ranked.take(TEMPLATE_RERANK_TOP_K)) {
        val entry = entries[i]
        // Example entries ("i want coffee" -> "{THING} I WANT") cannot fill their template
        if (!entry.fillable) continue
        val values = entry.slotPattern.match(lowered) ?: continue
        var filled = entry.pattern
        for ((slot, value) in values) filled = filled.replace("{$slot}", value)
        return i to cosineSimilarity(inputEmb, embed(filled))
    }
    return ranked[0] to sims[ranked[0]]
}

/**
 * Adapt an ASL template by trying to extract slot values from the input.
 * If the pattern has slots ({THING}, {PERSON}, etc.), attempt to fill them.
 * Otherwise return the template as-is.
 */
internal fun adaptTemplate(aslTemplate: String, matchedPattern: String, input: String): List<String> {
    val slots = SLOT_REGEX.findAll(aslTemplate).map { it.groupValues[1] }.toList()

    if (slots.isEmpty()) {
        // No slots: just split the template
        return aslTemplate.uppercase().split("\\s+".toRegex()).filter { it.isNotBlank() }
    }

    // Try to extract slot values with the matched pattern's regex
    val values = SlotPattern(matchedPattern).match(input.lowercase())
    if (values != null) {
        var filled = aslTemplate
        for ((slot, value) in values) filled = filled.replace("{$slot}", value.uppercase())
        if (!SLOT_REGEX.containsMatchIn(filled)) {
            return filled.split("\\s+".toRegex()).filter { it.isNotBlank() }
        }
    }

    // Fallback: return template without slot markers
    val cleaned = aslTemplate.replace(SLOT_REGEX, "")
    return cleaned.uppercase().split("\\s+".toRegex())
        .filter { it.isNotBlank() }
        .map { it.trim('-') }
        .filter { it.isNotBlank() }
}
