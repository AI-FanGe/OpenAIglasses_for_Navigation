# omni_client.py
# -*- coding: utf-8 -*-
import os
from typing import AsyncGenerator, Dict, Any, List, Optional

from openai import AsyncOpenAI

# ===== OpenAI 兼容（达摩院 DashScope 兼容模式）=====
# 必须从环境变量获取 API Key，不再硬编码
API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not API_KEY:
    # 尝试从 .env 文件加载 (如果存在)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        API_KEY = os.getenv("DASHSCOPE_API_KEY")
    except ImportError:
        pass

if not API_KEY:
    raise RuntimeError("未设置 DASHSCOPE_API_KEY 环境变量")

QWEN_MODEL = "qwen-omni-turbo"

# 兼容模式 (使用异步客户端)
oai_client = AsyncOpenAI(
    api_key=API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

class OmniStreamPiece:
    """对外的统一增量数据：text/audio 二选一或同时。"""
    def __init__(self, text_delta: Optional[str] = None, audio_b64: Optional[str] = None):
        self.text_delta = text_delta
        self.audio_b64  = audio_b64

async def stream_chat(
    content_list: List[Dict[str, Any]],
    voice: str = "Cherry",
    audio_format: str = "wav",
) -> AsyncGenerator[OmniStreamPiece, None]:
    """
    发起一轮 Omni-Turbo ChatCompletions 流式对话：
    - content_list: OpenAI chat 的 content，多模态（image_url/text）
    - 以 stream=True 返回
    - 增量产出：OmniStreamPiece(text_delta=?, audio_b64=?)
    """
    # 使用 await 调用异步客户端
    completion = await oai_client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[{"role": "user", "content": content_list}],
        modalities=["text", "audio"],
        audio={"voice": voice, "format": audio_format},
        stream=True,
        stream_options={"include_usage": True},
    )

    # 异步迭代
    async for chunk in completion:
        text_delta: Optional[str] = None
        audio_b64: Optional[str] = None

        if getattr(chunk, "choices", None):
            c0 = chunk.choices[0]
            delta = getattr(c0, "delta", None)
            # 文本增量
            if delta and getattr(delta, "content", None):
                piece = delta.content
                if piece:
                    text_delta = piece
            # 音频分片
            if delta and getattr(delta, "audio", None):
                aud = delta.audio
                audio_b64 = aud.get("data") if isinstance(aud, dict) else getattr(aud, "data", None)
            if audio_b64 is None:
                msg = getattr(c0, "message", None)
                if msg and getattr(msg, "audio", None):
                    ma = msg.audio
                    audio_b64 = ma.get("data") if isinstance(ma, dict) else getattr(ma, "data", None)

        if (text_delta is not None) or (audio_b64 is not None):
            yield OmniStreamPiece(text_delta=text_delta, audio_b64=audio_b64)
