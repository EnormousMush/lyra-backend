# Synesthesia

Chat with your music. Upload a song, then ask anything about it — BPM, key, dynamics, vibe, what it reminds you of. Detailed audio analysis runs in the backend, Claude answers in natural language with the metrics as context.

## Architecture

```
seeingmusic/
├── app/
│   ├── main.py              # FastAPI app & routes
│   ├── sessions.py          # In-memory session store (per-upload feature cache + chat history)
│   ├── analysis/            # Audio feature extraction
│   │   ├── _loader.py       # librosa load + HPSS split
│   │   ├── rhythm.py        # BPM, beat regularity, syncopation, groove
│   │   ├── key.py           # Krumhansl-Schmuckler key estimation
│   │   ├── dynamics.py      # RMS, crest factor, dynamic range, loudness arc
│   │   └── timbral.py       # MFCC, chroma, ZCR, flatness, H/P ratio
│   ├── chat.py              # Streaming chat over Claude (SSE)
│   └── images.py            # Nano Banana image gen — used by future "draw this song" tool
├── requirements.txt
└── README.md
```

## Endpoints

- `POST /upload` — multipart file upload. Runs all analysis modules, stores features in a session. Returns `{session_id, features}`.
- `POST /chat` — JSON `{session_id, message}`. Streams Claude's response as Server-Sent Events. Conversation history is tracked server-side per session.
- `GET /health` — health check.

## Stack

- **Backend:** FastAPI + Python 3.12
- **Audio analysis:** librosa, scipy (modules ported from [musicdeepfake](https://github.com/EnormousMush/musicdeepfake))
- **Chat:** Anthropic Claude Sonnet 4.5 with streaming
- **Image generation (future tool):** Google Gemini 2.5 Flash Image ("Nano Banana")
- **Frontend (future):** Lovable chat UI

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

Then run:

```bash
uvicorn app.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive API explorer.

## Quick test

Upload a file via Swagger to get a `session_id`, then in another terminal:

```bash
curl -N -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id": "YOUR_ID", "message": "what is the BPM?"}'
```

You'll see streaming `data: {...}` SSE events.

## Roadmap

- **Phase D** — register `generate_scene_image` as a Claude tool so the chat can produce visuals on demand.
- **Phase F** — Lovable chat UI in a separate `seeingmusic-frontend` repo.
