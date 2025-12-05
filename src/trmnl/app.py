from trmnl.config import settings
from trmnl.logo import print_logo
from trmnl.carousel import Carousel, TRMNLImage
from fastapi import FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    The lifespan context manager is used to set up and tear down resources for the FastAPI application.
    Kick off events like printing the logo, of course, but also initalize any global resources and
    store them in app.state for access in route handlers.
    app.state is like a dict accessed through dot notation.
    Any teardown code would go after the yield.
    """
    engine = settings.default_engine()
    carousel = Carousel(engine=engine)
    try:
        await carousel.next()  # pre-load the first image
    except Exception as e:
        logger.error(f"Error initializing carousel: {e}")
    app.state.carousel = carousel

    print_logo()
    yield


app = FastAPI(lifespan=lifespan)


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
    """
    Device asks for display content.
    Provide the next image URL (carousel.next) and display settings.
    """
    logger.info(f"Display request from device: {id}, token: {access_token}")
    logger.info(f"Headers: {dict(request.headers)}")
    next_image: TRMNLImage = await request.app.state.carousel.next()

    return JSONResponse(
        content={
            "status": 0,
            "image_url": next_image.image_url,
            "filename": next_image.filename,
            "update_firmware": False,
            "firmware_url": None,
            "refresh_rate": settings.refresh_interval,
            "reset_firmware": False,
        }
    )


@app.get("/api/image/{filename}")
async def serve_image(filename: str):
    """
    Serve the BMP image. (carousel.current)
    """
    logger.info("Serving image to device.")
    current_image = await app.state.carousel.current()
    assert filename == current_image.filename + ".bmp", "Filename mismatch!"
    current_file_path = current_image.path
    return FileResponse(current_file_path, media_type="image/bmp")


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
