"""
chat.py — Streaming chat about an uploaded song.

Exposes `stream_chat(session_id, message)` as an async generator that
yields SSE-formatted chunks. Conversation history lives in the session
store, so clients only need to pass the session_id + new message.

Phase D: Claude has a `generate_scene_image` tool it may invoke when
the user explicitly asks for a visual. Tool results are streamed back
as a distinct SSE event type so the frontend can render images inline.
"""

import json
from anthropic import AsyncAnthropic

from . import sessions, images


_client = AsyncAnthropic()  # picks up ANTHROPIC_API_KEY from env (loaded by main.py)
MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 1024
MAX_TOOL_TURNS = 4  # cap on consecutive tool-use rounds per user message


# --- Tool definitions -------------------------------------------------------

TOOLS = [
    {
        "name": "generate_scene_image",
        "description": (
            "Generate ONE photorealistic image that visualizes the song's mood "
            "or a specific scene the user asked for. Only call this tool when "
            "the user EXPLICITLY asks to see, draw, render, paint, generate, "
            "or visualize an image. Never call it unprompted. Ground the "
            "imagery in the song's actual audio features (key, dynamics, "
            "timbre, BPM) — the user has already seen the metrics, so the "
            "image should feel like a believable visual translation of them.\n\n"
            "HARD CONSTRAINT: only natural scenes — landscapes, weather, "
            "skies, oceans, forests, mountains, deserts, rivers, plants, "
            "natural light, abstract natural textures. NEVER include people, "
            "human figures, faces, silhouettes, body parts, hands, or crowds. "
            "Avoid man-made structures (buildings, vehicles, instruments) "
            "unless they're a small distant element. If the user asks for a "
            "scene with people, translate it into a peopleless natural "
            "equivalent (e.g., 'a couple dancing' → 'two intertwined wisps "
            "of mist over a moonlit meadow')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": (
                        "A vivid, concrete visual description of the scene. "
                        "1-3 sentences. Use specific imagery (subject, setting, "
                        "lighting, mood) rather than abstractions."
                    ),
                },
                "style_hints": {
                    "type": "string",
                    "description": (
                        "Optional extra style direction beyond the default "
                        "photorealistic cinematic look (e.g., 'warm golden hour', "
                        "'cool blue night', 'high-contrast monochrome'). Omit if "
                        "the description already conveys the look."
                    ),
                },
            },
            "required": ["description"],
        },
    }
]


# --- System prompt ----------------------------------------------------------


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
        "Image tool:\n"
        "- You have a `generate_scene_image` tool that produces ONE photorealistic "
        "image. Use it ONLY when the user explicitly asks for a visual ('draw', "
        "'show me', 'paint', 'render', 'image of', 'what would this look like'). "
        "Never call it on your own initiative. After it returns, briefly describe "
        "in one sentence what you generated and why it fits the song — don't "
        "re-describe the image in detail; the user can see it.\n\n"
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


# --- SSE helpers ------------------------------------------------------------


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# --- Tool execution ---------------------------------------------------------


async def _run_tool(name: str, tool_input: dict) -> tuple[str, str | None, bool]:
    """Run a tool by name. Returns (text_for_claude, image_data_url_or_None, is_error)."""
    if name == "generate_scene_image":
        try:
            data_url = await images.generate_one(
                description=tool_input["description"],
                style_hints=tool_input.get("style_hints"),
            )
            return ("Image generated and shown to the user.", data_url, False)
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            return (f"Image generation failed: {err}", None, True)
    return (f"Unknown tool: {name}", None, True)


def _assistant_blocks_to_dicts(content) -> list[dict]:
    """Convert SDK content blocks into plain dicts for round-tripping in history."""
    out = []
    for block in content:
        if block.type == "text":
            out.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            out.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
        # Other block types ignored — we don't currently use them.
    return out


# --- Main streaming entrypoint ---------------------------------------------


async def stream_chat(session_id: str, message: str):
    """Async generator yielding SSE-formatted chunks for /chat."""
    s = sessions.get_session(session_id)
    if s is None:
        yield _sse({"type": "error", "content": "session not found"})
        return

    sessions.append_message(session_id, "user", message)
    system = _build_system_prompt(s["features"])

    try:
        for _turn in range(MAX_TOOL_TURNS):
            async with _client.messages.stream(
                model=MODEL,
                system=system,
                messages=s["history"],
                tools=TOOLS,
                max_tokens=MAX_TOKENS,
            ) as stream:
                async for text in stream.text_stream:
                    yield _sse({"type": "text", "content": text})
                final = await stream.get_final_message()

            # Persist this assistant turn (may include tool_use blocks).
            sessions.append_message(
                session_id, "assistant", _assistant_blocks_to_dicts(final.content)
            )

            if final.stop_reason != "tool_use":
                break

            # Run every tool_use block in this turn and collect tool_results.
            tool_results = []
            for block in final.content:
                if block.type != "tool_use":
                    continue
                yield _sse({"type": "tool_use", "content": block.name})
                text_for_claude, image_url, is_error = await _run_tool(
                    block.name, block.input
                )
                if image_url is not None:
                    yield _sse({"type": "image", "content": image_url})
                result_block = {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": text_for_claude,
                }
                if is_error:
                    result_block["is_error"] = True
                tool_results.append(result_block)

            # Feed the tool_results back as the next user turn.
            sessions.append_message(session_id, "user", tool_results)
        else:
            # Loop exited via for-else: hit MAX_TOOL_TURNS without end_turn.
            yield _sse({
                "type": "error",
                "content": f"tool-use loop exceeded {MAX_TOOL_TURNS} turns",
            })
            return
    except Exception as e:
        yield _sse({"type": "error", "content": f"{type(e).__name__}: {e}"})
        return

    yield _sse({"type": "done"})
