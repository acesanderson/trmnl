# src/trmnl/control.py
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, Request, HTTPException
import yaml
import logging

from trmnl.config import CONFIG_FILE
from trmnl.engines.registry import get_engine_registry
from trmnl.engines.router import EngineRouter, MixEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/control")


class EngineRequest(BaseModel):
    engine: str
    sequence: list[str] | None = None
    artist: str | None = None
    artists: list[str] | None = None


@router.get("/status")
async def status(request: Request):
    eng_router: EngineRouter = request.app.state.router
    last = eng_router.last_served.name if eng_router.last_served else None
    logger.info("Control: GET /status")
    return {
        "engine": eng_router.active_name,
        "sequence": eng_router.active_sequence,
        "last_served": last,
    }


@router.get("/engines")
async def list_engines():
    logger.info("Control: GET /engines")
    return {"engines": list(get_engine_registry().keys())}


@router.post("/engine")
async def set_engine(request: Request, body: EngineRequest):
    registry = get_engine_registry()

    if body.engine != "mix" and body.engine not in registry:
        valid = ", ".join(registry.keys())
        raise HTTPException(400, detail=f"Unknown engine '{body.engine}'. Valid engines: {valid}")

    sequence = body.sequence or list(registry.keys())
    extra = {}
    if body.artist:
        extra["artist"] = body.artist
    if body.artists:
        extra["artists"] = body.artists
    engine_obj, name, resolved_seq = _build(body.engine, sequence, registry, extra=extra)

    eng_router: EngineRouter = request.app.state.router
    eng_router.set_engine(engine_obj, name, resolved_seq)

    _write_config(name, resolved_seq, extra=extra)
    logger.info(f"Control: POST /engine -> {name} {resolved_seq} {extra}")
    return {"ok": True, "engine": name, "sequence": resolved_seq, **extra}


@router.post("/next")
async def advance_next(request: Request):
    carousel = request.app.state.carousel
    image = await carousel.next()
    logger.info(f"Control: POST /next -> {image.filename}")
    return {"ok": True, "image": image.filename + ".bmp"}


@router.post("/reload")
async def reload_config(request: Request):
    from trmnl.config import build_engine_from_config
    try:
        engine_obj, name, sequence = build_engine_from_config()
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to reload config: {e}")

    eng_router: EngineRouter = request.app.state.router
    eng_router.set_engine(engine_obj, name, sequence)
    logger.info(f"Control: POST /reload -> {name} {sequence}")
    return {"ok": True, "engine": name, "sequence": sequence}


def _build(name: str, sequence: list[str], registry: dict, extra: dict | None = None) -> tuple:
    extra = extra or {}
    if name == "mix":
        valid = [s for s in sequence if s in registry]
        if not valid:
            valid = list(registry.keys())
        engines = [registry[s]() for s in valid]
        return MixEngine(engines), "mix", valid
    else:
        return registry[name](**extra), name, []


def _write_config(name: str, sequence: list[str], extra: dict | None = None) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {"engine": name, "sequence": sequence}
    if extra:
        data.update(extra)
    with CONFIG_FILE.open("w") as f:
        yaml.dump(data, f)
