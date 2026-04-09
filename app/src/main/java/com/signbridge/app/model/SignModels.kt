package com.signbridge.app.model

/**
 * Core data models for the SignBridge pipeline.
 * These define the contracts between components (STT, translation, dictionary, renderer).
 */

/** Output from STT engine */
data class SttResult(
    val sentence: String,
    val confidence: Float,
    val source: SttSource
)

enum class SttSource { VOSK, GROQ, DEEPGRAM, GOOGLE }

/** Output from ASL translation engine */
data class AslTranslation(
    val glossTokens: List<String>,
    val method: TranslationMethod,
    val confidence: Float,
    val pattern: String? = null // Only for pattern_hash matches
)

enum class TranslationMethod { PATTERN_HASH, VECTOR_SIMILARITY, MODEL, FINGERSPELL_ONLY }

/** A single sign or fingerspelled word in a sequence */
sealed class SignEntry {
    abstract val gloss: String
    abstract val durationMs: Int

    data class Sign(
        override val gloss: String,
        val signId: String,
        override val durationMs: Int
    ) : SignEntry()

    data class Fingerspell(
        override val gloss: String,
        val letters: List<Char>,
        override val durationMs: Int
    ) : SignEntry()
}

/** Full sign sequence ready for the renderer */
data class SignSequence(
    val english: String,
    val pipelineConfidence: Float,
    val entries: List<SignEntry>
)

/** Pipeline status events */
sealed class PipelineStatus {
    data object Listening : PipelineStatus()
    data object Processing : PipelineStatus()
    data class Signing(val confidence: Float) : PipelineStatus()
    data class Error(val fallbackText: String) : PipelineStatus()
}

/** A single keyframe for avatar animation */
data class BoneKeyframe(
    val timeMs: Int,
    val boneRotations: Map<String, Quaternion>,
    val faceParams: FaceParams
)

/** Quaternion for bone rotation */
data class Quaternion(
    val x: Float,
    val y: Float,
    val z: Float,
    val w: Float
) {
    companion object {
        val IDENTITY = Quaternion(0f, 0f, 0f, 1f)

        /** Spherical linear interpolation between two quaternions */
        fun slerp(a: Quaternion, b: Quaternion, t: Float): Quaternion {
            var dot = a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w
            val bx: Float; val by: Float; val bz: Float; val bw: Float

            // If dot is negative, negate one to take the shorter path
            if (dot < 0f) {
                dot = -dot
                bx = -b.x; by = -b.y; bz = -b.z; bw = -b.w
            } else {
                bx = b.x; by = b.y; bz = b.z; bw = b.w
            }

            val (s0, s1) = if (dot > 0.9995f) {
                // Very close — linear interpolation to avoid division by zero
                (1f - t) to t
            } else {
                val omega = kotlin.math.acos(dot)
                val sinOmega = kotlin.math.sin(omega)
                (kotlin.math.sin((1f - t) * omega) / sinOmega) to
                    (kotlin.math.sin(t * omega) / sinOmega)
            }

            return Quaternion(
                s0 * a.x + s1 * bx,
                s0 * a.y + s1 * by,
                s0 * a.z + s1 * bz,
                s0 * a.w + s1 * bw
            )
        }
    }
}

/** Continuous facial expression parameters (0.0 to 1.0) */
data class FaceParams(
    val eyebrowRaise: Float = 0f,
    val mouthOpen: Float = 0f,
    val headTilt: Float = 0f,    // -1.0 left, 0.0 center, 1.0 right
    val eyeGazeX: Float = 0f,   // -1.0 left, 0.0 center, 1.0 right
    val cheekPuff: Float = 0f
) {
    companion object {
        val NEUTRAL = FaceParams()

        fun lerp(a: FaceParams, b: FaceParams, t: Float): FaceParams = FaceParams(
            eyebrowRaise = a.eyebrowRaise + (b.eyebrowRaise - a.eyebrowRaise) * t,
            mouthOpen = a.mouthOpen + (b.mouthOpen - a.mouthOpen) * t,
            headTilt = a.headTilt + (b.headTilt - a.headTilt) * t,
            eyeGazeX = a.eyeGazeX + (b.eyeGazeX - a.eyeGazeX) * t,
            cheekPuff = a.cheekPuff + (b.cheekPuff - a.cheekPuff) * t
        )
    }
}

/** A complete sign from the dictionary */
data class DictionarySign(
    val signId: String,
    val gloss: String,
    val durationMs: Int,
    val category: String,
    val frames: List<BoneKeyframe>
)

/** A transition animation between two signs */
data class SignTransition(
    val fromSignId: String,
    val toSignId: String,
    val durationMs: Int,
    val frames: List<BoneKeyframe>
)

/** Confidence level for UI indicator */
enum class ConfidenceLevel {
    HIGH,   // Green glow — pipeline confident
    MEDIUM, // Yellow glow — one stage uncertain
    LOW;    // Red glow — auto-fallback to captions

    companion object {
        fun from(confidence: Float): ConfidenceLevel = when {
            confidence >= 0.7f -> HIGH
            confidence >= 0.3f -> MEDIUM
            else -> LOW
        }
    }
}
