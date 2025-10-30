# Changelog

This document records all significant changes made to the project.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),  
and the versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- First open-source release  
- Complete GitHub documentation (README, CONTRIBUTING, LICENSE, etc.)  
- Docker support  
- Environment variable configuration template  

### Changed
- Improved README structure  
- Enhanced code comments  

---

## [1.0.0] - 2025-01-XX

### Added
- 🚶 **Blind Path Navigation System**
  - Real-time tactile paving detection and segmentation  
  - Intelligent voice guidance  
  - Obstacle detection and avoidance  
  - Sharp turn detection and alerts  
  - Optical flow stabilization  

- 🚦 **Crosswalk Assistance**
  - Crosswalk recognition and direction detection  
  - Traffic light color recognition  
  - Alignment guidance system  
  - Safety reminders  

- 🔍 **Object Recognition and Search**
  - YOLO-E open-vocabulary detection  
  - MediaPipe hand tracking and guidance  
  - Real-time object tracking  
  - Grasp action detection  

- 🎙️ **Real-Time Voice Interaction**
  - Alibaba Paraformer ASR  
  - Qwen-Omni-Turbo multimodal dialogue  
  - Intelligent command parsing  
  - Context awareness  

- 📹 **Video and Audio Processing**
  - Real-time WebSocket streaming  
  - Audio-video synchronized recording  
  - IMU data fusion  
  - Multi-channel audio mixing  

- 🎨 **Visualization and Interaction**
  - Real-time web monitoring interface  
  - IMU 3D visualization  
  - Status dashboard  
  - Chinese-language interface  

### Tech Stack
- FastAPI + WebSocket  
- YOLO11 / YOLO-E  
- MediaPipe  
- PyTorch + CUDA  
- OpenCV  
- DashScope API  

### Known Issues
- [ ] Possible lag on low-end GPUs  
- [ ] No GPU acceleration support on macOS  
- [ ] Some Chinese fonts render incorrectly on Linux  

---

## Versioning Guidelines

### Major
- Incompatible API changes  

### Minor
- Backward-compatible new features  

### Patch
- Backward-compatible bug fixes  

---

[Unreleased]: https://github.com/yourusername/aiglass/compare/v1.0.0...HEAD  
[1.0.0]: https://github.com/yourusername/aiglass/releases/tag/v1.0.0
