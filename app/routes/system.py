"""Health, configuration status, catalog metadata, and the Suno atlas."""
from fastapi import APIRouter, Depends

from .. import atlas, config
from ..analysis.catalog import CATALOG, GROUP_ORDER
from ..auth import current_user
from ..db import User
from ..director import STYLES
from ..images import ASPECTS

router = APIRouter(prefix="/api", tags=["system"])
VERSION = "3.0.0"


@router.get("/health")
def health():
    return {"status": "ok", "service": "lyra", "version": VERSION}


@router.get("/meta")
def meta():
    return {
        "version": VERSION,
        "styles": [{"id": k, "label": v[0], "description": v[1]} for k, v in STYLES.items()],
        "aspects": list(ASPECTS.keys()),
        "catalog": CATALOG,
        "groups": GROUP_ORDER,
        "services": {
            "claude": {"live": config.claude_live(), "model": config.CLAUDE_MODEL,
                       "key_present": bool(config.ANTHROPIC_API_KEY)},
            "images": {"live": config.gemini_live(), "model": config.IMAGE_MODEL,
                       "key_present": bool(config.GEMINI_API_KEY)},
        },
        "atlas": atlas.status(),
    }


@router.get("/atlas")
def get_atlas(_: User = Depends(current_user)):
    return atlas.atlas_payload()


@router.post("/atlas/reload")
def reload_atlas(_: User = Depends(current_user)):
    atlas.reload()
    return atlas.status()
