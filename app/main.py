"""
main.py — FastAPI application for Synesthesia.

v2 architecture:
  POST /upload   — upload an audio file, returns {session_id, features}
  POST /chat     — streaming Q&A about the uploaded song (Phase C)
  GET  /health   — health check
"""

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .analysis import extract_all_features
from . import sessions, chat

# Per-IP rate limiter. Uvicorn must run with --proxy-headers --forwarded-allow-ips='*'
# in production so we see the real client IP (not Render's internal proxy IP).
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Synesthesia",
    description="Chat with your music — analysis-aware Q&A over an uploaded song.",
    version="0.2.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS open for now; tighten for production / Lovable preview origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ALLOWED_SUFFIXES = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "synesthesia", "version": "0.2.0"}


@app.post("/upload")
@limiter.limit("10/hour")
async def upload(request: Request, file: UploadFile = File(...)):
    """Upload an audio file. Runs analysis, stores features in a session,
    and returns a session_id the client uses for subsequent /chat calls.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            400,
            f"Unsupported format: {suffix or '(none)'}. "
            f"Use one of: {', '.join(sorted(ALLOWED_SUFFIXES))}",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        features = extract_all_features(tmp_path)
    finally:
        os.unlink(tmp_path)

    session_id = sessions.create_session(
        features=features,
        metadata={"filename": file.filename},
    )
    return {"session_id": session_id, "features": features}


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/chat")
@limiter.limit("100/hour")
async def chat_endpoint(request: Request, req: ChatRequest):
    """Streaming chat about the uploaded song. Returns Server-Sent Events.

    Each event is `data: {"type": "text"|"done"|"error", "content": "..."}\\n\\n`.
    """
    if sessions.get_session(req.session_id) is None:
        raise HTTPException(404, f"session_id not found: {req.session_id}")

    return StreamingResponse(
        chat.stream_chat(req.session_id, req.message),
        media_type="text/event-stream",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
