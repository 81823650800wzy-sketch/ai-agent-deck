package com.aideck.transfer

import android.annotation.SuppressLint
import android.bluetooth.*
import android.bluetooth.le.*
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import java.util.UUID

/**
 * BLE 图片传输管理器
 * 协议与固件 ble_img.h 一致
 */
class BleManager(private val context: Context) {

    companion object {
        private const val TAG = "BleManager"
        private val SERVICE_UUID = UUID.fromString("0000fff0-0000-1000-8000-00805f9b34fb")
        private val CHAR_CTRL_UUID = UUID.fromString("0000fff1-0000-1000-8000-00805f9b34fb")
        private val CHAR_DATA_UUID = UUID.fromString("0000fff2-0000-1000-8000-00805f9b34fb")
        private val CHAR_STATUS_UUID = UUID.fromString("0000fff3-0000-1000-8000-00805f9b34fb")
        private val CCCD_UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

        // 控制命令
        const val CMD_SHOW_IMAGE: Byte = 0x01
        const val CMD_GIF_START: Byte = 0x02
        const val CMD_GIF_FRAME: Byte = 0x03
        const val CMD_GIF_END: Byte = 0x04
        const val CMD_SET_DELAY: Byte = 0x05
        const val CMD_CLEAR: Byte = 0x06

        // 状态码
        const val STATUS_OK: Byte = 0x00
        const val STATUS_READY: Byte = 0x04
        const val STATUS_FRAME_ACK: Byte = 0x05

        private const val HEADER_SIZE = 7
        private const val MAX_CHUNK_SIZE = 500
    }

    interface BleCallback {
        fun onConnected()
        fun onDisconnected()
        fun onStatusChanged(status: String)
        fun onProgress(current: Int, total: Int)
        fun onError(msg: String)
    }

    private var bluetoothAdapter: BluetoothAdapter? = null
    private var bleScanner: BluetoothLeScanner? = null
    private var gatt: BluetoothGatt? = null
    private var ctrlChar: BluetoothGattCharacteristic? = null
    private var dataChar: BluetoothGattCharacteristic? = null
    private var statusChar: BluetoothGattCharacteristic? = null

    private var callback: BleCallback? = null
    private val handler = Handler(Looper.getMainLooper())
    private var isScanning = false
    private var isConnected = false

    // 传输状态
    @Volatile private var waitingForStatus = false
    @Volatile private var lastStatus: Byte = -1
    private val statusLock = Object()

    fun setCallback(cb: BleCallback) { callback = cb }

    fun isReady() = isConnected && ctrlChar != null && dataChar != null

    @SuppressLint("MissingPermission")
    fun startScan() {
        val manager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        bluetoothAdapter = manager.adapter
        if (bluetoothAdapter == null || !bluetoothAdapter!!.isEnabled) {
            callback?.onError("蓝牙未开启")
            return
        }

        bleScanner = bluetoothAdapter!!.bluetoothLeScanner
        if (bleScanner == null) {
            callback?.onError("BLE扫描器不可用")
            return
        }

        isScanning = true
        callback?.onStatusChanged("扫描中...")

        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()

        bleScanner?.startScan(null, settings, scanCallback)

        // 10秒超时
        handler.postDelayed({
            if (isScanning) {
                stopScan()
                callback?.onError("扫描超时,未找到设备")
            }
        }, 10000)
    }

    @SuppressLint("MissingPermission")
    fun stopScan() {
        if (isScanning) {
            isScanning = false
            bleScanner?.stopScan(scanCallback)
        }
    }

    private val scanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val device = result.device
            val name = result.scanRecord?.deviceName ?: device.name
            if (name == "AI-Agent-Deck") {
                Log.i(TAG, "Found device: $name (${device.address})")
                stopScan()
                handler.post { callback?.onStatusChanged("正在连接...") }
                connect(device)
            }
        }

        override fun onScanFailed(errorCode: Int) {
            Log.e(TAG, "Scan failed: $errorCode")
            handler.post { callback?.onError("扫描失败: $errorCode") }
        }
    }

    @SuppressLint("MissingPermission")
    private fun connect(device: BluetoothDevice) {
        gatt = device.connectGatt(context, false, gattCallback, BluetoothDevice.TRANSPORT_LE)
    }

    @SuppressLint("MissingPermission")
    fun disconnect() {
        gatt?.disconnect()
        gatt?.close()
        gatt = null
        isConnected = false
    }

    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            when (newState) {
                BluetoothProfile.STATE_CONNECTED -> {
                    Log.i(TAG, "GATT connected, discovering services...")
                    handler.post { callback?.onStatusChanged("已连接,发现服务中...") }
                    gatt.discoverServices()
                }
                BluetoothProfile.STATE_DISCONNECTED -> {
                    Log.i(TAG, "GATT disconnected")
                    isConnected = false
                    handler.post { callback?.onDisconnected() }
                }
            }
        }

        @SuppressLint("MissingPermission")
        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                handler.post { callback?.onError("服务发现失败") }
                return
            }

            val service = gatt.getService(SERVICE_UUID)
            if (service == null) {
                handler.post { callback?.onError("未找到目标服务") }
                return
            }

            ctrlChar = service.getCharacteristic(CHAR_CTRL_UUID)
            dataChar = service.getCharacteristic(CHAR_DATA_UUID)
            statusChar = service.getCharacteristic(CHAR_STATUS_UUID)

            if (ctrlChar == null || dataChar == null || statusChar == null) {
                handler.post { callback?.onError("特征值不完整") }
                return
            }

            // 启用状态通知
            gatt.setCharacteristicNotification(statusChar, true)
            val cccd = statusChar!!.getDescriptor(CCCD_UUID)
            if (cccd != null) {
                cccd.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                gatt.writeDescriptor(cccd)
            }

            isConnected = true
            Log.i(TAG, "All characteristics found")
            handler.post { callback?.onConnected() }
        }

        override fun onCharacteristicWrite(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, status: Int) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                Log.e(TAG, "Write failed: ${characteristic.uuid} status=$status")
            }
        }

        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
            if (characteristic.uuid == CHAR_STATUS_UUID) {
                val value = characteristic.value
                if (value != null && value.isNotEmpty()) {
                    val st = value[0]
                    Log.d(TAG, "Status: $st")
                    synchronized(statusLock) {
                        lastStatus = st
                        waitingForStatus = false
                        statusLock.notifyAll()
                    }
                }
            }
        }
    }

    /* ── 发送命令 ────────────────────────── */

    @SuppressLint("MissingPermission")
    private fun writeCtrl(data: ByteArray): Boolean {
        val c = ctrlChar ?: return false
        c.writeType = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        c.value = data
        return gatt?.writeCharacteristic(c) == true
    }

    @SuppressLint("MissingPermission")
    private fun writeData(data: ByteArray): Boolean {
        val c = dataChar ?: return false
        c.writeType = BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        c.value = data
        return gatt?.writeCharacteristic(c) == true
    }

    private fun waitForStatus(timeoutMs: Long): Byte {
        synchronized(statusLock) {
            waitingForStatus = true
            lastStatus = -1
            val deadline = System.currentTimeMillis() + timeoutMs
            while (waitingForStatus && System.currentTimeMillis() < deadline) {
                try { statusLock.wait(deadline - System.currentTimeMillis()) } catch (_: Exception) {}
            }
            return lastStatus
        }
    }

    /**
     * 发送数据分包
     * @param cmd     命令字节
     * @param frameIdx 帧索引
     * @param data    RGB565 像素数据
     * @param onProgress 进度回调 (currentChunk, totalChunks)
     */
    fun sendChunked(cmd: Byte, frameIdx: Int, data: ByteArray, onProgress: ((Int, Int) -> Unit)? = null): Boolean {
        val totalChunks = (data.size + MAX_CHUNK_SIZE - 1) / MAX_CHUNK_SIZE

        for (seq in 0 until totalChunks) {
            val offset = seq * MAX_CHUNK_SIZE
            val len = minOf(MAX_CHUNK_SIZE, data.size - offset)

            val packet = ByteArray(HEADER_SIZE + len)
            packet[0] = cmd
            packet[1] = (frameIdx and 0xFF).toByte()
            packet[2] = (frameIdx shr 8).toByte()
            packet[3] = (seq and 0xFF).toByte()
            packet[4] = (seq shr 8).toByte()
            packet[5] = (totalChunks and 0xFF).toByte()
            packet[6] = (totalChunks shr 8).toByte()
            System.arraycopy(data, offset, packet, HEADER_SIZE, len)

            if (!writeData(packet)) {
                Log.e(TAG, "writeData failed at chunk $seq")
                return false
            }

            onProgress?.invoke(seq + 1, totalChunks)

            // 小延迟避免 BLE 拥塞
            if (seq % 10 == 9) Thread.sleep(20)
        }
        return true
    }

    /**
     * 发送静态图片
     * @param rgb565Data 240*240*2 = 115200 bytes
     * @param onProgress 进度回调 (currentChunk, totalChunks)
     */
    fun sendImage(rgb565Data: ByteArray, onProgress: ((Int, Int) -> Unit)? = null): Boolean {
        if (!isReady()) return false

        // 1. 发送控制命令
        writeCtrl(byteArrayOf(CMD_SHOW_IMAGE))
        if (waitForStatus(3000) != STATUS_READY) {
            Log.e(TAG, "Device not ready for image")
            return false
        }

        // 2. 发送数据
        return sendChunked(CMD_SHOW_IMAGE, 0, rgb565Data, onProgress)
    }

    /**
     * 发送 GIF
     * @param frames RGB565帧数据列表
     * @param delayMs 帧间隔(毫秒)
     * @param onProgress 帧进度回调 (currentFrame, totalFrames)
     */
    fun sendGif(frames: List<ByteArray>, delayMs: Int, onProgress: ((Int, Int) -> Unit)? = null): Boolean {
        if (!isReady()) return false

        // 1. 发送 GIF 开始命令
        writeCtrl(byteArrayOf(CMD_GIF_START))
        if (waitForStatus(3000) != STATUS_READY) {
            Log.e(TAG, "Device not ready for GIF")
            return false
        }

        // 2. 设置帧间隔
        writeCtrl(byteArrayOf(CMD_SET_DELAY, (delayMs and 0xFF).toByte(), (delayMs shr 8).toByte()))
        Thread.sleep(100)

        // 3. 逐帧发送
        for (i in frames.indices) {
            onProgress?.invoke(i + 1, frames.size)

            if (!sendChunked(CMD_GIF_FRAME, i, frames[i])) {
                Log.e(TAG, "Failed to send GIF frame $i")
                return false
            }

            // 等待帧确认
            if (waitForStatus(5000) != STATUS_FRAME_ACK) {
                Log.w(TAG, "Frame $i ack timeout, continuing...")
            }
        }

        // 4. 发送 GIF 结束
        writeCtrl(byteArrayOf(CMD_GIF_END))
        Thread.sleep(200)

        Log.i(TAG, "GIF sent: ${frames.size} frames")
        return true
    }

    fun clearScreen() {
        if (!isReady()) return
        writeCtrl(byteArrayOf(CMD_CLEAR))
    }
}
