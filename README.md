# AI 智能盲人眼镜系统 🤖👓

<div align="center">

一个面向视障人士的智能导航与辅助系统，集成了盲道导航、过马路辅助、物品识别、实时语音交互等功能。  本项目仅为交流学习使用，请勿直接给视障人群使用。本项目内仅包含代码，模型地址：https://www.modelscope.cn/models/archifancy/AIGlasses_for_navigation  。下载后存放在/model 文件夹

[功能特性](#功能特性) • [快速开始](#快速开始) • [系统架构](#系统架构) • [使用说明](#使用说明) • [开发文档](#开发文档)

</div>

---
<img width="2481" height="3508" alt="1" src="https://github.com/user-attachments/assets/e8dec4a6-8fa6-4d94-bd66-4e9864b67daf" />
<img width="2480" height="3508" alt="2" src="https://github.com/user-attachments/assets/bc7d1aac-a9e9-4ef8-9d67-224708d0c9fd" />
<img width="2481" height="3508" alt="4" src="https://github.com/user-attachments/assets/6dd19750-57af-4560-a007-9a7059956b53" />

## 📋 目录

- [功能特性](#功能特性)
- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [系统架构](#系统架构)
- [使用说明](#使用说明)
- [配置说明](#配置说明)
- [开发文档](#开发文档)

## ✨ 功能特性

### 🚶 盲道导航系统
- **实时盲道检测**：基于 YOLO 分割模型实时识别盲道
- **智能语音引导**：提供精准的方向指引（左转、右转、直行等）
- **障碍物检测与避障**：自动识别前方障碍物并规划避障路线
- **转弯检测**：自动识别急转弯并提前提醒
- **光流稳定**：使用 Lucas-Kanade 光流算法稳定掩码，减少抖动

### 🚦 过马路辅助
- **斑马线识别**：实时检测斑马线位置和方向
- **红绿灯识别**：基于颜色和形状的红绿灯状态检测
- **对齐引导**：引导用户对准斑马线中心
- **安全提醒**：绿灯时语音提示可以通行

### 🔍 物品识别与查找
- **智能物品搜索**：语音指令查找物品（如"帮我找一下红牛"）
- **实时目标追踪**：使用 YOLO-E 开放词汇检测 + ByteTrack 追踪
- **手部引导**：结合 MediaPipe 手部检测，引导用户手部靠近物品
- **抓取检测**：检测手部握持动作，确认物品已拿到
- **多模态反馈**：视觉标注 + 语音引导 + 居中提示

### 🎙️ 实时语音交互
- **语音识别（ASR）**：基于阿里云 DashScope Paraformer 实时语音识别
- **多模态对话**：Qwen-Omni-Turbo 支持图像+文本输入，语音输出
- **智能指令解析**：自动识别导航、查找、对话等不同类型指令
- **上下文感知**：在不同模式下智能过滤无关指令

### 📹 视频与音频处理
- **实时视频流**：WebSocket 推流，支持多客户端同时观看
- **音视频同步录制**：自动保存带时间戳的录像和音频文件
- **IMU 数据融合**：接收 ESP32 的 IMU 数据，支持姿态估计
- **多路音频混音**：支持系统语音、AI 回复、环境音同时播放

### 🎨 可视化与交互
- **Web 实时监控**：浏览器端实时查看处理后的视频流
- **IMU 3D 可视化**：Three.js 实时渲染设备姿态
- **状态面板**：显示导航状态、检测信息、FPS 等
- **中文友好**：所有界面和语音使用中文，支持自定义字体

## 💻 系统要求

### 硬件要求
- **开发/服务器端**：
  - CPU: Intel i5 或以上（推荐 i7/i9）
  - GPU: NVIDIA GPU（支持 CUDA 11.8+，推荐 RTX 3060 或以上）
  - 内存: 8GB RAM（推荐 16GB）
  - 存储: 10GB 可用空间

- **客户端设备**（可选）：
  - ESP32-CAM 或其他支持 WebSocket 的摄像头
  - 麦克风（用于语音输入）
  - 扬声器/耳机（用于语音输出）

### 软件要求
- **操作系统**: Windows 10/11, Linux (Ubuntu 20.04+), macOS 10.15+
- **Python**: 3.9 - 3.11
- **CUDA**: 11.8 或更高版本（GPU 加速必需）
- **浏览器**: Chrome 90+, Firefox 88+, Edge 90+（用于 Web 监控）

### API 密钥
- **阿里云 DashScope API Key**（必需）：
  - 用于语音识别（ASR）和 Qwen-Omni 对话
  - 申请地址：https://dashscope.console.aliyun.com/

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/aiglass.git
cd aiglass/rebuild1002
```

### 2. 安装依赖

#### 创建虚拟环境（推荐）
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

#### 安装 Python 包
```bash
pip install -r requirements.txt
```

#### 安装 CUDA 和 cuDNN（GPU 加速）
请参考 [NVIDIA CUDA Toolkit 安装指南](https://developer.nvidia.com/cuda-downloads)

### 3. 下载模型文件

将以下模型文件放入 `model/` 目录：

| 模型文件 | 用途 | 大小 | 下载链接 |
|---------|------|------|---------|
| `yolo-seg.pt` | 盲道分割 | ~50MB | [待补充] |
| `yoloe-11l-seg.pt` | 开放词汇检测 | ~80MB | [待补充] |
| `shoppingbest5.pt` | 物品识别 | ~30MB | [待补充] |
| `trafficlight.pt` | 红绿灯检测 | ~20MB | [待补充] |
| `hand_landmarker.task` | 手部检测 | ~15MB | [MediaPipe Models](https://developers.google.com/mediapipe/solutions/vision/hand_landmarker#models) |

### 4. 配置 API 密钥

创建 `.env` 文件：

```bash
# .env
DASHSCOPE_API_KEY=your_api_key_here
```

或在代码中直接修改（不推荐）：
```python
# app_main.py, line 50
API_KEY = "your_api_key_here"
```

### 5. 启动系统

```bash
python app_main.py
```

系统将在 `http://0.0.0.0:8081` 启动，打开浏览器访问即可看到实时监控界面。

### 6. 连接设备（可选）

如果使用 ESP32-CAM，请：
1. 烧录 `compile/compile.ino` 到 ESP32
2. 修改 WiFi 配置，连接到同一网络
3. ESP32 自动连接到 WebSocket 端点

## 🏗️ 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  ESP32-CAM   │  │   浏览器      │  │   移动端      │      │
│  │  (视频/音频)  │  │  (监控界面)   │  │  (语音控制)   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │ WebSocket        │ HTTP/WS          │ WebSocket
┌─────────┼──────────────────┼──────────────────┼─────────────┐
│         │                  │                  │              │
│    ┌────▼──────────────────▼──────────────────▼────────┐    │
│    │         FastAPI 主服务 (app_main.py)              │    │
│    │  - WebSocket 路由管理                              │    │
│    │  - 音视频流分发                                     │    │
│    │  - 状态管理与协调                                   │    │
│    └────┬────────────────┬────────────────┬─────────────┘    │
│         │                │                │                  │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐         │
│  │ ASR 模块     │  │ Omni 对话   │  │ 音频播放     │         │
│  │ (asr_core)   │  │(omni_client)│  │(audio_player)│         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                               │
│         应用层                                                │
└───────────────────────────────────────────────────────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────────┐
│                     导航统领层                                │
│    ┌─────────────────────────────────────────────────┐       │
│    │  NavigationMaster (navigation_master.py)         │       │
│    │  - 状态机：IDLE/CHAT/BLINDPATH_NAV/              │       │
│    │            CROSSING/TRAFFIC_LIGHT/ITEM_SEARCH    │       │
│    │  - 模式切换与协调                                │       │
│    └───┬─────────────────────┬───────────────────┬───┘       │
│        │                     │                   │            │
│   ┌────▼────────┐   ┌────────▼────────┐   ┌─────▼──────┐   │
│   │ 盲道导航     │   │  过马路导航      │   │ 物品查找    │   │
│   │(blindpath)   │   │ (crossstreet)   │   │(yolomedia)  │   │
│   └──────────────┘   └──────────────────┘   └─────────────┘   │
└───────────────────────────────────────────────────────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────────┐
│                       模型推理层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ YOLO 分割     │  │  YOLO-E 检测 │  │ MediaPipe    │       │
│  │ (盲道/斑马线) │  │ (开放词汇)   │  │  (手部检测)   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ 红绿灯检测    │  │ 光流稳定      │                         │
│  │(HSV+YOLO)     │  │(Lucas-Kanade)│                         │
│  └──────────────┘  └──────────────┘                         │
└───────────────────────────────────────────────────────────────┘
          │
┌─────────▼─────────────────────────────────────────────────────┐
│                    外部服务层                                  │
│  ┌──────────────────────────────────────────────┐            │
│  │  阿里云 DashScope API                         │            │
│  │  - Paraformer ASR (实时语音识别)              │            │
│  │  - Qwen-Omni-Turbo (多模态对话)               │            │
│  │  - Qwen-Turbo (标签提取)                      │            │
│  └──────────────────────────────────────────────┘            │
└───────────────────────────────────────────────────────────────┘
```

### 核心模块说明

| 模块 | 文件 | 功能 |
|------|------|------|
| **主应用** | `app_main.py` | FastAPI 服务、WebSocket 管理、状态协调 |
| **导航统领** | `navigation_master.py` | 状态机管理、模式切换、语音节流 |
| **盲道导航** | `workflow_blindpath.py` | 盲道检测、避障、转弯引导 |
| **过马路导航** | `workflow_crossstreet.py` | 斑马线检测、红绿灯识别、对齐引导 |
| **物品查找** | `yolomedia.py` | 物品检测、手部引导、抓取确认 |
| **语音识别** | `asr_core.py` | 实时 ASR、VAD、指令解析 |
| **语音合成** | `omni_client.py` | Qwen-Omni 流式语音生成 |
| **音频播放** | `audio_player.py` | 多路混音、TTS 播放、音量控制 |
| **视频录制** | `sync_recorder.py` | 音视频同步录制 |
| **桥接 IO** | `bridge_io.py` | 线程安全的帧缓冲与分发 |

## 📖 使用说明

### 语音指令

系统支持以下语音指令（说话时无需唤醒词）：

#### 导航控制
```
"开始导航" / "盲道导航"     → 启动盲道导航
"停止导航" / "结束导航"     → 停止盲道导航
"开始过马路" / "帮我过马路"  → 启动过马路模式
"过马路结束" / "结束过马路"  → 停止过马路模式
```

#### 红绿灯检测
```
"检测红绿灯" / "看红绿灯"   → 启动红绿灯检测
"停止检测" / "停止红绿灯"   → 停止检测
```

#### 物品查找
```
"帮我找一下 [物品名]"       → 启动物品搜索
  示例：
  - "帮我找一下红牛"
  - "找一下AD钙奶"
  - "帮我找矿泉水"
"找到了" / "拿到了"         → 确认找到物品
```

#### 智能对话
```
"帮我看看这是什么"          → 拍照识别
"这个东西能吃吗"            → 物品咨询
任何其他问题                 → AI 对话
```

### 导航状态说明

系统包含以下主要状态（自动切换）：

1. **IDLE** - 空闲状态
   - 等待用户指令
   - 显示原始视频流

2. **CHAT** - 对话模式
   - 与 AI 进行多模态对话
   - 暂停导航功能

3. **BLINDPATH_NAV** - 盲道导航
   - **ONBOARDING**: 上盲道引导
     - ROTATION: 旋转对准盲道
     - TRANSLATION: 平移至盲道中心
   - **NAVIGATING**: 沿盲道行走
     - 实时方向修正
     - 障碍物检测
   - **MANEUVERING_TURN**: 转弯处理
   - **AVOIDING_OBSTACLE**: 避障

4. **CROSSING** - 过马路模式
   - **SEEKING_CROSSWALK**: 寻找斑马线
   - **WAIT_TRAFFIC_LIGHT**: 等待绿灯
   - **CROSSING**: 过马路中
   - **SEEKING_NEXT_BLINDPATH**: 寻找对面盲道

5. **ITEM_SEARCH** - 物品查找
   - 实时检测目标物品
   - 引导手部靠近
   - 确认抓取

6. **TRAFFIC_LIGHT_DETECTION** - 红绿灯检测
   - 实时检测红绿灯状态
   - 语音播报颜色变化

### Web 监控界面

打开浏览器访问 `http://localhost:8081`，可以看到：

- **实时视频流**：显示处理后的视频，包括导航标注
- **状态面板**：当前模式、检测信息、FPS
- **IMU 可视化**：设备姿态 3D 实时渲染
- **语音识别结果**：显示识别的文字和 AI 回复

### WebSocket 端点

| 端点 | 用途 | 数据格式 |
|------|------|---------|
| `/ws/camera` | ESP32 相机推流 | Binary (JPEG) |
| `/ws/viewer` | 浏览器订阅视频 | Binary (JPEG) |
| `/ws_audio` | ESP32 音频上传 | Binary (PCM16) |
| `/ws_ui` | UI 状态推送 | JSON |
| `/ws` | IMU 数据接收 | JSON |
| `/stream.wav` | 音频下载流 | Binary (WAV) |

## ⚙️ 配置说明

### 环境变量

创建 `.env` 文件配置以下参数：

```bash
# 阿里云 API
DASHSCOPE_API_KEY=sk-xxxxx

# 模型路径（可选，使用默认路径可不配置）
BLIND_PATH_MODEL=model/yolo-seg.pt
OBSTACLE_MODEL=model/yoloe-11l-seg.pt
YOLOE_MODEL_PATH=model/yoloe-11l-seg.pt

# 导航参数
AIGLASS_MASK_MIN_AREA=1500      # 最小掩码面积
AIGLASS_MASK_MORPH=3            # 形态学核大小
AIGLASS_MASK_MISS_TTL=6         # 掩码丢失容忍帧数
AIGLASS_PANEL_SCALE=0.65        # 数据面板缩放

# 音频配置
TTS_INTERVAL_SEC=1.0            # 语音播报间隔
ENABLE_TTS=true                 # 启用语音播报
```

### 修改模型路径

如果模型文件不在默认位置，可以在相应文件中修改：

```python
# workflow_blindpath.py
seg_model_path = "your/custom/path/yolo-seg.pt"

# yolomedia.py
YOLO_MODEL_PATH = "your/custom/path/shoppingbest5.pt"
HAND_TASK_PATH = "your/custom/path/hand_landmarker.task"
```

### 调整性能参数

根据硬件性能调整：

```python
# yolomedia.py
HAND_DOWNSCALE = 0.8    # 手部检测降采样（越小越快，精度降低）
HAND_FPS_DIV = 1        # 手部检测抽帧（2=隔帧，3=每3帧）

# workflow_blindpath.py  
FEATURE_PARAMS = dict(
    maxCorners=600,      # 光流特征点数（越少越快）
    qualityLevel=0.001,  # 特征点质量
    minDistance=5        # 特征点最小间距
)
```

## 🛠️ 开发文档

### 添加新的语音指令

1. 在 `app_main.py` 的 `start_ai_with_text_custom()` 函数中添加：

```python
# 检查新指令
if "新指令关键词" in user_text:
    # 执行自定义逻辑
    print("[CUSTOM] 新指令被触发")
    await ui_broadcast_final("[系统] 新功能已启动")
    return
```

2. 如需修改指令过滤规则：

```python
# 修改 allowed_keywords 列表
allowed_keywords = ["帮我看", "帮我找", "你的新关键词"]
```

### 扩展导航功能

1. 在 `workflow_blindpath.py` 添加新状态：

```python
# 在 BlindPathNavigator.__init__() 中初始化
self.your_new_state_var = False

# 在 process_frame() 中处理
def process_frame(self, image):
    if self.your_new_state_var:
        # 自定义处理逻辑
        guidance_text = "新状态引导"
    # ...
```

2. 在 `navigation_master.py` 添加状态机状态：

```python
class NavigationMaster:
    def start_your_new_mode(self):
        self.state = "YOUR_NEW_MODE"
        # 初始化逻辑
```

### 集成新模型

1. 创建模型包装类：

```python
# your_model_wrapper.py
class YourModelWrapper:
    def __init__(self, model_path):
        self.model = load_your_model(model_path)
    
    def detect(self, image):
        # 推理逻辑
        return results
```

2. 在 `app_main.py` 中加载：

```python
your_model = YourModelWrapper("model/your_model.pt")
```

3. 在相应的工作流中调用：

```python
results = your_model.detect(image)
```

### 调试技巧

1. **启用详细日志**：

```python
# app_main.py 顶部
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **查看帧率瓶颈**：

```python
# yolomedia.py
PERF_DEBUG = True  # 打印处理时间
```

3. **测试单个模块**：

```bash
# 测试盲道导航
python test_cross_street_blindpath.py

# 测试红绿灯检测
python test_traffic_light.py

# 测试录制功能
python test_recorder.py
```





## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件


