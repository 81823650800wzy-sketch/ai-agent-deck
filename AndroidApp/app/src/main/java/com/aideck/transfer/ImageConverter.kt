package com.aideck.transfer

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.ImageDecoder
import android.graphics.Movie
import android.graphics.Rect
import android.net.Uri
import android.os.Build
import android.content.Context
import java.io.ByteArrayOutputStream
import java.io.InputStream
import kotlin.math.min

/**
 * 图片/GIF 转 RGB565 工具
 * 输出: 240x240 RGB565 little-endian 数据
 */
object ImageConverter {

    const val SCREEN_W = 240
    const val SCREEN_H = 240
    const val FRAME_SIZE = SCREEN_W * SCREEN_H * 2  // 115200 bytes

    /**
     * 将 Bitmap 缩放并转换为 RGB565 字节数组
     */
    fun bitmapToRgb565(bitmap: Bitmap): ByteArray {
        val scaled = Bitmap.createScaledBitmap(bitmap, SCREEN_W, SCREEN_H, true)
        val pixels = IntArray(SCREEN_W * SCREEN_H)
        scaled.getPixels(pixels, 0, SCREEN_W, 0, 0, SCREEN_W, SCREEN_H)

        val buf = ByteArray(FRAME_SIZE)
        for (i in pixels.indices) {
            val px = pixels[i]
            val r = Color.red(px)
            val g = Color.green(px)
            val b = Color.blue(px)
            val rgb565 = ((r and 0xF8) shl 8) or ((g and 0xFC) shl 3) or (b shr 3)
            buf[i * 2] = (rgb565 and 0xFF).toByte()
            buf[i * 2 + 1] = (rgb565 shr 8).toByte()
        }

        if (scaled !== bitmap) scaled.recycle()
        return buf
    }

    /**
     * 从 URI 加载静态图片并转换为 RGB565
     */
    fun loadStaticImage(context: Context, uri: Uri): ByteArray? {
        return try {
            val bitmap = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                val source = ImageDecoder.createSource(context.contentResolver, uri)
                ImageDecoder.decodeBitmap(source) { decoder, _, _ ->
                    decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
                }
            } else {
                BitmapFactory.decodeStream(context.contentResolver.openInputStream(uri))
            } ?: return null

            val result = bitmapToRgb565(bitmap)
            bitmap.recycle()
            result
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    /**
     * GIF 帧数据
     */
    data class GifFrame(
        val rgb565: ByteArray,
        val delayMs: Int
    )

    /**
     * 从 URI 加载 GIF 并逐帧转换为 RGB565
     * 使用 Android Movie 类解码 GIF
     */
    fun loadGif(context: Context, uri: Uri): List<GifFrame>? {
        return try {
            val inputStream = context.contentResolver.openInputStream(uri) ?: return null
            val bytes = inputStream.readBytes()
            inputStream.close()

            // 检查是否为 GIF
            if (bytes.size < 6 || String(bytes, 0, 6) != "GIF89a" && String(bytes, 0, 6) != "GIF87a") {
                return null
            }

            val movie = Movie.decodeByteArray(bytes, 0, bytes.size)
            if (movie == null || movie.duration() <= 0) {
                // 不是动画GIF，当作静态图
                val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return null
                val frame = GifFrame(bitmapToRgb565(bitmap), 100)
                bitmap.recycle()
                return listOf(frame)
            }

            val frames = mutableListOf<GifFrame>()
            val canvas = Bitmap.createBitmap(movie.width(), movie.height(), Bitmap.Config.ARGB_8888)
            val canvasDraw = Canvas(canvas)
            var lastTime = 0

            movie.setTime(0)
            val firstDelay = maxOf(10, 100) // 默认100ms
            frames.add(GifFrame(bitmapToRgb565(canvas), firstDelay))

            var time = 0
            val duration = movie.duration()
            val step = maxOf(33, duration / 100) // ~30fps 或更少

            while (time < duration) {
                time += step
                movie.setTime(time)

                canvasDraw.drawColor(Color.BLACK)
                movie.draw(canvasDraw, 0f, 0f)

                val delay = maxOf(10, step)
                frames.add(GifFrame(bitmapToRgb565(canvas), delay))

                if (frames.size > 500) break // 安全限制
            }

            canvas.recycle()
            frames
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    /**
     * 检查 URI 指向的是否为 GIF
     */
    fun isGif(context: Context, uri: Uri): Boolean {
        return try {
            val type = context.contentResolver.getType(uri)
            type == "image/gif"
        } catch (e: Exception) {
            false
        }
    }
}
