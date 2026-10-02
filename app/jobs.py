"""Background work: track analysis and image batches. Progress is written to SQLite
and the UI polls it, so a reload or a second tab always sees the true state."""
import asyncio
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlmodel import Session, select

from . import atlas, director, images
from .analysis import analyze_track
from .config import IMAGE_DIR
from .db import Generation, Track, engine

log = logging.getLogger("lyra.jobs")
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="analysis")
_tasks: set[asyncio.Task] = set()


def spawn(coro) -> None:
    t = asyncio.create_task(coro)
    _tasks.add(t)
    t.add_done_callback(_tasks.discard)


def _friendly(e: Exception) -> str:
    name = type(e).__name__
    msg = str(e)
    if "authentication" in msg.lower() or "api key" in msg.lower() or name in {"AuthenticationError", "PermissionDeniedError"}:
        return "The API key was rejected. Check the keys in your .env file."
    if "not_found" in msg.lower() or "NotFound" in name or "404" in msg:
        return "The model was not found. Check LYRA_CLAUDE_MODEL / LYRA_IMAGE_MODEL in .env."
    if "rate" in msg.lower() and "limit" in msg.lower():
        return "Rate limited by the API. Wait a moment and try again."
    if "safety" in msg.lower() or "blocked" in msg.lower():
        return "The image model declined this prompt. Try a different direction."
    return msg[:240] or name


def _set_stage(track_id: str, stage: str) -> None:
    with Session(engine) as s:
        t = s.get(Track, track_id)
        if t:
            t.stage = stage
            s.add(t)
            s.commit()


async def analyze(track_id: str) -> None:
    loop = asyncio.get_running_loop()
    with Session(engine) as s:
        path = s.get(Track, track_id).audio_path
    try:
        result = await loop.run_in_executor(
            _pool, lambda: analyze_track(path, lambda st: _set_stage(track_id, st)))
        with Session(engine) as s:
            t = s.get(Track, track_id)
            t.features, t.sections = result["features"], result["sections"]
            t.waveform, t.duration_s = result["waveform"], result["duration_s"]
            t.stage = "listening"
            s.add(t)
            s.commit()

        flat = result["features"]["flat"]
        data_dna = atlas.data_dna(flat)
        listening = await director.listen(result["features"], result["sections"],
                                          atlas.percentiles(flat), data_dna)
        with Session(engine) as s:
            t = s.get(Track, track_id)
            t.dna = data_dna or listening.pop("dna", None)
            listening.pop("dna", None)
            t.listening = listening
            t.stage = "ready"
            s.add(t)
            s.commit()
    except Exception as e:
        log.error("analysis failed for %s\n%s", track_id, traceback.format_exc())
        with Session(engine) as s:
            t = s.get(Track, track_id)
            t.stage, t.error = "error", _friendly(e)
            s.add(t)
            s.commit()


async def generate(batch_id: str, people_ok: bool) -> None:
    with Session(engine) as s:
        gens = s.exec(select(Generation).where(Generation.batch_id == batch_id)
                      .order_by(Generation.created_at, Generation.section_index)).all()
        if not gens:
            return
        g0 = gens[0]
        track = s.get(Track, g0.track_id)
        parent = s.get(Generation, g0.parent_id) if g0.parent_id else None
        parent_info = {"prompt": parent.prompt} if parent else None
        parent_path = Path(parent.image_path) if parent and parent.image_path else None
        targets = [track.sections[g.section_index] for g in gens] if g0.mode == "scenes" else []
        ctx = dict(features=track.features, listening=track.listening or {},
                   sections=track.sections or [], percentiles=atlas.percentiles(track.features.get("flat", {})))
        ids = [g.id for g in gens]
        mode, style, aspect, direction = g0.mode, g0.style, g0.aspect, g0.direction

    try:
        briefs = await director.direct(**ctx, mode=mode, style=style, count=len(ids),
                                       direction=direction, targets=targets,
                                       parent=parent_info, people_ok=people_ok)
    except Exception as e:
        log.error("direction failed for %s\n%s", batch_id, traceback.format_exc())
        _fail(ids, _friendly(e))
        return

    with Session(engine) as s:
        for gid, b in zip(ids, briefs):
            g = s.get(Generation, gid)
            g.title, g.prompt = b["title"], b["prompt"]
            g.rationale, g.palette = b["rationale"], b["palette"]
            g.status = "rendering"
            s.add(g)
        s.commit()

    async def one(gid: str, b: dict):
        try:
            path, mock = await images.render(b["prompt"], aspect, IMAGE_DIR / gid, b["palette"],
                                             parent_image=parent_path, people_ok=people_ok)
            with Session(engine) as s:
                g = s.get(Generation, gid)
                g.image_path, g.mock, g.status = str(path), mock, "done"
                s.add(g)
                s.commit()
        except Exception as e:
            log.error("render failed for %s\n%s", gid, traceback.format_exc())
            _fail([gid], _friendly(e))

    await asyncio.gather(*(one(gid, b) for gid, b in zip(ids, briefs)))


def _fail(ids: list[str], msg: str) -> None:
    with Session(engine) as s:
        for gid in ids:
            g = s.get(Generation, gid)
            if g:
                g.status, g.error = "error", msg
                s.add(g)
        s.commit()


def recover_interrupted() -> None:
    """Jobs do not survive a restart; mark anything left mid-flight so the UI can retry."""
    with Session(engine) as s:
        for t in s.exec(select(Track).where(Track.stage.not_in(["ready", "error"]))).all():
            t.stage, t.error = "error", "The server restarted during analysis. Re-run analysis."
            s.add(t)
        for g in s.exec(select(Generation).where(Generation.status.not_in(["done", "error"]))).all():
            g.status, g.error = "error", "The server restarted during rendering."
            s.add(g)
        s.commit()
