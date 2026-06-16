/**
 * 轻量级 GIF89a 解码器
 * 支持: LZW压缩、多帧、透明色、帧延迟
 * 针对 ESP32-S3 PSRAM 优化
 */
#include <string.h>
#include <stdlib.h>
#include "gifdec.h"
#include "esp_log.h"
#include "esp_heap_caps.h"

static const char *TAG = "GIFDEC";

/* ── LZW 解码器 ───────────────────────── */
#define MAX_LZW_BITS    12
#define MAX_LZW_TABLE   (1 << MAX_LZW_BITS)
#define MAX_STACK_SIZE  (2 * MAX_LZW_TABLE)

typedef struct {
    const uint8_t *data;
    uint32_t       pos;
    uint32_t       size;
    int            byte_count;  /* 当前子块剩余字节 */
    uint8_t        buf;
    int            buf_bits;
} bit_reader_t;

typedef struct {
    int prefix;
    int first;
    int suffix;
} lzw_entry_t;

struct gd_gif {
    const uint8_t *data;
    uint32_t       size;
    uint32_t       pos;
    uint16_t       width;
    uint16_t       height;
    uint16_t       frame_count;
    uint32_t       bg_color;
    bool           has_gct;
    int            gct_size;
    uint8_t        gct[256][3];
    /* 当前帧状态 */
    int            left, top, fw, fh;
    bool           has_lct;
    int            lct_size;
    uint8_t        lct[256][3];
    int            transparent;
    int            disposal;
    uint16_t       delay;
    bool           interlaced;
};

/* ── 位读取器 ─────────────────────────── */
static void br_init(bit_reader_t *br, const uint8_t *data, uint32_t size) {
    br->data = data;
    br->pos = 0;
    br->size = size;
    br->byte_count = 0;
    br->buf = 0;
    br->buf_bits = 0;
}

static void br_start_subblock(bit_reader_t *br, const uint8_t *data, int len) {
    br->data = data;
    br->pos = 0;
    br->size = len;
    br->byte_count = len;
    br->buf = 0;
    br->buf_bits = 0;
}

static int br_read_bits(bit_reader_t *br, int n) {
    while (br->buf_bits < n) {
        if (br->pos >= br->size) return -1;
        br->buf |= (int)br->data[br->pos++] << br->buf_bits;
        br->buf_bits += 8;
    }
    int val = br->buf & ((1 << n) - 1);
    br->buf >>= n;
    br->buf_bits -= n;
    return val;
}

/* ── 辅助函数 ─────────────────────────── */
static inline uint16_t read16(const uint8_t *p) { return p[0] | (p[1] << 8); }

static void skip_subblocks(gd_gif_t *gif) {
    while (gif->pos < gif->size) {
        uint8_t len = gif->data[gif->pos++];
        if (len == 0) break;
        gif->pos += len;
    }
}

/* ── 解析 GIF 头部 ───────────────────── */
gd_gif_t *gd_open_gif_from_memory(const uint8_t *data, uint32_t size) {
    if (size < 13) return NULL;
    if (memcmp(data, "GIF89a", 6) != 0 && memcmp(data, "GIF87a", 6) != 0) {
        ESP_LOGE(TAG, "Not a GIF file");
        return NULL;
    }

    gd_gif_t *gif = heap_caps_calloc(1, sizeof(gd_gif_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!gif) return NULL;

    gif->data = data;
    gif->size = size;
    gif->pos = 6;

    /* Logical Screen Descriptor */
    gif->width  = read16(data + 6);
    gif->height = read16(data + 8);
    uint8_t flags = data[10];
    gif->bg_color = data[11];
    gif->pos = 13;

    gif->has_gct = (flags & 0x80) != 0;
    if (gif->has_gct) {
        gif->gct_size = 1 << ((flags & 0x07) + 1);
        memcpy(gif->gct, data + 13, gif->gct_size * 3);
        gif->pos += gif->gct_size * 3;
    }

    ESP_LOGI(TAG, "GIF: %dx%d, GCT=%d, bg=%lu", gif->width, gif->height,
             gif->has_gct ? gif->gct_size : 0, gif->bg_color);

    /* 统计帧数 */
    uint32_t scan_pos = gif->pos;
    gif->frame_count = 0;
    while (scan_pos < size) {
        uint8_t b = data[scan_pos++];
        if (b == 0x2C) { /* Image Descriptor */
            gif->frame_count++;
            /* Image Descriptor: left(2) + top(2) + w(2) + h(2) + flags(1) = 9 bytes */
            if (scan_pos + 9 > size) break;
            uint8_t iflags = data[scan_pos + 8];
            scan_pos += 9;
            bool has_lct = (iflags & 0x80) != 0;
            if (has_lct) {
                int lct_sz = 1 << ((iflags & 0x07) + 1);
                scan_pos += lct_sz * 3;
            }
            if (scan_pos >= size) break;
            scan_pos++; /* LZW min code size */
            /* skip sub-blocks */
            while (scan_pos < size) {
                uint8_t slen = data[scan_pos++];
                if (slen == 0) break;
                scan_pos += slen;
            }
        } else if (b == 0x21) { /* Extension */
            scan_pos++; /* extension type */
            while (scan_pos < size) {
                uint8_t slen = data[scan_pos++];
                if (slen == 0) break;
                scan_pos += slen;
            }
        } else if (b == 0x3B) { /* Trailer */
            break;
        }
    }
    ESP_LOGI(TAG, "Frames: %d", gif->frame_count);

    /* 重置 pos 到第一个 block */
    if (gif->has_gct) {
        gif->pos = 6 + 7 + gif->gct_size * 3;
    } else {
        gif->pos = 13;
    }

    return gif;
}

/* ── 解码一帧 ─────────────────────────── */
int gd_decode_frame(gd_gif_t *gif, gd_frame_t *frame) {
    if (!gif || !frame) return -1;
    memset(frame, 0, sizeof(gd_frame_t));

    gif->transparent = -1;
    gif->disposal = 0;
    gif->delay = 0;
    gif->interlaced = false;
    gif->has_lct = false;

    /* 寻找下一个 Image Descriptor, 处理中间的 Extension */
    while (gif->pos < gif->size) {
        uint8_t b = gif->data[gif->pos++];

        if (b == 0x21) { /* Extension */
            if (gif->pos >= gif->size) return -1;
            uint8_t ext_type = gif->data[gif->pos++];
            if (ext_type == 0xF9) { /* Graphic Control Extension */
                uint8_t gsize = gif->data[gif->pos++];
                if (gsize >= 4) {
                    uint8_t gflags = gif->data[gif->pos];
                    gif->disposal = (gflags >> 2) & 7;
                    bool has_trans = gflags & 0x01;
                    gif->delay = read16(gif->data + gif->pos + 1);
                    if (gif->delay == 0) gif->delay = 10; /* 最小延迟 */
                    gif->delay *= 10; /* 转换为毫秒 */
                    if (has_trans) gif->transparent = gif->data[gif->pos + 3];
                    else gif->transparent = -1;
                }
                gif->pos += gsize;
            } else {
                /* 跳过其他扩展 */
                while (gif->pos < gif->size) {
                    uint8_t slen = gif->data[gif->pos++];
                    if (slen == 0) break;
                    gif->pos += slen;
                }
            }
            /* 跳过块终止符 */
            if (gif->pos < gif->size && gif->data[gif->pos] == 0) {
                gif->pos++;
            }
            continue;
        }

        if (b == 0x2C) { /* Image Descriptor */
            if (gif->pos + 9 > gif->size) return -1;
            gif->left  = read16(gif->data + gif->pos);     gif->pos += 2;
            gif->top   = read16(gif->data + gif->pos);     gif->pos += 2;
            gif->fw    = read16(gif->data + gif->pos);     gif->pos += 2;
            gif->fh    = read16(gif->data + gif->pos);     gif->pos += 2;
            uint8_t iflags = gif->data[gif->pos++];

            gif->interlaced = (iflags & 0x40) != 0;
            gif->has_lct = (iflags & 0x80) != 0;
            if (gif->has_lct) {
                gif->lct_size = 1 << ((iflags & 0x07) + 1);
                memcpy(gif->lct, gif->data + gif->pos, gif->lct_size * 3);
                gif->pos += gif->lct_size * 3;
            }

            /* LZW 最小代码大小 */
            if (gif->pos >= gif->size) return -1;
            int min_code_size = gif->data[gif->pos++];
            if (min_code_size < 2 || min_code_size > 8) return -1;

            /* ── 收集所有子块到连续缓冲区 ── */
            uint32_t comp_start = gif->pos;
            uint32_t comp_size = 0;
            uint32_t tmp_pos = gif->pos;
            while (tmp_pos < gif->size) {
                uint8_t slen = gif->data[tmp_pos++];
                if (slen == 0) break;
                comp_size += slen;
                tmp_pos += slen;
            }

            /* 分配压缩数据缓冲 */
            uint8_t *comp_data = heap_caps_malloc(comp_size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
            if (!comp_data) {
                ESP_LOGE(TAG, "comp_data alloc failed (%lu bytes)", comp_size);
                gif->pos = tmp_pos;
                return -1;
            }

            /* 拷贝压缩数据到连续缓冲 */
            uint32_t cpos = comp_start;
            uint32_t wpos = 0;
            while (cpos < gif->size) {
                uint8_t slen = gif->data[cpos++];
                if (slen == 0) break;
                memcpy(comp_data + wpos, gif->data + cpos, slen);
                wpos += slen;
                cpos += slen;
            }
            gif->pos = cpos; /* 跳过子块 */

            /* ── LZW 解码 ── */
            int npix = gif->fw * gif->fh;
            uint8_t *indexed = heap_caps_malloc(npix, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
            if (!indexed) {
                free(comp_data);
                ESP_LOGE(TAG, "indexed alloc failed");
                return -1;
            }

            bit_reader_t br;
            br_init(&br, comp_data, comp_size);

            int clear_code = 1 << min_code_size;
            int eoi_code = clear_code + 1;
            int code_size = min_code_size + 1;
            int next_code = eoi_code + 1;
            int max_code = 1 << code_size;

            lzw_entry_t *table = heap_caps_malloc(MAX_LZW_TABLE * sizeof(lzw_entry_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
            uint8_t *stack = heap_caps_malloc(MAX_STACK_SIZE, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
            if (!table || !stack) {
                free(comp_data); free(indexed);
                if (table) free(table);
                if (stack) free(stack);
                return -1;
            }

            /* 初始化码表 */
            for (int i = 0; i < clear_code; i++) {
                table[i].prefix = -1;
                table[i].first = i;
                table[i].suffix = i;
            }

            int sp = 0;
            int pixel_idx = 0;
            int prev_code = -1;
            int first_pixel = 0;

            while (pixel_idx < npix) {
                int code = br_read_bits(&br, code_size);
                if (code < 0) break;

                if (code == clear_code) {
                    code_size = min_code_size + 1;
                    next_code = eoi_code + 1;
                    max_code = 1 << code_size;
                    prev_code = -1;
                    continue;
                }
                if (code == eoi_code) break;

                int cur_code = code;
                if (cur_code >= next_code) {
                    /* 特殊情况: cur_code 在码表中不存在 */
                    stack[sp++] = first_pixel;
                    cur_code = prev_code;
                }
                while (cur_code >= 0 && cur_code < MAX_LZW_TABLE && sp < MAX_STACK_SIZE) {
                    stack[sp++] = table[cur_code].suffix;
                    cur_code = table[cur_code].prefix;
                }
                if (sp == 0) break;

                first_pixel = stack[sp - 1];

                /* 输出像素 */
                while (sp > 0 && pixel_idx < npix) {
                    indexed[pixel_idx++] = stack[--sp];
                }

                /* 添加新码表项 */
                if (prev_code >= 0 && next_code < MAX_LZW_TABLE) {
                    table[next_code].prefix = prev_code;
                    table[next_code].first = table[prev_code].first;
                    table[next_code].suffix = first_pixel;
                    next_code++;
                    if (next_code >= max_code && code_size < MAX_LZW_BITS) {
                        code_size++;
                        max_code = 1 << code_size;
                    }
                }
                prev_code = code;
            }

            free(comp_data);
            free(table);
            free(stack);

            /* ── 转换为 RGB565 ── */
            uint8_t (*ct)[3] = gif->has_lct ? gif->lct : gif->gct;
            int ct_size = gif->has_lct ? gif->lct_size : gif->gct_size;

            frame->width = gif->fw;
            frame->height = gif->fh;
            frame->delay_ms = gif->delay;
            frame->is_disposal2 = (gif->disposal == 2);
            frame->pixels = heap_caps_malloc(gif->fw * gif->fh * 2, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
            if (!frame->pixels) {
                free(indexed);
                return -1;
            }

            for (int i = 0; i < npix; i++) {
                int idx = indexed[i];
                if (idx == gif->transparent || idx >= ct_size) {
                    frame->pixels[i] = 0x0000; /* 黑/透明 */
                } else {
                    uint8_t r = ct[idx][0];
                    uint8_t g = ct[idx][1];
                    uint8_t b = ct[idx][2];
                    frame->pixels[i] = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
                }
            }

            free(indexed);

            /* 处理交错 */
            if (gif->interlaced) {
                uint16_t *deinterlaced = heap_caps_malloc(gif->fw * gif->fh * 2, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
                if (deinterlaced) {
                    int row = 0;
                    /* Pass 1: every 8th row, starting at 0 */
                    for (int y = 0; y < gif->fh; y += 8)
                        memcpy(deinterlaced + y * gif->fw, frame->pixels + row++ * gif->fw, gif->fw * 2);
                    /* Pass 2: every 8th row, starting at 4 */
                    for (int y = 4; y < gif->fh; y += 8)
                        memcpy(deinterlaced + y * gif->fw, frame->pixels + row++ * gif->fw, gif->fw * 2);
                    /* Pass 3: every 4th row, starting at 2 */
                    for (int y = 2; y < gif->fh; y += 4)
                        memcpy(deinterlaced + y * gif->fw, frame->pixels + row++ * gif->fw, gif->fw * 2);
                    /* Pass 4: every 2nd row, starting at 1 */
                    for (int y = 1; y < gif->fh; y += 2)
                        memcpy(deinterlaced + y * gif->fw, frame->pixels + row++ * gif->fw, gif->fw * 2);
                    free(frame->pixels);
                    frame->pixels = deinterlaced;
                }
            }

            return 0; /* 成功 */
        }

        if (b == 0x3B) return -1; /* Trailer */
    }
    return -1;
}

void gd_get_info(gd_gif_t *gif, uint16_t *w, uint16_t *h, uint16_t *frame_count) {
    if (!gif) return;
    if (w) *w = gif->width;
    if (h) *h = gif->height;
    if (frame_count) *frame_count = gif->frame_count;
}

void gd_close_gif(gd_gif_t *gif) {
    if (gif) free(gif);
}
