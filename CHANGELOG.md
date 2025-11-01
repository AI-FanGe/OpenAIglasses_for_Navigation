# 更新日志
[🇬🇧 English Version here](CHANGELOG_en.md)

本文档记录项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- 首次开源发布
- 完整的 GitHub 文档（README, CONTRIBUTING, LICENSE 等）
- Docker 支持
- 环境变量配置模板

### 修改
- 优化了 README 文档结构
- 改进了代码注释

## [1.0.0] - 2025-01-XX

### 新增
- 🚶 盲道导航系统
  - 实时盲道检测与分割
  - 智能语音引导
  - 障碍物检测与避障
  - 急转弯检测与提醒
  - 光流稳定算法

- 🚦 过马路辅助
  - 斑马线识别与方向检测
  - 红绿灯颜色识别
  - 对齐引导系统
  - 安全提醒

- 🔍 物品识别与查找
  - YOLO-E 开放词汇检测
  - MediaPipe 手部引导
  - 实时目标追踪
  - 抓取动作检测

- 🎙️ 实时语音交互
  - 阿里云 Paraformer ASR
  - Qwen-Omni-Turbo 多模态对话
  - 智能指令解析
  - 上下文感知

- 📹 视频与音频处理
  - WebSocket 实时推流
  - 音视频同步录制
  - IMU 数据融合
  - 多路音频混音

- 🎨 可视化与交互
  - Web 实时监控界面
  - IMU 3D 可视化
  - 状态面板
  - 中文友好界面

### 技术栈
- FastAPI + WebSocket
- YOLO11 / YOLO-E
- MediaPipe
- PyTorch + CUDA
- OpenCV
- DashScope API

### 已知问题
- [ ] 在低端 GPU 上可能出现卡顿
- [ ] macOS 上缺少 GPU 加速支持
- [ ] 部分中文字体在 Linux 上显示不正确

---

## 版本说明

### 主版本（Major）
- 不兼容的 API 更改

### 次版本（Minor）
- 向后兼容的新功能

### 修订版本（Patch）
- 向后兼容的问题修复

---

[未发布]: https://github.com/yourusername/aiglass/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/aiglass/releases/tag/v1.0.0

