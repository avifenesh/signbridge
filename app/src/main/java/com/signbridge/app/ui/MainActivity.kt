package com.signbridge.app.ui

import android.app.Activity
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.signbridge.app.R
import com.signbridge.app.audio.AudioCaptureService
import com.signbridge.app.overlay.OverlayService
import com.signbridge.app.util.Preferences

/**
 * Main activity — home screen.
 *
 * Shows:
 * - Status (ready / always-ready / overlay active)
 * - Start overlay button
 * - Quick phrases customization
 * - Settings link
 */
class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MainActivity"
    }

    private lateinit var preferences: Preferences

    private lateinit var statusText: TextView
    private lateinit var startButton: Button
    private lateinit var alwaysReadyButton: Button
    private lateinit var settingsButton: Button

    // MediaProjection result for audio capture
    private var mediaProjectionResultCode: Int = -1
    private var mediaProjectionResultData: Intent? = null

    private val overlayPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        if (Settings.canDrawOverlays(this)) {
            Log.i(TAG, "Overlay permission granted")
            updateUI()
        } else {
            Toast.makeText(this, "Overlay permission required", Toast.LENGTH_SHORT).show()
        }
    }

    private val mediaProjectionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            mediaProjectionResultCode = result.resultCode
            mediaProjectionResultData = result.data
            Log.i(TAG, "MediaProjection permission granted")
            startServices()
        } else {
            Toast.makeText(this, "Audio capture permission required", Toast.LENGTH_SHORT).show()
        }
    }

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            Log.i(TAG, "Notification permission granted")
        }
        updateUI()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        preferences = Preferences(this)

        // Check if setup is needed
        if (!preferences.isSetupComplete) {
            startActivity(Intent(this, SetupActivity::class.java))
            finish()
            return
        }

        buildUI()
        updateUI()
    }

    override fun onResume() {
        super.onResume()
        updateUI()
    }

    private fun buildUI() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 48, 48, 48)
        }

        // App title
        root.addView(TextView(this).apply {
            text = "SignBridge"
            textSize = 28f
            setPadding(0, 0, 0, 16)
        })

        // Status
        statusText = TextView(this).apply {
            text = "Ready"
            textSize = 16f
            setPadding(0, 0, 0, 32)
        }
        root.addView(statusText)

        // Demo button — test avatar without Telegram (no credentials needed)
        Button(this).apply {
            text = "Try Demo — Type & Sign"
            setBackgroundColor(android.graphics.Color.rgb(21, 101, 192))
            setTextColor(android.graphics.Color.WHITE)
            setOnClickListener {
                startActivity(Intent(this@MainActivity, DemoActivity::class.java))
            }
        }.also {
            root.addView(it, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = 24 })
        }

        // Start button
        startButton = Button(this).apply {
            text = getString(R.string.action_start_overlay)
            setOnClickListener { onStartOverlay() }
        }
        root.addView(startButton, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { bottomMargin = 16 })

        // Always ready toggle
        alwaysReadyButton = Button(this).apply {
            text = "Always Ready: OFF"
            setOnClickListener { toggleAlwaysReady() }
        }
        root.addView(alwaysReadyButton, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { bottomMargin = 16 })

        // Settings
        settingsButton = Button(this).apply {
            text = getString(R.string.action_settings)
            setOnClickListener {
                startActivity(Intent(this@MainActivity,
                    com.signbridge.app.settings.SettingsActivity::class.java))
            }
        }
        root.addView(settingsButton, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ))

        setContentView(root)
    }

    private fun updateUI() {
        val overlayPermission = Settings.canDrawOverlays(this)
        val isOverlayRunning = OverlayService.NOTIFICATION_ID > 0 // TODO: proper check

        val relayConfigured = preferences.relayUrl.isNotBlank()
        statusText.text = when {
            !overlayPermission -> "Overlay permission needed"
            preferences.alwaysReadyEnabled -> "Always Ready — waiting for call"
            preferences.useRelay && !relayConfigured -> "Set relay URL in Settings"
            preferences.useRelay -> "Ready (relay: ${preferences.relayUrl})"
            else -> "Ready (on-device capture — experimental)"
        }

        startButton.isEnabled = overlayPermission
        alwaysReadyButton.text = if (preferences.alwaysReadyEnabled) {
            "Always Ready: ON"
        } else {
            "Always Ready: OFF"
        }
    }

    private fun onStartOverlay() {
        // Check overlay permission
        if (!Settings.canDrawOverlays(this)) {
            val intent = Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:$packageName")
            )
            overlayPermissionLauncher.launch(intent)
            return
        }

        // Check notification permission (Android 13+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
                != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                notificationPermissionLauncher.launch(android.Manifest.permission.POST_NOTIFICATIONS)
                return
            }
        }

        // If Always-Ready is active, capture service is already running — just start overlay
        if (preferences.alwaysReadyEnabled) {
            val overlayIntent = Intent(this, OverlayService::class.java)
            startForegroundService(overlayIntent)
            Toast.makeText(this, "SignBridge overlay started (Always Ready)", Toast.LENGTH_SHORT).show()
            updateUI()
            return
        }

        // Path B (relay) is the default — no MediaProjection needed
        if (preferences.useRelay) {
            if (preferences.relayUrl.isBlank()) {
                Toast.makeText(this, "Set relay server URL in Settings first", Toast.LENGTH_LONG).show()
                return
            }
            val overlayIntent = Intent(this, OverlayService::class.java)
            startForegroundService(overlayIntent)
            Toast.makeText(this, "SignBridge overlay started (relay mode)", Toast.LENGTH_SHORT).show()
            updateUI()
            return
        }

        // Path A fallback (unlikely to work with voice calls, but kept for experimentation)
        val projectionManager = getSystemService(MediaProjectionManager::class.java)
        mediaProjectionLauncher.launch(projectionManager.createScreenCaptureIntent())
    }

    private fun startServices() {
        val resultData = mediaProjectionResultData ?: return

        // Start audio capture service
        val captureIntent = Intent(this, AudioCaptureService::class.java).apply {
            putExtra(AudioCaptureService.EXTRA_RESULT_CODE, mediaProjectionResultCode)
            putExtra(AudioCaptureService.EXTRA_RESULT_DATA, resultData)
        }
        startForegroundService(captureIntent)

        // Start overlay service
        val overlayIntent = Intent(this, OverlayService::class.java)
        startForegroundService(overlayIntent)

        Toast.makeText(this, "SignBridge overlay started", Toast.LENGTH_SHORT).show()
        updateUI()
    }

    private fun toggleAlwaysReady() {
        if (preferences.alwaysReadyEnabled) {
            // Turn off: stop the background audio capture
            preferences.alwaysReadyEnabled = false
            val stopIntent = Intent(this, AudioCaptureService::class.java)
            stopService(stopIntent)
            Toast.makeText(this, "Always Ready mode OFF", Toast.LENGTH_SHORT).show()
        } else {
            // Turn on: request MediaProjection now, keep AudioCaptureService running
            // so the overlay can bind to it instantly when a call starts
            if (!Settings.canDrawOverlays(this)) {
                Toast.makeText(this, "Grant overlay permission first", Toast.LENGTH_SHORT).show()
                return
            }
            // Request MediaProjection — the callback will start the capture service
            val projectionManager = getSystemService(MediaProjectionManager::class.java)
            alwaysReadyProjectionLauncher.launch(projectionManager.createScreenCaptureIntent())
        }
        updateUI()
    }

    /** MediaProjection result handler for Always-Ready mode */
    private val alwaysReadyProjectionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK && result.data != null) {
            preferences.alwaysReadyEnabled = true

            // Start audio capture in background (no overlay yet)
            val captureIntent = Intent(this, AudioCaptureService::class.java).apply {
                putExtra(AudioCaptureService.EXTRA_RESULT_CODE, result.resultCode)
                putExtra(AudioCaptureService.EXTRA_RESULT_DATA, result.data)
            }
            startForegroundService(captureIntent)

            Toast.makeText(this, "Always Ready mode ON — capture active in background", Toast.LENGTH_LONG).show()
            updateUI()
        } else {
            Toast.makeText(this, "Permission denied — Always Ready requires screen capture", Toast.LENGTH_LONG).show()
        }
    }
}
