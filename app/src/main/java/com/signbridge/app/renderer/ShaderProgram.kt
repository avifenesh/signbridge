package com.signbridge.app.renderer

import android.content.Context
import android.opengl.GLES20
import android.util.Log

/**
 * Compiles and links a GLSL vertex+fragment shader pair.
 * Provides uniform/attribute location lookups with caching.
 */
class ShaderProgram(
    context: Context,
    vertexAsset: String,
    fragmentAsset: String
) {
    companion object {
        private const val TAG = "ShaderProgram"
    }

    val programId: Int

    private val uniformLocations = mutableMapOf<String, Int>()
    private val attribLocations = mutableMapOf<String, Int>()

    init {
        val vertSrc = context.assets.open(vertexAsset).bufferedReader().readText()
        val fragSrc = context.assets.open(fragmentAsset).bufferedReader().readText()
        programId = createProgram(vertSrc, fragSrc)
    }

    fun use() {
        GLES20.glUseProgram(programId)
    }

    fun getUniformLocation(name: String): Int =
        uniformLocations.getOrPut(name) {
            GLES20.glGetUniformLocation(programId, name).also {
                if (it == -1) Log.w(TAG, "Uniform '$name' not found")
            }
        }

    fun getAttribLocation(name: String): Int =
        attribLocations.getOrPut(name) {
            GLES20.glGetAttribLocation(programId, name).also {
                if (it == -1) Log.w(TAG, "Attribute '$name' not found")
            }
        }

    fun setUniformMatrix4fv(name: String, matrix: FloatArray) {
        GLES20.glUniformMatrix4fv(getUniformLocation(name), 1, false, matrix, 0)
    }

    fun setUniformMatrix4fvArray(name: String, matrices: FloatArray, count: Int) {
        GLES20.glUniformMatrix4fv(getUniformLocation(name), count, false, matrices, 0)
    }

    fun setUniform3f(name: String, x: Float, y: Float, z: Float) {
        GLES20.glUniform3f(getUniformLocation(name), x, y, z)
    }

    fun setUniform4f(name: String, x: Float, y: Float, z: Float, w: Float) {
        GLES20.glUniform4f(getUniformLocation(name), x, y, z, w)
    }

    fun setUniform1f(name: String, v: Float) {
        GLES20.glUniform1f(getUniformLocation(name), v)
    }

    fun setUniform1i(name: String, v: Int) {
        GLES20.glUniform1i(getUniformLocation(name), v)
    }

    fun release() {
        GLES20.glDeleteProgram(programId)
    }

    private fun createProgram(vertSrc: String, fragSrc: String): Int {
        val vertShader = compileShader(GLES20.GL_VERTEX_SHADER, vertSrc)
        val fragShader = compileShader(GLES20.GL_FRAGMENT_SHADER, fragSrc)

        val program = GLES20.glCreateProgram()
        GLES20.glAttachShader(program, vertShader)
        GLES20.glAttachShader(program, fragShader)
        GLES20.glLinkProgram(program)

        val linkStatus = IntArray(1)
        GLES20.glGetProgramiv(program, GLES20.GL_LINK_STATUS, linkStatus, 0)
        if (linkStatus[0] == 0) {
            val log = GLES20.glGetProgramInfoLog(program)
            GLES20.glDeleteProgram(program)
            throw RuntimeException("Program link failed: $log")
        }

        // Shaders can be detached after linking
        GLES20.glDetachShader(program, vertShader)
        GLES20.glDetachShader(program, fragShader)
        GLES20.glDeleteShader(vertShader)
        GLES20.glDeleteShader(fragShader)

        Log.d(TAG, "Shader program linked ($vertShader, $fragShader) → $program")
        return program
    }

    private fun compileShader(type: Int, source: String): Int {
        val shader = GLES20.glCreateShader(type)
        GLES20.glShaderSource(shader, source)
        GLES20.glCompileShader(shader)

        val compileStatus = IntArray(1)
        GLES20.glGetShaderiv(shader, GLES20.GL_COMPILE_STATUS, compileStatus, 0)
        if (compileStatus[0] == 0) {
            val log = GLES20.glGetShaderInfoLog(shader)
            GLES20.glDeleteShader(shader)
            val typeName = if (type == GLES20.GL_VERTEX_SHADER) "vertex" else "fragment"
            throw RuntimeException("$typeName shader compile failed: $log")
        }
        return shader
    }
}
