"""
AI Agent Deck - 壁纸管理器 (PC 端)
负责图片加载、预处理、RGB565 转换、串口/BLE 上传
"""

import base64
import json
import struct
import io
import time
from pathlib import Path
from typing import Optional, Callable

try:
    from PIL import Image
except ImportError:
    Image = None


class WallpaperManager:
    """
    壁纸管理器

    功能:
    - 加载图片 (PNG/JPG/BMP/GIF)
    - 智能预处理：自动缩放、裁剪、量化
    - 转换为 240x240 RGB565
    - 通过串口/BLE/WiFi 上传到 ESP32
    - 预览图片
    """

    WIDTH = 240
    HEIGHT = 240
    RGB565_SIZE = WIDTH * HEIGHT * 2  # 115200 bytes

    def __init__(self, send_func: Callable[[str], bool] = None):
        self.send_func = send_func
        self.current_image: Optional[Image.Image] = None
        self.current_frames: list = []
        self._upload_log: list = []
        self._ack_count = 0
        self._ack_lock = __import__('threading').Lock()

    def set_send_func(self, func: Callable[[str], bool]):
        self.send_func = func

    def signal_ack(self, offset: int = -1):
        """信号：收到 ACK（由接收线程调用）"""
        with self._ack_lock:
            self._ack_count += 1

    def wait_for_ack(self, expected_offset: int, timeout: float = 3.0) -> bool:
        """等待任意 ACK"""
        import time
        start_count = self._ack_count
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._ack_count > start_count:
                return True
            time.sleep(0.05)
        return False

    def get_upload_log(self) -> list:
        return self._upload_log.copy()

    def clear_upload_log(self):
        self._upload_log.clear()

    def _log(self, msg: str):
        self._upload_log.append(msg)
        print(msg)

    def load_image(self, file_path: str) -> Optional[Image.Image]:
        """加载并预处理图片"""
        if not Image:
            self._log("[壁纸] Pillow 未安装: pip install Pillow")
            return None

        try:
            img = Image.open(file_path)
            orig_size = img.size
            orig_mode = img.mode

            self._log(f"[壁纸] 原始: {orig_size[0]}x{orig_size[1]} {orig_mode} {file_path}")

            # 处理 GIF 动图
            if getattr(img, "is_animated", False):
                self.current_frames = []
                frame_idx = 0
                try:
                    while True:
                        frame = self._preprocess_frame(img)
                        delay = img.info.get("duration", 100)
                        self.current_frames.append((frame, delay))
                        frame_idx += 1
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass
                self.current_image = self.current_frames[0][0]
                self._log(f"[壁纸] GIF: {frame_idx} 帧, 已转换为 240x240 RGB565")
                return self.current_image
            else:
                # 静态图片预处理
                img = self._preprocess_image(img)
                self.current_image = img
                self.current_frames = []
                self._log(f"[壁纸] 静态: 已转换为 240x240 RGB565 ({self.RGB565_SIZE} bytes)")
                return img

        except Exception as e:
            self._log(f"[壁纸] 加载失败: {e}")
            return None

    def _preprocess_image(self, img: Image.Image) -> Image.Image:
        """智能预处理图片：缩放 + 裁剪 + 量化"""
        # 1. 转换为 RGB（去除 alpha 通道）
        if img.mode in ('RGBA', 'LA', 'P'):
            # 创建白色背景
            bg = Image.new('RGB', img.size, (0, 0, 0))
            if img.mode == 'P':
                img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 2. 智能缩放：保持宽高比，居中裁剪
        w, h = img.size
        target_ratio = self.WIDTH / self.HEIGHT
        img_ratio = w / h

        if img_ratio > target_ratio:
            # 图片更宽，按高度缩放
            new_h = self.HEIGHT
            new_w = int(new_h * img_ratio)
        else:
            # 图片更高，按宽度缩放
            new_w = self.WIDTH
            new_h = int(new_w / img_ratio)

        img = img.resize((new_w, new_h), Image.LANCZOS)

        # 3. 居中裁剪到 240x240
        left = (new_w - self.WIDTH) // 2
        top = (new_h - self.HEIGHT) // 2
        img = img.crop((left, top, left + self.WIDTH, top + self.HEIGHT))

        # 4. 颜色量化（减少色彩，提高压缩率）
        # 不做量化，保持原始色彩质量

        return img

    def _preprocess_frame(self, img: Image.Image) -> Image.Image:
        """预处理 GIF 帧"""
        frame = img.copy()
        return self._preprocess_image(frame)

    def image_to_rgb565(self, img: Image.Image) -> bytes:
        """将 PIL Image 转换为 RGB565 字节数据（优化版）"""
        # 确保尺寸正确
        if img.size != (self.WIDTH, self.HEIGHT):
            img = img.resize((self.WIDTH, self.HEIGHT), Image.LANCZOS)

        # 使用 tobytes 代替手动转换（更快）
        rgb_data = img.tobytes('raw', 'RGB')
        buf = bytearray(self.WIDTH * self.HEIGHT * 2)

        for i in range(self.WIDTH * self.HEIGHT):
            r = rgb_data[i * 3]
            g = rgb_data[i * 3 + 1]
            b = rgb_data[i * 3 + 2]
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buf[i * 2] = rgb565 & 0xFF
            buf[i * 2 + 1] = (rgb565 >> 8) & 0xFF

        return bytes(buf)

    def upload_static(self, img: Image.Image = None, ack_func=None) -> bool:
        """上传静态壁纸到 ESP32"""
        if not self.send_func:
            self._log("[壁纸] 未配置发送函数")
            return False

        img = img or self.current_image
        if not img:
            self._log("[壁纸] 未加载图片")
            return False

        # 确保图片已预处理
        if img.size != (self.WIDTH, self.HEIGHT):
            self._log(f"[壁纸] 重新调整尺寸: {img.size} -> {self.WIDTH}x{self.HEIGHT}")
            img = self._preprocess_image(img)

        self._log(f"[壁纸] 开始上传: {self.WIDTH}x{self.HEIGHT}")

        # 转换为 RGB565
        rgb565_data = self.image_to_rgb565(img)
        total = len(rgb565_data)
        self._log(f"[壁纸] RGB565 数据: {total} bytes ({total/1024:.1f} KB)")

        # 发送开始命令
        start_cmd = json.dumps({
            "cmd": "wallpaper_start",
            "width": self.WIDTH,
            "height": self.HEIGHT,
            "size": total
        })
        if not self.send_func(start_cmd):
            self._log("[壁纸] 发送开始命令失败")
            return False

        time.sleep(2.0)  # 等待 ESP32 进入上传模式（暂停屏幕刷新）

        # 分块上传（96字节 = ~128字节 base64 + JSON ≈ 160字节，低于 UART 缓冲区）
        chunk_size = 96
        offset = 0
        retries = 0
        max_retries = 5
        start_time = time.time()

        while offset < total:
            end = min(offset + chunk_size, total)
            chunk = rgb565_data[offset:end]
            b64_chunk = base64.b64encode(chunk).decode("ascii")

            cmd = json.dumps({
                "cmd": "wp_chunk",
                "off": offset,
                "total": total,
                "data": b64_chunk
            }, separators=(',', ':'))  # 紧凑 JSON，减少大小

            if not self.send_func(cmd):
                retries += 1
                if retries > max_retries:
                    self._log(f"[壁纸] 上传失败: offset={offset}, 重试次数超限")
                    return False
                time.sleep(0.5)
                continue

            # 等待 ESP32 处理
            if ack_func:
                if not ack_func(timeout=2.0):
                    retries += 1
                    if retries > max_retries:
                        self._log(f"[壁纸] 上传失败: offset={offset}, 无 ACK")
                        return False
                    continue
            else:
                # 使用计数器等待 ACK
                time.sleep(0.08)  # 给 ESP32 时间处理
                if not self.wait_for_ack(offset, timeout=5.0):
                    retries += 1
                    if retries > max_retries:
                        self._log(f"[壁纸] 上传失败: offset={offset}, 无 ACK")
                        return False
                    self._log(f"[壁纸] 重试: offset={offset}")
                    continue

            retries = 0
            offset = end

            # 进度日志（每 5%）
            pct = int(offset * 100 / total)
            if pct % 5 == 0 and offset > 0:
                elapsed = time.time() - start_time
                speed = offset / elapsed if elapsed > 0 else 0
                eta = (total - offset) / speed if speed > 0 else 0
                self._log(f"[壁纸] 进度: {pct}% ({offset}/{total}) "
                         f"速度: {speed/1024:.1f} KB/s 预计剩余: {eta:.0f}s")

        elapsed = time.time() - start_time
        self._log(f"[壁纸] 上传完成: {elapsed:.1f}s, 平均 {total/elapsed/1024:.1f} KB/s")

        # 发送完成命令
        end_cmd = json.dumps({"cmd": "wallpaper_end"})
        self.send_func(end_cmd)

        return True

    def upload_gif(self, file_path: str = None) -> bool:
        """上传 GIF 动图壁纸到 ESP32"""
        if not self.send_func:
            self._log("[壁纸] 未配置发送函数")
            return False

        if file_path:
            self.load_image(file_path)

        if not self.current_frames:
            self._log("[壁纸] 无 GIF 帧")
            return False

        frame_count = len(self.current_frames)
        self._log(f"[壁纸] 开始上传 GIF: {frame_count} 帧")

        # 1. 发送 GIF 开始命令
        start_cmd = json.dumps({
            "cmd": "wallpaper_gif_start",
            "frames": frame_count,
            "width": self.WIDTH,
            "height": self.HEIGHT
        })
        if not self.send_func(start_cmd):
            return False

        time.sleep(0.5)

        # 2. 逐帧发送
        for idx, (frame_img, delay) in enumerate(self.current_frames):
            rgb565_data = self.image_to_rgb565(frame_img)
            b64_data = base64.b64encode(rgb565_data).decode("ascii")

            frame_cmd = json.dumps({
                "cmd": "wallpaper_gif_frame",
                "idx": idx,
                "delay": delay,
                "data": b64_data
            })
            if not self.send_func(frame_cmd):
                self._log(f"[壁纸] GIF 帧 {idx} 发送失败")
                return False

            time.sleep(0.5)  # 每帧延迟

            if idx % 5 == 0:
                self._log(f"[壁纸] GIF 进度: {idx+1}/{frame_count}")

        # 3. 发送完成命令
        end_cmd = json.dumps({"cmd": "wallpaper_gif_end"})
        self.send_func(end_cmd)

        self._log(f"[壁纸] GIF 上传完成: {frame_count} 帧")
        return True

    def clear_wallpaper(self) -> bool:
        """清除 ESP32 上的壁纸"""
        if not self.send_func:
            return False
        cmd = json.dumps({"cmd": "wallpaper_clear"})
        return self.send_func(cmd)

    def get_preview_pixmap(self, img: Image.Image = None, size: int = 200):
        """生成预览 QPixmap"""
        if not Image:
            return None

        img = img or self.current_image
        if not img:
            return None

        try:
            from PyQt5.QtGui import QPixmap, QImage
            from PyQt5.QtCore import Qt

            rgb_img = img.convert("RGB")
            data = rgb_img.tobytes("raw", "RGB")
            qimg = QImage(data, rgb_img.width, rgb_img.height,
                          3 * rgb_img.width, QImage.Format_RGB888)

            pixmap = QPixmap.fromImage(qimg)
            return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except ImportError:
            return None

    def get_image_info(self) -> dict:
        """获取当前图片信息"""
        if not self.current_image:
            return {"loaded": False}

        img = self.current_image
        rgb565_size = self.WIDTH * self.HEIGHT * 2

        return {
            "loaded": True,
            "width": self.WIDTH,
            "height": self.HEIGHT,
            "mode": img.mode,
            "rgb565_size": rgb565_size,
            "rgb565_kb": rgb565_size / 1024,
            "frames": len(self.current_frames),
            "is_gif": len(self.current_frames) > 0
        }
