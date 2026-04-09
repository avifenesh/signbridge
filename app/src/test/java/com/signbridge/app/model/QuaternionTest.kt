package com.signbridge.app.model

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.abs
import kotlin.math.sqrt

class QuaternionTest {

    private fun assertQuatNear(expected: Quaternion, actual: Quaternion, eps: Float = 0.001f) {
        assertTrue("x: expected ${expected.x}, got ${actual.x}", abs(expected.x - actual.x) < eps)
        assertTrue("y: expected ${expected.y}, got ${actual.y}", abs(expected.y - actual.y) < eps)
        assertTrue("z: expected ${expected.z}, got ${actual.z}", abs(expected.z - actual.z) < eps)
        assertTrue("w: expected ${expected.w}, got ${actual.w}", abs(expected.w - actual.w) < eps)
    }

    @Test
    fun `identity quaternion`() {
        val q = Quaternion.IDENTITY
        assertEquals(0f, q.x)
        assertEquals(0f, q.y)
        assertEquals(0f, q.z)
        assertEquals(1f, q.w)
    }

    @Test
    fun `slerp t=0 returns first quaternion`() {
        val a = Quaternion(0.1f, 0.2f, 0.3f, 0.9f)
        val b = Quaternion(0.5f, 0.1f, 0.0f, 0.8f)
        val result = Quaternion.slerp(a, b, 0f)
        assertQuatNear(a, result)
    }

    @Test
    fun `slerp t=1 returns second quaternion`() {
        val a = Quaternion(0.1f, 0.2f, 0.3f, 0.9f)
        val b = Quaternion(0.5f, 0.1f, 0.0f, 0.8f)
        val result = Quaternion.slerp(a, b, 1f)
        assertQuatNear(b, result)
    }

    @Test
    fun `slerp t=0_5 is midpoint`() {
        val a = Quaternion.IDENTITY
        val b = Quaternion(0f, 0f, 0.383f, 0.924f) // ~45 degrees around Z
        val mid = Quaternion.slerp(a, b, 0.5f)
        // Midpoint should be ~22.5 degrees
        assertTrue(mid.w > 0.9f)
        assertTrue(mid.z > 0f && mid.z < b.z)
    }

    @Test
    fun `slerp identical quaternions returns same`() {
        val q = Quaternion(0.1f, 0.2f, 0.3f, 0.9f)
        val result = Quaternion.slerp(q, q, 0.5f)
        assertQuatNear(q, result, 0.02f) // Slightly looser for floating point
    }

    @Test
    fun `slerp with negative dot takes shorter path`() {
        val a = Quaternion(0f, 0f, 0f, 1f)
        val b = Quaternion(0f, 0f, 0f, -1f) // Same rotation, opposite sign
        val result = Quaternion.slerp(a, b, 0.5f)
        // Should still be close to identity (short path)
        assertTrue(abs(result.w) > 0.9f)
    }
}

class FaceParamsTest {

    @Test
    fun `neutral face params are all zero`() {
        val n = FaceParams.NEUTRAL
        assertEquals(0f, n.eyebrowRaise)
        assertEquals(0f, n.mouthOpen)
        assertEquals(0f, n.headTilt)
        assertEquals(0f, n.eyeGazeX)
        assertEquals(0f, n.cheekPuff)
    }

    @Test
    fun `lerp t=0 returns first`() {
        val a = FaceParams(0.5f, 0.3f, 0.1f, -0.2f, 0.8f)
        val b = FaceParams(0f, 0f, 0f, 0f, 0f)
        val result = FaceParams.lerp(a, b, 0f)
        assertEquals(0.5f, result.eyebrowRaise, 0.001f)
        assertEquals(0.3f, result.mouthOpen, 0.001f)
    }

    @Test
    fun `lerp t=1 returns second`() {
        val a = FaceParams(0.5f, 0.3f, 0.1f, -0.2f, 0.8f)
        val b = FaceParams(0f, 0f, 0f, 0f, 0f)
        val result = FaceParams.lerp(a, b, 1f)
        assertEquals(0f, result.eyebrowRaise, 0.001f)
    }

    @Test
    fun `lerp t=0_5 is midpoint`() {
        val a = FaceParams(1f, 0f, 0f, 0f, 0f)
        val b = FaceParams(0f, 1f, 0f, 0f, 0f)
        val result = FaceParams.lerp(a, b, 0.5f)
        assertEquals(0.5f, result.eyebrowRaise, 0.001f)
        assertEquals(0.5f, result.mouthOpen, 0.001f)
    }
}

class ConfidenceLevelTest {

    @Test
    fun `high confidence above 0_7`() {
        assertEquals(ConfidenceLevel.HIGH, ConfidenceLevel.from(0.8f))
        assertEquals(ConfidenceLevel.HIGH, ConfidenceLevel.from(1.0f))
        assertEquals(ConfidenceLevel.HIGH, ConfidenceLevel.from(0.7f))
    }

    @Test
    fun `medium confidence between 0_3 and 0_7`() {
        assertEquals(ConfidenceLevel.MEDIUM, ConfidenceLevel.from(0.5f))
        assertEquals(ConfidenceLevel.MEDIUM, ConfidenceLevel.from(0.3f))
    }

    @Test
    fun `low confidence below 0_3`() {
        assertEquals(ConfidenceLevel.LOW, ConfidenceLevel.from(0.2f))
        assertEquals(ConfidenceLevel.LOW, ConfidenceLevel.from(0.0f))
    }
}
