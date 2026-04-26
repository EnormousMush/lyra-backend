# Architecture

## Goal

Single-page premise: user uploads a song, then chats with Claude about it. Detailed audio analysis runs in the backend, the resulting feature dict is baked into Claude's system prompt, and Claude answers naturally — citing real metrics for "what's the BPM" and using them as evidence for impressionistic questions like "what does this remind you of." Image generation is one tool Claude can invoke when the user explicitly asks for a visual.

## High-level pipeline

```
audio file
   │
   ▼
POST /upload  ─────────────────────────────────┐
   │                                           │
   │  (1) load audio once via librosa + HPSS   │
   │  (2) run 4 analysis modules in sequence   │
   │  (3) cache features in in-memory session  │
   │                                           │
   └──> { session_id, features }               │
                                               │
        user types a message ─────────────────►│
                                               │
POST /chat (SSE) ──────────────────────────────┘
   │
   │  feature dict baked into system prompt
   │  conversation history kept server-side
   │  Claude streams text tokens
   │  if Claude requests `generate_scene_image` tool:
   │      call Gemini Nano Banana
   │      stream image data URL back as SSE event
   │      feed tool_result back, continue stream
   │
   └──> stream of SSE events: text | tool_use | image | error | done
```

## Module breakdown

### `app/main.py` — FastAPI router

- Loads `.env` (Anthropic + Gemini keys) before any imports that need them.
- CORS open to `*` (tighten for prod — see `docs/ROADMAP.md`).
- Three routes: `GET /health`, `POST /upload`, `POST /chat`.
- `ALLOWED_SUFFIXES` whitelists audio formats.
- `/upload` writes the upload to a tempfile, runs `extract_all_features`, deletes the tempfile, registers a session.
- `/chat` validates the session and returns a `StreamingResponse` wrapping `chat.stream_chat`.

### `app/sessions.py` — in-memory session store

- Single-process dict keyed by 12-char uuid hex prefix.
- A session holds `{features, metadata, history}`.
- `history` is a list of Anthropic-format messages. Plain text turns store `content` as a string; tool-use turns store `content` as a list of content blocks (text / tool_use / tool_result). Both forms round-trip through the Anthropic messages API.
- **No persistence.** `--reload` and any process restart wipe the dict — every code edit forces a re-upload to get a fresh `session_id`. Persistence belongs in a separate phase (see roadmap).

### `app/analysis/` — feature extraction

Public surface: `extract_all_features(audio_path) -> dict`, defined in `app/analysis/__init__.py`. Loads audio once via `_loader.load_audio`, then runs four analyzers in sequence. Each analyzer is a pure function over pre-loaded `(y, sr, ...)` arrays — audio is never re-decoded.

- **`_loader.py`** — `librosa.load(sr=22050)` + HPSS (`margin=4`) split into harmonic and percussive components. Returns `(y, sr, duration, y_harm, y_perc)`.
- **`rhythm.py`** — `analyze(y, sr, duration, y_perc)` → tempo BPM, onset density, inter-beat-interval stats, beat regularity, syncopation index, tempo stability, groove consistency.
- **`key.py`** — `analyze(y_harm, sr)` → primary key + correlation, alternate key + correlation. Krumhansl-Schmuckler profiles. **Internally resamples to 11025 Hz** because the KS profile coefficients were calibrated there.
- **`dynamics.py`** — `analyze(y, sr, duration)` → RMS dB stats, dynamic range, crest factor stats, loudness arc slope, RMS autocorrelation.
- **`timbral.py`** — `analyze(y, sr, duration, y_harm, y_perc)` → ZCR, spectral flatness, harmonic-to-percussive ratio, MFCC means/stds (20-dim), MFCC delta, chroma entropy, chord change rate.

### `app/chat.py` — streaming chat + tool use

The actual Claude interaction. Three things live here:

- **System prompt** — `_build_system_prompt(features)` injects the feature dict as JSON inside a fenced block, plus a style guide ("be vivid but concise", "never invent metrics") and a feature reference glossary. The image-tool guidance ("only when explicitly asked") is also in the system prompt.
- **Tool definition** — `TOOLS` declares one tool: `generate_scene_image(description, style_hints?)`. The tool's `description` field includes the **HARD CONSTRAINT** of natural-scene-only imagery (no people / faces / man-made structures), with a worked example of how Claude should rewrite a people-scene request.
- **Streaming tool-use loop** — `stream_chat` runs up to `MAX_TOOL_TURNS = 4` iterations. Each iteration: open a `messages.stream()`, async-iterate `text_stream` (yielding `text` SSE events), await `get_final_message()`. If `stop_reason == "tool_use"`, run each tool block via `_run_tool`, emit `tool_use` and `image` SSE events, append the tool_results as a new user turn, and loop. Otherwise break and emit `done`.

### `app/images.py` — Gemini Nano Banana wrapper

- One public function: `async generate_one(description, style_hints=None) -> str` (data URL).
- `STYLE_SUFFIX` is appended to every prompt — currently locks the aesthetic to natural scenes (no people, no structures, photorealistic cinematic look).
- Uses `google.genai`'s async client.
- Raises `RuntimeError` if Gemini returns no image data.

## Design decisions (and why)

**Chat-first, not auto-generate-N-images.** v1 was "upload song → get 4 themed images automatically." It was cute but limited; users had no way to ask follow-up questions or steer the output. v2 reshaped around chat with image-generation as one optional tool. Strictly more expressive and easier to extend.

**Image as a Claude tool, not a separate endpoint.** Claude decides when to invoke based on the user's intent. The user can ask "draw what this sounds like" or "show me the chorus" and Claude routes to the tool; ask "what's the key" and it doesn't. Adding a second tool (e.g. `find_similar_song`) is purely additive.

**Audio loaded once, HPSS shared.** Analyzers receive pre-loaded arrays, not paths. Decoding a 4-minute MP3 takes ~1s; running HPSS takes another ~1s. Doing that once and sharing across modules cuts upload latency roughly in half.

**`key.py` re-resamples internally.** The Krumhansl-Schmuckler profiles were calibrated at 11025 Hz; using them on 22050 Hz audio gives noticeably worse key estimates. Fixing this in `key.py` rather than at the loader keeps the loader generic for the other modules.

**Server-side conversation history.** Clients only send `{session_id, message}`. The history (including tool-use round-trips) lives in the session store. Frontend is dumber, backend is the source of truth.

**Two repos, not a monorepo.** Lovable owns the frontend repo and auto-commits every UI change; mixing those into the backend git history would be noise. Different stacks, different deploy targets. The cost is contract drift — managed by `docs/API.md` being the agreed source of truth.

## Tweak points

Quick reference for the most common edits:

| What you want to change | Where |
|---|---|
| Claude's answering style / tone | `app/chat.py` → `_build_system_prompt` |
| Image tool's gating rules / wording | `app/chat.py` → `TOOLS[0]["description"]` |
| Model + max tokens + tool-use turn cap | `app/chat.py` → `MODEL`, `MAX_TOKENS`, `MAX_TOOL_TURNS` |
| Image aesthetic (no-people guard, style) | `app/images.py` → `STYLE_SUFFIX` |
| Add a new audio metric | new module under `app/analysis/`, register in `app/analysis/__init__.py:extract_all_features` |
| Add a new Claude tool | append to `app/chat.py:TOOLS`, handle the new name in `_run_tool` |
| Allowed audio formats | `app/main.py` → `ALLOWED_SUFFIXES` |
| Sample rate / HPSS margin | `app/analysis/_loader.py` |
| CORS allow-list | `app/main.py` → `CORSMiddleware` config |

## Things that will surprise you later

- `--reload` wipes sessions. Every code edit means re-uploading.
- `STYLE_SUFFIX` is the hard backstop for image content rules. The tool description in `chat.py` is the soft layer (steers Claude's prompts); `STYLE_SUFFIX` is the layer Gemini actually sees. Both should agree.
- The Anthropic SDK returns content blocks as Pydantic models, not dicts. We convert to dicts via `_assistant_blocks_to_dicts` before storing in history so reload doesn't break round-tripping.
- Cloudflared trycloudflare URLs change every restart. Hardcoding one in the Lovable frontend is fine for dev but will break overnight.
