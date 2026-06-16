package com.aideck.transfer

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.*

class MainActivity : AppCompatActivity(), BleManager.BleCallback {

    private lateinit var bleManager: BleManager
    private lateinit var btnConnect: Button
    private lateinit var btnSelectImage: Button
    private lateinit var btnSelectGif: Button
    private lateinit var btnClear: Button
    private lateinit var tvStatus: TextView
    private lateinit var tvDeviceInfo: TextView
    private lateinit var progressBar: ProgressBar
    private lateinit var ivPreview: ImageView

    private var selectedUri: Uri? = null
    private var isGif = false
    private var connected = false

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    // 图片选择
    private val imagePicker = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val uri = result.data?.data ?: return@registerForActivityResult
            selectedUri = uri
            isGif = ImageConverter.isGif(this, uri)

            ivPreview.setImageURI(uri)
            tvStatus.text = if (isGif) "已选择: GIF 动图，开始传输..." else "已选择: 静态图片，开始传输..."

            // 自动发送
            if (connected && bleManager.isReady()) {
                sendSelectedImage()
            }
        }
    }

    // 权限请求
    private val permissionLauncher = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { permissions ->
        val allGranted = permissions.all { it.value }
        if (allGranted) {
            startBleScan()
        } else {
            tvStatus.text = "需要蓝牙和存储权限"
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        bleManager = BleManager(this)
        bleManager.setCallback(this)

        initViews()
    }

    private fun initViews() {
        btnConnect = findViewById(R.id.btn_connect)
        btnSelectImage = findViewById(R.id.btn_select_image)
        btnSelectGif = findViewById(R.id.btn_select_gif)
        btnClear = findViewById(R.id.btn_clear)
        tvStatus = findViewById(R.id.tv_status)
        tvDeviceInfo = findViewById(R.id.tv_device_info)
        progressBar = findViewById(R.id.progress_bar)
        ivPreview = findViewById(R.id.iv_preview)

        btnConnect.setOnClickListener {
            if (connected) {
                bleManager.disconnect()
            } else {
                checkPermissionsAndScan()
            }
        }

        btnSelectImage.setOnClickListener {
            if (!connected) {
                tvStatus.text = "请先连接设备"
                return@setOnClickListener
            }
            openImagePicker("image/*")
        }

        btnSelectGif.setOnClickListener {
            if (!connected) {
                tvStatus.text = "请先连接设备"
                return@setOnClickListener
            }
            openImagePicker("image/gif")
        }

        btnClear.setOnClickListener {
            if (connected) {
                bleManager.clearScreen()
                tvStatus.text = "已发送清屏命令"
            }
        }

        updateUI()
    }

    private fun openImagePicker(type: String) {
        val intent = Intent(Intent.ACTION_PICK, MediaStore.Images.Media.EXTERNAL_CONTENT_URI)
        intent.type = type
        imagePicker.launch(intent)
    }

    private fun checkPermissionsAndScan() {
        val perms = mutableListOf<String>()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) != PackageManager.PERMISSION_GRANTED)
                perms.add(Manifest.permission.BLUETOOTH_SCAN)
            if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED)
                perms.add(Manifest.permission.BLUETOOTH_CONNECT)
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (checkSelfPermission(Manifest.permission.READ_MEDIA_IMAGES) != PackageManager.PERMISSION_GRANTED)
                perms.add(Manifest.permission.READ_MEDIA_IMAGES)
        } else {
            if (checkSelfPermission(Manifest.permission.READ_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED)
                perms.add(Manifest.permission.READ_EXTERNAL_STORAGE)
        }

        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED)
            perms.add(Manifest.permission.ACCESS_FINE_LOCATION)

        if (perms.isNotEmpty()) {
            permissionLauncher.launch(perms.toTypedArray())
        } else {
            startBleScan()
        }
    }

    private fun startBleScan() {
        tvStatus.text = "正在扫描..."
        btnConnect.isEnabled = false
        bleManager.startScan()
    }

    private fun updateUI() {
        btnConnect.text = if (connected) "断开连接" else "搜索设备"
        btnConnect.isEnabled = true

        btnSelectImage.isEnabled = connected
        btnSelectGif.isEnabled = connected
        btnClear.isEnabled = connected

        if (connected) {
            tvDeviceInfo.text = "AI-Agent-Deck 已连接"
            tvDeviceInfo.setTextColor(0xFF4CAF50.toInt())
        } else {
            tvDeviceInfo.text = "未连接"
            tvDeviceInfo.setTextColor(0xFFF44336.toInt())
        }
    }

    private fun sendSelectedImage() {
        val uri = selectedUri ?: return
        if (!bleManager.isReady()) {
            tvStatus.text = "设备未就绪"
            return
        }

        btnSelectImage.isEnabled = false
        btnSelectGif.isEnabled = false
        progressBar.visibility = android.view.View.VISIBLE

        scope.launch {
            try {
                val success = withContext(Dispatchers.IO) {
                    if (isGif) {
                        sendGif(uri)
                    } else {
                        sendStaticImage(uri)
                    }
                }

                tvStatus.text = if (success) "发送成功!" else "发送失败"
            } catch (e: Exception) {
                tvStatus.text = "错误: ${e.message}"
                e.printStackTrace()
            } finally {
                progressBar.visibility = android.view.View.GONE
                btnSelectImage.isEnabled = connected && !isGif
                btnSelectGif.isEnabled = connected && isGif
            }
        }
    }

    private fun sendStaticImage(uri: Uri): Boolean {
        val data = ImageConverter.loadStaticImage(this, uri) ?: return false
        runOnUiThread { tvStatus.text = "发送图片中... (${data.size} bytes)" }
        return bleManager.sendImage(data) { current, total ->
            runOnUiThread {
                progressBar.max = total
                progressBar.progress = current
                tvStatus.text = "发送中: $current/$total 包"
            }
        }
    }

    private fun sendGif(uri: Uri): Boolean {
        val frames = ImageConverter.loadGif(this, uri) ?: return false
        runOnUiThread { tvStatus.text = "发送GIF: ${frames.size} 帧" }

        val frameDataList = frames.map { it.rgb565 }
        val delay = frames.firstOrNull()?.delayMs ?: 100

        return bleManager.sendGif(frameDataList, delay) { current, total ->
            runOnUiThread {
                progressBar.max = total
                progressBar.progress = current
                tvStatus.text = "GIF帧: $current/$total"
            }
        }
    }

    // ── BleCallback ──────────────────────────

    override fun onConnected() {
        connected = true
        runOnUiThread {
            tvStatus.text = "已连接 AI-Agent-Deck"
            updateUI()

            // 如果已选择图片，自动启用发送按钮
            if (selectedUri != null) {
                btnSelectImage.isEnabled = !isGif
                btnSelectGif.isEnabled = isGif
            }
        }
    }

    override fun onDisconnected() {
        connected = false
        runOnUiThread {
            tvStatus.text = "连接已断开"
            updateUI()
        }
    }

    override fun onStatusChanged(status: String) {
        runOnUiThread { tvStatus.text = status }
    }

    override fun onProgress(current: Int, total: Int) {
        runOnUiThread {
            progressBar.max = total
            progressBar.progress = current
        }
    }

    override fun onError(msg: String) {
        runOnUiThread {
            tvStatus.text = msg
            btnConnect.isEnabled = true
            btnConnect.text = "搜索设备"
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
        bleManager.disconnect()
    }
}
