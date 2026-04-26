# Synesthesia

Chat with your music. Upload a song, then ask anything about it — BPM, key, dynamics, vibe, what it reminds you of. Detailed audio analysis runs in the backend, Claude answers in natural language with the metrics as context. Ask Claude to "draw what this sounds like" and it generates a photorealistic natural-scene image grounded in the song's features.

## Repos

- **`seeingmusic`** (this repo) — FastAPI backend: audio analysis + streaming chat + image-generation tool.
- **`seeingmusic-frontend`** — Lovable-generated chat UI. Deployed separately, talks to this backend via HTTPS.

## Stack

- **Backend:** FastAPI + Python 3.12
- **Audio analysis:** librosa, scipy (modules ported from [musicdeepfake](https://github.com/EnormousMush/musicdeepfake) Part 1)
- **Chat:** Anthropic Claude Sonnet 4.5 with streaming + tool use
- **Image generation:** Google Gemini 2.5 Flash Image ("Nano Banana"), invoked as a Claude tool
- **Frontend:** Lovable (React + TypeScript + Tailwind + shadcn/ui)

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

Run:

```bash
uvicorn app.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive API explorer.

## Daily startup (cheat sheet)

Two terminals, both inside `~/seeingmusic`:

**Terminal 1 — backend:**
```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2 — public tunnel (so the Lovable frontend can reach localhost):**
```bash
cloudflared tunnel --url http://localhost:8000
```

Copy the printed `https://*.trycloudflare.com` URL and paste it into the Lovable frontend's `BACKEND_URL` constant. The URL changes every cloudflared restart — that's expected until the backend is deployed.

To shut down: `Ctrl+C` in each terminal. Nothing persists between runs (sessions are in-memory).

## Quick test

Upload a file via Swagger to get a `session_id`, then:

```bash
curl -N -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id": "YOUR_ID", "message": "what is the BPM?"}'
```

You'll see streaming `data: {...}` SSE events. Ask "draw me what this song looks like" to trigger the image-generation tool.

## Exposing locally for the Lovable frontend

The Lovable preview is hosted, so it can't reach `localhost:8000` directly. Use a tunnel:

```bash
cloudflared tunnel --url http://localhost:8000
```

Copy the printed `https://*.trycloudflare.com` URL into Lovable's `BACKEND_URL`. Note: ad-hoc cloudflared URLs change every restart — for a stable URL, see `docs/ROADMAP.md` (production-readiness section).

## Documentation

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — module-by-module breakdown, design decisions, tweak points
- **[docs/API.md](docs/API.md)** — endpoint contract + SSE event types (source of truth between backend and frontend)
- **[docs/ROADMAP.md](docs/ROADMAP.md)** — current status, next stages, production-readiness checklist
