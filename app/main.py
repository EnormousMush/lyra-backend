"""Lyra Studio backend (v3): turn a song into images, grounded in measured audio features.

Run:  ./dev.sh  (API on :8765, see LYRA_API_PORT)
The Vite dev server in web/ proxies /api to this process, so cookies stay same-origin.
"""
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from . import config, jobs  # noqa: E402
from .auth import router as auth_router  # noqa: E402
from .db import init_db  # noqa: E402
from .routes.generations import router as gen_router  # noqa: E402
from .routes.system import VERSION, router as system_router  # noqa: E402
from .routes.tracks import router as tracks_router  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    jobs.recover_interrupted()
    log = logging.getLogger("lyra")
    log.info("Claude: %s (%s)", "live" if config.claude_live() else "preview mode", config.CLAUDE_MODEL)
    log.info("Images: %s (%s)", "live" if config.gemini_live() else "preview mode", config.IMAGE_MODEL)
    yield


app = FastAPI(title="Lyra Studio", version=VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
for r in (auth_router, tracks_router, gen_router, system_router):
    app.include_router(r)
