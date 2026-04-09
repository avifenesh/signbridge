package com.signbridge.app.translation

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.util.Log
import java.io.File
import java.nio.LongBuffer
import kotlin.math.sqrt

/**
 * MiniLM-L6-v2 sentence embedder via ONNX Runtime on Android.
 * Produces 384-dimensional sentence embeddings for Tier 2 vector similarity.
 *
 * Includes a minimal WordPiece tokenizer compatible with BERT-style models.
 *
 * Falls back to BoW embedding if the model files aren't available.
 */
class MiniLmEmbedder(private val context: Context) {

    companion object {
        private const val TAG = "MiniLmEmbedder"
        private const val MODEL_DIR = "minilm"
        private const val MODEL_FILE = "model.onnx"
        private const val VOCAB_FILE = "vocab.txt"
        private const val MAX_LENGTH = 128
        const val DIMS = 384
    }

    private var session: OrtSession? = null
    private var env: OrtEnvironment? = null
    private var vocab: Map<String, Int> = emptyMap()
    private var unkId = 0
    private var clsId = 101
    private var sepId = 102
    private var padId = 0

    var isLoaded = false
        private set

    /**
     * Try to load the MiniLM model. Returns true if successful.
     */
    fun load(): Boolean {
        try {
            val modelDir = File(context.filesDir, MODEL_DIR)
            val modelFile = File(modelDir, MODEL_FILE)
            val vocabFile = File(modelDir, VOCAB_FILE)

            if (!modelFile.exists() || !vocabFile.exists()) {
                Log.d(TAG, "MiniLM model not found at ${modelDir.absolutePath}")
                return false
            }

            // Load vocab
            vocab = vocabFile.readLines().withIndex().associate { (idx, line) -> line.trim() to idx }
            unkId = vocab["[UNK]"] ?: 0
            clsId = vocab["[CLS]"] ?: 101
            sepId = vocab["[SEP]"] ?: 102
            padId = vocab["[PAD]"] ?: 0

            // Load ONNX model
            env = OrtEnvironment.getEnvironment()
            session = env!!.createSession(modelFile.absolutePath)

            isLoaded = true
            Log.i(TAG, "MiniLM loaded: ${vocab.size} vocab, model at ${modelFile.absolutePath}")
            return true
        } catch (e: Exception) {
            Log.w(TAG, "Failed to load MiniLM", e)
            return false
        }
    }

    /**
     * Embed a sentence into a 384-dimensional vector.
     * If MiniLM isn't loaded, falls back to BoW.
     */
    fun embed(text: String): FloatArray {
        if (!isLoaded) return bowEmbed(text)

        try {
            val tokens = tokenize(text)
            val ortEnv = env ?: return bowEmbed(text)

            val inputIds = OnnxTensor.createTensor(ortEnv,
                LongBuffer.wrap(tokens.inputIds.map { it.toLong() }.toLongArray()),
                longArrayOf(1, tokens.inputIds.size.toLong()))

            val attentionMask = OnnxTensor.createTensor(ortEnv,
                LongBuffer.wrap(tokens.attentionMask.map { it.toLong() }.toLongArray()),
                longArrayOf(1, tokens.attentionMask.size.toLong()))

            val tokenTypeIds = OnnxTensor.createTensor(ortEnv,
                LongBuffer.wrap(LongArray(tokens.inputIds.size)),
                longArrayOf(1, tokens.inputIds.size.toLong()))

            val inputs = mapOf(
                "input_ids" to inputIds,
                "attention_mask" to attentionMask,
                "token_type_ids" to tokenTypeIds
            )

            val results = session!!.run(inputs)
            val output = results[0].value

            // output shape: [1, seq_len, 384] — mean pool over non-padding tokens
            @Suppress("UNCHECKED_CAST")
            val hidden = output as Array<Array<FloatArray>> // [1][seq_len][384]
            val seqLen = hidden[0].size
            val pooled = FloatArray(DIMS)

            var tokenCount = 0f
            for (i in 0 until seqLen) {
                if (tokens.attentionMask[i] == 1) {
                    for (d in 0 until DIMS) {
                        pooled[d] += hidden[0][i][d]
                    }
                    tokenCount += 1f
                }
            }

            // Average
            if (tokenCount > 0) {
                for (d in 0 until DIMS) pooled[d] /= tokenCount
            }

            // L2 normalize
            var norm = 0f
            for (v in pooled) norm += v * v
            norm = sqrt(norm)
            if (norm > 0) {
                for (d in pooled.indices) pooled[d] /= norm
            }

            // Cleanup
            inputIds.close()
            attentionMask.close()
            tokenTypeIds.close()
            results.close()

            return pooled
        } catch (e: Exception) {
            Log.w(TAG, "MiniLM inference failed, falling back to BoW", e)
            return bowEmbed(text)
        }
    }

    private data class TokenizerOutput(
        val inputIds: List<Int>,
        val attentionMask: List<Int>
    )

    private fun tokenize(text: String): TokenizerOutput {
        val cleanText = text.lowercase().trim()
        val wordTokens = preTokenize(cleanText)
        val pieces = mutableListOf<String>()

        for (word in wordTokens) {
            pieces.addAll(wordPiece(word))
        }

        // Truncate
        val truncated = pieces.take(MAX_LENGTH - 2)

        // Build ids: [CLS] + tokens + [SEP] + padding
        val ids = mutableListOf(clsId)
        ids.addAll(truncated.map { vocab[it] ?: unkId })
        ids.add(sepId)

        val attn = MutableList(ids.size) { 1 }

        // Pad
        while (ids.size < MAX_LENGTH) {
            ids.add(padId)
            attn.add(0)
        }

        return TokenizerOutput(ids, attn)
    }

    private fun wordPiece(word: String): List<String> {
        if (word in vocab) return listOf(word)

        val pieces = mutableListOf<String>()
        var start = 0

        while (start < word.length) {
            var end = word.length
            var found = false

            while (start < end) {
                val sub = word.substring(start, end)
                val candidate = if (start > 0) "##$sub" else sub

                if (candidate in vocab) {
                    pieces.add(candidate)
                    start = end
                    found = true
                    break
                }
                end--
            }

            if (!found) {
                pieces.add("[UNK]")
                break
            }
        }
        return pieces
    }

    private fun preTokenize(text: String): List<String> {
        val tokens = mutableListOf<String>()
        val buf = StringBuilder()

        for (ch in text) {
            if (ch.isLetterOrDigit()) {
                buf.append(ch)
            } else {
                if (buf.isNotEmpty()) {
                    tokens.add(buf.toString())
                    buf.clear()
                }
                if (!ch.isWhitespace()) {
                    tokens.add(ch.toString())
                }
            }
        }
        if (buf.isNotEmpty()) tokens.add(buf.toString())
        return tokens
    }

    /** BoW fallback — same hash-based embedding as the Python BagOfWordsEmbedder */
    private fun bowEmbed(text: String): FloatArray {
        val vec = FloatArray(DIMS)
        for (word in text.lowercase().split("\\s+".toRegex())) {
            if (word.isBlank()) continue
            val idx = fnv32a(word) % DIMS
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
            h *= 16777619
        }
        return h and 0x7FFFFFFF
    }

    fun release() {
        session?.close()
        env?.close()
        session = null
        env = null
        isLoaded = false
    }
}
