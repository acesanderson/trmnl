from trmnl.generate import generate
from fastapi import FastAPI, Header, Response, Request
from fastapi import BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import uvicorn
import logging

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()


def discover_bmp(path: Path) -> Path:
    """
    Find a BMP in DIR_PATH.
    """
    for file in path.iterdir():
        if file.suffix.lower() == ".bmp":
            return file
    raise FileNotFoundError("No BMP file found in the specified directory.")


@app.get("/api/setup")
async def setup(request: Request, id: str = Header(None, alias="ID")):
    """Device registration - called once after WiFi setup."""
    base_url = str(request.base_url).rstrip("/")
    logger.info(f"Setup request from device: {id}")
    return JSONResponse(
        content={
            "status": 200,
            "api_key": "local-server-key",
            "friendly_id": "LOCAL",
            "image_url": f"{base_url}/api/image/setup.bmp",
            "filename": "setup",
        }
    )


@app.get("/api/display")
async def display_config(
    request: Request,
    id: str = Header(None, alias="ID"),
    access_token: str = Header(None, alias="Access-Token"),
):
    """Device asks for display content."""
    logger.info("Creating image URL for device display.")
    bmp_file = discover_bmp(BASE_DIR)
    base_url = str(request.base_url).rstrip("/")
    image_url = f"{base_url}/api/image/{bmp_file.name}"
    logger.info(f"Display request from device: {id}, token: {access_token}")

    return JSONResponse(
        content={
            "status": 0,
            "image_url": image_url,
            "filename": bmp_file.stem,
            "update_firmware": False,
            "firmware_url": None,
            "refresh_rate": "30",
            "reset_firmware": False,
        }
    )


@app.get("/api/image/{filename}")
async def serve_image(filename: str, background_tasks: BackgroundTasks):
    """Serve the BMP image."""
    logger.info("Serving image to device.")
    background_tasks.add_task(generate)
    bmp_file = discover_bmp(BASE_DIR)
    return FileResponse(bmp_file, media_type="image/bmp")


@app.post("/api/log")
async def log_device_stats(request: Request):
    logger.info("Received device log.")
    payload = await request.json()
    logger.info(f"DEVICE LOG: {payload}")
    return {"status": "ok"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(request: Request, path: str):
    logger.info(f"CATCH-ALL: {request.method} /{path}")
    logger.info(f"Headers: {dict(request.headers)}")
    return {"caught": path}


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
    # run main, but on exit, run generate to refresh the image
    try:
        main()
    finally:
        generate()
