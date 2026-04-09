package com.signbridge.app.audio

import android.util.Log
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import okio.ByteString
import org.json.JSONObject
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.TimeUnit

/**
 * Path B relay client — connects to the SignBridge bot relay server and receives
 * audio from a Telegram call over WebSocket.
 *
 * Provides the same SharedFlow<ShortArray> interface as AudioCaptureService
 * so the STT pipeline can consume audio from either path identically.
 *
 * Usage:
 *   1. Call startSession(chatId) to tell the relay bot to join a Telegram call
 *   2. Client automatically connects the WebSocket for audio streaming
 *   3. Collect audioFlow for PCM audio chunks
 *   4. Call endSession() when done
 */
class RelayClient(
    private val relayBaseUrl: String
) {
    companion object {
        private const val TAG = "RelayClient"
        private const val CONNECT_TIMEOUT_S = 10L
        private const val READ_TIMEOUT_S = 30L
    }

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(CONNECT_TIMEOUT_S, TimeUnit.SECONDS)
        .readTimeout(READ_TIMEOUT_S, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private var sessionId: String? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private val _audioFlow = MutableSharedFlow<ShortArray>(extraBufferCapacity = 64)
    val audioFlow: SharedFlow<ShortArray> = _audioFlow

    private var _isConnected = false
    val isConnected: Boolean get() = _isConnected

    /**
     * Start a relay session: tell the bot to join the Telegram call,
     * then connect the audio WebSocket.
     *
     * @param chatId The Telegram chat ID of the call to join.
     * @return true if session started successfully.
     */
    suspend fun startSession(chatId: Long): Boolean = withContext(Dispatchers.IO) {
        try {
            // POST /session/start
            val jsonType = "application/json".toMediaType()
            val body = JSONObject().put("chat_id", chatId).toString()
                .toRequestBody(jsonType)
            val request = Request.Builder()
                .url("$relayBaseUrl/session/start")
                .post(body)
                .build()

            val response = httpClient.newCall(request).execute()
            if (!response.isSuccessful) {
                Log.e(TAG, "Start session failed: ${response.code} ${response.body?.string()}")
                return@withContext false
            }

            val json = JSONObject(response.body!!.string())
            sessionId = json.getString("session_id")
            val audioUrl = json.getString("audio_url")

            Log.i(TAG, "Session started: $sessionId")
            Log.i(TAG, "Audio WebSocket URL: $audioUrl")

            // Connect WebSocket for audio streaming
            connectAudioWebSocket(audioUrl)
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start relay session", e)
            false
        }
    }

    private fun connectAudioWebSocket(url: String) {
        val request = Request.Builder().url(url).build()

        webSocket = httpClient.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                _isConnected = true
                Log.i(TAG, "Audio WebSocket connected")
            }

            override fun onMessage(ws: WebSocket, bytes: ByteString) {
                // Relay sends raw PCM 16-bit LE audio frames
                val byteArray = bytes.toByteArray()
                val shortBuffer = ByteBuffer.wrap(byteArray)
                    .order(ByteOrder.LITTLE_ENDIAN)
                    .asShortBuffer()
                val samples = ShortArray(shortBuffer.remaining())
                shortBuffer.get(samples)

                // Emit to the same flow interface as AudioCaptureService
                _audioFlow.tryEmit(samples)
            }

            override fun onClosing(ws: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "Audio WebSocket closing: $code $reason")
                _isConnected = false
            }

            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "Audio WebSocket closed: $code $reason")
                _isConnected = false
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "Audio WebSocket error", t)
                _isConnected = false
            }
        })
    }

    /**
     * End the relay session: disconnect WebSocket and tell the bot to leave the call.
     */
    suspend fun endSession() = withContext(Dispatchers.IO) {
        val sid = sessionId ?: return@withContext

        // Close WebSocket
        webSocket?.close(1000, "session ending")
        webSocket = null
        _isConnected = false

        // POST /session/end
        try {
            val jsonType = "application/json".toMediaType()
            val body = JSONObject().put("session_id", sid).toString()
                .toRequestBody(jsonType)
            val request = Request.Builder()
                .url("$relayBaseUrl/session/end")
                .post(body)
                .build()

            httpClient.newCall(request).execute()
            Log.i(TAG, "Session ended: $sid")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to end relay session", e)
        }

        sessionId = null
    }

    /**
     * Check if the relay server is reachable.
     */
    suspend fun checkHealth(): Boolean = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$relayBaseUrl/health")
                .get()
                .build()
            val response = httpClient.newCall(request).execute()
            response.isSuccessful
        } catch (e: Exception) {
            false
        }
    }

    fun destroy() {
        webSocket?.cancel()
        webSocket = null
        _isConnected = false
        sessionId = null
        scope.cancel()
    }
}
