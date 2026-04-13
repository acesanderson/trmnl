# src/trmnl/app.py
from __future__ import annotations
from trmnl.config import settings, build_engine_from_config
from trmnl.logo import print_logo
from trmnl.carousel import Carousel, TRMNLImage
from trmnl.engines.router import EngineRouter
from trmnl.control import router as control_router
from fastapi import FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine, name, sequence = build_engine_from_config()
    logger.info(f"Loaded engine config: engine={name} sequence={sequence}")

    router = EngineRouter(engine, name, sequence)
    carousel = Carousel(engine=router)

    try:
        await carousel.next()  # pre-load first image
    except Exception as e:
        logger.error(f"Error pre-loading carousel: {e}")

    app.state.router = router
    app.state.carousel = carousel

    print_logo()
    yield


app = FastAPI(lifespan=lifespan)

# Mount admin control router
app.include_router(control_router)


@app.get("/ping")
async def ping():
    return {"status": "ok"}


@app.get("/api/setup")
async def setup(request: Request, id: str = Header(None, alias="ID")):
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
    logger.info(f"Display request from device: {id}, token: {access_token}")
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
    logger.info("Serving image to device.")
    current_image = await app.state.carousel.current()
    assert filename == current_image.filename + ".bmp", "Filename mismatch!"
    return FileResponse(current_image.path, media_type="image/bmp")


@app.post("/api/log")
async def log_device_stats(request: Request):
    logger.info("Received device log.")
    payload = await request.json()
    logger.info(f"DEVICE LOG: {payload}")
    return {"status": "ok"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(request: Request, path: str):
    logger.info(f"CATCH-ALL: {request.method} /{path}")
    return {"caught": path}
