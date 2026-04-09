package com.signbridge.app.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.signbridge.app.R
import com.signbridge.app.util.Preferences
import kotlinx.coroutines.*
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipInputStream

/**
 * First-launch setup flow.
 *
 * Steps:
 * 1. Grant overlay permission (SYSTEM_ALERT_WINDOW)
 * 2. Grant notification permission (Android 13+)
 * 3. Download Vosk English model (~50MB)
 * 4. Optional: enter cloud STT API key
 */
class SetupActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "SetupActivity"
        private const val VOSK_MODEL_URL =
            "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
        private const val VOSK_MODEL_DIR = "vosk-model"
        private const val MINILM_MODEL_DIR = "minilm"
        private const val MINILM_MODEL_URL =
            "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/onnx/model.onnx"
        private const val MINILM_VOCAB_URL =
            "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/vocab.txt"
    }

    private lateinit var preferences: Preferences
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private lateinit var statusText: TextView
    private lateinit var overlayBtn: Button
    private lateinit var notificationBtn: Button
    private lateinit var downloadBtn: Button
    private lateinit var downloadProgress: ProgressBar
    private lateinit var doneBtn: Button

    private val overlayPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        updateUI()
    }

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) {
        updateUI()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        preferences = Preferences(this)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 64, 48, 48)
        }

        root.addView(TextView(this).apply {
            text = getString(R.string.setup_welcome)
            textSize = 24f
            setPadding(0, 0, 0, 8)
        })

        root.addView(TextView(this).apply {
            text = getString(R.string.setup_permissions)
            textSize = 14f
            setPadding(0, 0, 0, 32)
        })

        // Step 1: Overlay permission
        overlayBtn = Button(this).apply {
            text = getString(R.string.setup_overlay_permission)
            setOnClickListener {
                val intent = Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:$packageName")
                )
                overlayPermissionLauncher.launch(intent)
            }
        }
        root.addView(overlayBtn, buttonParams())

        // Step 2: Notification permission
        notificationBtn = Button(this).apply {
            text = getString(R.string.setup_notification_permission)
            setOnClickListener {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                }
            }
        }
        root.addView(notificationBtn, buttonParams())

        // Step 3: Download models
        downloadBtn = Button(this).apply {
            text = getString(R.string.setup_download_models)
            setOnClickListener { downloadModels() }
        }
        root.addView(downloadBtn, buttonParams())

        downloadProgress = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            visibility = View.GONE
            max = 100
        }
        root.addView(downloadProgress, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { bottomMargin = 16 })

        statusText = TextView(this).apply {
            text = ""
            textSize = 12f
            setPadding(0, 0, 0, 24)
        }
        root.addView(statusText)

        // Step 4: Relay server URL (Path B — required)
        root.addView(TextView(this).apply {
            text = "Relay Server (required for call audio)"
            textSize = 16f
            setPadding(0, 16, 0, 4)
        })
        root.addView(TextView(this).apply {
            text = "A relay bot joins your Telegram call and streams audio to this app. " +
                "Self-host from github.com/signbridge or use a community server."
            textSize = 12f
            setPadding(0, 0, 0, 8)
        })
        val relayUrlField = android.widget.EditText(this).apply {
            hint = "Relay URL (e.g. http://192.168.1.100:8080)"
            setText(preferences.relayUrl)
            setOnFocusChangeListener { _, hasFocus ->
                if (!hasFocus) preferences.relayUrl = text.toString().trimEnd('/')
            }
        }
        root.addView(relayUrlField, buttonParams())

        // Done
        doneBtn = Button(this).apply {
            text = getString(R.string.setup_complete)
            isEnabled = false
            setOnClickListener {
                // Save relay URL from field
                preferences.relayUrl = relayUrlField.text.toString().trimEnd('/')
                preferences.isSetupComplete = true
                startActivity(Intent(this@SetupActivity, MainActivity::class.java))
                finish()
            }
        }
        root.addView(doneBtn, buttonParams())

        setContentView(root)
        updateUI()
    }

    private fun buttonParams() = LinearLayout.LayoutParams(
        LinearLayout.LayoutParams.MATCH_PARENT,
        LinearLayout.LayoutParams.WRAP_CONTENT
    ).apply { bottomMargin = 16 }

    private fun updateUI() {
        val hasOverlay = Settings.canDrawOverlays(this)
        val hasNotification = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        } else true
        val hasModels = preferences.isModelsDownloaded

        overlayBtn.isEnabled = !hasOverlay
        overlayBtn.text = if (hasOverlay) "Overlay permission granted" else getString(R.string.setup_overlay_permission)

        notificationBtn.isEnabled = !hasNotification
        notificationBtn.text = if (hasNotification) "Notification permission granted" else getString(R.string.setup_notification_permission)
        notificationBtn.visibility = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) View.VISIBLE else View.GONE

        downloadBtn.isEnabled = !hasModels
        downloadBtn.text = if (hasModels) "Models downloaded" else getString(R.string.setup_download_models)

        doneBtn.isEnabled = hasOverlay && hasNotification && hasModels
    }

    private fun downloadModels() {
        downloadBtn.isEnabled = false
        downloadProgress.visibility = View.VISIBLE
        statusText.text = "Downloading Vosk English model..."

        scope.launch(Dispatchers.IO) {
            try {
                val client = OkHttpClient()
                val request = Request.Builder().url(VOSK_MODEL_URL).build()
                val response = client.newCall(request).execute()

                if (!response.isSuccessful) {
                    withContext(Dispatchers.Main) {
                        statusText.text = "Download failed: ${response.code}"
                        downloadBtn.isEnabled = true
                    }
                    return@launch
                }

                val body = response.body ?: return@launch
                val totalBytes = body.contentLength()
                val modelDir = File(filesDir, VOSK_MODEL_DIR)

                // Extract zip directly
                val inputStream = body.byteStream()
                val zipStream = ZipInputStream(inputStream)
                var entry = zipStream.nextEntry
                var bytesRead = 0L

                while (entry != null) {
                    val outFile = File(modelDir, entry.name.substringAfter("/"))
                    if (entry.isDirectory) {
                        outFile.mkdirs()
                    } else {
                        outFile.parentFile?.mkdirs()
                        FileOutputStream(outFile).use { fos ->
                            val buffer = ByteArray(8192)
                            var len: Int
                            while (zipStream.read(buffer).also { len = it } > 0) {
                                fos.write(buffer, 0, len)
                                bytesRead += len
                                if (totalBytes > 0) {
                                    val progress = ((bytesRead * 100) / totalBytes).toInt()
                                    withContext(Dispatchers.Main) {
                                        downloadProgress.progress = progress.coerceAtMost(100)
                                    }
                                }
                            }
                        }
                    }
                    zipStream.closeEntry()
                    entry = zipStream.nextEntry
                }
                zipStream.close()

                withContext(Dispatchers.Main) {
                    statusText.text = "Vosk model ready. Downloading MiniLM embeddings..."
                    downloadProgress.progress = 80
                }
                Log.i(TAG, "Vosk model downloaded to ${modelDir.absolutePath}")

                // Download MiniLM model for Tier 2 vector similarity
                try {
                    val miniLmDir = File(filesDir, MINILM_MODEL_DIR)
                    miniLmDir.mkdirs()

                    // Download model.onnx
                    val modelReq = Request.Builder().url(MINILM_MODEL_URL).build()
                    val modelResp = client.newCall(modelReq).execute()
                    if (modelResp.isSuccessful) {
                        File(miniLmDir, "model.onnx").outputStream().use { out ->
                            modelResp.body?.byteStream()?.copyTo(out)
                        }
                        Log.i(TAG, "MiniLM model downloaded")
                    }

                    // Download vocab.txt
                    val vocabReq = Request.Builder().url(MINILM_VOCAB_URL).build()
                    val vocabResp = client.newCall(vocabReq).execute()
                    if (vocabResp.isSuccessful) {
                        File(miniLmDir, "vocab.txt").outputStream().use { out ->
                            vocabResp.body?.byteStream()?.copyTo(out)
                        }
                        Log.i(TAG, "MiniLM vocab downloaded")
                    }
                } catch (e: Exception) {
                    Log.w(TAG, "MiniLM download failed (non-fatal, BoW fallback available)", e)
                }

                withContext(Dispatchers.Main) {
                    preferences.isModelsDownloaded = true
                    statusText.text = "All models downloaded"
                    downloadProgress.progress = 100
                    updateUI()
                }

            } catch (e: Exception) {
                Log.e(TAG, "Model download failed", e)
                withContext(Dispatchers.Main) {
                    statusText.text = "Download failed: ${e.message}"
                    downloadBtn.isEnabled = true
                    downloadProgress.visibility = View.GONE
                }
            }
        }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
