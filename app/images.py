"""Image rendering: Gemini 3.1 Flash Image (Nano Banana 2), with a local preview renderer.

The preview renderer runs when no GEMINI_API_KEY is configured or LYRA_MOCK is set.
It paints an abstract composition from the art direction's palette, so the whole
app can be exercised offline without spending API credit. Previews are flagged
`mock` in the database and labelled in the UI.
"""
import asyncio
import hashlib
import io
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from . import config

SAFETY_SUFFIX = ("No text, no letters, no logos, no watermarks, no signatures. "
                 "Do not depict any real, identifiable person.")
NO_PEOPLE = "No people, no human figures, no faces, no silhouettes, no hands."

ASPECTS = {"1:1": (1, 1), "4:5": (4, 5), "3:2": (3, 2), "16:9": (16, 9), "9:16": (9, 16)}

_sem = asyncio.Semaphore(3)
_client = None


def _gemini():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def final_prompt(prompt: str, people_ok: bool) -> str:
    parts = [prompt.strip(), SAFETY_SUFFIX]
    if not people_ok:
        parts.append(NO_PEOPLE)
    return " ".join(parts)


async def render(prompt: str, aspect: str, out_stem: Path, palette: list[str] | None,
                 parent_image: Path | None = None, people_ok: bool = False) -> tuple[Path, bool]:
    """Render one image. Returns (path, is_mock)."""
    if not config.gemini_live():
        path = await asyncio.to_thread(_mock_render, prompt, aspect, out_stem, palette or [])
        return path, True

    from google.genai import types
    contents: list = []
    if parent_image is not None and parent_image.exists():
        mime = "image/png" if parent_image.suffix == ".png" else "image/jpeg"
        contents.append(types.Part.from_bytes(data=parent_image.read_bytes(), mime_type=mime))
    contents.append(final_prompt(prompt, people_ok))
    cfg = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio=aspect if aspect in ASPECTS else "1:1"),
    )
    async with _sem:
        resp = await _gemini().aio.models.generate_content(
            model=config.IMAGE_MODEL, contents=contents, config=cfg)
    for cand in resp.candidates or []:
        for part in (cand.content.parts if cand.content else []) or []:
            data = getattr(part, "inline_data", None)
            if data is not None and data.data:
                ext = ".png" if (data.mime_type or "").endswith("png") else ".jpg"
                path = out_stem.with_suffix(ext)
                path.write_bytes(data.data)
                return path, False
    reason = getattr(resp, "prompt_feedback", None)
    raise RuntimeError(f"The image model returned no image{f' ({reason})' if reason else ''}.")


# ---------------------------------------------------------------- preview renderer

def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    if len(c) != 6:
        return (120, 120, 140)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _mock_render(prompt: str, aspect: str, out_stem: Path, palette: list[str]) -> Path:
    wr, hr = ASPECTS.get(aspect, (1, 1))
    long_side = 1024
    w, h = (long_side, int(long_side * hr / wr)) if wr >= hr else (int(long_side * wr / hr), long_side)
    seed = int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16)
    rnd = random.Random(seed)
    cols = [_hex(c) for c in palette] or [(24, 22, 40), (90, 70, 140), (220, 150, 120), (250, 220, 180)]
    while len(cols) < 4:
        cols.append(cols[-1])

    img = Image.new("RGB", (w, h), cols[0])
    px = img.load()
    top, mid, bot = cols[0], cols[1], cols[2]
    horizon = rnd.uniform(0.45, 0.7)
    for y in range(h):
        t = y / h
        if t < horizon:
            u = t / horizon
            c = tuple(int(top[i] + (mid[i] - top[i]) * u) for i in range(3))
        else:
            u = (t - horizon) / (1 - horizon)
            c = tuple(int(mid[i] + (bot[i] - mid[i]) * u) for i in range(3))
        for x in range(w):
            px[x, y] = c

    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    for _ in range(rnd.randint(5, 9)):
        cx, cy = rnd.uniform(0, w), rnd.uniform(0, h * horizon * 1.2)
        r = rnd.uniform(0.08, 0.32) * max(w, h)
        col = cols[rnd.randint(1, len(cols) - 1)]
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (rnd.randint(60, 140),))
    glow = glow.filter(ImageFilter.GaussianBlur(max(w, h) * 0.06))
    img = Image.alpha_composite(img.convert("RGBA"), glow)

    ridge = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ridge)
    for layer in range(3):
        base = h * (horizon + 0.06 * layer)
        pts, x = [(0, h)], 0.0
        amp = h * rnd.uniform(0.03, 0.09)
        while x <= w:
            pts.append((x, base - amp * abs(rnd.gauss(0, 1))))
            x += w / rnd.randint(8, 18)
        pts += [(w, h)]
        shade = tuple(int(v * (0.55 - 0.12 * layer)) for v in cols[-1])
        d.polygon(pts, fill=shade + (170 + 25 * layer,))
    ridge = ridge.filter(ImageFilter.GaussianBlur(2 + layer))
    img = Image.alpha_composite(img, ridge).convert("RGB")

    noise = Image.effect_noise((w, h), 18).convert("L")
    img = Image.blend(img, Image.merge("RGB", (noise, noise, noise)), 0.05)

    path = out_stem.with_suffix(".png")
    img.save(path, optimize=True)
    return path
