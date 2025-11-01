# 项目结构说明
[🇬🇧 English Version here](PROJECT_STRUCTURE_en.md)

本文档详细说明项目的目录结构和主要文件的作用。

## 📁 目录结构

```
rebuild1002/
├── 📄 主要应用文件
│   ├── app_main.py                    # 主应用入口（FastAPI 服务）
│   ├── navigation_master.py           # 导航统领器（状态机）
│   ├── workflow_blindpath.py          # 盲道导航工作流
│   ├── workflow_crossstreet.py        # 过马路导航工作流
│   └── yolomedia.py                   # 物品查找工作流
│
├── 🎙️ 语音处理模块
│   ├── asr_core.py                    # 语音识别核心
│   ├── omni_client.py                 # Qwen-Omni 客户端
│   ├── qwen_extractor.py              # 标签提取（中文->英文）
│   ├── audio_player.py                # 音频播放器
│   └── audio_stream.py                # 音频流管理
│
├── 🤖 模型相关
│   ├── yoloe_backend.py               # YOLO-E 后端（开放词汇）
│   ├── trafficlight_detection.py      # 红绿灯检测
│   ├── obstacle_detector_client.py    # 障碍物检测客户端
│   └── models.py                      # 模型定义
│
├── 🎥 视频处理
│   ├── bridge_io.py                   # 线程安全的帧缓冲
│   ├── sync_recorder.py               # 音视频同步录制
│   └── video_recorder.py              # 视频录制（旧版）
│
├── 🌐 Web 前端
│   ├── templates/
│   │   └── index.html                 # 主界面 HTML
│   ├── static/
│   │   ├── main.js                    # 主 JS 脚本
│   │   ├── vision.js                  # 视觉流处理
│   │   ├── visualizer.js              # 数据可视化
│   │   ├── vision_renderer.js         # 渲染器
│   │   ├── vision.css                 # 样式表
│   │   └── models/                    # 3D 模型（IMU 可视化）
│
├── 🎵 音频资源
│   ├── music/                         # 系统提示音
│   │   ├── converted_向上.wav
│   │   ├── converted_向下.wav
│   │   └── ...
│   └── voice/                         # 预录语音
│       ├── voice_mapping.json
│       └── *.wav
│
├── 🧠 模型文件
│   └── model/
│       ├── yolo-seg.pt                # 盲道分割模型
│       ├── yoloe-11l-seg.pt           # YOLO-E 开放词汇模型
│       ├── shoppingbest5.pt           # 物品识别模型
│       ├── trafficlight.pt            # 红绿灯检测模型
│       └── hand_landmarker.task       # MediaPipe 手部模型
│
├── 📹 录制文件
│   └── recordings/                    # 自动保存的视频和音频
│       ├── video_*.avi
│       └── audio_*.wav
│
├── 🛠️ ESP32 固件
│   └── compile/
│       ├── compile.ino                # Arduino 主程序
│       ├── camera_pins.h              # 摄像头引脚定义
│       ├── ICM42688.cpp/h             # IMU 驱动
│       └── ESP32_VIDEO_OPTIMIZATION.md
│
├── 🧪 测试文件
│   ├── test_recorder.py               # 录制功能测试
│   ├── test_traffic_light.py          # 红绿灯检测测试
│   ├── test_cross_street_blindpath.py # 导航测试
│   └── test_crosswalk_awareness.py    # 斑马线检测测试
│
├── 📚 文档
│   ├── README.md                      # 项目主文档
│   ├── INSTALLATION.md                # 安装指南
│   ├── CONTRIBUTING.md                # 贡献指南
│   ├── FAQ.md                         # 常见问题
│   ├── CHANGELOG.md                   # 更新日志
│   ├── SECURITY.md                    # 安全政策
│   └── PROJECT_STRUCTURE.md           # 本文件
│
├── 🐳 Docker 相关
│   ├── Dockerfile                     # Docker 镜像定义
│   ├── docker-compose.yml             # Docker Compose 配置
│   └── .dockerignore                  # Docker 忽略文件
│
├── ⚙️ 配置文件
│   ├── .env.example                   # 环境变量模板
│   ├── .gitignore                     # Git 忽略文件
│   ├── requirements.txt               # Python 依赖
│   ├── setup.sh                       # Linux/macOS 安装脚本
│   └── setup.bat                      # Windows 安装脚本
│
├── 📄 许可证
│   └── LICENSE                        # MIT 许可证
│
└── 🔧 GitHub 相关
    └── .github/
        ├── ISSUE_TEMPLATE/
        │   ├── bug_report.md
        │   └── feature_request.md
        └── pull_request_template.md
```

## 🔑 核心文件说明

### 主应用层

#### `app_main.py`
- **作用**: FastAPI 主服务，处理所有 WebSocket 连接
- **主要功能**:
  - WebSocket 路由管理（/ws/camera, /ws_audio, /ws/viewer 等）
  - 模型加载与初始化
  - 状态协调与管理
  - 音视频流分发
- **依赖**: 所有其他模块
- **入口点**: `python app_main.py`

#### `navigation_master.py`
- **作用**: 导航统领器，管理整个系统的状态机
- **主要状态**:
  - IDLE: 空闲
  - CHAT: 对话模式
  - BLINDPATH_NAV: 盲道导航
  - CROSSING: 过马路
  - TRAFFIC_LIGHT_DETECTION: 红绿灯检测
  - ITEM_SEARCH: 物品查找
- **核心方法**:
  - `process_frame()`: 处理每一帧
  - `start_blind_path_navigation()`: 启动盲道导航
  - `start_crossing()`: 启动过马路模式
  - `on_voice_command()`: 处理语音命令

### 工作流模块

#### `workflow_blindpath.py`
- **作用**: 盲道导航核心逻辑
- **主要功能**:
  - 盲道分割与检测
  - 障碍物检测
  - 转弯检测
  - 光流稳定
  - 方向引导生成
- **状态机**:
  - ONBOARDING: 上盲道
  - NAVIGATING: 导航中
  - MANEUVERING_TURN: 转弯
  - AVOIDING_OBSTACLE: 避障

#### `workflow_crossstreet.py`
- **作用**: 过马路导航逻辑
- **主要功能**:
  - 斑马线检测
  - 方向对齐
  - 引导生成
- **核心方法**:
  - `_is_crosswalk_near()`: 判断是否接近斑马线
  - `_compute_angle_and_offset()`: 计算角度和偏移

#### `yolomedia.py`
- **作用**: 物品查找工作流
- **主要功能**:
  - YOLO-E 文本提示检测
  - MediaPipe 手部追踪
  - 光流目标追踪
  - 手部引导（方向提示）
  - 抓取动作检测
- **模式**:
  - SEGMENT: 检测模式
  - FLASH: 闪烁确认
  - CENTER_GUIDE: 居中引导
  - TRACK: 手部追踪

### 语音模块

#### `asr_core.py`
- **作用**: 阿里云 Paraformer ASR 实时语音识别
- **主要功能**:
  - 实时语音识别
  - VAD（语音活动检测）
  - 识别结果回调
- **关键类**: `ASRCallback`

#### `omni_client.py`
- **作用**: Qwen-Omni-Turbo 多模态对话客户端
- **主要功能**:
  - 流式对话生成
  - 图像+文本输入
  - 语音输出
- **核心函数**: `stream_chat()`

#### `audio_player.py`
- **作用**: 统一的音频播放管理
- **主要功能**:
  - TTS 语音播放
  - 多路音频混音
  - 音量控制
  - 线程安全播放
- **核心函数**: `play_voice_text()`, `play_audio_threadsafe()`

### 模型后端

#### `yoloe_backend.py`
- **作用**: YOLO-E 开放词汇检测后端
- **主要功能**:
  - 文本提示设置
  - 实时分割
  - 目标追踪
- **核心类**: `YoloEBackend`

#### `trafficlight_detection.py`
- **作用**: 红绿灯检测模块
- **检测方法**:
  1. YOLO 模型检测
  2. HSV 颜色分类（备用）
- **输出**: 红灯/绿灯/黄灯/未知

#### `obstacle_detector_client.py`
- **作用**: 障碍物检测客户端
- **主要功能**:
  - 白名单类别过滤
  - 路径掩码内检测
  - 物体属性计算（面积、位置、危险度）

### 视频处理

#### `bridge_io.py`
- **作用**: 线程安全的帧缓冲与分发
- **主要功能**:
  - 生产者-消费者模式
  - 原始帧缓存
  - 处理后帧分发
- **核心函数**:
  - `push_raw_jpeg()`: 接收 ESP32 帧
  - `wait_raw_bgr()`: 取原始帧
  - `send_vis_bgr()`: 发送处理后的帧

#### `sync_recorder.py`
- **作用**: 音视频同步录制
- **主要功能**:
  - 同步录制视频和音频
  - 自动文件命名（时间戳）
  - 线程安全
- **输出**: `recordings/video_*.avi`, `audio_*.wav`

### 前端

#### `templates/index.html`
- **作用**: Web 监控界面
- **主要区域**:
  - 视频流显示
  - 状态面板
  - IMU 3D 可视化
  - 语音识别结果

#### `static/main.js`
- **作用**: 主 JavaScript 逻辑
- **主要功能**:
  - WebSocket 连接管理
  - UI 更新
  - 事件处理

#### `static/vision.js`
- **作用**: 视觉流处理
- **主要功能**:
  - WebSocket 接收视频帧
  - Canvas 渲染
  - FPS 计算

#### `static/visualizer.js`
- **作用**: IMU 3D 可视化（Three.js）
- **主要功能**:
  - 接收 IMU 数据
  - 实时渲染设备姿态
  - 动态灯光效果

## 🔄 数据流

### 视频流
```
ESP32-CAM 
  → [JPEG] WebSocket /ws/camera 
  → bridge_io.push_raw_jpeg() 
  → yolomedia / navigation_master 
  → bridge_io.send_vis_bgr() 
  → [JPEG] WebSocket /ws/viewer 
  → Browser Canvas
```

### 音频流（上行）
```
ESP32-MIC 
  → [PCM16] WebSocket /ws_audio 
  → asr_core 
  → DashScope ASR 
  → 识别结果 
  → start_ai_with_text_custom()
```

### 音频流（下行）
```
Qwen-Omni / TTS 
  → audio_player 
  → [PCM16] audio_stream 
  → [WAV] HTTP /stream.wav 
  → ESP32-Speaker
```

### IMU 数据流
```
ESP32-IMU 
  → [JSON] UDP 12345 
  → process_imu_and_maybe_store() 
  → [JSON] WebSocket /ws 
  → visualizer.js (Three.js)
```

## 🎯 关键设计模式

### 1. 状态机模式
- **位置**: `navigation_master.py`
- **作用**: 管理系统状态转换
- **状态**: IDLE → CHAT / BLINDPATH_NAV / CROSSING / ...

### 2. 生产者-消费者模式
- **位置**: `bridge_io.py`
- **作用**: 解耦视频接收与处理
- **实现**: 线程 + 队列

### 3. 策略模式
- **位置**: 各 `workflow_*.py`
- **作用**: 不同导航策略的实现
- **实现**: 统一的 `process_frame()` 接口

### 4. 单例模式
- **位置**: 模型加载
- **作用**: 全局共享模型实例
- **实现**: 全局变量 + 初始化检查

### 5. 观察者模式
- **位置**: WebSocket 通信
- **作用**: 多客户端订阅视频流
- **实现**: `camera_viewers: Set[WebSocket]`

## 📦 依赖关系

```
app_main.py
├── navigation_master.py
│   ├── workflow_blindpath.py
│   │   ├── yoloe_backend.py
│   │   └── obstacle_detector_client.py
│   ├── workflow_crossstreet.py
│   └── trafficlight_detection.py
├── yolomedia.py
│   └── yoloe_backend.py
├── asr_core.py
├── omni_client.py
├── audio_player.py
├── audio_stream.py
├── bridge_io.py
└── sync_recorder.py
```

## 🚀 启动流程

1. **初始化阶段** (`app_main.py`)
   - 加载环境变量
   - 加载导航模型（YOLO、MediaPipe）
   - 初始化音频系统
   - 启动录制系统
   - 预加载红绿灯模型

2. **服务启动** (FastAPI)
   - 注册 WebSocket 路由
   - 挂载静态文件
   - 启动 UDP 监听（IMU）
   - 启动 HTTP 服务（8081 端口）

3. **运行阶段**
   - 等待 ESP32 连接
   - 接收视频/音频/IMU 数据
   - 处理用户语音指令
   - 实时推送处理结果

4. **关闭阶段**
   - 停止录制（保存文件）
   - 关闭所有 WebSocket 连接
   - 释放模型资源
   - 清理临时文件

---

**提示**: 如需了解某个模块的详细实现，请查看相应源文件的注释和 docstring。

