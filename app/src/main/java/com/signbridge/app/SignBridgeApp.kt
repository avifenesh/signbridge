package com.signbridge.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

class SignBridgeApp : Application() {

    companion object {
        const val CHANNEL_OVERLAY = "signbridge_overlay"
        const val CHANNEL_CAPTURE = "signbridge_capture"
        const val CHANNEL_READY = "signbridge_ready"
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        val manager = getSystemService(NotificationManager::class.java)

        val overlayChannel = NotificationChannel(
            CHANNEL_OVERLAY,
            getString(R.string.channel_overlay),
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Shows when the SignBridge overlay is active"
            setShowBadge(false)
        }

        val captureChannel = NotificationChannel(
            CHANNEL_CAPTURE,
            getString(R.string.channel_capture),
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Shows when audio capture is active"
            setShowBadge(false)
        }

        val readyChannel = NotificationChannel(
            CHANNEL_READY,
            "Always Ready",
            NotificationManager.IMPORTANCE_MIN
        ).apply {
            description = "Shows when always-ready mode is active"
            setShowBadge(false)
        }

        manager.createNotificationChannels(listOf(overlayChannel, captureChannel, readyChannel))
    }
}
