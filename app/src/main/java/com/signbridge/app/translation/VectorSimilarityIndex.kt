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

    private data class VectorEntry(
        val pattern: String,
        val aslTemplate: String,
        val embedding: FloatArray
    )

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

        var bestIdx = -1
        var bestSim = -1f

        for (i in entries.indices) {
            val sim = cosineSimilarity(inputEmb, entries[i].embedding)
            if (sim > bestSim) {
                bestSim = sim
                bestIdx = i
            }
        }

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

    private fun cosineSimilarity(a: FloatArray, b: FloatArray): Float {
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
     * Adapt an ASL template by trying to extract slot values from the input.
     * If the pattern has slots ({THING}, {PERSON}, etc.), attempt to fill them.
     * Otherwise return the template as-is.
     */
    private fun adaptTemplate(aslTemplate: String, matchedPattern: String, input: String): List<String> {
        // Check if template has slots
        val slotRegex = Regex("\\{(\\w+)\\}")
        val slots = slotRegex.findAll(aslTemplate).map { it.groupValues[1] }.toList()

        if (slots.isEmpty()) {
            // No slots — just split the template
            return aslTemplate.uppercase().split("\\s+".toRegex()).filter { it.isNotBlank() }
        }

        // Try to build a regex from the matched pattern and extract slot values
        try {
            var regexStr = Regex.escape(matchedPattern.lowercase())
            for (slot in slots) {
                regexStr = regexStr.replace("\\{${slot.lowercase()}\\}", "(?<${slot}>.+?)")
                    .replace("\\{${slot}\\}", "(?<${slot}>.+?)")
            }
            regexStr = "^$regexStr[.?!]?\$"

            val regex = Regex(regexStr, RegexOption.IGNORE_CASE)
            val match = regex.find(input.lowercase())

            if (match != null) {
                var filled = aslTemplate
                for (slot in slots) {
                    val value = try { match.groups[slot]?.value?.uppercase() } catch (e: Exception) { null }
                    if (value != null) {
                        filled = filled.replace("{$slot}", value)
                    }
                }
                return filled.split("\\s+".toRegex()).filter { it.isNotBlank() }
            }
        } catch (e: Exception) {
            Log.d(TAG, "Slot extraction failed: ${e.message}")
        }

        // Fallback: return template without slot markers
        val cleaned = aslTemplate.replace(slotRegex, "")
        return cleaned.uppercase().split("\\s+".toRegex())
            .filter { it.isNotBlank() }
            .map { it.trim('-') }
            .filter { it.isNotBlank() }
    }
}
