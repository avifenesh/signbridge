package com.signbridge.app.renderer

import android.content.Context
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.opengl.Matrix
import android.util.Log
import com.signbridge.app.model.*
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

/**
 * OpenGL ES 2.0 renderer for the 3D sign language avatar.
 * Used in audio call mode (full screen avatar).
 *
 * Drives a rigged GLTF model with quaternion-based bone rotations.
 * Handles keyframe playback, slerp interpolation, and transition paths.
 * Uses linear blend skinning (LBS) with up to 48 bones.
 */
class AvatarRenderer(private val context: Context) : GLSurfaceView.Renderer {

    companion object {
        private const val TAG = "AvatarRenderer"
        private const val AVATAR_GLB = "models/avatar.glb"
    }

    // Shader + model
    private var shader: ShaderProgram? = null
    private var model: GltfModel? = null
    private var modelLoaded = false

    // Current animation state
    private var currentSequence: List<AnimationSegment> = emptyList()
    private var sequenceStartTime = 0L
    private var isAnimating = false

    // Confidence level for glow effect
    private var confidenceLevel = ConfidenceLevel.HIGH

    // Matrices
    private val modelMatrix = FloatArray(16)
    private val viewMatrix = FloatArray(16)
    private val projectionMatrix = FloatArray(16)
    private val mvpMatrix = FloatArray(16)
    private val tempMatrix = FloatArray(16)

    // Current bone state (from animation keyframes)
    private val currentBones = mutableMapOf<String, Quaternion>()
    private var currentFace = FaceParams.NEUTRAL

    // Bone world matrices built from quaternions each frame
    private val boneWorldMatrices = mutableMapOf<String, FloatArray>()

    // Background color
    private var bgR = 0.1f
    private var bgG = 0.1f
    private var bgB = 0.15f

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        GLES20.glClearColor(bgR, bgG, bgB, 0.85f)
        GLES20.glEnable(GLES20.GL_DEPTH_TEST)
        GLES20.glEnable(GLES20.GL_BLEND)
        GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA)
        GLES20.glEnable(GLES20.GL_CULL_FACE)
        GLES20.glCullFace(GLES20.GL_BACK)

        // Load shader
        try {
            shader = ShaderProgram(
                context,
                "shaders/avatar_vert.glsl",
                "shaders/avatar_frag.glsl"
            )
            Log.i(TAG, "Shader compiled successfully")
        } catch (e: Exception) {
            Log.e(TAG, "Shader compilation failed", e)
        }

        // Load GLTF model
        try {
            val loader = GltfLoader(context)
            model = loader.loadFromAssets(AVATAR_GLB)
            model?.uploadToGpu()
            modelLoaded = true
            Log.i(TAG, "GLTF model loaded: ${model?.vertexCount} verts, ${model?.jointNames?.size} joints")
        } catch (e: Exception) {
            Log.w(TAG, "GLTF model not available yet — rendering will be skipped until model is provided", e)
            modelLoaded = false
        }

        // Identity model matrix
        Matrix.setIdentityM(modelMatrix, 0)

        Log.i(TAG, "Surface created (model loaded: $modelLoaded)")
    }

    override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
        GLES20.glViewport(0, 0, width, height)

        val ratio = width.toFloat() / height.toFloat()
        Matrix.perspectiveM(projectionMatrix, 0, 45f, ratio, 0.1f, 100f)
        Matrix.setLookAtM(viewMatrix, 0,
            0f, 0.3f, 2.5f, // Eye — slightly above, looking at chest level
            0f, 0.2f, 0f,   // Center — upper body
            0f, 1f, 0f      // Up
        )
    }

    override fun onDrawFrame(gl: GL10?) {
        // Update confidence glow
        updateConfidenceGlow()
        GLES20.glClearColor(bgR, bgG, bgB, 0.85f)
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)

        // Update animation
        if (isAnimating) {
            updateAnimation()
        }

        if (!modelLoaded || shader == null || model == null) return

        val sh = shader!!
        val md = model!!

        sh.use()

        // Compute MVP
        Matrix.multiplyMM(tempMatrix, 0, viewMatrix, 0, modelMatrix, 0)
        Matrix.multiplyMM(mvpMatrix, 0, projectionMatrix, 0, tempMatrix, 0)

        sh.setUniformMatrix4fv("u_mvp", mvpMatrix)
        sh.setUniformMatrix4fv("u_model", modelMatrix)

        // Build bone world matrices from current quaternion state
        buildBoneMatrices()
        md.applyPose(boneWorldMatrices)
        sh.setUniformMatrix4fvArray("u_joints", md.jointMatrices, GltfModel.MAX_JOINTS)

        // Lighting — key light from upper-left-front
        sh.setUniform3f("u_lightDir", 0.5f, 0.8f, 0.6f)
        sh.setUniform3f("u_lightColor", 1.0f, 0.98f, 0.95f)
        sh.setUniform3f("u_ambientColor", 0.25f, 0.25f, 0.3f)

        // Material
        sh.setUniform3f("u_baseColor", 0.85f, 0.7f, 0.55f) // Skin tone

        // Confidence glow
        val (gr, gg, gb) = when (confidenceLevel) {
            ConfidenceLevel.HIGH -> Triple(0.1f, 0.8f, 0.1f)
            ConfidenceLevel.MEDIUM -> Triple(0.9f, 0.8f, 0.0f)
            ConfidenceLevel.LOW -> Triple(0.9f, 0.2f, 0.1f)
        }
        sh.setUniform3f("u_glowColor", gr, gg, gb)
        sh.setUniform1f("u_glowStrength", 0.4f)

        // Draw skinned mesh
        md.draw(sh)
    }

    /**
     * Convert current quaternion bone state into 4×4 world matrices for the model.
     */
    private fun buildBoneMatrices() {
        boneWorldMatrices.clear()
        for ((boneName, quat) in currentBones) {
            val mat = FloatArray(16)
            quaternionToMatrix(quat, mat)
            boneWorldMatrices[boneName] = mat
        }
    }

    /**
     * Convert a quaternion to a 4×4 rotation matrix.
     */
    private fun quaternionToMatrix(q: Quaternion, out: FloatArray) {
        val x = q.x; val y = q.y; val z = q.z; val w = q.w
        val xx = x * x; val yy = y * y; val zz = z * z
        val xy = x * y; val xz = x * z; val yz = y * z
        val wx = w * x; val wy = w * y; val wz = w * z

        out[0] = 1f - 2f * (yy + zz)
        out[1] = 2f * (xy + wz)
        out[2] = 2f * (xz - wy)
        out[3] = 0f
        out[4] = 2f * (xy - wz)
        out[5] = 1f - 2f * (xx + zz)
        out[6] = 2f * (yz + wx)
        out[7] = 0f
        out[8] = 2f * (xz + wy)
        out[9] = 2f * (yz - wx)
        out[10] = 1f - 2f * (xx + yy)
        out[11] = 0f
        out[12] = 0f // translation x
        out[13] = 0f // translation y
        out[14] = 0f // translation z
        out[15] = 1f
    }

    /**
     * Start playing a sign sequence.
     */
    fun playSignSequence(sequence: SignSequence, dictionary: com.signbridge.app.translation.SignDictionary) {
        val segments = mutableListOf<AnimationSegment>()
        var timeOffset = 0

        for ((index, entry) in sequence.entries.withIndex()) {
            when (entry) {
                is SignEntry.Sign -> {
                    val frames = dictionary.getSignFrames(entry.signId)
                    if (frames != null) {
                        segments.add(AnimationSegment.SignAnim(
                            signId = entry.signId,
                            frames = frames,
                            startTimeMs = timeOffset,
                            durationMs = entry.durationMs
                        ))
                    }
                }
                is SignEntry.Fingerspell -> {
                    for (letter in entry.letters) {
                        val pose = dictionary.getFingerspellPose(letter)
                        if (pose != null) {
                            segments.add(AnimationSegment.StaticPose(
                                label = letter.toString(),
                                pose = pose,
                                startTimeMs = timeOffset,
                                durationMs = 300
                            ))
                            timeOffset += 400
                            continue
                        }
                    }
                }
            }

            if (index < sequence.entries.size - 1) {
                val next = sequence.entries[index + 1]
                if (entry is SignEntry.Sign && next is SignEntry.Sign) {
                    val transition = dictionary.getTransition(entry.signId, next.signId)
                    if (transition != null) {
                        segments.add(AnimationSegment.TransitionAnim(
                            frames = transition.frames,
                            startTimeMs = timeOffset + entry.durationMs,
                            durationMs = transition.durationMs
                        ))
                        timeOffset += entry.durationMs + transition.durationMs
                        continue
                    }
                }
            }

            timeOffset += entry.durationMs + 200
        }

        currentSequence = segments
        sequenceStartTime = System.currentTimeMillis()
        isAnimating = true
        confidenceLevel = ConfidenceLevel.from(sequence.pipelineConfidence)
    }

    fun setConfidence(level: ConfidenceLevel) {
        confidenceLevel = level
    }

    private fun updateAnimation() {
        val elapsed = (System.currentTimeMillis() - sequenceStartTime).toInt()
        val activeSegment = currentSequence.findLast { elapsed >= it.startTimeMs } ?: return

        val lastSegment = currentSequence.lastOrNull()
        if (lastSegment != null && elapsed > lastSegment.startTimeMs + lastSegment.durationMs) {
            isAnimating = false
            return
        }

        val segmentElapsed = elapsed - activeSegment.startTimeMs

        when (activeSegment) {
            is AnimationSegment.SignAnim -> interpolateFrames(activeSegment.frames, segmentElapsed)
            is AnimationSegment.StaticPose -> {
                currentBones.clear()
                currentBones.putAll(activeSegment.pose.boneRotations)
                currentFace = activeSegment.pose.faceParams
            }
            is AnimationSegment.TransitionAnim -> interpolateFrames(activeSegment.frames, segmentElapsed)
        }
    }

    private fun interpolateFrames(frames: List<BoneKeyframe>, elapsedMs: Int) {
        if (frames.isEmpty()) return
        if (frames.size == 1) {
            currentBones.clear()
            currentBones.putAll(frames[0].boneRotations)
            currentFace = frames[0].faceParams
            return
        }

        var frameA = frames.first()
        var frameB = frames.last()

        for (i in 0 until frames.size - 1) {
            if (elapsedMs >= frames[i].timeMs && elapsedMs < frames[i + 1].timeMs) {
                frameA = frames[i]
                frameB = frames[i + 1]
                break
            }
        }

        val frameDuration = frameB.timeMs - frameA.timeMs
        val t = if (frameDuration > 0) {
            ((elapsedMs - frameA.timeMs).toFloat() / frameDuration).coerceIn(0f, 1f)
        } else 0f

        currentBones.clear()
        val allBones = frameA.boneRotations.keys + frameB.boneRotations.keys
        for (bone in allBones) {
            val rotA = frameA.boneRotations[bone] ?: Quaternion.IDENTITY
            val rotB = frameB.boneRotations[bone] ?: Quaternion.IDENTITY
            currentBones[bone] = Quaternion.slerp(rotA, rotB, t)
        }

        currentFace = FaceParams.lerp(frameA.faceParams, frameB.faceParams, t)
    }

    private fun updateConfidenceGlow() {
        when (confidenceLevel) {
            ConfidenceLevel.HIGH -> { bgR = 0.05f; bgG = 0.12f; bgB = 0.05f }
            ConfidenceLevel.MEDIUM -> { bgR = 0.12f; bgG = 0.12f; bgB = 0.0f }
            ConfidenceLevel.LOW -> { bgR = 0.12f; bgG = 0.05f; bgB = 0.05f }
        }
    }

    fun release() {
        model?.release()
        shader?.release()
    }
}

/** Represents a segment of animation within a sign sequence */
sealed class AnimationSegment {
    abstract val startTimeMs: Int
    abstract val durationMs: Int

    data class SignAnim(
        val signId: String,
        val frames: List<BoneKeyframe>,
        override val startTimeMs: Int,
        override val durationMs: Int
    ) : AnimationSegment()

    data class StaticPose(
        val label: String,
        val pose: BoneKeyframe,
        override val startTimeMs: Int,
        override val durationMs: Int
    ) : AnimationSegment()

    data class TransitionAnim(
        val frames: List<BoneKeyframe>,
        override val startTimeMs: Int,
        override val durationMs: Int
    ) : AnimationSegment()
}
