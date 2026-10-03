"""Image generation: batches (cover / scenes / variation), gallery, favourites, files."""
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from .. import jobs, quota
from ..auth import current_user
from ..db import Generation, Track, User, get_session
from ..director import STYLES
from ..images import ASPECTS
from .tracks import gen_out

router = APIRouter(prefix="/api", tags=["generations"])


class GenerateIn(BaseModel):
    mode: Literal["cover", "scenes", "variation"]
    style: str = "cinematic"
    aspect: str = "1:1"
    direction: Optional[str] = Field(default=None, max_length=600)
    count: int = Field(default=2, ge=1, le=4)
    sections: Optional[list[int]] = None
    parent_id: Optional[str] = None
    people: bool = False


@router.post("/tracks/{track_id}/generate")
async def generate(track_id: str, body: GenerateIn, user: User = Depends(current_user),
             s: Session = Depends(get_session)):
    t = s.get(Track, track_id)
    if t is None or t.user_id != user.id:
        raise HTTPException(404, "Track not found")
    if t.stage != "ready":
        raise HTTPException(409, "The track is still being analysed")
    if body.style not in STYLES:
        raise HTTPException(400, "Unknown style")
    if body.aspect not in ASPECTS:
        raise HTTPException(400, "Unknown aspect ratio")

    n_requested = (len(body.sections) if body.mode == "scenes" and body.sections
                   else len(t.sections or []) if body.mode == "scenes" else body.count)
    quota.check_images(s, user, n_requested)
    batch = uuid.uuid4().hex[:12]
    direction = (body.direction or "").strip() or None
    rows: list[Generation] = []
    if body.mode == "scenes":
        n_sec = len(t.sections or [])
        idx = sorted(set(body.sections)) if body.sections else list(range(n_sec))
        idx = [i for i in idx if 0 <= i < n_sec][:10]
        if not idx:
            raise HTTPException(400, "No sections selected")
        rows = [Generation(user_id=user.id, track_id=t.id, batch_id=batch, mode="scenes",
                           style=body.style, aspect=body.aspect, direction=direction,
                           section_index=i) for i in idx]
    else:
        parent_id = None
        if body.mode == "variation":
            parent = s.get(Generation, body.parent_id) if body.parent_id else None
            if parent is None or parent.user_id != user.id or parent.status != "done":
                raise HTTPException(400, "Pick a finished image to vary")
            parent_id = parent.id
        rows = [Generation(user_id=user.id, track_id=t.id, batch_id=batch, mode=body.mode,
                           style=body.style, aspect=body.aspect, direction=direction,
                           parent_id=parent_id) for _ in range(body.count)]
    for r in rows:
        s.add(r)
    s.commit()
    jobs.spawn(jobs.generate(batch, body.people))
    return {"batch_id": batch, "generations": [gen_out(r) for r in rows]}


@router.get("/generations")
def gallery(favorites: bool = False, user: User = Depends(current_user),
            s: Session = Depends(get_session)):
    q = select(Generation, Track).join(Track, Track.id == Generation.track_id).where(
        Generation.user_id == user.id, Generation.status == "done")
    if favorites:
        q = q.where(Generation.favorite == True)  # noqa: E712
    out = []
    for g, t in s.exec(q.order_by(Generation.created_at.desc())).all():
        out.append({**gen_out(g), "track_title": t.title})
    return out


class FavIn(BaseModel):
    favorite: bool


@router.post("/generations/{gen_id}/favorite")
def favorite(gen_id: str, body: FavIn, user: User = Depends(current_user),
             s: Session = Depends(get_session)):
    g = s.get(Generation, gen_id)
    if g is None or g.user_id != user.id:
        raise HTTPException(404, "Image not found")
    g.favorite = body.favorite
    s.add(g)
    s.commit()
    return gen_out(g)


@router.get("/generations/{gen_id}/image")
def image(gen_id: str, download: bool = False, user: User = Depends(current_user),
          s: Session = Depends(get_session)):
    g = s.get(Generation, gen_id)
    if g is None or g.user_id != user.id or not g.image_path:
        raise HTTPException(404, "Image not found")
    name = f"lyra-{(g.title or g.id).lower().replace(' ', '-')}{g.image_path[-4:]}"
    return FileResponse(g.image_path, filename=name if download else None,
                        headers={"Cache-Control": "private, max-age=31536000, immutable"})
