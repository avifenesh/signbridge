package com.signbridge.app.renderer

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.view.SurfaceHolder
import android.view.SurfaceView
import android.util.Log
import com.signbridge.app.model.*
import com.signbridge.app.translation.SignDictionary
import kotlinx.coroutines.*

/**
 * 2D sprite-based avatar renderer for video call mode.
 *
 * Uses Canvas drawing on a SurfaceView instead of OpenGL to minimize GPU
 * contention with Telegram's video decode. Lighter weight than the 3D renderer.
 *
 * Each sign/fingerspell frame maps to a pre-rendered sprite. For V1, we render
 * a simplified 2D representation: a circle (head), trapezoid (torso), and
 * line segments (arms/hands) positioned according to the keyframe bone data.
 *
 * When pre-rendered sprite sheets become available (from Agent 3), this
 * renderer can switch to blitting those directly.
 */
class SpriteAvatarRenderer(
    context: Context,
    private val surfaceView: SurfaceView
) : SurfaceHolder.Callback {

    companion object {
        private const val TAG = "SpriteRenderer"
        private const val TARGET_FPS = 30
        private const val FRAME_TIME_MS = 1000L / TARGET_FPS
    }

    private var renderJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())

    // Current animation state
    private var currentSequence: SignSequence? = null
    private var dictionary: SignDictionary? = null
    private var sequenceStartTime = 0L
    private var isAnimating = false
    private var confidenceLevel = ConfidenceLevel.HIGH

    // Paints
    private val skinPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(240, 200, 160) // Skin tone
        style = Paint.Style.FILL
    }
    private val outlinePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(80, 60, 40)
        style = Paint.Style.STROKE
        strokeWidth = 3f
    }
    private val glowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.GREEN
        style = Paint.Style.STROKE
        strokeWidth = 6f
    }
    private val bodyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(70, 130, 180) // Blue shirt
        style = Paint.Style.FILL
    }
    private val jointPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(240, 200, 160)
        style = Paint.Style.FILL
    }
    private val bgPaint = Paint().apply {
        color = Color.argb(200, 20, 20, 30)
        style = Paint.Style.FILL
    }

    // Current bone positions for 2D rendering (normalized 0-1 coordinate space)
    private val bonePositions = mutableMapOf<String, Pair<Float, Float>>()

    init {
        surfaceView.holder.addCallback(this)
        resetBonesToRest()
    }

    fun playSignSequence(sequence: SignSequence, dict: SignDictionary) {
        currentSequence = sequence
        dictionary = dict
        sequenceStartTime = System.currentTimeMillis()
        isAnimating = true
        confidenceLevel = ConfidenceLevel.from(sequence.pipelineConfidence)
    }

    fun setConfidence(level: ConfidenceLevel) {
        confidenceLevel = level
    }

    override fun surfaceCreated(holder: SurfaceHolder) {
        startRenderLoop(holder)
    }

    override fun surfaceChanged(holder: SurfaceHolder, format: Int, width: Int, height: Int) {
        // Render loop adapts to current surface size each frame
    }

    override fun surfaceDestroyed(holder: SurfaceHolder) {
        renderJob?.cancel()
        renderJob = null
    }

    private fun startRenderLoop(holder: SurfaceHolder) {
        renderJob = scope.launch {
            while (isActive) {
                val frameStart = System.currentTimeMillis()

                if (isAnimating) {
                    updateAnimation()
                }

                val canvas = holder.lockCanvas()
                if (canvas != null) {
                    try {
                        drawFrame(canvas)
                    } finally {
                        holder.unlockCanvasAndPost(canvas)
                    }
                }

                val elapsed = System.currentTimeMillis() - frameStart
                val sleep = FRAME_TIME_MS - elapsed
                if (sleep > 0) delay(sleep)
            }
        }
    }

    private fun updateAnimation() {
        val sequence = currentSequence ?: return
        val dict = dictionary ?: return
        val elapsed = (System.currentTimeMillis() - sequenceStartTime).toInt()

        // Find which sign entry is active based on elapsed time
        var timeOffset = 0
        var activeEntry: SignEntry? = null

        for (entry in sequence.entries) {
            if (elapsed >= timeOffset && elapsed < timeOffset + entry.durationMs) {
                activeEntry = entry
                break
            }
            timeOffset += entry.durationMs + 200 // 200ms transition gap
        }

        if (activeEntry == null) {
            isAnimating = false
            resetBonesToRest()
            return
        }

        when (activeEntry) {
            is SignEntry.Sign -> {
                val frames = dict.getSignFrames(activeEntry.signId) ?: return
                if (frames.isNotEmpty()) {
                    // Map bone quaternion rotations to 2D positions for sprite rendering
                    val entryElapsed = elapsed - timeOffset
                    updateBonesFrom3DFrames(frames, entryElapsed)
                }
            }
            is SignEntry.Fingerspell -> {
                val entryElapsed = elapsed - timeOffset
                val letterIdx = (entryElapsed / 400).coerceIn(0, activeEntry.letters.size - 1)
                val letter = activeEntry.letters[letterIdx]
                updateBonesForFingerspell(letter)
            }
        }
    }

    private fun drawFrame(canvas: Canvas) {
        val w = canvas.width.toFloat()
        val h = canvas.height.toFloat()

        // Background
        canvas.drawRect(0f, 0f, w, h, bgPaint)

        // Confidence glow border
        glowPaint.color = when (confidenceLevel) {
            ConfidenceLevel.HIGH -> Color.rgb(0, 200, 0)
            ConfidenceLevel.MEDIUM -> Color.rgb(255, 200, 0)
            ConfidenceLevel.LOW -> Color.rgb(255, 50, 50)
        }
        canvas.drawRect(2f, 2f, w - 2f, h - 2f, glowPaint)

        // Avatar: positioned in the center of the frame
        val cx = w * 0.5f
        val baseY = h * 0.3f  // Head center
        val scale = minOf(w, h) * 0.4f

        // Head
        canvas.drawCircle(cx, baseY, scale * 0.22f, skinPaint)
        canvas.drawCircle(cx, baseY, scale * 0.22f, outlinePaint)

        // Eyes
        val eyeY = baseY - scale * 0.03f
        canvas.drawCircle(cx - scale * 0.08f, eyeY, scale * 0.03f, outlinePaint)
        canvas.drawCircle(cx + scale * 0.08f, eyeY, scale * 0.03f, outlinePaint)

        // Torso
        val torsoTop = baseY + scale * 0.25f
        val torsoBottom = baseY + scale * 0.7f
        canvas.drawRect(cx - scale * 0.25f, torsoTop, cx + scale * 0.25f, torsoBottom, bodyPaint)

        // Arms and hands based on bone positions
        drawArm(canvas, cx, torsoTop, scale, isRight = true)
        drawArm(canvas, cx, torsoTop, scale, isRight = false)
    }

    private fun drawArm(canvas: Canvas, cx: Float, torsoTop: Float, scale: Float, isRight: Boolean) {
        val side = if (isRight) 1f else -1f
        val prefix = if (isRight) "right" else "left"

        val shoulderX = cx + side * scale * 0.25f
        val shoulderY = torsoTop + scale * 0.05f

        // Get animated positions or default
        val elbowPos = bonePositions["${prefix}_elbow"]
        val wristPos = bonePositions["${prefix}_wrist"]

        val elbowX = elbowPos?.first?.let { cx + it * scale } ?: (shoulderX + side * scale * 0.2f)
        val elbowY = elbowPos?.second?.let { torsoTop + it * scale } ?: (shoulderY + scale * 0.25f)

        val wristX = wristPos?.first?.let { cx + it * scale } ?: (elbowX + side * scale * 0.15f)
        val wristY = wristPos?.second?.let { torsoTop + it * scale } ?: (elbowY + scale * 0.2f)

        // Upper arm
        val armPaint = Paint(outlinePaint).apply { strokeWidth = scale * 0.06f; color = skinPaint.color }
        canvas.drawLine(shoulderX, shoulderY, elbowX, elbowY, armPaint)

        // Lower arm
        canvas.drawLine(elbowX, elbowY, wristX, wristY, armPaint)

        // Hand (circle at wrist)
        canvas.drawCircle(wristX, wristY, scale * 0.08f, skinPaint)
        canvas.drawCircle(wristX, wristY, scale * 0.08f, outlinePaint)

        // Joint circles
        canvas.drawCircle(elbowX, elbowY, scale * 0.03f, jointPaint)
    }

    private fun updateBonesFrom3DFrames(frames: List<BoneKeyframe>, elapsedMs: Int) {
        if (frames.isEmpty()) return

        // Find interpolation frame pair
        var frameA = frames.first()
        var frameB = frames.last()

        for (i in 0 until frames.size - 1) {
            if (elapsedMs >= frames[i].timeMs && elapsedMs < frames[i + 1].timeMs) {
                frameA = frames[i]
                frameB = frames[i + 1]
                break
            }
        }

        // For 2D sprite rendering, we project quaternion rotations to 2D positions.
        // Simplified: extract x,y components from the rotation to drive arm positions.
        for (boneName in frameA.boneRotations.keys) {
            val rotA = frameA.boneRotations[boneName] ?: Quaternion.IDENTITY
            val rotB = frameB.boneRotations[boneName] ?: rotA
            val dt = frameB.timeMs - frameA.timeMs
            val t = if (dt > 0) ((elapsedMs - frameA.timeMs).toFloat() / dt).coerceIn(0f, 1f) else 0f
            val rot = Quaternion.slerp(rotA, rotB, t)

            // Project rotation to 2D offset for the bone
            // This is a simplification: we use the x,y quaternion components as position offsets
            val shortName = boneName.replace("right_", "").replace("left_", "")
            val prefix = when {
                boneName.startsWith("right_") -> "right"
                boneName.startsWith("left_") -> "left"
                else -> continue
            }

            when (shortName) {
                "elbow" -> bonePositions["${prefix}_elbow"] = Pair(
                    rot.x * 2f * if (prefix == "right") 1f else -1f,
                    0.25f + rot.y * 0.5f
                )
                "wrist" -> bonePositions["${prefix}_wrist"] = Pair(
                    rot.x * 2.5f * if (prefix == "right") 1f else -1f,
                    0.45f + rot.y * 0.5f
                )
            }
        }
    }

    private fun updateBonesForFingerspell(letter: Char) {
        // For fingerspelling in 2D: raise the dominant (right) hand to signing position
        bonePositions["right_elbow"] = Pair(0.35f, 0.05f)
        bonePositions["right_wrist"] = Pair(0.45f, -0.15f)
        // Left arm rests
        bonePositions["left_elbow"] = Pair(-0.2f, 0.25f)
        bonePositions["left_wrist"] = Pair(-0.3f, 0.45f)
    }

    private fun resetBonesToRest() {
        bonePositions["right_elbow"] = Pair(0.2f, 0.25f)
        bonePositions["right_wrist"] = Pair(0.3f, 0.45f)
        bonePositions["left_elbow"] = Pair(-0.2f, 0.25f)
        bonePositions["left_wrist"] = Pair(-0.3f, 0.45f)
    }

    fun release() {
        renderJob?.cancel()
        scope.cancel()
    }
}
