package com.signbridge.app.renderer

import android.opengl.GLES20
import android.opengl.Matrix
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.nio.ShortBuffer

/**
 * In-memory representation of a skinned GLTF mesh, ready for GL rendering.
 *
 * Holds:
 *  - Vertex data: positions, normals, joint indices, joint weights
 *  - Index buffer for indexed drawing
 *  - Skin: inverse bind matrices per joint, joint-to-bone name mapping
 *
 * After loading, call [uploadToGpu] once on the GL thread, then [draw] each frame.
 */
class GltfModel {

    companion object {
        const val MAX_JOINTS = 48
        const val FLOATS_PER_POSITION = 3
        const val FLOATS_PER_NORMAL = 3
        const val FLOATS_PER_JOINT_IDX = 4  // 4 joint influences
        const val FLOATS_PER_WEIGHT = 4     // 4 weights
    }

    // CPU-side data (set by GltfLoader)
    var positions: FloatArray = floatArrayOf()
    var normals: FloatArray = floatArrayOf()
    var jointIndices: FloatArray = floatArrayOf() // stored as float for GLES20 compatibility
    var jointWeights: FloatArray = floatArrayOf()
    var indices: ShortArray = shortArrayOf()

    var vertexCount: Int = 0
    var indexCount: Int = 0

    // Skin data
    var inverseBindMatrices: FloatArray = floatArrayOf() // MAX_JOINTS * 16 floats
    var jointNames: List<String> = emptyList()           // bone name per joint index

    // GPU handles
    private var posVbo = 0
    private var normVbo = 0
    private var jointIdxVbo = 0
    private var weightVbo = 0
    private var ebo = 0
    private var uploaded = false

    // Current joint matrices (set each frame by the animation system)
    val jointMatrices = FloatArray(MAX_JOINTS * 16).apply {
        // Initialize to identity
        for (i in 0 until MAX_JOINTS) {
            Matrix.setIdentityM(this, i * 16)
        }
    }

    /**
     * Upload vertex/index data to GPU. Call once on the GL thread after loading.
     */
    fun uploadToGpu() {
        if (uploaded) return
        if (vertexCount == 0) return

        val vbos = IntArray(4)
        GLES20.glGenBuffers(4, vbos, 0)
        posVbo = vbos[0]; normVbo = vbos[1]; jointIdxVbo = vbos[2]; weightVbo = vbos[3]

        uploadBuffer(posVbo, positions)
        uploadBuffer(normVbo, normals)
        uploadBuffer(jointIdxVbo, jointIndices)
        uploadBuffer(weightVbo, jointWeights)

        val iboArr = IntArray(1)
        GLES20.glGenBuffers(1, iboArr, 0)
        ebo = iboArr[0]

        val idxBuf = ByteBuffer.allocateDirect(indices.size * 2)
            .order(ByteOrder.nativeOrder()).asShortBuffer()
        idxBuf.put(indices).position(0)
        GLES20.glBindBuffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, ebo)
        GLES20.glBufferData(GLES20.GL_ELEMENT_ARRAY_BUFFER, indices.size * 2, idxBuf, GLES20.GL_STATIC_DRAW)

        uploaded = true
    }

    /**
     * Update joint matrices from the current animation pose.
     * Call this each frame before [draw].
     *
     * @param boneRotations map of bone name → world-space 4×4 matrix
     */
    fun applyPose(boneMatrices: Map<String, FloatArray>) {
        for ((idx, name) in jointNames.withIndex()) {
            if (idx >= MAX_JOINTS) break
            val worldMat = boneMatrices[name]
            if (worldMat != null) {
                // finalMatrix = worldMatrix * inverseBindMatrix
                val ibm = FloatArray(16)
                System.arraycopy(inverseBindMatrices, idx * 16, ibm, 0, 16)

                val result = FloatArray(16)
                Matrix.multiplyMM(result, 0, worldMat, 0, ibm, 0)
                System.arraycopy(result, 0, jointMatrices, idx * 16, 16)
            } else {
                // Identity if bone not animated
                Matrix.setIdentityM(jointMatrices, idx * 16)
            }
        }
    }

    /**
     * Bind vertex attributes and draw the skinned mesh.
     * Shader must already be active and MVP + joint uniforms set.
     */
    fun draw(shader: ShaderProgram) {
        if (!uploaded || indexCount == 0) return

        bindAttribute(shader, "a_position", posVbo, FLOATS_PER_POSITION)
        bindAttribute(shader, "a_normal", normVbo, FLOATS_PER_NORMAL)
        bindAttribute(shader, "a_joints", jointIdxVbo, FLOATS_PER_JOINT_IDX)
        bindAttribute(shader, "a_weights", weightVbo, FLOATS_PER_WEIGHT)

        GLES20.glBindBuffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, ebo)
        GLES20.glDrawElements(GLES20.GL_TRIANGLES, indexCount, GLES20.GL_UNSIGNED_SHORT, 0)

        // Disable attribs
        disableAttribute(shader, "a_position")
        disableAttribute(shader, "a_normal")
        disableAttribute(shader, "a_joints")
        disableAttribute(shader, "a_weights")
    }

    fun release() {
        if (uploaded) {
            GLES20.glDeleteBuffers(4, intArrayOf(posVbo, normVbo, jointIdxVbo, weightVbo), 0)
            GLES20.glDeleteBuffers(1, intArrayOf(ebo), 0)
            uploaded = false
        }
    }

    private fun uploadBuffer(vbo: Int, data: FloatArray) {
        val buf = ByteBuffer.allocateDirect(data.size * 4)
            .order(ByteOrder.nativeOrder()).asFloatBuffer()
        buf.put(data).position(0)
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vbo)
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, data.size * 4, buf, GLES20.GL_STATIC_DRAW)
    }

    private fun bindAttribute(shader: ShaderProgram, name: String, vbo: Int, size: Int) {
        val loc = shader.getAttribLocation(name)
        if (loc < 0) return
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vbo)
        GLES20.glEnableVertexAttribArray(loc)
        GLES20.glVertexAttribPointer(loc, size, GLES20.GL_FLOAT, false, 0, 0)
    }

    private fun disableAttribute(shader: ShaderProgram, name: String) {
        val loc = shader.getAttribLocation(name)
        if (loc >= 0) GLES20.glDisableVertexAttribArray(loc)
    }
}
