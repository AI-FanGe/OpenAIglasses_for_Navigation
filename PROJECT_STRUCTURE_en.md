# Project Structure Guide

This document explains the project’s directory layout and the purpose of the main files.

## 📁 Directory Structure

```
rebuild1002/
├── 📄 Main Application Files
│   ├── app_main.py                    # App entry point (FastAPI service)
│   ├── navigation_master.py           # Navigation controller (state machine)
│   ├── workflow_blindpath.py          # Blind-path navigation workflow
│   ├── workflow_crossstreet.py        # Crosswalk navigation workflow
│   └── yolomedia.py                   # Item search workflow
│
├── 🎙️ Speech & Audio
│   ├── asr_core.py                    # Speech recognition core
│   ├── omni_client.py                 # Qwen-Omni client
│   ├── qwen_extractor.py              # Tag extraction (Chinese → English)
│   ├── audio_player.py                # Audio player
│   └── audio_stream.py                # Audio stream manager
│
├── 🤖 Models
│   ├── yoloe_backend.py               # YOLO-E backend (open vocabulary)
│   ├── trafficlight_detection.py      # Traffic light detection
│   ├── obstacle_detector_client.py    # Obstacle detector client
│   └── models.py                      # Model definitions
│
├── 🎥 Video Processing
│   ├── bridge_io.py                   # Thread-safe frame buffers
│   ├── sync_recorder.py               # A/V synchronized recording
│   └── video_recorder.py              # Legacy video recorder
│
├── 🌐 Web Frontend
│   ├── templates/
│   │   └── index.html                 # Main UI HTML
│   ├── static/
│   │   ├── main.js                    # Main JS
│   │   ├── vision.js                  # Vision stream handling
│   │   ├── visualizer.js              # Data visualization
│   │   ├── vision_renderer.js         # Rendering
│   │   ├── vision.css                 # Styles
│   │   └── models/                    # 3D models (IMU visualization)
│
├── 🎵 Audio Assets
│   ├── music/                         # System chimes
│   │   ├── converted_向上.wav
│   │   ├── converted_向下.wav
│   │   └── ...
│   └── voice/                         # Pre-recorded voice lines
│       ├── voice_mapping.json
│       └── *.wav
│
├── 🧠 Model Files
│   └── model/
│       ├── yolo-seg.pt                # Blind-path segmentation model
│       ├── yoloe-11l-seg.pt           # YOLO-E open-vocabulary model
│       ├── shoppingbest5.pt           # Item recognition model
│       ├── trafficlight.pt            # Traffic light model
│       └── hand_landmarker.task       # MediaPipe hand model
│
├── 📹 Recordings
│   └── recordings/                    # Auto-saved video & audio
│       ├── video_*.avi
│       └── audio_*.wav
│
├── 🛠️ ESP32 Firmware
│   └── compile/
│       ├── compile.ino                # Arduino main program
│       ├── camera_pins.h              # Camera pin definitions
│       ├── ICM42688.cpp/h             # IMU driver
│       └── ESP32_VIDEO_OPTIMIZATION.md
│
├── 🧪 Tests
│   ├── test_recorder.py               # Recording tests
│   ├── test_traffic_light.py          # Traffic light tests
│   ├── test_cross_street_blindpath.py # Navigation tests
│   └── test_crosswalk_awareness.py    # Crosswalk awareness tests
│
├── 📚 Docs
│   ├── README.md                      # Main project doc
│   ├── INSTALLATION.md                # Install guide
│   ├── CONTRIBUTING.md                # Contribution guide
│   ├── FAQ.md                         # Frequently Asked Questions
│   ├── CHANGELOG.md                   # Changelog
│   ├── SECURITY.md                    # Security policy
│   └── PROJECT_STRUCTURE.md           # This file
│
├── 🐳 Docker
│   ├── Dockerfile                     # Docker image
│   ├── docker-compose.yml             # Docker Compose config
│   └── .dockerignore                  # Docker ignore list
│
├── ⚙️ Config
│   ├── .env.example                   # Environment variable template
│   ├── .gitignore                     # Git ignore list
│   ├── requirements.txt               # Python deps
│   ├── setup.sh                       # Linux/macOS setup script
│   └── setup.bat                      # Windows setup script
│
├── 📄 License
│   └── LICENSE                        # MIT License
│
└── 🔧 GitHub
    └── .github/
        ├── ISSUE_TEMPLATE/
        │   ├── bug_report.md
        │   └── feature_request.md
        └── pull_request_template.md
```

## 🔑 Key Files Overview

### Main Application Layer

#### `app_main.py`
- **Purpose:** FastAPI main service handling all WebSocket connections
- **Key Features:**
  - WebSocket routing (`/ws/camera`, `/ws_audio`, `/ws/viewer`, etc.)
  - Model loading & initialization
  - State coordination & management
  - Audio/video stream distribution
- **Depends on:** All other modules
- **Entry point:** `python app_main.py`

#### `navigation_master.py`
- **Purpose:** Central navigation controller; manages the system state machine
- **Primary States:**
  - IDLE — idle
  - CHAT — dialogue mode
  - BLINDPATH_NAV — tactile path navigation
  - CROSSING — crosswalk
  - TRAFFIC_LIGHT_DETECTION — traffic-light detection
  - ITEM_SEARCH — item search
- **Core Methods:**
  - `process_frame()` — per-frame processing
  - `start_blind_path_navigation()` — start tactile path navigation
  - `start_crossing()` — start crosswalk mode
  - `on_voice_command()` — handle voice commands

### Workflow Modules

#### `workflow_blindpath.py`
- **Purpose:** Core logic for tactile path navigation
- **Features:**
  - Path segmentation & detection
  - Obstacle detection
  - Turn detection
  - Optical-flow stabilization
  - Directional guidance generation
- **State Machine:**
  - ONBOARDING — getting onto the path
  - NAVIGATING — navigating along the path
  - MANEUVERING_TURN — handling turns
  - AVOIDING_OBSTACLE — obstacle avoidance

#### `workflow_crossstreet.py`
- **Purpose:** Crosswalk navigation logic
- **Features:**
  - Crosswalk detection
  - Directional alignment
  - Guidance generation
- **Core Methods:**
  - `_is_crosswalk_near()` — determine crosswalk proximity
  - `_compute_angle_and_offset()` — compute angle and lateral offset

#### `yolomedia.py`
- **Purpose:** Item search workflow
- **Features:**
  - YOLO-E prompt-based detection
  - MediaPipe hand tracking
  - Optical-flow target tracking
  - Hand guidance (direction prompts)
  - Grasp-action detection
- **Modes:**
  - `SEGMENT`, `FLASH`, `CENTER_GUIDE`, `TRACK`

### Speech / Voice Modules

#### `asr_core.py`
- **Purpose:** AliCloud Paraformer ASR (real-time speech recognition)
- **Features:**
  - Real-time transcription
  - VAD (Voice Activity Detection)
  - Result callbacks
- **Key Class:** `ASRCallback`

#### `omni_client.py`
- **Purpose:** Qwen-Omni-Turbo multimodal dialogue client
- **Features:**
  - Streaming dialogue generation
  - Image + text inputs
  - Speech output
- **Core Function:** `stream_chat()`

#### `audio_player.py`
- **Purpose:** Unified audio playback manager
- **Features:**
  - TTS playback
  - Multi-channel audio mixing
  - Volume control
  - Thread-safe playback
- **Core Functions:** `play_voice_text()`, `play_audio_threadsafe()`

### Model Backends

#### `yoloe_backend.py`
- **Purpose:** YOLO-E open-vocabulary backend
- **Features:**
  - Prompt setup
  - Real-time segmentation
  - Target tracking
- **Key Class:** `YoloEBackend`

#### `trafficlight_detection.py`
- **Purpose:** Traffic-light detection module
- **Detection Methods:**
  1. YOLO model detection
  2. HSV color classification (fallback)
- **Output:** Red / Green / Yellow / Unknown

#### `obstacle_detector_client.py`
- **Purpose:** Obstacle detection client
- **Features:**
  - Whitelist category filtering
  - In-mask (path) checks
  - Object attributes (area, position, risk)

### Video Processing

#### `bridge_io.py`
- **Purpose:** Thread-safe frame buffering & distribution
- **Features:**
  - Producer–consumer pattern
  - Raw frame buffer
  - Processed frame fan-out
- **Core Functions:**
  - `push_raw_jpeg()` — receive ESP32 frames
  - `wait_raw_bgr()` — get raw frame
  - `send_vis_bgr()` — send processed frame

#### `sync_recorder.py`
- **Purpose:** Synchronized audio/video recording
- **Features:**
  - Sync record video & audio
  - Auto timestamped filenames
  - Thread safety
- **Outputs:** `recordings/video_*.avi`, `audio_*.wav`

### Frontend

#### `templates/index.html`
- **Purpose:** Web monitoring interface
- **Main Areas:**
  - Video stream display
  - Status panel
  - IMU 3D visualization
  - Speech recognition results

#### `static/main.js`
- **Purpose:** Main JavaScript logic
- **Features:**
  - WebSocket connection management
  - UI updates
  - Event handling

#### `static/vision.js`
- **Purpose:** Vision stream handling
- **Features:**
  - Receive video frames via WebSocket
  - Canvas rendering
  - FPS calculation

#### `static/visualizer.js`
- **Purpose:** IMU 3D visualization (Three.js)
- **Features:**
  - Receive IMU data
  - Real-time pose rendering
  - Dynamic lighting effects

## 🔄 Data Flow

### Video Stream
```
ESP32-CAM
→ [JPEG] WebSocket /ws/camera
→ bridge_io.push_raw_jpeg()
→ yolomedia / navigation_master
→ bridge_io.send_vis_bgr()
→ [JPEG] WebSocket /ws/viewer
→ Browser Canvas
```
### Audio Stream (Upstream)
```
ESP32-MIC
→ [PCM16] WebSocket /ws_audio
→ asr_core
→ DashScope ASR
→ Recognition Result
→ start_ai_with_text_custom()
```

### Audio Stream (Downstream)

```
Qwen-Omni / TTS
→ audio_player
→ [PCM16] audio_stream
→ [WAV] HTTP /stream.wav
→ ESP32 Speaker
```


### IMU Data Stream
```
ESP32-IMU
→ [JSON] UDP 12345
→ process_imu_and_maybe_store()
→ [JSON] WebSocket /ws
→ visualizer.js (Three.js)
```

## 🎯 Key Design Patterns

### 1. State Machine Pattern
- **Location:** `navigation_master.py`
- **Purpose:** Manage system state transitions  
- **States:** IDLE → CHAT / BLINDPATH_NAV / CROSSING / ...

### 2. Producer–Consumer Pattern
- **Location:** `bridge_io.py`
- **Purpose:** Decouple video reception and processing  
- **Implementation:** Threads + Queues

### 3. Strategy Pattern
- **Location:** Each `workflow_*.py`
- **Purpose:** Implement different navigation strategies  
- **Implementation:** Unified `process_frame()` interface

### 4. Singleton Pattern
- **Location:** Model loading
- **Purpose:** Share model instances globally  
- **Implementation:** Global variables + initialization checks

### 5. Observer Pattern
- **Location:** WebSocket communication
- **Purpose:** Allow multiple clients to subscribe to video streams  
- **Implementation:** `camera_viewers: Set[WebSocket]`

## 📦 Dependencies
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

## 🚀 Startup Process

1. **Initialization Phase** (`app_main.py`)
   - Load environment variables  
   - Load navigation models (YOLO, MediaPipe)  
   - Initialize the audio system  
   - Start the recording system  
   - Preload the traffic light detection model  

2. **Service Launch** (FastAPI)
   - Register WebSocket routes  
   - Mount static files  
   - Start UDP listener (for IMU data)  
   - Start HTTP service (port 8081)  

3. **Runtime Phase**
   - Wait for ESP32 connection  
   - Receive video/audio/IMU data  
   - Process user voice commands  
   - Push real-time processing results  

4. **Shutdown Phase**
   - Stop recording (save files)  
   - Close all WebSocket connections  
   - Release model resources  
   - Clean up temporary files  

---

**Note:** For detailed implementation of each module, please refer to the corresponding source file comments and docstrings.
