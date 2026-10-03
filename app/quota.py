"""Per-user daily limits. Every upload costs CPU and Claude tokens, every image costs
Gemini credit, so each account gets a daily allowance (LYRA_DAILY_UPLOADS, LYRA_DAILY_IMAGES).
Admins are exempt. The day boundary is UTC."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlmodel import Session, func, select

from . import config
from .db import Generation, Track, User


def _day_start() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def usage(s: Session, user: User) -> dict:
    start = _day_start()
    uploads = s.exec(select(func.count(Track.id)).where(Track.user_id == user.id,
                                                        Track.created_at >= start)).one()
    images = s.exec(select(func.count(Generation.id)).where(Generation.user_id == user.id,
                                                            Generation.created_at >= start,
                                                            Generation.status != "error")).one()
    return {
        "uploads": {"used": int(uploads), "limit": None if user.is_admin else config.DAILY_UPLOADS},
        "images": {"used": int(images), "limit": None if user.is_admin else config.DAILY_IMAGES},
        "resets_at": (start + timedelta(days=1)).isoformat(),
    }


def check_upload(s: Session, user: User) -> None:
    u = usage(s, user)["uploads"]
    if u["limit"] is not None and u["used"] >= u["limit"]:
        raise HTTPException(429, f"Daily limit reached: {u['limit']} songs a day. It resets at midnight UTC.")


def check_images(s: Session, user: User, n: int) -> None:
    u = usage(s, user)["images"]
    if u["limit"] is not None and u["used"] + n > u["limit"]:
        left = max(0, u["limit"] - u["used"])
        raise HTTPException(429, f"Daily limit: {u['limit']} images a day, {left} left today. It resets at midnight UTC.")
