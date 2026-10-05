"""Track library: upload, list, read, rename, re-analyse, stream audio."""
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import atlas, jobs, quota
from ..analysis.catalog import readout
from ..auth import current_user
from ..config import AUDIO_DIR
from ..db import Generation, Track, User, get_session

router = APIRouter(prefix="/api/tracks", tags=["tracks"])
# M4A and AAC need an ffmpeg decoder, which the server does not have.
ALLOWED = {".mp3", ".wav", ".flac", ".ogg"}
MAX_BYTES = 80 * 1024 * 1024


def gen_out(g: Generation) -> dict:
    return {
        "id": g.id, "track_id": g.track_id, "batch_id": g.batch_id, "mode": g.mode,
        "style": g.style, "aspect": g.aspect, "direction": g.direction,
        "section_index": g.section_index, "parent_id": g.parent_id, "status": g.status,
        "error": g.error, "title": g.title, "prompt": g.prompt, "rationale": g.rationale,
        "palette": g.palette, "mock": g.mock, "favorite": g.favorite,
        "image_url": f"/api/generations/{g.id}/image" if g.status == "done" else None,
        "created_at": g.created_at.isoformat(),
    }


def _cover(s: Session, track_id: str) -> str | None:
    q = (select(Generation).where(Generation.track_id == track_id, Generation.status == "done")
         .order_by(Generation.favorite.desc(), Generation.created_at.desc()))
    g = s.exec(q).first()
    return f"/api/generations/{g.id}/image" if g else None


def track_summary(s: Session, t: Track) -> dict:
    n = len(s.exec(select(Generation.id).where(Generation.track_id == t.id,
                                                Generation.status == "done")).all())
    feats = t.features or {}
    return {
        "id": t.id, "title": t.title, "filename": t.filename, "stage": t.stage, "error": t.error,
        "duration_s": t.duration_s, "created_at": t.created_at.isoformat(),
        "headline": (t.listening or {}).get("headline"),
        "palette": [p["hex"] for p in (t.listening or {}).get("palette", [])],
        "tempo": (feats.get("flat") or {}).get("stats.tempo_bpm"),
        "key": (feats.get("key") or {}).get("best_key"),
        "cover_url": _cover(s, t.id), "image_count": n,
    }


def _own(s: Session, track_id: str, user: User) -> Track:
    t = s.get(Track, track_id)
    if t is None or t.user_id != user.id:
        raise HTTPException(404, "Track not found")
    return t


@router.post("")
async def upload(file: UploadFile = File(...), user: User = Depends(current_user),
                 s: Session = Depends(get_session)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(400, f"Unsupported format {suffix or '(none)'}. Use {', '.join(sorted(ALLOWED))}.")
    quota.check_upload(s, user)
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 80 MB.")
    title = Path(file.filename).stem.replace("_", " ").strip() or "Untitled"
    t = Track(user_id=user.id, title=title[:120], filename=file.filename, audio_path="")
    s.add(t)
    s.commit()
    path = AUDIO_DIR / f"{t.id}{suffix}"
    path.write_bytes(data)
    t.audio_path = str(path)
    s.add(t)
    s.commit()
    jobs.spawn(jobs.analyze(t.id))
    return track_summary(s, t)


@router.get("")
def list_tracks(user: User = Depends(current_user), s: Session = Depends(get_session)):
    ts = s.exec(select(Track).where(Track.user_id == user.id).order_by(Track.created_at.desc())).all()
    return [track_summary(s, t) for t in ts]


@router.get("/{track_id}")
def get_track(track_id: str, user: User = Depends(current_user), s: Session = Depends(get_session)):
    t = _own(s, track_id, user)
    gens = s.exec(select(Generation).where(Generation.track_id == t.id)
                  .order_by(Generation.created_at.desc(), Generation.section_index)).all()
    flat = (t.features or {}).get("flat", {})
    return {
        **track_summary(s, t),
        "features": {k: v for k, v in (t.features or {}).items() if k != "flat"},
        "readout": readout(flat),
        "percentiles": atlas.percentiles(flat),
        "sections": t.sections or [],
        "waveform": t.waveform or [],
        "dna": t.dna,
        "listening": t.listening,
        "generations": [gen_out(g) for g in gens],
    }


class RenameIn(BaseModel):
    title: str


@router.patch("/{track_id}")
def rename(track_id: str, body: RenameIn, user: User = Depends(current_user),
           s: Session = Depends(get_session)):
    t = _own(s, track_id, user)
    title = body.title.strip()[:120]
    if not title:
        raise HTTPException(400, "Title cannot be empty")
    t.title = title
    s.add(t)
    s.commit()
    return track_summary(s, t)


@router.post("/{track_id}/reanalyze")
async def reanalyze(track_id: str, user: User = Depends(current_user), s: Session = Depends(get_session)):
    t = _own(s, track_id, user)
    if t.stage not in {"ready", "error"}:
        raise HTTPException(409, "Analysis is already running")
    t.stage, t.error = "queued", None
    s.add(t)
    s.commit()
    jobs.spawn(jobs.analyze(t.id))
    return track_summary(s, t)


@router.get("/{track_id}/audio")
def audio(track_id: str, user: User = Depends(current_user), s: Session = Depends(get_session)):
    t = _own(s, track_id, user)
    return FileResponse(t.audio_path, filename=t.filename)


@router.delete("/{track_id}")
def delete_track(track_id: str, user: User = Depends(current_user), s: Session = Depends(get_session)):
    """Remove a song, its analysis and every image made from it, including the files on disk."""
    t = _own(s, track_id, user)
    gens = s.exec(select(Generation).where(Generation.track_id == t.id)).all()
    for g in gens:
        if g.image_path:
            Path(g.image_path).unlink(missing_ok=True)
        s.delete(g)
    if t.audio_path:
        Path(t.audio_path).unlink(missing_ok=True)
    s.delete(t)
    s.commit()
    return {"ok": True}
