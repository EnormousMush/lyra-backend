"""
images.py — Generate a single image from a scene description using
Gemini 2.5 Flash Image (a.k.a. "Nano Banana").

Exposed as a Claude tool from app/chat.py: Claude only invokes this
when the user explicitly asks for a visual.
"""

import os
import base64

from google import genai


# Tweak this to shape the aesthetic of every generated image.
STYLE_SUFFIX = (
    "Photorealistic natural landscape, cinematic still, 35mm film, natural light, "
    "shallow depth of field, high detail, evocative composition. "
    "No people, no human figures, no faces, no silhouettes, no body parts, "
    "no man-made structures except subtle distant ones if essential, no text."
)


_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


async def generate_one(description: str, style_hints: str | None = None) -> str:
    """Generate one image from a scene description.

    Returns a base64 data URL ('data:image/png;base64,...') suitable for
    embedding directly in HTML <img src=...> or sending over SSE.
    Raises RuntimeError if Gemini returned no image data.
    """
    parts = [description.strip()]
    if style_hints:
        parts.append(style_hints.strip())
    parts.append(STYLE_SUFFIX)
    prompt = " ".join(p for p in parts if p)

    response = await _client.aio.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
    )
    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) is not None:
            b64 = base64.b64encode(part.inline_data.data).decode("ascii")
            mime = part.inline_data.mime_type or "image/png"
            return f"data:{mime};base64,{b64}"
    raise RuntimeError("Gemini returned no image data")
