"""Runtime configuration, read once from the environment (.env is loaded in main.py)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("LYRA_DATA_DIR", ROOT / "storage"))
AUDIO_DIR = DATA_DIR / "audio"
IMAGE_DIR = DATA_DIR / "images"
DB_PATH = DATA_DIR / "lyra.db"
BUNDLED = Path(__file__).resolve().parent / "data"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# gemini-2.5-flash-image was shut down on 2026-10-02; 3.1 Flash Image is its replacement.
CLAUDE_MODEL = os.environ.get("LYRA_CLAUDE_MODEL", "claude-sonnet-5-5")
IMAGE_MODEL = os.environ.get("LYRA_IMAGE_MODEL", "gemini-3.1-flash-image")

FRONTEND_ORIGIN = os.environ.get("LYRA_FRONTEND_ORIGIN", "http://localhost:5173")
SESSION_DAYS = 30


def _flag(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, "").strip().lower()
    return default if v == "" else v in {"1", "true", "yes", "on"}


# Hosting controls. Locally everything is open; on a server set these in the environment.
INVITE_ONLY = _flag("LYRA_INVITE_ONLY", False)        # sign-up needs an invite code
SECURE_COOKIES = _flag("LYRA_SECURE_COOKIES", False)  # set on HTTPS hosts
ADMIN_EMAIL = os.environ.get("LYRA_ADMIN_EMAIL", "").strip().lower()  # this account is admin
DAILY_UPLOADS = int(os.environ.get("LYRA_DAILY_UPLOADS", "5"))
DAILY_IMAGES = int(os.environ.get("LYRA_DAILY_IMAGES", "20"))
STATIC_DIR = ROOT / "web" / "dist"  # built web app, served by the API when present

_mock_flag = os.environ.get("LYRA_MOCK", "").strip().lower()


def claude_live() -> bool:
    return bool(ANTHROPIC_API_KEY) and _mock_flag not in {"1", "true", "yes", "all", "claude"}


def gemini_live() -> bool:
    return bool(GEMINI_API_KEY) and _mock_flag not in {"1", "true", "yes", "all", "images"}


for d in (AUDIO_DIR, IMAGE_DIR):
    d.mkdir(parents=True, exist_ok=True)
