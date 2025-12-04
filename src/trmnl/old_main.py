from fastapi import FastAPI, Header, Response
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from pathlib import Path
import uvicorn
import logging

logger = logging.getLogger(__name__)

# Define absolute path once
BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "current.bmp"

app = FastAPI()


@app.get("/api/display")
async def display_config(request: Request):
    """
    Step 1: Device asks for configuration.
    We return JSON pointing to the image URL.
    """
    # Dynamically build the URL based on the incoming request IP/Port
    # This avoids hardcoding "http://10.0.0.82:8070"
    base_url = str(request.base_url).rstrip("/")
    image_url = f"{base_url}/api/image.bmp"

    logger.info(f"Handing off device to image: {image_url}")

    return JSONResponse(
        content={
            "image_url": image_url,
            "refresh_rate": 900,  # 15 minutes (in seconds)
            "reset_firmware": False,
        }
    )


@app.get("/api/image.bmp")
async def serve_image():
    """
    Step 2: Device downloads the actual binary asset.
    """
    if not IMAGE_PATH.exists():
        return Response(status_code=404)

    # FileResponse handles 304 Not Modified automatically
    return FileResponse(IMAGE_PATH, media_type="application/octet-stream")


@app.post("/api/log")
async def log_device_stats(request: Request):
    # TRMNL sends battery voltage, RSSI (signal), and error messages here
    payload = await request.json()
    print(f"DEVICE LOG: {payload}")
    return {"status": "ok"}


def main():
    uvicorn.run(
        "trmnl.main:app",
        host="0.0.0.0",
        port=8070,
        reload=True,
        reload_dirs=[str(BASE_DIR)],
        log_level="info",
    )


if __name__ == "__main__":
    main()
