"""
images.py — Generate images from scene descriptions using Gemini 2.5 Flash Image
(a.k.a. "Nano Banana"). One image per scene, generated in parallel.
"""

import os
import base64
import asyncio

from google import genai


# Tweak this to shape the aesthetic of every generated image.
# Keep it consistent so the 4 scenes feel like a cohesive visual set.
STYLE_SUFFIX = (
    "Photorealistic, cinematic still, 35mm film, natural light, "
    "shallow depth of field, high detail, evocative composition, no text."
)


_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _build_prompt(scene: dict) -> str:
    description = scene.get("description", "").strip()
    colors = scene.get("colors", [])
    parts = [description]
    if colors:
        parts.append(f"Color palette: {', '.join(colors)}.")
    parts.append(STYLE_SUFFIX)
    return " ".join(parts)


async def _generate_one(scene: dict) -> str | None:
    prompt = _build_prompt(scene)
    response = await _client.aio.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
    )
    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) is not None:
            b64 = base64.b64encode(part.inline_data.data).decode("ascii")
            mime = part.inline_data.mime_type or "image/png"
            return f"data:{mime};base64,{b64}"
    return None


async def generate_images_for_scenes(scenes: list[dict]) -> list[str | None]:
    """Generate one image per scene, in parallel. Returns data-URL strings (or None on failure)."""
    return await asyncio.gather(
        *(_generate_one(s) for s in scenes),
        return_exceptions=False,
    )
