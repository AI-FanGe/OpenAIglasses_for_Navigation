import asyncio
import base64
import os
import requests
from omni_client import stream_chat, OmniStreamPiece

# Use a dummy image with text
IMAGE_URL = "https://dummyimage.com/600x400/000/fff&text=HELLO+WORLD+OCR+TEST"
IMAGE_PATH = "sample_text.png"

# Ensure API Key is set
if not os.getenv("DASHSCOPE_API_KEY"):
    print("Error: DASHSCOPE_API_KEY environment variable is not set.")
    print("Please set it before running this script.")
    # We don't exit here because omni_client might have loaded it from .env

def download_image():
    if not os.path.exists(IMAGE_PATH):
        print(f"Downloading sample image from {IMAGE_URL}...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(IMAGE_URL, headers=headers, timeout=10)
            if response.status_code == 200:
                with open(IMAGE_PATH, 'wb') as f:
                    f.write(response.content)
                print(f"Download complete: {IMAGE_PATH}")
                return True
            else:
                print(f"Failed to download image: {response.status_code}")
                return False
        except Exception as e:
            print(f"Error downloading image: {e}")
            return False
    return True

async def main():
    if not download_image():
        print("Skipping OCR test because image download failed.")
        return

    try:
        with open(IMAGE_PATH, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error reading image file: {e}")
        return

    # Construct the multimodal message
    content_list = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{encoded_string}"}
        },
        {"type": "text", "text": "请读取这张图片里的所有文字，并直接输出原文，不要加任何修饰。"}
    ]

    print("Sending image to Qwen-Omni for OCR...")
    print("-" * 40)

    full_text = ""
    try:
        # Iterate over the async generator
        async for piece in stream_chat(content_list, voice="Cherry", audio_format="wav"):
            if piece.text_delta:
                print(piece.text_delta, end="", flush=True)
                full_text += piece.text_delta
    except Exception as e:
        print(f"\nError during API call: {e}")
        print("Make sure DASHSCOPE_API_KEY is valid.")

    print("\n" + "-" * 40)
    print("OCR Test Finished.")

if __name__ == "__main__":
    asyncio.run(main())
