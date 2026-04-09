package com.signbridge.app.overlay

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.graphics.Color
import android.graphics.PixelFormat
import android.opengl.GLSurfaceView
import android.os.IBinder
import android.util.Log
import android.util.TypedValue
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.core.app.NotificationCompat
import com.signbridge.app.R
import com.signbridge.app.SignBridgeApp
import com.signbridge.app.audio.AudioCaptureService
import com.signbridge.app.audio.RelayClient
import com.signbridge.app.model.*
import com.signbridge.app.renderer.AvatarRenderer
import com.signbridge.app.stt.SttPipeline
import com.signbridge.app.stt.VoskSttEngine
import com.signbridge.app.translation.AslTranslationEngine
import com.signbridge.app.translation.SignDictionary
import com.signbridge.app.ui.MainActivity
import com.signbridge.app.util.Preferences
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collectLatest

/**
 * The main overlay service. Draws the avatar, subtitle bar, confidence indicator,
 * and quick phrase buttons on top of Telegram.
 *
 * Manages the full pipeline: audio capture → VAD → STT → ASL translation → avatar animation
 */
class OverlayService : Service() {

    companion object {
        private const val TAG = "OverlayService"
        const val NOTIFICATION_ID = 2002
        const val ACTION_STOP = "com.signbridge.app.STOP_OVERLAY"
        const val ACTION_TOGGLE_EXPAND = "com.signbridge.app.TOGGLE_EXPAND"
        const val EXTRA_RELAY_CHAT_ID = "relay_chat_id"
    }

    private lateinit var windowManager: WindowManager
    private lateinit var preferences: Preferences

    // Overlay views
    private var overlayView: View? = null
    private var glSurfaceView: GLSurfaceView? = null
    private var subtitleText: TextView? = null
    private var confidenceBar: View? = null
    private var quickPhraseContainer: LinearLayout? = null

    // Renderer
    private var avatarRenderer: AvatarRenderer? = null

    // Pipeline components
    private var voskEngine: VoskSttEngine? = null
    private var translationEngine: AslTranslationEngine? = null
    private var dictionary: SignDictionary? = null
    private var pipeline: SttPipeline? = null

    // Audio capture — Path A (on-device)
    private var audioCaptureService: AudioCaptureService? = null
    private var audioServiceBound = false

    // Audio capture — Path B (relay)
    private var relayClient: RelayClient? = null

    // State
    private var isExpanded = true // Start expanded
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private val audioServiceConnection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            val service = (binder as AudioCaptureService.LocalBinder).getService()
            audioCaptureService = service
            audioServiceBound = true
            Log.i(TAG, "Audio capture service connected")
            startPipeline()
        }

        override fun onServiceDisconnected(name: ComponentName?) {
            audioCaptureService = null
            audioServiceBound = false
            Log.w(TAG, "Audio capture service disconnected")
        }
    }

    override fun onCreate() {
        super.onCreate()
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        preferences = Preferences(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_TOGGLE_EXPAND -> {
                toggleExpand()
                return START_STICKY
            }
        }

        startForeground(NOTIFICATION_ID, createNotification())
        initializeComponents()
        createOverlay()

        if (preferences!!.useRelay && preferences!!.relayUrl.isNotBlank()) {
            startRelayPath(intent)
        } else {
            bindAudioService()
        }

        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun initializeComponents() {
        // Initialize STT
        voskEngine = VoskSttEngine(this)
        scope.launch(Dispatchers.IO) {
            voskEngine?.initialize()
        }

        // Initialize translation engine
        translationEngine = AslTranslationEngine(this)
        translationEngine?.initialize()

        // Initialize dictionary
        dictionary = SignDictionary(this)
        dictionary?.load()

        // Initialize renderer
        avatarRenderer = AvatarRenderer(this)

        // Build pipeline
        pipeline = SttPipeline(voskEngine!!, translationEngine!!, dictionary!!)

        Log.i(TAG, "All components initialized")
    }

    private fun createOverlay() {
        val layoutParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
        }

        // Build overlay view programmatically
        val rootLayout = FrameLayout(this).apply {
            setBackgroundColor(Color.TRANSPARENT)
        }

        // GLSurfaceView for avatar
        glSurfaceView = GLSurfaceView(this).apply {
            setEGLContextClientVersion(2)
            setEGLConfigChooser(8, 8, 8, 8, 16, 0)
            holder.setFormat(PixelFormat.TRANSLUCENT)
            setZOrderOnTop(true)
            setRenderer(avatarRenderer)
            renderMode = if (preferences.isBatterySaver) {
                GLSurfaceView.RENDERMODE_WHEN_DIRTY
            } else {
                GLSurfaceView.RENDERMODE_CONTINUOUSLY
            }
        }
        rootLayout.addView(glSurfaceView, FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT
        ))

        // Bottom panel: subtitle + confidence + quick phrases
        val bottomPanel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.argb(200, 20, 20, 30))
            setPadding(24, 16, 24, 16)
        }

        // Confidence indicator bar
        confidenceBar = View(this).apply {
            setBackgroundColor(Color.GREEN) // High confidence default
        }
        bottomPanel.addView(confidenceBar, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 6
        ))

        // Subtitle text (always visible)
        subtitleText = TextView(this).apply {
            text = getString(R.string.label_subtitle)
            setTextColor(Color.WHITE)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, preferences.subtitleFontSizeSp.toFloat())
            setPadding(0, 12, 0, 12)
            maxLines = 3
        }
        bottomPanel.addView(subtitleText, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ))

        // Quick phrase buttons
        quickPhraseContainer = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, 8, 0, 0)
        }
        buildQuickPhraseButtons()
        bottomPanel.addView(quickPhraseContainer, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ))

        val bottomParams = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.WRAP_CONTENT
        ).apply {
            gravity = Gravity.BOTTOM
        }
        rootLayout.addView(bottomPanel, bottomParams)

        // Touch handler for expand/collapse
        rootLayout.setOnTouchListener { _, event ->
            if (event.action == MotionEvent.ACTION_DOWN) {
                toggleExpand()
                true
            } else {
                false
            }
        }

        overlayView = rootLayout
        windowManager.addView(overlayView, layoutParams)
        Log.i(TAG, "Overlay created")
    }

    private fun buildQuickPhraseButtons() {
        quickPhraseContainer?.removeAllViews()
        for (phrase in preferences.quickPhrases) {
            val btn = TextView(this).apply {
                text = phrase
                setTextColor(Color.WHITE)
                setBackgroundColor(Color.argb(150, 60, 60, 80))
                setPadding(24, 12, 24, 12)
                setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f)
                setOnClickListener { sendQuickPhrase(phrase) }
            }
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                marginEnd = 8
            }
            quickPhraseContainer?.addView(btn, params)
        }
    }

    private fun sendQuickPhrase(phrase: String) {
        // Send as Telegram message via intent
        // This opens Telegram's share/message interface
        Log.d(TAG, "Quick phrase: $phrase")
        // TODO: Integrate with Telegram message sending
        // For now, copy to clipboard as fallback
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
        val clip = android.content.ClipData.newPlainText("SignBridge", phrase)
        clipboard.setPrimaryClip(clip)
    }

    private fun toggleExpand() {
        isExpanded = !isExpanded
        // TODO: Animate between full screen and corner bubble modes
        Log.d(TAG, "Overlay ${if (isExpanded) "expanded" else "collapsed"}")
    }

    private fun bindAudioService() {
        val intent = Intent(this, AudioCaptureService::class.java)
        bindService(intent, audioServiceConnection, Context.BIND_AUTO_CREATE)
    }

    /**
     * Path B: Connect to relay server and start streaming audio.
     * The relay bot joins the Telegram call and forwards audio to us.
     */
    private fun startRelayPath(intent: Intent?) {
        val url = preferences!!.relayUrl
        val chatId = intent?.getLongExtra(EXTRA_RELAY_CHAT_ID, 0L) ?: 0L

        relayClient = RelayClient(url)

        scope.launch(Dispatchers.IO) {
            val healthy = relayClient!!.checkHealth()
            if (!healthy) {
                Log.e(TAG, "Relay server unreachable at $url — falling back to Path A")
                withContext(Dispatchers.Main) {
                    bindAudioService()
                }
                return@launch
            }

            val started = relayClient!!.startSession(chatId)
            if (!started) {
                Log.e(TAG, "Relay session failed to start — falling back to Path A")
                withContext(Dispatchers.Main) {
                    bindAudioService()
                }
                return@launch
            }

            Log.i(TAG, "Path B relay connected")
            withContext(Dispatchers.Main) {
                startPipelineWithFlow(relayClient!!.audioFlow)
            }
        }
    }

    private fun startPipeline() {
        val audioService = audioCaptureService ?: return
        startPipelineWithFlow(audioService.audioFlow)
    }

    private fun startPipelineWithFlow(audioFlow: kotlinx.coroutines.flow.SharedFlow<ShortArray>) {
        val pipe = pipeline ?: return

        // Collect sign sequences and update the renderer
        scope.launch {
            pipe.signSequences.collectLatest { sequence ->
                avatarRenderer?.playSignSequence(sequence, dictionary!!)
            }
        }

        // Collect subtitles and update the text view
        scope.launch {
            pipe.subtitles.collectLatest { text ->
                subtitleText?.text = text
            }
        }

        // Collect status and update confidence indicator
        scope.launch {
            pipe.status.collectLatest { status ->
                updateStatusUI(status)
            }
        }

        // Start processing audio from whichever path
        scope.launch(Dispatchers.IO) {
            pipe.processAudioStream(audioFlow)
        }

        Log.i(TAG, "Pipeline started")
    }

    private fun updateStatusUI(status: PipelineStatus) {
        when (status) {
            is PipelineStatus.Listening -> {
                confidenceBar?.setBackgroundColor(Color.GRAY)
            }
            is PipelineStatus.Processing -> {
                confidenceBar?.setBackgroundColor(Color.CYAN)
            }
            is PipelineStatus.Signing -> {
                val color = when (ConfidenceLevel.from(status.confidence)) {
                    ConfidenceLevel.HIGH -> Color.GREEN
                    ConfidenceLevel.MEDIUM -> Color.YELLOW
                    ConfidenceLevel.LOW -> Color.RED
                }
                confidenceBar?.setBackgroundColor(color)
            }
            is PipelineStatus.Error -> {
                confidenceBar?.setBackgroundColor(Color.RED)
                subtitleText?.text = status.fallbackText
            }
        }
    }

    override fun onDestroy() {
        scope.cancel()
        glSurfaceView?.onPause()

        if (audioServiceBound) {
            unbindService(audioServiceConnection)
            audioServiceBound = false
        }

        // Clean up Path B relay if active
        relayClient?.let { client ->
            scope.launch(Dispatchers.IO) {
                client.endSession()
                client.destroy()
            }
        }
        relayClient = null

        overlayView?.let { windowManager.removeView(it) }
        overlayView = null

        voskEngine?.release()
        pipeline?.reset()

        Log.i(TAG, "Overlay service destroyed")
        super.onDestroy()
    }

    private fun createNotification(): Notification {
        val mainIntent = Intent(this, MainActivity::class.java)
        val mainPending = PendingIntent.getActivity(
            this, 0, mainIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val stopIntent = Intent(this, OverlayService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPending = PendingIntent.getService(
            this, 1, stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, SignBridgeApp.CHANNEL_OVERLAY)
            .setContentTitle(getString(R.string.notification_overlay_title))
            .setContentText(getString(R.string.notification_overlay_text))
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(mainPending)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel,
                getString(R.string.action_stop_overlay), stopPending)
            .setOngoing(true)
            .build()
    }
}
