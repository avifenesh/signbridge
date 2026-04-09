package com.signbridge.app.translation

import android.content.Context
import android.util.Log
import com.signbridge.app.model.*
import org.json.JSONObject
import java.io.InputStream

/**
 * In-memory sign dictionary.
 * Maps ASL gloss tokens to keyframe animation data.
 * Falls back to fingerspelling for unknown words.
 */
class SignDictionary(private val context: Context) {

    companion object {
        private const val TAG = "SignDictionary"
        private const val FINGERSPELL_LETTER_MS = 300 // ms per letter
        private const val FINGERSPELL_PAUSE_MS = 100   // pause between letters
        private const val DEFAULT_SIGN_DURATION_MS = 500
    }

    private val signs = mutableMapOf<String, DictionarySign>()
    private val transitions = mutableMapOf<String, SignTransition>()
    private val fingerspellPoses = mutableMapOf<Char, BoneKeyframe>()

    val signCount: Int get() = signs.size
    val isLoaded: Boolean get() = fingerspellPoses.isNotEmpty()

    /**
     * Load the dictionary from bundled JSON assets.
     */
    fun load() {
        loadFingerspelling()
        loadSigns()
        loadTransitions()
        Log.i(TAG, "Dictionary loaded: ${signs.size} signs, ${fingerspellPoses.size} fingerspell chars, ${transitions.size} transitions")
    }

    /**
     * Look up a list of ASL gloss tokens and return SignEntry list.
     * Unknown glosses are fingerspelled.
     */
    fun lookupGloss(glossTokens: List<String>): List<SignEntry> {
        return glossTokens.map { gloss ->
            val sign = signs[gloss.lowercase()]
            if (sign != null) {
                SignEntry.Sign(
                    gloss = gloss,
                    signId = sign.signId,
                    durationMs = sign.durationMs
                )
            } else {
                // Fingerspell unknown words
                val letters = gloss.filter { it.isLetter() }.toList()
                val duration = letters.size * (FINGERSPELL_LETTER_MS + FINGERSPELL_PAUSE_MS)
                SignEntry.Fingerspell(
                    gloss = gloss,
                    letters = letters,
                    durationMs = duration
                )
            }
        }
    }

    /**
     * Get the keyframes for a specific sign.
     */
    fun getSignFrames(signId: String): List<BoneKeyframe>? {
        return signs[signId]?.frames
    }

    /**
     * Get the fingerspell pose for a letter.
     */
    fun getFingerspellPose(letter: Char): BoneKeyframe? {
        return fingerspellPoses[letter.uppercaseChar()]
    }

    /**
     * Get a transition animation between two signs, if one exists.
     */
    fun getTransition(fromSignId: String, toSignId: String): SignTransition? {
        return transitions["${fromSignId}_to_${toSignId}"]
    }

    private fun loadFingerspelling() {
        // Load 26 A-Z poses + 10 number signs
        // For now, create placeholder poses — real data comes from Agent 3
        for (c in 'A'..'Z') {
            fingerspellPoses[c] = createPlaceholderPose()
        }
        for (n in '0'..'9') {
            fingerspellPoses[n] = createPlaceholderPose()
        }
        Log.d(TAG, "Fingerspelling: ${fingerspellPoses.size} poses loaded")
    }

    private fun loadSigns() {
        // Try to load from assets; fall back to empty dictionary
        try {
            val inputStream: InputStream = context.assets.open("dictionary/signs.json")
            val json = JSONObject(inputStream.bufferedReader().readText())
            inputStream.close()

            for (key in json.keys()) {
                val signJson = json.getJSONObject(key)
                val frames = parseFrames(signJson.getJSONArray("frames"))
                signs[key] = DictionarySign(
                    signId = signJson.getString("sign_id"),
                    gloss = signJson.getString("gloss"),
                    durationMs = signJson.getInt("duration_ms"),
                    category = signJson.optString("category", "general"),
                    frames = frames
                )
            }
        } catch (e: Exception) {
            Log.w(TAG, "No sign dictionary found in assets — starting with fingerspelling only", e)
        }
    }

    private fun loadTransitions() {
        try {
            val inputStream: InputStream = context.assets.open("dictionary/transitions.json")
            val json = JSONObject(inputStream.bufferedReader().readText())
            inputStream.close()

            for (key in json.keys()) {
                val transJson = json.getJSONObject(key)
                transitions[key] = SignTransition(
                    fromSignId = transJson.getString("from_sign"),
                    toSignId = transJson.getString("to_sign"),
                    durationMs = transJson.getInt("duration_ms"),
                    frames = parseFrames(transJson.getJSONArray("frames"))
                )
            }
        } catch (e: Exception) {
            Log.d(TAG, "No transitions file found — using default slerp", e)
        }
    }

    private fun parseFrames(framesArray: org.json.JSONArray): List<BoneKeyframe> {
        val frames = mutableListOf<BoneKeyframe>()
        for (i in 0 until framesArray.length()) {
            val frameJson = framesArray.getJSONObject(i)
            val timeMs = frameJson.getInt("time_ms")

            val bones = mutableMapOf<String, Quaternion>()
            val bonesJson = frameJson.getJSONObject("bones")
            for (boneName in bonesJson.keys()) {
                val rotJson = bonesJson.getJSONObject(boneName).getJSONArray("rotation")
                bones[boneName] = Quaternion(
                    x = rotJson.getDouble(0).toFloat(),
                    y = rotJson.getDouble(1).toFloat(),
                    z = rotJson.getDouble(2).toFloat(),
                    w = rotJson.getDouble(3).toFloat()
                )
            }

            val faceJson = frameJson.optJSONObject("face")
            val face = if (faceJson != null) {
                FaceParams(
                    eyebrowRaise = faceJson.optDouble("eyebrow_raise", 0.0).toFloat(),
                    mouthOpen = faceJson.optDouble("mouth_open", 0.0).toFloat(),
                    headTilt = faceJson.optDouble("head_tilt", 0.0).toFloat(),
                    eyeGazeX = faceJson.optDouble("eye_gaze_x", 0.0).toFloat(),
                    cheekPuff = faceJson.optDouble("cheek_puff", 0.0).toFloat()
                )
            } else {
                FaceParams.NEUTRAL
            }

            frames.add(BoneKeyframe(timeMs, bones, face))
        }
        return frames
    }

    private fun createPlaceholderPose(): BoneKeyframe {
        return BoneKeyframe(
            timeMs = 0,
            boneRotations = mapOf("right_wrist" to Quaternion.IDENTITY),
            faceParams = FaceParams.NEUTRAL
        )
    }
}
