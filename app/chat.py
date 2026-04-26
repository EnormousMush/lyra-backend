"""
chat.py — Streaming chat about an uploaded song.

Exposes `stream_chat(session_id, message)` as an async generator that
yields SSE-formatted chunks. Conversation history lives in the session
store, so clients only need to pass the session_id + new message.
"""

import os
import json
from anthropic import AsyncAnthropic

from . import sessions


_client = AsyncAnthropic()  # picks up ANTHROPIC_API_KEY from env (loaded by main.py)
MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 1024


def _build_system_prompt(features: dict) -> str:
    """Inject the song's analysis features into the system prompt as context."""
    return (
        "You are a friendly, knowledgeable music analyst chatting with the user "
        "about a song they have uploaded. You've been given audio-analysis "
        "features extracted from the file (BPM, key, dynamics, timbre, etc.). "
        "Use them to ground every answer.\n\n"
        "Style:\n"
        "- For specific-metric questions (BPM, key, dynamic range), give the value "
        "directly with one sentence of context — not a lecture.\n"
        "- For impressionistic questions ('what does this remind you of', "
        "'what's the vibe'), use the features as evidence. Be vivid but concise.\n"
        "- Never invent metrics that aren't in the feature dict. If the user asks "
        "about something we didn't measure (lyrics, exact instruments, vocals), "
        "say so honestly and offer the closest proxy we do have (e.g., timbre, "
        "harmonic-to-percussive ratio).\n"
        "- Keep responses short by default; expand only when the user clearly wants depth.\n\n"
        "Feature reference (rough guide, not exhaustive):\n"
        "- rhythm.tempo_bpm: tempo in BPM\n"
        "- rhythm.beat_regularity: 0-1, higher = more metronomic\n"
        "- rhythm.syncopation_index: 0-1, higher = more off-beat\n"
        "- key.primary_key: estimated key (e.g. 'A# major')\n"
        "- dynamics.rms_mean_db / dynamic_range_db: loudness and range\n"
        "- dynamics.crest_mean: low (~2-3) = compressed, high = dynamic\n"
        "- timbral.harm_perc_ratio: high = melodic/harmonic, low = percussive\n"
        "- timbral.spec_flat_mean: high = noisy, low = tonal\n"
        "- timbral.chord_change_rate_hz: harmonic motion rate\n\n"
        "Audio features for the uploaded song:\n"
        f"```json\n{json.dumps(features, indent=2)}\n```"
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def stream_chat(session_id: str, message: str):
    """Async generator yielding SSE-formatted chunks for /chat."""
    s = sessions.get_session(session_id)
    if s is None:
        yield _sse({"type": "error", "content": "session not found"})
        return

    sessions.append_message(session_id, "user", message)
    system = _build_system_prompt(s["features"])

    full_text = ""
    try:
        async with _client.messages.stream(
            model=MODEL,
            system=system,
            messages=s["history"],
            max_tokens=MAX_TOKENS,
        ) as stream:
            async for text in stream.text_stream:
                full_text += text
                yield _sse({"type": "text", "content": text})
    except Exception as e:
        yield _sse({"type": "error", "content": f"{type(e).__name__}: {e}"})
        return

    sessions.append_message(session_id, "assistant", full_text)
    yield _sse({"type": "done"})
