"""
main.py — FastAPI application for Synesthesia.
Endpoints:
  POST /analyze/upload   — upload an audio file
  POST /analyze/url      — provide a YouTube/Spotify URL
  GET  /health           — health check
"""

import os
import tempfile
import subprocess
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .audio import extract_features
from .associations import generate_associations
from .images import generate_images_for_scenes

app = FastAPI(
    title="Synesthesia",
    description="Turn music into vivid visual scenes",
    version="0.1.0",
)

# Allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class URLRequest(BaseModel):
    url: str
    title: str | None = None
    artist: str | None = None


class AnalysisResponse(BaseModel):
    features: dict
    associations: dict


# ---- Endpoints ----

@app.get("/health")
async def health():
    return {"status": "ok", "service": "synesthesia"}


@app.post("/analyze/upload", response_model=AnalysisResponse)
async def analyze_upload(
    file: UploadFile = File(...),
    title: str | None = None,
    artist: str | None = None,
):
    """Analyze an uploaded audio file."""
    # Validate file type
    allowed = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, f"Unsupported format: {suffix}. Use: {', '.join(allowed)}")

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Extract features
        features = extract_features(tmp_path)

        # Generate associations
        metadata = {}
        if title:
            metadata["title"] = title
        if artist:
            metadata["artist"] = artist

        associations = await generate_associations(features, metadata or None)

        scenes = associations.get("scenes", [])[:4]
        images = await generate_images_for_scenes(scenes)
        for scene, img in zip(scenes, images):
            scene["image"] = img
        associations["scenes"] = scenes

        return AnalysisResponse(features=features, associations=associations)
    finally:
        os.unlink(tmp_path)


@app.post("/analyze/url", response_model=AnalysisResponse)
async def analyze_url(request: URLRequest):
    """Analyze a song from a YouTube or other URL using yt-dlp."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(tmp_dir, "audio.wav")

        # Download audio with yt-dlp
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--extract-audio",
                    "--audio-format", "wav",
                    "--output", output_path,
                    "--no-playlist",
                    "--max-filesize", "50M",
                    request.url,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise HTTPException(400, f"Failed to download audio: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            raise HTTPException(408, "Download timed out")
        except FileNotFoundError:
            raise HTTPException(500, "yt-dlp not installed. Run: pip install yt-dlp")

        # yt-dlp may add extension, find the actual file
        actual_files = list(Path(tmp_dir).glob("audio*"))
        if not actual_files:
            raise HTTPException(500, "Audio download produced no output file")
        audio_file = str(actual_files[0])

        # Extract features
        features = extract_features(audio_file)

        # Generate associations
        metadata = {}
        if request.title:
            metadata["title"] = request.title
        if request.artist:
            metadata["artist"] = request.artist

        associations = await generate_associations(features, metadata or None)

        scenes = associations.get("scenes", [])[:4]
        images = await generate_images_for_scenes(scenes)
        for scene, img in zip(scenes, images):
            scene["image"] = img
        associations["scenes"] = scenes

        return AnalysisResponse(features=features, associations=associations)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
