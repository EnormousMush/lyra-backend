# API Contract

This is the agreed surface between the `seeingmusic` backend and any client (Lovable frontend, curl tests, future native apps). Treat it as authoritative — if the code drifts from this doc, fix the code or update this doc, don't let them disagree silently.

Current backend version: **0.2.0** (see `app/main.py`).

## Base URL

- **Local dev:** `http://localhost:8000`
- **Tunneled dev:** `https://<random>.trycloudflare.com` (ephemeral; changes every cloudflared restart)
- **Production:** TBD — see `docs/ROADMAP.md`

CORS is currently open to `*` for development. This must be locked down before any public deploy.

## Authentication

**None.** No API keys, no user accounts, no session tokens beyond the upload-scoped `session_id`. Anyone with the base URL can upload and chat. Adding auth is a roadmap item (see `docs/ROADMAP.md` — abuse prevention).

---

## `GET /health`

Health check.

**Response 200:**
```json
{"status": "ok", "service": "synesthesia", "version": "0.2.0"}
```

---

## `POST /upload`

Upload an audio file. Runs the four analysis modules, registers an in-memory session, returns the session id and the full feature dict.

**Request:** `multipart/form-data`
- Field: `file` — audio file
- Allowed extensions: `.mp3 .wav .flac .ogg .m4a .aac .wma`

**Response 200:**
```json
{
  "session_id": "0a209f1f1cce",
  "features": {
    "duration_s": 215.3,
    "sample_rate": 22050,
    "rhythm": {
      "tempo_bpm": 117.5,
      "beat_regularity": 0.82,
      "syncopation_index": 0.31,
      "tempo_stability": 0.94,
      "groove_consistency": 0.78,
      "...": "..."
    },
    "key": {
      "primary_key": "A# major",
      "primary_corr": 0.71,
      "alternate_key": "F minor",
      "alternate_corr": 0.64
    },
    "dynamics": {
      "rms_mean_db": -18.2,
      "rms_std_db": 4.5,
      "dynamic_range_db": 24.1,
      "crest_mean": 4.2,
      "loudness_arc_slope": 0.003,
      "...": "..."
    },
    "timbral": {
      "zcr_mean": 0.07,
      "spec_flat_mean": 0.12,
      "harm_perc_ratio": 1.4,
      "chord_change_rate_hz": 0.5,
      "mfcc_means": [/* 20 floats */],
      "mfcc_stds":  [/* 20 floats */],
      "...": "..."
    }
  }
}
```

The exact feature dict shape is what the analyzers in `app/analysis/` return. Frontend should not assume any specific subset of keys exists — render the headline pills (`tempo_bpm`, `primary_key`, `dynamic_range_db`, `duration_s`) and offer a JSON drawer for the rest.

**Response 400:** Unsupported format
```json
{"detail": "Unsupported format: .xyz. Use one of: .aac, .flac, .m4a, .mp3, .ogg, .wav, .wma"}
```

**Latency:** ~5-30 s for analysis, depending on song length and CPU. Frontend should show a spinner and disable upload during this window.

---

## `POST /chat`

Streaming chat about an uploaded song. Claude receives the song's features in its system prompt and may invoke the `generate_scene_image` tool when the user explicitly asks for a visual.

**Request:** `application/json`
```json
{
  "session_id": "0a209f1f1cce",
  "message": "what is the BPM?"
}
```

**Response:** `text/event-stream` (Server-Sent Events).

⚠️ **Browser clients:** the standard `EventSource` API only supports GET. Use `fetch` with a `ReadableStream` reader and parse the SSE format manually (split on `\n\n`, strip the `data: ` prefix, JSON.parse the rest).

**Response 404:** `session_id` not found.

### SSE event types

Each event is one line of the form:
```
data: {"type": "<type>", "content": <content>}\n\n
```

| `type`     | `content`                              | Meaning |
|------------|----------------------------------------|---------|
| `text`     | string (token chunk)                   | Append to the current assistant message |
| `tool_use` | string (tool name)                     | Claude is invoking a tool — show a "generating image…" placeholder in the current assistant message |
| `image`    | string (`data:image/png;base64,...`)   | Replace the placeholder with `<img src={content}>` |
| `done`     | (omitted)                              | Turn complete — close out the message and re-enable input |
| `error`    | string (`ErrorClass: error message`)   | Something failed — render as an error message and re-enable input. Stream ends after this event. |

### Example flow — text-only question

```
data: {"type": "text", "content": "The"}
data: {"type": "text", "content": " BPM is **117.5**."}
data: {"type": "text", "content": " Moderate tempo — comfortable mid-pace dance speed..."}
data: {"type": "done"}
```

### Example flow — image request

```
data: {"type": "text", "content": "Sure, let me visualize that for you."}
data: {"type": "tool_use", "content": "generate_scene_image"}
data: {"type": "image", "content": "data:image/png;base64,iVBORw0KGgo...<long>"}
data: {"type": "text", "content": "There you go — the moody minor key and slow loudness arc..."}
data: {"type": "done"}
```

A single assistant turn may interleave any number of `text` events and `tool_use` → `image` pairs before `done`. Render in the order received. If multiple images are generated in one turn, they should appear inline at the points where their `image` events arrive.

### Conversation state

History is server-side, keyed by `session_id`. The client only ever sends one new user message per request. Server appends both the user message and Claude's response (including any tool-use blocks) to the session's history.

Sessions are in-memory and lost on backend restart (including `--reload`). Frontends should treat any 404 from `/chat` as "session is gone, please re-upload" rather than retrying.

### Image tool details

- Tool name: `generate_scene_image`
- Inputs: `description` (required, string), `style_hints` (optional, string)
- Output: a single base64 PNG data URL ~1.5-2.5 MB.
- Hard constraint: natural scenes only (no people, no man-made structures). Enforced at two layers — Claude's tool description and `app/images.py:STYLE_SUFFIX`.
- Triggered only when the user explicitly asks ("draw", "show me", "render", "visualize", "image of"). System prompt instructs Claude not to call unprompted.

---

## Versioning

The version string in `GET /health` will bump when the API surface changes:

- **0.1.x** — v1 batch endpoint (`/analyze/upload`, returned 4 images). Removed in 0.2.0.
- **0.2.x** — current. Chat-first with `/upload` + `/chat` + image as Claude tool.

Breaking changes to event types or response shapes warrant a minor bump and a frontend update. Adding a new optional event type or new tool is non-breaking.
