import asyncio
import base64
import os
import time
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import omni_client

# ===== 配置 =====
HOST = "0.0.0.0"
PORT = 8081
OCR_INTERVAL = 5.0  # 每隔5秒进行一次OCR识别

# 从环境变量获取 API Key，必须设置
API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not API_KEY:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        API_KEY = os.getenv("DASHSCOPE_API_KEY")
    except ImportError:
        pass

if not API_KEY:
    print("Warning: DASHSCOPE_API_KEY not set. OCR will fail.")

# ===== FastAPI =====
app = FastAPI()

# ===== 全局变量 =====
last_ocr_time = 0
current_frame = None

@app.get("/")
async def root():
    return HTMLResponse("<h1>OCR Test Server is Running</h1><p>Connect your ESP32 to ws://SERVER_IP:8081/ws/camera</p>")

@app.websocket("/ws/camera")
async def websocket_endpoint(websocket: WebSocket):
    global last_ocr_time, current_frame
    await websocket.accept()
    print(f"[SERVER] ESP32 Connected from {websocket.client}")

    try:
        while True:
            # 接收二进制数据 (JPEG)
            data = await websocket.receive_bytes()
            current_frame = data

            # 检查是否到了OCR识别的时间
            now = time.time()
            if now - last_ocr_time > OCR_INTERVAL:
                last_ocr_time = now

                # 启动异步OCR任务，不阻塞视频流接收
                asyncio.create_task(process_ocr(data))

    except WebSocketDisconnect:
        print("[SERVER] ESP32 Disconnected")
    except Exception as e:
        print(f"[SERVER] Error: {e}")

async def process_ocr(image_bytes):
    if not API_KEY:
        print("[OCR] Skipping: API Key not set.")
        return

    print(f"\n[OCR] Capture frame ({len(image_bytes)} bytes), sending to Qwen-Omni...")

    try:
        # 编码为Base64
        encoded_string = base64.b64encode(image_bytes).decode('utf-8')

        # 构建请求
        content_list = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}
            },
            {"type": "text", "text": "请读取这张图片里的所有文字，并直接输出原文，不要加任何修饰。"}
        ]

        print("[OCR] Waiting for response...")
        full_text = ""
        # 使用 async for 迭代异步生成器
        async for piece in omni_client.stream_chat(content_list, voice="Cherry", audio_format="wav"):
            if piece.text_delta:
                print(piece.text_delta, end="", flush=True)
                full_text += piece.text_delta

        print("\n[OCR] Done.")

    except Exception as e:
        print(f"[OCR] Error processing image: {e}")

if __name__ == "__main__":
    if not API_KEY:
        print("Error: DASHSCOPE_API_KEY not set. Please set it in environment variables or .env file.")
        # exit(1) # 不强制退出，允许仅作为视频流服务器运行

    print(f"Starting OCR Test Server on {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
