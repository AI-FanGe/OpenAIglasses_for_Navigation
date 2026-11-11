# -*- coding: utf-8 -*-
"""
YOLOv8 单类分割 + MediaPipe Hand Landmarker + 光流追踪（多边形）
更新点（本版重点）：
- 左下角第二个进度条"距离(≈1)" 已完全替换为：ratio = 物体面积 / 手面积 的"接近 1 程度"可视化
  -> range_score = 1 - clamp(|ratio - 1| / RATIO_TOL, 0..1)
  -> 画面同时显示 ratio 数值；ratio<1 提示"向前靠近"，ratio>1 提示"后退"，在 [1±RATIO_TOL] 内为"保持"
其他特性：
- Enter 锁定：在分割掩码"内收 5px"的内边界上取光流点
- TRACK 期间：监控当前多边形外扩 40px 周边区域的分割，命中即重锁
- 成功判定：放宽"握持(Grasp)"启发式（拿瓶子无需特别紧）
- 手骨架单色渲染；测距箭头（端点定位线 + 箭头 + 像素值）
- 中文绘制优先 Pillow + 系统中文字体（避免问号）
"""

import os
import time
import threading
import math
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
from ultralytics import YOLO
from ultralytics.utils.plotting import Colors
import bridge_io
import pygame  # 用于播放本地音频文件

from audio_player import play_audio_threadsafe
PERF_DEBUG = False        # 打印调试信息（False 关闭）
HAND_DOWNSCALE = 0.8      # HandLandmarker 的输入缩放 0.5=长宽各减半（≈1/4 像素量）
HAND_FPS_DIV = 1          # 人手每 2 帧跑一次（1=每帧；2=隔帧；3=每3帧）


# === 前端风格配色（BGR） + UI叠加管理（左下角按行堆叠） ===
FRONTEND_COLORS = {
    "text": (230, 237, 243),   # --text: #e6edf3
    "muted": (159, 176, 195),  # --muted: #9fb0c3
    "ok": (126, 231, 135),     # --ok: #7ee787
    "err": (128, 128, 255),    # --err: #ff8080 (BGR)
    "accent": (251, 218, 97),  # #61dafb 近似的强调色（BGR 取近似亮色）
}

# 底部指令按钮文本
CURRENT_COMMAND_TEXT = "—"

_UI_LINE = 0
_UI_H = 0
_UI_TR_LINE = 0  # 右上角逐行叠放计数
_UI_TOP_MARGIN = 12
_UI_RIGHT_MARGIN = 12
UNIFIED_FONT_PX = 12  # 统一字号


def ui_reset_overlay(img_h: int):
    """每帧调用一次，重置叠加行计数（改为右上角布局）。"""
    global _UI_LINE, _UI_H, _UI_TR_LINE
    _UI_LINE = 0
    _UI_TR_LINE = 0
    _UI_H = int(img_h)


def _ui_next_y_top(font_size: int) -> int:
    """返回右上角下一行的y(顶部对齐)，并推进行计数。"""
    global _UI_TR_LINE
    line_gap = max(4, int(font_size * 0.25))
    y_top = _UI_TOP_MARGIN + (_UI_TR_LINE * (font_size + line_gap))
    _UI_TR_LINE += 1
    return y_top


def set_current_command(text: str):
    global CURRENT_COMMAND_TEXT
    try:
        CURRENT_COMMAND_TEXT = str(text) if text else "—"
    except Exception:
        CURRENT_COMMAND_TEXT = "—"


def draw_command_pill(img_bgr: np.ndarray, label: str):
    """统一改为右上角白色文案。不再绘制底部圆角按钮。"""
    text_prefix = "当前指令："
    full_text = f"{text_prefix}{label if label else '—'}"
    # 直接用统一文本渲染
    draw_text_cn(img_bgr, full_text, (0, 0), font_size=UNIFIED_FONT_PX, color=(255,255,255), ui_hint=True)

try:
    from yoloe_backend import YoloEBackend
    _YOLOE_READY = True
except Exception as e:
    _YOLOE_READY = False
    print(f"[DETECTOR] YOLOE backend not ready: {e}", flush=True)

# ========= 路径参数（按需修改）=========
YOLO_MODEL_PATH = r'C:\Users\Administrator\Desktop\rebuild1002\model\shoppingbest5.pt'
HAND_TASK_PATH  = r"C:\Users\Administrator\Desktop\rebuild1002\model\hand_landmarker.task"

# ========= 摄像头 =========
CAM_INDEX = 0
INPUT_W, INPUT_H = 600, 480

# ========= 分割显示 =========
STROKE_WIDTH = 5  # 增加描边宽度，让黄框和绿框更粗
MASK_ALPHA   = 0.45
CONF_THRESHOLD = 0.20

# —— 单 prompt 识别（只显示一个类）——
PROMPT_NAME   = "AD_milk"
PROMPT_STRICT = True

# ========= 对齐条参数 =========
ALIGN_LOOSE_PCT      = 0.12   # 归一化距离阈（相对画面对角线）

# ========= 距离条参数（本版采用"ratio≈1"为目标）=========
RATIO_IDEAL          = 1.0    # 理想值：物体面积/手面积 ≈ 1
RATIO_TOL            = 0.25   # 容许偏离：±25% 内认为距离合适

# ========= 语音播报 =========
TTS_INTERVAL_SEC     = 1.0
ENABLE_TTS           = True

# ========= 光流（LK）与特征点 =========
LK_PARAMS = dict(winSize=(21, 21),
                 maxLevel=3,
                 criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 12, 0.03))
FEATURE_PARAMS = dict(maxCorners=600,
                      qualityLevel=0.001,
                      minDistance=5,
                      blockSize=7)

# ========= 关键参数：内收与周边监控 =========
INNER_OFFSET_PX_LOCK = 5     # Enter 锁定：掩码腐蚀像素，保证点在物体内部
EDGE_DILATE_PX       = 2     # 取内边界后小膨胀，利于提点
PERI_MONITOR_PX      = 40    # TRACK：监控多边形外扩 40px 的周边带
PERI_CHECK_EVERY     = 5     # 每隔 N 帧做一次周边分割检查，改为每帧

# ========= 轮廓精度参数 =========
CONTOUR_EPSILON_FACTOR = 0.002  # Douglas-Peucker算法的精度因子，越小越精细
TRACK_EPSILON_FACTOR = 0.003    # 追踪模式下的轮廓精度因子

# ========= YOLO实时矫正参数 =========
YOLO_CORRECTION_IOU_THRESHOLD = 0.2  # IoU阈值，越低越积极矫正
YOLO_CORRECTION_CONF_THRESHOLD = 0.15  # 置信度阈值，越低检测越敏感

# ========= 方向引导音频路径 =========
AUDIO_DIR = r"E:\沙粒云\自媒体\2025视频制作\20250925AI眼镜\AI眼镜合并\audio"  # 请修改为实际路径
AUDIO_FILES = {
    "向上": os.path.join(AUDIO_DIR, "up.wav"),
    "向下": os.path.join(AUDIO_DIR, "down.wav"),
    "向左": os.path.join(AUDIO_DIR, "left.wav"),
    "向右": os.path.join(AUDIO_DIR, "right.wav"),
    "向前": os.path.join(AUDIO_DIR, "forward.wav"),
    "后退": os.path.join(AUDIO_DIR, "backward.wav"),
    "OK": os.path.join(AUDIO_DIR, "ok.wav"),  # 添加OK音效
}
GUIDANCE_INTERVAL_SEC = 1.5  # 引导播报间隔

# 初始化pygame音频
pygame.mixer.init()

# ========= 窗口 =========
WINDOW = "YOLO Seg + Flow Polygon (Peri-Relock) (Grab Guidance)"

# ======== MediaPipe 别名 ========
BaseOptions           = mp.tasks.BaseOptions
VisionRunningMode     = mp.tasks.vision.RunningMode
HandLandmarker        = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
HAND_CONNECTIONS      = mp.solutions.hands.HAND_CONNECTIONS

# ======== HandLandmarker 回调缓存 ========
_last_result = None  # (result, timestamp_ms)

def on_result(result: mp.tasks.vision.HandLandmarkerResult,
              output_image: mp.Image, timestamp_ms: int):
    global _last_result
    _last_result = (result, timestamp_ms)

def _to_proto(hand_lms) -> landmark_pb2.NormalizedLandmarkList:
    proto = landmark_pb2.NormalizedLandmarkList()
    proto.landmark.extend([
        landmark_pb2.NormalizedLandmark(x=p.x, y=p.y, z=p.z) for p in hand_lms
    ])
    return proto

# —— 手骨架单色渲染 —— #
def draw_hands_mono(img_bgr, hand_lms, color=(0, 255, 255), r=2, t=2):
    mp_drawing = mp.solutions.drawing_utils
    landmark_spec   = mp_drawing.DrawingSpec(color=color, thickness=-1, circle_radius=r)
    connection_spec = mp_drawing.DrawingSpec(color=color, thickness=t,  circle_radius=r)
    if hasattr(hand_lms, "landmark"):
        proto = hand_lms
    else:
        proto = _to_proto(hand_lms)
    mp_drawing.draw_landmarks(
        img_bgr,
        landmark_list=proto,
        connections=HAND_CONNECTIONS,
        landmark_drawing_spec=landmark_spec,
        connection_drawing_spec=connection_spec,
    )

def norm_name(s: str) -> str:
    return "".join(str(s).lower().split())

# ======== TTS（pyttsx3）========
class Speaker:
    def __init__(self, enable=True):
        self.enable = enable
        self._engine = None
        self._lock = threading.Lock()
        if enable:
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
                self._engine.setProperty('rate', 190)
                self._engine.setProperty('volume', 1.0)
            except Exception:
                self._engine = None
                self.enable = False

    def say_async(self, text: str):
        if not self.enable or not text:
            return
        def _run():
            try:
                with self._lock:
                    self._engine.stop()
                    self._engine.say(text)
                    self._engine.iterate()
                    t0 = time.time()
                    while self._engine.isBusy() and (time.time() - t0) < 1.2:
                        self._engine.iterate()
                        time.sleep(0.01)
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

# ======== 中文文本绘制（优先 Pillow）========
_PIL_OK = False
_FONT_PATH = None
def _init_font():
    global _PIL_OK, _FONT_PATH
    try:
        from PIL import ImageFont  # noqa
        _PIL_OK = True
    except Exception:
        _PIL_OK = False
        return
    candidates = [
        r"C:\\Windows\\Fonts\\msyh.ttc",
        r"C:\\Windows\\Fonts\\msyh.ttf",
        r"C:\\Windows\\Fonts\\simhei.ttf",
        r"C:\\Windows\\Fonts\\simfang.ttf",
        r"C:\\Windows\\Fonts\\simsun.ttc",
        r"C:\\Windows\\Fonts\\simsunb.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            _FONT_PATH = p
            return
    _PIL_OK = False
_init_font()

def draw_text_cn(img_bgr, text, xy, font_size=20, color=(255,255,255), stroke=None, ui_hint=True):
    """
    统一的文本绘制：
    - 默认采用前端风格：小字体、左下角按行堆叠(ui_hint=True)。
    - 若 ui_hint=False 则按传入 xy 精确定位（用于贴近目标的小标注）。
    """
    # 统一样式：微软雅黑 + 固定字号 + 纯白
    color = (255, 255, 255)
    font_size = int(UNIFIED_FONT_PX)

    H, W = img_bgr.shape[:2]
    # 右上角堆叠布局：计算y顶边，并按文本宽度右对齐
    y_top = _ui_next_y_top(font_size) if ui_hint else _ui_next_y_top(font_size)
    # 先估算文本尺寸
    tw = th = 0
    font_obj = None

    if _PIL_OK and _FONT_PATH:
        try:
            from PIL import Image, ImageDraw, ImageFont
            font_obj = ImageFont.truetype(_FONT_PATH, font_size)
            # 计算文本尺寸
            bbox = ImageDraw.Draw(Image.new('RGB', (1,1))).textbbox((0,0), text, font=font_obj)
            tw = max(1, bbox[2] - bbox[0])
            th = max(1, bbox[3] - bbox[1])
        except Exception:
            pass
    if _PIL_OK and _FONT_PATH and font_obj is not None:
        try:
            from PIL import Image, ImageDraw
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            draw = ImageDraw.Draw(pil_img)
            x = max(8, W - _UI_RIGHT_MARGIN - tw)
            y = y_top
            draw.text((x, y), text, fill=(255,255,255), font=font_obj)
            img_bgr[:] = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            return
        except Exception:
            pass
    # OpenCV 回退：估算尺寸并右对齐
    if tw <= 0 or th <= 0:
        scale = font_size/24.0
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
    x = max(8, W - _UI_RIGHT_MARGIN - int(tw))
    y_baseline = int(y_top + th)
    cv2.putText(img_bgr, text, (x, y_baseline), cv2.FONT_HERSHEY_SIMPLEX, font_size/24.0, color, 2, cv2.LINE_AA)

# ======== 工具函数 ========
def clamp01(x): return max(0.0, min(1.0, x))

def draw_progress_bars(vis, align_score, range_score):
    """第一条=对齐，第二条=距离(≈1)，对应 ratio 与 1 的接近程度"""
    H, W = vis.shape[:2]
    bar_w = int(W * 0.28)
    bar_h = 12
    gap   = 8
    x0    = 12
    y0    = H - 2*bar_h - gap - 12
    # 背景
    cv2.rectangle(vis, (x0, y0), (x0 + bar_w, y0 + bar_h), (50, 50, 50), -1)
    cv2.rectangle(vis, (x0, y0 + bar_h + gap), (x0 + bar_w, y0 + 2*bar_h + gap), (50, 50, 50), -1)
    # 填充
    cv2.rectangle(vis, (x0, y0), (x0 + int(bar_w * clamp01(align_score)), y0 + bar_h), (0, 220, 0), -1)
    cv2.rectangle(vis, (x0, y0 + bar_h + gap), (x0 + int(bar_w * clamp01(range_score)), y0 + 2*bar_h + gap), (0, 180, 255), -1)
    draw_text_cn(vis, "对齐",       (x0, y0 - 18),                 font_size=18, color=(180,180,180))
    draw_text_cn(vis, "距离(≈1)",   (x0, y0 + bar_h + gap - 18),   font_size=18, color=(180,180,180))

def polygon_center_and_area(poly):
    if poly is None or len(poly) < 3:
        return None, 0.0
    poly = np.array(poly, dtype=np.float32)
    M = cv2.moments(poly)
    if abs(M["m00"]) < 1e-6:
        c = np.mean(poly, axis=0)
        return (float(c[0]), float(c[1])), 0.0
    cx = float(M["m10"] / M["m00"])
    cy = float(M["m01"] / M["m00"])
    area = float(cv2.contourArea(poly.astype(np.int32)))
    return (cx, cy), area

def hand_bbox_and_area(lms, W, H):
    xs = [int(p.x * W) for p in lms]
    ys = [int(p.y * H) for p in lms]
    if not xs or not ys:
        return None, 0.0
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    w = max(1, x1 - x0)
    h = max(1, y1 - y0)
    area = float(w * h)
    return (x0, y0, w, h), area

# ======== 手势：握持(Grasp) 识别（放宽版启发式）========
THUMB_INDEX_CLOSE = 0.34   # 放宽
FINGERTIP_NEAR    = 0.44   # 放宽
MIN_CURLED_COUNT  = 1      # 放宽

def detect_grasp(hand_lms, W, H):
    box, _ = hand_bbox_and_area(hand_lms, W, H)
    if not box:
        return False, 0.0
    x0, y0, w0, h0 = box
    hand_diag = float(np.hypot(w0, h0)) + 1e-6
    palm_idx = [0, 5, 9, 13, 17]
    px = np.mean([hand_lms[i].x * W for i in palm_idx])
    py = np.mean([hand_lms[i].y * H for i in palm_idx])
    palm = np.array([px, py], dtype=np.float32)
    t4 = np.array([hand_lms[4].x * W, hand_lms[4].y * H], dtype=np.float32)
    t8 = np.array([hand_lms[8].x * W, hand_lms[8].y * H], dtype=np.float32)
    thumb_index_dist = float(np.linalg.norm(t4 - t8)) / hand_diag
    tips = [12, 16, 20]
    dists = []
    for i in tips:
        ti = np.array([hand_lms[i].x * W, hand_lms[i].y * H], dtype=np.float32)
        dists.append(float(np.linalg.norm(ti - palm)) / hand_diag)
    curled_cnt = sum(1 for d in dists if d < FINGERTIP_NEAR)
    cond1 = (thumb_index_dist < THUMB_INDEX_CLOSE)
    cond2 = (curled_cnt >= MIN_CURLED_COUNT)
    score = 0.5 * (1.0 - min(thumb_index_dist / THUMB_INDEX_CLOSE, 1.0)) + \
            0.5 * min(curled_cnt / 3.0, 1.0)
    return (cond1 and cond2), score

# ======== 内收后的边界提点 ========
def inner_offset_edge(mask_bin, offset_px=5, edge_dilate_px=2):
    if offset_px > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*offset_px+1, 2*offset_px+1))
        eroded = cv2.erode(mask_bin.astype(np.uint8), k, iterations=1)
    else:
        eroded = mask_bin.astype(np.uint8)
    edges = cv2.Canny(eroded*255, 50, 150)
    if edge_dilate_px > 0:
        k2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*edge_dilate_px+1, 2*edge_dilate_px+1))
        edges = cv2.dilate(edges, k2, iterations=1)
    return edges  # uint8 0/255

# ======== YOLO 分割：全帧或 ROI 内选择最佳 mask ========
def find_best_mask(frame_bgr, yolo, W, H, target_cls_id, conf_thr=0.10, roi_rect=None):
    results = yolo(frame_bgr, verbose=False)
    best_mask = None
    best_score = 0.0
    if results and results[0].masks is not None:
        r0 = results[0]
        for mask_t, conf_t, cls_t in zip(r0.masks.data, r0.boxes.conf, r0.boxes.cls):
            cls_id = int(cls_t.item())
            conf_value = float(conf_t.item())
            if target_cls_id is not None and cls_id != target_cls_id:
                continue
            if conf_value < conf_thr:
                continue
            mask_np = mask_t.detach().cpu().numpy()
            mask_rz = cv2.resize(mask_np, (W, H), interpolation=cv2.INTER_LINEAR)
            mask_bin = (mask_rz > 0.5).astype(np.uint8)

            if roi_rect is not None:
                x0, y0, x1, y1 = roi_rect
                x0, y0 = max(0, x0), max(0, y0)
                x1, y1 = min(W-1, x1), min(H-1, y1)
                roi = np.zeros_like(mask_bin, dtype=np.uint8)
                roi[y0:y1+1, x0:x1+1] = 1
                overlap = (mask_bin & roi).sum()
                score = float(overlap)
            else:
                score = float(mask_bin.sum())

            if score > best_score:
                best_score = score
                best_mask = mask_bin
    return best_mask

# ======== 工程化：测距箭头（端点定位线 + 箭头 + 像素值）========
def draw_measure_arrow(img, p1, p2, txt=None):
    p1 = (int(p1[0]), int(p1[1]))
    p2 = (int(p2[0]), int(p2[1]))
    # 端点定位线
    def end_cap(pt, size=8, color=(255,255,255), t=1):
        x, y = pt
        cv2.line(img, (x - size, y), (x + size, y), color, t, cv2.LINE_AA)
        cv2.line(img, (x, y - size), (x, y + size), color, t, cv2.LINE_AA)
    end_cap(p1, size=7, color=(255,255,255), t=1)
    end_cap(p2, size=7, color=(255,255,255), t=1)
    # 箭头
    cv2.arrowedLine(img, p1, p2, (255,255,255), 2, cv2.LINE_AA, tipLength=0.18)
    # 文本
    if txt is None:
        d = int(np.hypot(p2[0]-p1[0], p2[1]-p1[1]))
        txt = f"{d}px"
    mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
    font = cv2.FONT_HERSHEY_SIMPLEX
    fs, th = 0.6, 2
    (tw, th_text), _ = cv2.getTextSize(txt, font, fs, th)
    pad = 4
    x0 = mid[0] - tw//2 - pad
    y0 = mid[1] - th_text - 6
    x1 = mid[0] + tw//2 + pad
    y1 = mid[1] + 6
    cv2.rectangle(img, (x0, y0), (x1, y1), (32,32,32), -1)
    cv2.putText(img, txt, (x0+pad, y1-6), font, fs, (255,255,255), th, cv2.LINE_AA)

# 添加绘制虚线的函数
def draw_dashed_line(img, pt1, pt2, color=(255, 255, 255), thickness=2, dash_length=10, gap_length=5):
    """绘制虚线"""
    pt1 = np.array(pt1, dtype=np.float32)
    pt2 = np.array(pt2, dtype=np.float32)
    line_vec = pt2 - pt1
    line_len = np.linalg.norm(line_vec)
    if line_len < 1:
        return
    
    line_vec = line_vec / line_len  # 单位向量
    
    # 绘制虚线段
    current_pos = 0
    while current_pos < line_len:
        start_pos = current_pos
        end_pos = min(current_pos + dash_length, line_len)
        
        start_pt = pt1 + line_vec * start_pos
        end_pt = pt1 + line_vec * end_pos
        
        cv2.line(img, tuple(start_pt.astype(int)), tuple(end_pt.astype(int)), color, thickness)
        
        current_pos += dash_length + gap_length

# 添加绘制手部轮廓的函数
def draw_hand_contour(img, hand_lms, W, H, color=(255, 255, 255), thickness=1):
    """绘制手部landmarks的凸包轮廓"""
    # 获取所有手部关键点
    points = []
    for lm in hand_lms:
        x = int(lm.x * W)
        y = int(lm.y * H)
        points.append([x, y])
    
    if len(points) > 3:
        points = np.array(points, dtype=np.int32)
        # 计算凸包
        hull = cv2.convexHull(points)
        # 绘制凸包轮廓
        cv2.polylines(img, [hull], True, color, thickness)

# 检测手和物体是否接触
def check_hand_object_contact(hand_box, poly, overlap_threshold=0.15):
    """
    检测手的边界框和物体多边形是否有重叠
    返回: (是否接触, 重叠比例)
    """
    if hand_box is None or poly is None or len(poly) < 3:
        return False, 0.0
    
    # 获取手的边界框
    hx, hy, hw, hh = hand_box
    hand_rect = np.array([
        [hx, hy],
        [hx + hw, hy],
        [hx + hw, hy + hh],
        [hx, hy + hh]
    ], dtype=np.int32)
    
    # 创建掩码来计算重叠
    H = int(max(hy + hh, np.max(poly[:, 1])) + 10)
    W = int(max(hx + hw, np.max(poly[:, 0])) + 10)
    
    hand_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.fillPoly(hand_mask, [hand_rect], 1)
    
    obj_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.fillPoly(obj_mask, [poly.astype(np.int32)], 1)
    
    # 计算重叠
    intersection = np.logical_and(hand_mask, obj_mask).sum()
    hand_area = hand_mask.sum()
    
    # 重叠比例（相对于手的面积）
    overlap_ratio = intersection / max(1.0, hand_area)
    
    return overlap_ratio > overlap_threshold, overlap_ratio

# 添加方向判断函数
def get_guidance_direction(hand_center, object_center, hand_area, object_area, hand_box=None, poly=None):
    """
    根据手心和物体中心位置，以及面积比，返回引导方向
    返回: (方向文字, 是否需要前后调整)
    """
    if hand_center is None or object_center is None:
        return None, None
    
    # 首先检查手和物体是否接触
    is_touching = False
    overlap_ratio = 0.0
    if hand_box is not None and poly is not None:
        is_touching, overlap_ratio = check_hand_object_contact(hand_box, poly, overlap_threshold=0.1)
    
    hx, hy = hand_center
    ox, oy = object_center
    
    # 计算水平和垂直偏差
    dx = ox - hx  # 正数表示物体在右边
    dy = oy - hy  # 正数表示物体在下边
    
    # 如果手和物体已经接触，直接返回"向前"
    if is_touching:
        return "向前", f"接触度: {overlap_ratio:.1%}"
    
    # 如果没有接触，引导上下左右
    # 判断主要方向
    h_threshold = 30  # 水平偏差阈值（像素）
    v_threshold = 30  # 垂直偏差阈值（像素）
    
    h_dir = None
    v_dir = None
    
    # 水平方向
    if abs(dx) > h_threshold:
        h_dir = "向右" if dx > 0 else "向左"
    
    # 垂直方向
    if abs(dy) > v_threshold:
        v_dir = "向下" if dy > 0 else "向上"
    
    # 选择偏移最大的方向
    if abs(dx) > abs(dy) and h_dir:
        # 水平偏移更大
        return h_dir, v_dir
    elif v_dir:
        # 垂直偏移更大或相等
        return v_dir, h_dir
    else:
        # 已经在中心附近但还没接触，提示靠近
        distance = np.sqrt(dx**2 + dy**2)
        if distance < 50:  # 很近但还没接触
            return "向前", "请缓慢靠近"
        else:
            return "保持", None

# 播放音频的函数
def play_guidance_audio(direction):
    """播放方向引导音频"""
    # 直接调用新的音频播放函数
    play_audio_threadsafe(direction)
    # 同步更新底部按钮的指令文本
    try:
        if isinstance(direction, str) and direction.strip():
            set_current_command(direction.strip())
    except Exception:
        pass

# 添加居中判断函数
def get_center_guidance(object_center, frame_center, threshold=30):
    """
    判断物体是否在画面中心，返回引导方向
    返回: (方向文字, 是否已居中)
    """
    if object_center is None:
        return None, False
    
    ox, oy = object_center
    cx, cy = frame_center
    
    dx = cx - ox  # 正数表示需要向右移动
    dy = cy - oy  # 正数表示需要向下移动
    
    # 判断是否已经居中
    distance = np.sqrt(dx**2 + dy**2)
    if distance < threshold:
        return "已居中", True
    
    # 判断主要方向（对调左右和上下）
    if abs(dx) > abs(dy):
        return "向左" if dx > 0 else "向右", False  # 对调了
    else:
        return "向上" if dy > 0 else "向下", False  # 对调了

def main(headless: bool = False, prompt_name: str = None, stop_event=None):

    # OpenCV 优化
    try:
        import cv2
        cv2.setUseOptimized(True)
        cv2.setNumThreads(2)   # 视 CPU 核心数而定；树莓派类设备可设 1
    except Exception:
        pass




    # 如果传入了 prompt_name，使用它替换全局的 PROMPT_NAME
    global PROMPT_NAME
    if prompt_name:
        PROMPT_NAME = prompt_name
        print(f"[YOLOMEDIA] Using dynamic prompt: {PROMPT_NAME}")
    
    speaker = Speaker(ENABLE_TTS)
    last_tts_ts = 0.0
    MODE = "SEGMENT"  # 模式：SEGMENT -> FLASH -> CENTER_GUIDE -> TRACK
    colors = Colors()

    FRAME_IDX    = 0
    last_mask    = None      # 上一帧"目标掩膜"（用于 IoU 降噪）
    flow_mask    = None      # 光流外推得到的掩膜（你现有代码里会更新它）
    flow_grace   = 0         # YOLOE 丢检后，允许光流顶住的计数
    last_seen_ts = 0.0       # 最近一次 YOLOE 成功检测的时间戳
    locked_id    = None      # （可选）若你在 tracker 里记录了 id，可在下面选择相同 id
    # 刷新/容错参数（可按需微调）
    REDETECT_EVERY = 5       # 每 5 帧强制"信任 YOLOE 一次"
    FLOW_GRACE_MAX = 8       # YOLOE 连续丢检时，光流最多顶 8 帧
    IOU_MIN_KEEP   = 0.20    # 新/旧掩膜 IoU 太低时，用平滑合成，避免闪烁



    print("[INIT] 加载 YOLO 模型...")
    # NOTE: shoppingbest 不再用于找东西流程；如其他模式仍需，可保留 yolo = YOLO(...) 但不在本流程使用
    # yolo = YOLO(YOLO_MODEL_PATH)

    # —— 直接启用 YOLOE 文本提示后端（不再先查 shoppingbest）——
    use_yoloe = False
    yoloe_backend = None
    if _YOLOE_READY:
        try:
            yoloe_backend = YoloEBackend()                  # 可用 YOLOE_MODEL_PATH 环境变量指定模型
            yoloe_backend.set_text_classes([PROMPT_NAME])   # 文本类别
            use_yoloe = True
            print(f"[DETECTOR] YOLOE text-prompt backend enabled for: {PROMPT_NAME}", flush=True)
        except Exception as e:
            print(f"[DETECTOR] YOLOE init failed: {e}", flush=True)
    else:
        print("[DETECTOR] YOLOE backend not ready (import failed)", flush=True)

    # 类名映射（YOLOE 模式下简化）
    if use_yoloe:
        # YOLOE 模式下，只有一个目标类
        id_to_name = {0: PROMPT_NAME}
        name_to_id = {norm_name(PROMPT_NAME): 0}
        target_cls_id = 0
    else:
        # 如果将来需要支持传统 YOLO，可以在这里初始化
        id_to_name = {}
        name_to_id = {}
        target_cls_id = None

    # 目标类已在上面的 YOLOE 模式中设置

    print(f"[CLASS] target id={target_cls_id}, name={id_to_name.get(target_cls_id, 'N/A')}")
    print(f"[阈值] conf >= {CONF_THRESHOLD:.2f}")

    # Hand Landmarker
    print("[INIT] 初始化 Hand Landmarker...")
    base = BaseOptions(model_asset_path=HAND_TASK_PATH)
    hand_options = HandLandmarkerOptions(
        base_options=base,
        running_mode=VisionRunningMode.LIVE_STREAM,
        num_hands=1,
        min_hand_detection_confidence=0.40,
        min_hand_presence_confidence=0.50,
        min_tracking_confidence=0.70,
        result_callback=on_result
    )
    landmarker = HandLandmarker.create_from_options(hand_options)

    W = None
    H = None
    print("[Bridge] 等待 ESP32 画面 ...")

    # [headless] 仅在非 headless 时创建窗口（原逻辑保留，外层加判断）
    if not headless:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)

    # 光流缓存
    old_gray = None
    p0 = None
    lock_edge_debug = None     # 调试可视化：内边界
    track_frame_count = 0      # 控制周边监控频率
    last_poly_box = None       # 当前多边形外接矩形

    fps_hist = []
    
    # 添加自动锁定相关变量
    auto_lock_start_time = None  # 开始检测到物体的时间
    auto_lock_delay = 1.0        # 1秒后自动锁定
    last_detected_mask = None    # 最后检测到的mask
    
    # 添加闪烁动画相关变量
    flash_start_time = None      # 闪烁开始时间
    flash_duration = 1.0         # 闪烁持续时间（秒）
    flash_frequency = 1          # 闪烁频率（Hz） - 只闪一次
    flash_mask = None            # 用于闪烁的mask
    flash_color = (0, 255, 255)  # 闪烁颜色（黄色）

    # 添加引导相关变量
    last_guidance_time = 0
    last_guidance_direction = None

    # 添加居中引导相关变量
    center_guide_mask = None      # 用于居中引导的mask
    center_guide_start = None     # 居中引导开始时间
    center_threshold = 30         # 居中判定阈值（像素）
    last_center_guide_time = 0   # 上次居中引导语音时间
    center_reached = False        # 是否已经到达中心

    # 添加抓取跟踪相关变量
    grasp_tracking_frames = []  # 存储最近的手和物体位置
    grasp_tracking_duration = 1.0  # 需要持续1秒
    grasp_movement_threshold = 10  # 最小移动像素阈值（提高阈值）
    grasp_detected = False  # 是否已经检测到抓取
    grasp_start_time = None  # 开始检测到协同移动的时间
    
    # 背景参考点（用于检测相机移动） - 移到这里初始化
    background_points = None
    old_background_gray = None

    try:
        while True:
            # 检查停止事件
            if stop_event and stop_event.is_set():
                print("[YOLOMEDIA] Stop event detected, exiting...")
                break
                
            frame = bridge_io.wait_raw_bgr(timeout_sec=0.5)
            if frame is None:
                # 没取到帧就继续等（ESP32还没连上或暂时无新帧）
                # [headless] 给出 1ms 让出调度，避免空转
                if headless:
                    cv2.waitKey(1)
                continue
            
            # 每帧重置 UI 文字叠加到左下角
            H, W = frame.shape[:2]
            ui_reset_overlay(H)

            vis = frame.copy()
            t_now = time.time()

            # 抽帧 + 降采样（人手识别）
            if FRAME_IDX % HAND_FPS_DIV == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if HAND_DOWNSCALE and HAND_DOWNSCALE != 1.0:
                    small = cv2.resize(rgb, None, fx=HAND_DOWNSCALE, fy=HAND_DOWNSCALE, interpolation=cv2.INTER_AREA)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=small)
                else:
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                landmarker.detect_async(mp_image, int(t_now * 1000))
            # 否则跳过，复用上一次 _last_result；Landmarker 会自己做 tracking


            # 取手心、手框、握持（放宽版）
            hand_center = None
            hand_area = None
            hand_box = None
            grasp_now = False
            grasp_score = 0.0
            if _last_result is not None:
                res, _ = _last_result
                if res.hand_landmarks and len(res.hand_landmarks) > 0:
                    l0 = res.hand_landmarks[0]
                    
                    # 绘制手部骨骼
                    draw_hands_mono(vis, l0, color=(0, 255, 255), r=2, t=2)
                    
                    # 绘制手部轮廓（替代矩形框）
                    draw_hand_contour(vis, l0, W, H, color=(255, 255, 255), thickness=1)
                    
                    xs = [p.x * W for p in l0]
                    ys = [p.y * H for p in l0]
                    hand_center = (float(sum(xs)/len(xs)), float(sum(ys)/len(ys)))
                    hand_box, hand_area = hand_bbox_and_area(l0, W, H)
                    # 注释掉矩形框绘制
                    # if hand_box:
                    #     x0, y0, w0, h0 = hand_box
                    #     cv2.rectangle(vis, (x0, y0), (x0+w0, y0+h0), (0,255,255), 1)
                    grasp_now, grasp_score = detect_grasp(l0, W, H)
                    draw_text_cn(vis, f"握持评分: {grasp_score:.2f}", (10, 70), font_size=18, color=(0, 180, 255))
                    

            if MODE == "SEGMENT":
                # —— 仅 YOLOE：每帧文本提示分割 + 取最大目标（删掉 shoppingbest 与重复 YOLOE 段）——
                FRAME_IDX += 1
                candidate_masks = []
                detected_object = False

                if use_yoloe and yoloe_backend is not None:
                    # 每帧都跑；persist=True 便于维持目标 ID
                    det = yoloe_backend.segment(frame, conf=0.20, iou=0.45, imgsz=640, persist=True)
                    H, W = frame.shape[:2]

                    # 选一个掩膜：优先与 locked_id 相同；否则面积最大
                    chosen_idx = None
                    if det["masks"]:
                        if locked_id is not None and det["ids"] and (locked_id in det["ids"]):
                            chosen_idx = det["ids"].index(locked_id)
                        else:
                            areas = [int(m.sum()) for m in det["masks"]]
                            chosen_idx = int(np.argmax(areas))

                    if chosen_idx is not None:
                        m = det["masks"][chosen_idx]
                        if m.shape[:2] != (H, W):
                            m = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST)

                        mask_bin = (m > 0).astype(np.uint8)
                        candidate_masks.append({
                            "mask": mask_bin,
                            "area": int(mask_bin.sum()),
                            "name": PROMPT_NAME,
                            "cls_id": 0,
                            "conf": 0.99,
                        })
                        detected_object = True

                        # 简单可视化（半透明叠层 + 轮廓），不影响你后面的逻辑
                        colored = np.zeros_like(frame, dtype=np.uint8)
                        colored[mask_bin == 1] = (0, 255, 255)
                        vis = cv2.addWeighted(vis, 1.0, colored, MASK_ALPHA, 0)
                        contours, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                        if contours:
                            # 选择最大轮廓并进行适度平滑
                            largest_contour = max(contours, key=cv2.contourArea)
                            # 使用Douglas-Peucker算法适度简化，保持更多细节
                            epsilon = CONTOUR_EPSILON_FACTOR * cv2.arcLength(largest_contour, True)  # 更小的epsilon保留更多细节
                            smoothed_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
                            cv2.drawContours(vis, [smoothed_contour], -1, (0, 255, 255), STROKE_WIDTH)

                        # 记录 id，减少目标跳变
                        if det["ids"] and len(det["ids"]) > chosen_idx and det["ids"][chosen_idx] is not None:
                            locked_id = int(det["ids"][chosen_idx])

                else:
                    # YOLOE 未就绪：提示并保持原画面（不阻塞前端）
                    draw_text_cn(vis, "YOLOE 未就绪，显示原始画面", (10, 100), font_size=22, color=(0, 215, 255))

                # 选择面积最大的mask  ←—— 这一行下面开始保留你的原代码

                # 选择面积最大的mask
                if candidate_masks:
                    # 按面积降序排序
                    candidate_masks.sort(key=lambda x: x['area'], reverse=True)
                    largest_mask_info = candidate_masks[0]
                    last_detected_mask = largest_mask_info['mask']
                    
                    # 可选：在最大的物体上添加特殊标记
                    contours, _ = cv2.findContours(last_detected_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    if contours:
                        # 找到最大轮廓的中心
                        M = cv2.moments(contours[0])
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])
                            # 在最大物体中心画一个圆圈标记
                            cv2.circle(vis, (cx, cy), 8, (0, 255, 0), 2)
                            cv2.circle(vis, (cx, cy), 12, (0, 255, 0), 1)
                            # 目标标签：保持就地标注
                            draw_text_cn(vis, "目标", (cx + 15, cy - 5), font_size=16, color=FRONTEND_COLORS["ok"], ui_hint=False)
                    
                    # 显示检测信息
                    if len(candidate_masks) > 1:
                        draw_text_cn(vis, f"检测到{len(candidate_masks)}个物体，选择最大的（面积: {largest_mask_info['area']}）", 
                                   (10, H - 30), font_size=16, color=(255, 255, 0))
                
                # 自动锁定逻辑
                if detected_object and last_detected_mask is not None:
                    if auto_lock_start_time is None:
                        auto_lock_start_time = t_now
                        print(f"[AUTO] 检测到物体，选择最大的（面积: {np.sum(last_detected_mask)}），开始倒计时...")
                        #play_guidance_audio("检测到物体")  # 添加这行
                    
                    elapsed = t_now - auto_lock_start_time
                    remaining = auto_lock_delay - elapsed
                    
                    if remaining > 0:
                        # 显示倒计时（移动到左下角，前端风格）
                        draw_text_cn(vis, f"检测到物体，{remaining:.1f}秒后自动锁定", (10, 100), font_size=16, color=FRONTEND_COLORS["text"], stroke=(0,0,0))
                        
                        # 绘制锁定框 - 使用虚线框表示正在准备锁定
                        if last_detected_mask is not None:
                            contours, _ = cv2.findContours(last_detected_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                            if contours:
                                # 找到最大轮廓
                                largest_contour = max(contours, key=cv2.contourArea)
                                # 简化轮廓
                                epsilon = CONTOUR_EPSILON_FACTOR * cv2.arcLength(largest_contour, True)
                                smoothed_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
                                
                                # 根据倒计时进度改变颜色亮度
                                progress = 1.0 - (remaining / auto_lock_delay)
                                color_intensity = int(100 + 155 * progress)  # 从100到255
                                lock_color = (0, color_intensity, color_intensity)  # 黄色渐亮
                                
                                # 绘制虚线轮廓
                                pts = smoothed_contour.reshape(-1, 2)
                                for i in range(len(pts)):
                                    pt1 = tuple(pts[i])
                                    pt2 = tuple(pts[(i + 1) % len(pts)])
                                    # 使用虚线效果（通过绘制短线段）
                                    draw_dashed_line(vis, pt1, pt2, color=lock_color, thickness=3, 
                                                   dash_length=15, gap_length=8)
                    else:
                        # 进入闪烁模式
                        print("[AUTO] 进入闪烁动画模式")
                        MODE = "FLASH"
                        flash_start_time = t_now
                        flash_mask = last_detected_mask.copy()
                        auto_lock_start_time = None
                        play_guidance_audio("检测到物体") 
                else:
                    # 没有检测到物体，重置计时器
                    if auto_lock_start_time is not None:
                        print("[AUTO] 物体丢失，重置倒计时")
                    auto_lock_start_time = None
                    last_detected_mask = None
                    draw_text_cn(vis, "分割中... 等待检测到物体", (10, 100), font_size=16, color=FRONTEND_COLORS["muted"])

            elif MODE == "FLASH":
                # 闪烁动画模式
                if flash_start_time is not None and flash_mask is not None:
                    elapsed = t_now - flash_start_time
                    
                    if elapsed < flash_duration:
                        # 计算渐入渐出效果
                        # 前0.3秒渐入，中间0.4秒保持，后0.3秒渐出
                        if elapsed < 0.3:
                            # 渐入阶段
                            alpha = elapsed / 0.3 * 0.8  # 0到0.8
                        elif elapsed < 0.7:
                            # 保持阶段
                            alpha = 0.8
                        else:
                            # 渐出阶段
                            alpha = (1.0 - elapsed) / 0.3 * 0.8  # 0.8到0
                        
                        # 绘制闪烁的mask
                        colored = np.zeros_like(frame, dtype=np.uint8)
                        colored[flash_mask == 1] = flash_color
                        vis = cv2.addWeighted(vis, 1.0 - alpha, colored, alpha, 0)
                        
                        # 绘制轮廓（固定粗细，颜色渐变）
                        contours, _ = cv2.findContours(flash_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                        if contours:
                            # 轮廓颜色也跟随alpha变化
                            contour_color = tuple(int(c * (0.5 + alpha * 0.5)) for c in flash_color)
                            cv2.drawContours(vis, contours, -1, contour_color, STROKE_WIDTH + 1)
                        
                        # 显示提示文字（左下角）
                        draw_text_cn(vis, "正在锁定目标...", (10, 100), font_size=18, color=FRONTEND_COLORS["accent"]) 
                    else:
                        # 闪烁结束，初始化光流追踪并进入居中引导模式
                        print("[AUTO] 闪烁结束，初始化光流追踪")
                        edge_mask = inner_offset_edge(flash_mask, offset_px=INNER_OFFSET_PX_LOCK, edge_dilate_px=EDGE_DILATE_PX)
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        pts = cv2.goodFeaturesToTrack(gray, mask=edge_mask, **FEATURE_PARAMS)
                        
                        if pts is not None and len(pts) >= 8:
                            p0 = pts
                            old_gray = gray
                            MODE = "CENTER_GUIDE"
                            lock_edge_debug = edge_mask.copy()
                            track_frame_count = 0
                            center_guide_start = t_now
                            center_reached = False
                            flash_start_time = None
                            flash_mask = None
                            last_detected_mask = None
                            print(f"[LOCK] 内边界特征点数={len(p0)} → CENTER_GUIDE")
                        else:
                            print("[LOCK] 内边界特征点不足，返回检测模式")
                            MODE = "SEGMENT"
                            flash_start_time = None
                            flash_mask = None
                            last_detected_mask = None
            
            elif MODE == "CENTER_GUIDE":
                # 居中引导模式（使用光流追踪）
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                poly_center = None
                poly_area = 0.0
                
                if old_gray is not None and p0 is not None and len(p0) >= 5:
                    # 光流追踪
                    p1, st, err = cv2.calcOpticalFlowPyrLK(old_gray, gray, p0, None, **LK_PARAMS)
                    if p1 is not None and st is not None:
                        good_new = p1[st == 1]
                        if len(good_new) >= 5:
                            p0 = good_new.reshape(-1, 1, 2)
                            hull = cv2.convexHull(good_new.reshape(-1,1,2))
                            poly = hull.reshape(-1, 2)
                            
                            if len(poly) >= 3:
                                H, W = frame.shape[:2]

                                # 把当前光流多边形 rasterize 成掩膜（便于与 YOLOE 掩膜做 IoU）
                                poly_mask = np.zeros((H, W), dtype=np.uint8)
                                cv2.fillPoly(poly_mask, [poly.astype(np.int32)], 1)

                                # 降频：每3帧用 YOLOE 重新检测，其余帧依赖光流维持
                                need_reseed = False
                                new_det_mask = None

                                if use_yoloe and yoloe_backend is not None and (FRAME_IDX % 3 == 0):
                                    # 添加调试信息
                                    if FRAME_IDX % 30 == 0:  # 每30帧打印一次
                                        print(f"[YOLOE] 实时检测第 {FRAME_IDX} 帧")
                                    det = yoloe_backend.segment(frame, conf=0.20, iou=0.45, imgsz=640, persist=True)
                                    if det["masks"]:
                                        # 取面积最大的那个
                                        areas = [int(m.sum()) for m in det["masks"]]
                                        j = int(np.argmax(areas))
                                        m = det["masks"][j]
                                        if m.shape[:2] != (H, W):
                                            m = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST)
                                        new_det_mask = (m > 0).astype(np.uint8)

                                        # 和当前光流多边形的 IoU
                                        inter = np.logical_and(new_det_mask, poly_mask).sum()
                                        union = np.logical_or(new_det_mask, poly_mask).sum() + 1e-6
                                        iou   = inter / union

                                        # IoU 太低，说明漂了：用 YOLOE 的掩膜重播种光流
                                        # 降低阈值，让 YOLOE 更容易更新光流
                                        if iou < 0.5:  # 从 IOU_MIN_KEEP (0.20) 提高到 0.5
                                            need_reseed = True
                                            # 用新掩膜的「内边界特征点」播种
                                            edge_mask = inner_offset_edge(new_det_mask, offset_px=INNER_OFFSET_PX_LOCK, edge_dilate_px=EDGE_DILATE_PX)
                                            gray2 = gray  # 本帧灰度图已在上面算过
                                            pts = cv2.goodFeaturesToTrack(gray2, mask=edge_mask, **FEATURE_PARAMS)
                                            if pts is not None and len(pts) >= 8:
                                                p0 = pts
                                                old_gray = gray2
                                                # 更新 last_mask，便于下游逻辑一致
                                                last_mask = new_det_mask.copy()
                                                last_seen_ts = time.time()
                                                flow_grace = 0
                                                print("[RESEED] YOLOE 低 IoU 触发重播种（已更新光流特征点）")

                                # 如果这帧没重播种，但 YOLOE 有结果且与 poly 很接近，可以做一次"平滑融合"，抑制抖动
                                if (not need_reseed) and (new_det_mask is not None):
                                    inter = np.logical_and(new_det_mask, poly_mask).sum()
                                    union = np.logical_or(new_det_mask, poly_mask).sum() + 1e-6
                                    iou   = inter / union
                                    # 降低融合阈值，让 YOLOE 结果更容易被采用
                                    if iou < 0.95:  # 从 0.90 提高到 0.95
                                        # 增加 YOLOE 的权重，让实时检测更明显
                                        poly_mask = ((0.8 * new_det_mask + 0.2 * poly_mask) > 0.5).astype(np.uint8)
                                        # 用更新后的 poly_mask 回写到可视化与引导的后续变量（如果你下游用的是 last_detected_mask/last_mask）
                                        last_mask = poly_mask.copy()
                                                                                # 更新多边形轮廓，让可视化实时更新
                                        contours, _ = cv2.findContours(poly_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                                        if contours:
                                            # 找到最大轮廓
                                            largest_contour = max(contours, key=cv2.contourArea)
                                            # 使用精细的轮廓处理，保留更多细节
                                            epsilon = TRACK_EPSILON_FACTOR * cv2.arcLength(largest_contour, True)
                                            poly = cv2.approxPolyDP(largest_contour, epsilon, True).reshape(-1, 2)
                                            # 注释掉凸包处理，保留原始轮廓细节
                                            # hull = cv2.convexHull(poly.reshape(-1,1,2))
                                            # poly = hull.reshape(-1, 2)
                                            # 重新计算特征点
                                            edge_mask = inner_offset_edge(poly_mask, offset_px=INNER_OFFSET_PX_LOCK, edge_dilate_px=EDGE_DILATE_PX)
                                            pts = cv2.goodFeaturesToTrack(gray, mask=edge_mask, **FEATURE_PARAMS)
                                            if pts is not None and len(pts) >= 5:
                                                p0 = pts

                                # 绘制追踪的多边形 - 使用更粗的线条
                                cv2.polylines(vis, [poly.astype(np.int32)], isClosed=True, color=(0,255,255), thickness=STROKE_WIDTH)
                                
                                # 计算多边形中心
                                poly_center, poly_area = polygon_center_and_area(poly)
                                
                                if poly_center:
                                    object_center = (int(poly_center[0]), int(poly_center[1]))
                                    
                                    # 画面中心
                                    frame_center = (W // 2, H // 2)
                                    
                                    # 绘制物品中心点
                                    cv2.circle(vis, object_center, 8, (0, 255, 0), -1)
                                    cv2.circle(vis, object_center, 12, (0, 255, 0), 2)
                                    
                                    # 绘制画面中心十字
                                    cv2.line(vis, (frame_center[0] - 20, frame_center[1]), 
                                            (frame_center[0] + 20, frame_center[1]), (255, 255, 255), 2)
                                    cv2.line(vis, (frame_center[0], frame_center[1] - 20), 
                                            (frame_center[0], frame_center[1] + 20), (255, 255, 255), 2)
                                    
                                    # 绘制引导虚线
                                    draw_dashed_line(vis, object_center, frame_center, 
                                                   color=(255, 255, 0), thickness=2, 
                                                   dash_length=10, gap_length=5)
                                    
                                    # 获取引导方向
                                    direction, is_centered = get_center_guidance(object_center, frame_center, center_threshold)
                                    
                                    if not center_reached:
                                        if is_centered:
                                            # 到达中心，播放OK音效
                                            center_reached = True
                                            last_center_guide_time = t_now
                                            play_guidance_audio("OK")
                                            try:
                                                bridge_io.send_ui_final("✓ 物品已居中！")
                                            except Exception:
                                                pass
                                            draw_text_cn(vis, "✓ 物品已居中！", (10, 60), font_size=18, color=FRONTEND_COLORS["ok"]) 
                                        else:
                                            # 显示引导文字
                                            msg = f"请将物品移到画面中心: {direction}"
                                            try:
                                                # 节流：每次语音播报也推一次final
                                                if t_now - last_center_guide_time > GUIDANCE_INTERVAL_SEC:
                                                    bridge_io.send_ui_final(msg)
                                            except Exception:
                                                pass
                                            draw_text_cn(vis, msg, 
                                                       (10, 40), font_size=18, color=FRONTEND_COLORS["text"])
                                            
                                            # 显示距离信息
                                            dx = frame_center[0] - object_center[0]
                                            dy = frame_center[1] - object_center[1]
                                            distance = int(np.sqrt(dx**2 + dy**2))
                                            draw_text_cn(vis, f"距离: {distance}px", 
                                                       (10, 60), font_size=16, color=FRONTEND_COLORS["muted"])
                                            
                                            # 播放语音引导
                                            if t_now - last_center_guide_time > GUIDANCE_INTERVAL_SEC:
                                                play_guidance_audio(direction)
                                                last_center_guide_time = t_now
                                    else:
                                        # 已经居中，显示成功信息
                                        try:
                                            bridge_io.send_ui_final("✓ 物品已成功移到中心！")
                                        except Exception:
                                            pass
                                        draw_text_cn(vis, "✓ 物品已成功移到中心！", 
                                                   (10, 60), font_size=18, color=FRONTEND_COLORS["ok"])
                                        
                                        # 等待1秒后进入手部追踪模式
                                        if t_now - last_center_guide_time > 1.0:
                                            print("[CENTER] 进入手部追踪模式")
                                            try:
                                                bridge_io.send_ui_final("进入手部追踪模式")
                                            except Exception:
                                                pass
                                            MODE = "TRACK"
                                            # 保持当前的光流追踪状态
                                else:
                                    # 多边形中心计算失败，显示警告
                                    draw_text_cn(vis, "正在追踪物体...", (10, 100), font_size=20, color=(255, 255, 0))
                        else:
                            # 光流点数不足，尝试重新检测
                            MODE = "SEGMENT"
                            old_gray = None
                            p0 = None
                            print("[CENTER] 光流追踪失败，返回检测模式")
                
                old_gray = gray

            else:  # MODE == "TRACK"
                # 手部追踪模式（原有逻辑保持不变）
                align_score = 0.0
                range_score = 0.0
                ratio = None

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                track_frame_count += 1

                relock_done = False
                poly_center = None
                poly_area = 0.0

                # 初始化camera_movement为默认值
                camera_movement = np.array([0.0, 0.0])
                
                # 初始化或更新背景参考点（在物体多边形外部取点）
                if background_points is None or track_frame_count % 30 == 0:
                    # 在画面四角取一些背景特征点
                    mask_for_bg = np.ones((H, W), dtype=np.uint8) * 255
                    if last_poly_box:
                        x, y, w, h = last_poly_box
                        # 扩大区域，排除物体和手
                        expand = 100
                        x1 = max(0, x - expand)
                        y1 = max(0, y - expand)
                        x2 = min(W, x + w + expand)
                        y2 = min(H, y + h + expand)
                        mask_for_bg[y1:y2, x1:x2] = 0
                    
                    # 在背景区域提取特征点
                    try:
                        bg_pts = cv2.goodFeaturesToTrack(gray, maxCorners=20, 
                                                       qualityLevel=0.1, 
                                                       minDistance=30, 
                                                       mask=mask_for_bg)
                        if bg_pts is not None and len(bg_pts) >= 5:
                            background_points = bg_pts
                            old_background_gray = gray.copy()
                    except Exception as e:
                        #print(f"[TRACK] 背景特征点提取失败: {e}")
                        background_points = None
                
                # 计算背景移动（相机移动）
                if old_background_gray is not None and background_points is not None and len(background_points) > 0:
                    try:
                        bg_p1, bg_st, _ = cv2.calcOpticalFlowPyrLK(
                            old_background_gray, gray, background_points, None, **LK_PARAMS
                        )
                        if bg_p1 is not None and bg_st is not None:
                            good_bg_old = background_points[bg_st == 1]
                            good_bg_new = bg_p1[bg_st == 1]
                            if len(good_bg_new) >= 3 and len(good_bg_old) >= 3:
                                # 计算背景的平均移动
                                bg_movement = np.mean(good_bg_new - good_bg_old, axis=0)
                                camera_movement = bg_movement.reshape(2)
                                background_points = good_bg_new.reshape(-1, 1, 2)
                                old_background_gray = gray.copy()
                    except Exception as e:
                        print(f"[TRACK] 背景光流计算失败: {e}")
                        camera_movement = np.array([0.0, 0.0])

                if old_gray is not None and p0 is not None and len(p0) >= 5:
                    p1, st, err = cv2.calcOpticalFlowPyrLK(old_gray, gray, p0, None, **LK_PARAMS)
                    if p1 is not None and st is not None:
                        good_new = p1[st == 1]
                        if len(good_new) >= 5:
                            p0 = good_new.reshape(-1, 1, 2)
                            hull = cv2.convexHull(good_new.reshape(-1,1,2))
                            poly = hull.reshape(-1, 2)
                            
                            if len(poly) >= 3:
                                # 统一的 YOLOE 实时检测和校正（每帧）
                                latest_det_mask = None
                                if use_yoloe and yoloe_backend is not None:
                                    # 添加调试信息
                                    if track_frame_count % 30 == 0:  # 每30帧打印一次
                                        print(f"[YOLOE] TRACK模式实时检测第 {track_frame_count} 帧")
                                    
                                    # YOLOE 实时检测（统一调用，避免重复）
                                    det = yoloe_backend.segment(frame, conf=YOLO_CORRECTION_CONF_THRESHOLD, iou=0.45, imgsz=640, persist=True)
                                    if det["masks"]:
                                        # 取面积最大的那个
                                        areas = [int(m.sum()) for m in det["masks"]]
                                        j = int(np.argmax(areas))
                                        m = det["masks"][j]
                                        if m.shape[:2] != (H, W):
                                            m = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST)
                                        latest_det_mask = (m > 0).astype(np.uint8)
                                        
                                        # 和当前光流多边形的 IoU
                                        poly_mask = np.zeros((H, W), dtype=np.uint8)
                                        cv2.fillPoly(poly_mask, [poly.astype(np.int32)], 1)
                                        inter = np.logical_and(latest_det_mask, poly_mask).sum()
                                        union = np.logical_or(latest_det_mask, poly_mask).sum() + 1e-6
                                        iou = inter / union
                                        
                                        # 降低IoU阈值，更积极地校正
                                        if iou > YOLO_CORRECTION_IOU_THRESHOLD:  # 使用可配置阈值
                                            # 用 YOLOE 结果更新多边形
                                            contours, _ = cv2.findContours(latest_det_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                                            if contours:
                                                largest_contour = max(contours, key=cv2.contourArea)
                                                # 使用更精细的轮廓处理，减少过度简化
                                                epsilon = TRACK_EPSILON_FACTOR * cv2.arcLength(largest_contour, True)
                                                poly = cv2.approxPolyDP(largest_contour, epsilon, True).reshape(-1, 2)
                                                
                                                # 更新光流特征点
                                                edge_mask = inner_offset_edge(latest_det_mask, offset_px=INNER_OFFSET_PX_LOCK, edge_dilate_px=EDGE_DILATE_PX)
                                                pts = cv2.goodFeaturesToTrack(gray, mask=edge_mask, **FEATURE_PARAMS)
                                                if pts is not None and len(pts) >= 5:
                                                    p0 = pts
                                                    #print(f"[TRACK] YOLOE 实时校正，IoU: {iou:.3f}")
                                
                                # 检查是否接触，决定轮廓颜色
                                is_touching = False
                                overlap_ratio = 0.0
                                if hand_box is not None and poly is not None:
                                    is_touching, overlap_ratio = check_hand_object_contact(hand_box, poly, overlap_threshold=0.1)
                                
                                # 绘制多边形（可能已被 YOLOE 更新）- 使用更粗的线条
                                if is_touching:
                                    # 接触时用亮绿色，并添加发光效果
                                    poly_color = (0, 255, 127)
                                    # 绘制一个更粗的外层轮廓作为发光效果
                                    cv2.polylines(vis, [poly.astype(np.int32)], isClosed=True, 
                                                color=(127, 255, 127), thickness=STROKE_WIDTH + 4)
                                    # 添加半透明的填充效果
                                    overlay = vis.copy()
                                    cv2.fillPoly(overlay, [poly.astype(np.int32)], (0, 255, 0))
                                    cv2.addWeighted(overlay, 0.15, vis, 0.85, 0, vis)
                                else:
                                    # 未接触时用普通绿色
                                    poly_color = (0, 255, 0)
                                cv2.polylines(vis, [poly.astype(np.int32)], isClosed=True, color=poly_color, thickness=STROKE_WIDTH)
                                # 多边形质心与面积
                                poly_center, poly_area = polygon_center_and_area(poly)
                                if poly_center:
                                    pc = (int(poly_center[0]), int(poly_center[1]))
                                    cv2.circle(vis, pc, 6, (0,255,0), -1)

                                # 多边形外接矩形（用于周边监控）
                                x, y, w, h = cv2.boundingRect(poly.astype(np.int32))
                                last_poly_box = (x, y, w, h)

                                # ====== 对齐分数（第一条）======
                                if hand_center and poly_center:
                                    hc = np.array(hand_center, dtype=np.float32)
                                    oc = np.array(poly_center, dtype=np.float32)
                                    dist = float(np.linalg.norm(oc - hc))
                                    diag = float(np.linalg.norm([W, H]))
                                    align_score = 1.0 - min(dist/(ALIGN_LOOSE_PCT*diag + 1e-6), 1.0)
                                    
                                    # 绘制虚线引导（替代原来的实线箭头）
                                    draw_dashed_line(vis, (hc[0], hc[1]), (oc[0], oc[1]), 
                                                   color=(255, 255, 0), thickness=2, 
                                                   dash_length=15, gap_length=10)
                                    
                                    # 方向引导
                                    direction, secondary = get_guidance_direction(
                                        hand_center, poly_center, hand_area, poly_area,
                                        hand_box, poly
                                    )
                                    
                                    if direction and direction != "保持":
                                        # 根据是否接触显示不同颜色
                                        if direction == "向前":
                                            # 手已经接触物体，用绿色显示
                                            guide_color = (0, 255, 0)  # 绿色
                                            draw_text_cn(vis, f"引导: {direction} - 伸手抓取", (W//2 - 80, 40), 
                                                       font_size=24, color=guide_color, stroke=(0, 0, 0))
                                        else:
                                            # 还未接触，用黄色显示
                                            guide_color = (0, 255, 255)  # 黄色
                                            draw_text_cn(vis, f"引导: {direction}", (W//2 - 60, 40), 
                                                       font_size=24, color=guide_color, stroke=(0, 0, 0))
                                        
                                        # 显示次要信息（接触度或其他方向）
                                        if secondary:
                                            if isinstance(secondary, str):
                                                # 接触度信息
                                                draw_text_cn(vis, secondary, (W//2 - 60, 70), 
                                                           font_size=18, color=(0, 255, 0))
                                            else:
                                                # 其他方向信息
                                                draw_text_cn(vis, f"（或 {secondary}）", (W//2 - 60, 70), 
                                                           font_size=18, color=(200, 200, 200))
                                        
                                        # 播放语音引导 - 确保每个方向都会播放
                                        if t_now - last_guidance_time > GUIDANCE_INTERVAL_SEC:
                                            # 检查方向是否改变，或者时间间隔足够
                                            if direction != last_guidance_direction or t_now - last_guidance_time > GUIDANCE_INTERVAL_SEC * 2:
                                                play_guidance_audio(direction)
                                                last_guidance_direction = direction
                                                last_guidance_time = t_now
                                                print(f"[GUIDE] 播放引导音频: {direction}")
                                else:
                                    align_score = 0.0

                                # 显示接触状态
                                is_touching, overlap_ratio = check_hand_object_contact(hand_box, poly, overlap_threshold=0.1)
                                if is_touching:
                                    draw_text_cn(vis, f"状态: 已接触 ({overlap_ratio:.1%})", (10, 95), 
                                               font_size=16, color=(0, 255, 0))
                                else:
                                    # 计算手和物体的距离
                                    if hand_center and poly_center:
                                        distance = np.sqrt((hand_center[0] - poly_center[0])**2 + 
                                                         (hand_center[1] - poly_center[1])**2)
                                        draw_text_cn(vis, f"距离: {distance:.0f}px", (10, 95), 
                                                   font_size=16, color=FRONTEND_COLORS["muted"])

                                # 成功条件：握持（放宽）
                                if (_last_result and _last_result[0].hand_landmarks and len(_last_result[0].hand_landmarks) > 0):
                                    l0 = _last_result[0].hand_landmarks[0]
                                    grasp_now, grasp_score = detect_grasp(l0, W, H)
                                else:
                                    grasp_now, grasp_score = False, 0.0
             
                                # guidance_msg 相关代码已经集成到上面的引导逻辑中

                                # ===== 周边监控 & 重新锁定（复用YOLO结果）=====
                                if (track_frame_count % PERI_CHECK_EVERY == 0) and (last_poly_box is not None) and (latest_det_mask is not None):
                                    # 直接使用刚才的YOLO检测结果，避免重复调用
                                    px, py, pw, ph = last_poly_box
                                    x0 = max(0, px - PERI_MONITOR_PX)
                                    y0 = max(0, py - PERI_MONITOR_PX)
                                    x1 = min(W - 1, px + pw + PERI_MONITOR_PX)
                                    y1 = min(H - 1, py + ph + PERI_MONITOR_PX)
                                    
                                    # 检查周边区域是否有更好的检测结果
                                    peri_area = latest_det_mask[y0:y1, x0:x1].sum()
                                    total_area = latest_det_mask.sum()
                                    
                                    # 如果周边区域有显著检测结果，重新锁定
                                    if peri_area > total_area * 0.1:  # 周边有10%以上的检测面积
                                        edge_mask = inner_offset_edge(latest_det_mask, offset_px=INNER_OFFSET_PX_LOCK, edge_dilate_px=EDGE_DILATE_PX)
                                        pts = cv2.goodFeaturesToTrack(gray, mask=edge_mask, **FEATURE_PARAMS)
                                        if pts is not None and len(pts) >= 8:
                                            p0 = pts
                                            old_gray = gray
                                            lock_edge_debug = edge_mask.copy()
                                            #print(f"[PERI] 周边重锁定，特征点数={len(p0)}")
                            else:
                                MODE = "SEGMENT"; old_gray = None; p0 = None; lock_edge_debug = None
                        else:
                            MODE = "SEGMENT"; old_gray = None; p0 = None; lock_edge_debug = None
                    else:
                        MODE = "SEGMENT"; old_gray = None; p0 = None; lock_edge_debug = None
                else:
                    MODE = "SEGMENT"; old_gray = None; p0 = None; lock_edge_debug = None

  

                if MODE == "SEGMENT":
                    draw_text_cn(vis, "追踪丢失 → 正在重新识别。按 Enter 重新锁定", (10, 100), font_size=22, color=(0,0,255))

                old_gray = gray

            # FPS（移动到左下角样式）
            if 'fps_hist' not in locals():
                fps_hist = []
            fps_hist.append(t_now)
            if len(fps_hist) > 30:
                fps_hist.pop(0)
            fps = 0.0 if len(fps_hist) < 2 else (len(fps_hist)-1)/(fps_hist[-1]-fps_hist[0])
            draw_text_cn(vis, f"FPS: {fps:.1f}", (10, 40), font_size=16, color=FRONTEND_COLORS["ok"]) 

            # 右下角显示"内边界/最近一次锁定"的调试图
            if lock_edge_debug is not None:
                # 极小缩放并放在右下角
                small = cv2.resize(lock_edge_debug, (0,0), fx=0.22, fy=0.22, interpolation=cv2.INTER_NEAREST)
                sh, sw = small.shape[:2]
                small_bgr = cv2.cvtColor(small, cv2.COLOR_GRAY2BGR)
                # 右下角位置，留 10-12px 边距
                x1 = max(8, W - sw - 12)
                y1 = max(8, H - sh - 12)
                y2 = y1 + sh
                x2 = x1 + sw
                vis[y1:y2, x1:x2] = small_bgr
                # 标签置于图上方紧贴，使用更小字号
                #draw_text_cn(vis, "内边界", (x1, y1 - 8), font_size=12, color=FRONTEND_COLORS["muted"], ui_hint=False)

            # 底部中间的"当前指令"按钮（始终绘制，文案随音频同步）
            draw_command_pill(vis, CURRENT_COMMAND_TEXT)

            # 展示（无论 headless 与否，都会推给前端）
            bridge_io.send_vis_bgr(vis)

            # [headless] 只有非 headless 时才弹窗与键盘交互；headless 下用 waitKey(1) 让出调度
            if not headless:
                cv2.imshow(WINDOW, vis)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord('q')):
                    break
                elif key == ord('r'):
                    MODE = "SEGMENT"; old_gray = None; p0 = None; lock_edge_debug = None
                elif key == 13:  # Enter：从 SEGMENT 锁定并开始 TRACK（内收 5px）
                    if MODE == "SEGMENT":
                        # 使用 YOLOE 进行手动锁定
                        if use_yoloe and yoloe_backend is not None:
                            det = yoloe_backend.segment(frame, conf=CONF_THRESHOLD, iou=0.45, imgsz=640, persist=True)
                            if det["masks"]:
                                # 取面积最大的那个
                                areas = [int(m.sum()) for m in det["masks"]]
                                j = int(np.argmax(areas))
                                m = det["masks"][j]
                                if m.shape[:2] != (H, W):
                                    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST)
                                best_mask = (m > 0.5).astype(np.uint8)
                            else:
                                best_mask = None
                        else:
                            best_mask = None
                        if best_mask is not None:
                            edge_mask = inner_offset_edge(best_mask, offset_px=INNER_OFFSET_PX_LOCK, edge_dilate_px=EDGE_DILATE_PX)
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            pts = cv2.goodFeaturesToTrack(gray, mask=edge_mask, **FEATURE_PARAMS)
                            if pts is not None and len(pts) >= 8:
                                p0 = pts
                                old_gray = gray
                                MODE = "TRACK"
                                lock_edge_debug = edge_mask.copy()
                                track_frame_count = 0
                                print(f"[LOCK] 内边界特征点数={len(p0)} → TRACK")
                            else:
                                print("[LOCK] 内边界特征点不足，请调整画面后重试。")
                        else:
                            print("[LOCK] 当前帧未找到有效分割，请重试。")
            else:
                # headless 下也调用一次 waitKey(1)，让 OpenCV 的计时器/回调得到机会，且避免 CPU 忙等
                cv2.waitKey(1)
                
                # 在 headless 模式下检查停止事件
                if stop_event and stop_event.is_set():
                    print("[YOLOMEDIA] Received stop signal in headless mode")
                    break

    finally:
        try:
            landmarker.close()
        except Exception:
            pass
        #cap.release()
        # [headless] 仅在非 headless 时销毁窗口
        if not headless:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
