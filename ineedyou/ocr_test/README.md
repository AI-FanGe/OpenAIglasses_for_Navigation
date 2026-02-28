# OCR Test with ESP32 Hardware

This folder contains a simplified server-side script (`ocr_server.py`) to test OCR functionality using the ESP32-CAM hardware.

## Prerequisites

1.  **Python Environment**: Ensure you have Python 3.9+ installed.
2.  **Dependencies**: Install the required packages using `pip`:
    ```bash
    pip install -r requirements.txt
    ```
    (Note: `requirements.txt` should contain `fastapi`, `uvicorn`, `openai`, `requests`, `python-dotenv`)

3.  **API Key**: You **must** set the `DASHSCOPE_API_KEY` environment variable.
    -   Create a `.env` file in this directory or set it in your shell:
        ```bash
        export DASHSCOPE_API_KEY="sk-your-api-key"
        ```

4.  **ESP32 Firmware**: The ESP32 should be flashed with the firmware located in the root `compile/` directory of this repository. Specifically, `compile/compile.ino`.
    -   Open `compile/compile.ino` in Arduino IDE.
    -   Ensure `SERVER_HOST` is set to your computer's IP address (where you will run `ocr_server.py`).
    -   Ensure `SERVER_PORT` matches the port used by `ocr_server.py` (default: `8081`).
    -   Flash the firmware to your ESP32-CAM.

## How to Run

1.  **Start the OCR Server**:
    Run the `ocr_server.py` script. This will start a WebSocket server listening for video frames from the ESP32.
    ```bash
    python ocr_server.py
    ```
    By default, it listens on `0.0.0.0:8081`.

2.  **Power on the ESP32**:
    Connect the ESP32 to power. It should automatically connect to the server's WebSocket endpoint (`/ws/camera`).

3.  **Observe OCR Results**:
    -   The server will receive video frames from the ESP32.
    -   Every 5 seconds (configurable via `OCR_INTERVAL` in `ocr_server.py`), it will capture the latest frame.
    -   It sends this frame to the Qwen-Omni API for OCR processing.
    -   The recognized text will be printed directly to the console running `ocr_server.py`.

## Files in this Folder

-   `ocr_server.py`: The main server script. Handles WebSocket connection and triggers OCR.
-   `omni_client.py`: Client library for interacting with the Qwen-Omni multimodal model (async version).
-   `test_ocr.py`: A standalone script to test OCR with a static/downloaded image (no hardware required).
-   `requirements.txt`: Python dependencies.

## Troubleshooting

-   **Connection Failed**: Check if the ESP32 and your computer are on the same Wi-Fi network. Check if `SERVER_HOST` in `compile.ino` is correct.
-   **API Key Error**: Ensure `DASHSCOPE_API_KEY` is set correctly. The script will skip OCR if the key is missing.
-   **No Video**: Check the ESP32 camera connection and serial output for errors.
