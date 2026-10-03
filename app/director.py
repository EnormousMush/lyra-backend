"""Claude as Lyra's art director.

Claude never chats with the user here. It does two structured jobs, each forced
through a single tool call so the output is always valid JSON:

  listen()  reads the measured features once per track and writes the track's
            visual identity: summary, motifs, palette, evidence, and (when the
            Suno atlas index is not built yet) an estimated Prompt DNA chosen
            from the real Suno prompt vocabulary.
  direct()  turns that identity plus the user's controls into image briefs for
            covers, per-section scenes, or variations of an earlier image.

Without an ANTHROPIC_API_KEY (or with LYRA_MOCK) both fall back to deterministic
templates built from the same numbers, so the app still runs end to end.
"""
import json

from . import config
from .analysis.catalog import readout
from .atlas import compose_prompt, vocabulary

STYLES = {
    "cinematic": ("Cinematic still", "cinematic photograph, 35mm film still, natural light, shallow depth of field, evocative composition"),
    "analog": ("Analog film", "medium-format analog film photograph, visible grain, soft halation, slightly faded colour"),
    "painterly": ("Oil painting", "expressive oil painting on canvas, visible brushwork, layered pigment, painterly light"),
    "watercolor": ("Watercolor", "loose watercolour on cold-press paper, bleeding washes, generous white space"),
    "ink": ("Ink and paper", "sumi ink on rice paper, minimal confident brush strokes, wide negative space"),
    "abstract": ("Abstract field", "abstract composition of flowing colour fields, light and texture, no recognisable objects"),
    "graphic": ("Graphic poster", "bold graphic poster artwork, flat shapes, strong geometry, limited palette, no typography"),
    "dreamscape": ("Dreamscape", "surreal dreamlike landscape, impossible scale, soft volumetric light, quiet atmosphere"),
}

MODE_GUIDE = {
    "cover": "Album-cover concepts for the whole track. Each concept must be a distinct idea, not a reworded copy.",
    "scenes": "One image per listed section, in order, so the images read as a visual sequence of the song. "
              "Keep one consistent world across the set and let each image follow that section's energy and brightness.",
    "variation": "Variations of the parent image. Keep its subject and composition recognisable and change what the direction asks for. "
                 "The parent image is passed to the image model as a reference.",
}

_client = None


def _claude():
    global _client
    if _client is None:
        from anthropic import AsyncAnthropic
        _client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _numbers(features: dict, percentiles: dict) -> str:
    lines = []
    for r in readout(features.get("flat", {})):
        p = percentiles.get(r["key"])
        ptxt = f" (Suno percentile {p:.0f})" if p is not None else ""
        lines.append(f"- {r['label']} [{r['key']}]: {r['value']:.{r['fmt']}f}{r['unit']}{ptxt}")
    k = features.get("key") or {}
    if k.get("best_key"):
        lines.append(f"- Key: {k['best_key']} (correlation {k.get('best_corr')})")
    lines.append(f"- Duration: {features.get('duration_s')} s")
    return "\n".join(lines)


def _sections_text(sections: list) -> str:
    return "\n".join(
        f"- #{s['index']} {s['label']} ({s['group']}) {s['start']:.0f}-{s['end']:.0f}s, "
        f"energy {s['energy']:.2f}, brightness {s['brightness_hz']:.0f} Hz"
        for s in sections)


async def _call_tool(system: str, user: str, tool: dict, max_tokens: int = 2500) -> dict:
    resp = await _claude().messages.create(
        model=config.CLAUDE_MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
        tools=[tool], tool_choice={"type": "tool", "name": tool["name"]},
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Claude did not return structured output.")


# ------------------------------------------------------------------ listen

LISTEN_TOOL = {
    "name": "submit_listening",
    "description": "Submit the visual identity of the track.",
    "input_schema": {
        "type": "object",
        "properties": {
            "headline": {"type": "string", "description": "3 to 6 word evocative name for the track's visual world."},
            "summary": {"type": "string", "description": "Two plain sentences on what the track sounds like, grounded in the numbers."},
            "motifs": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5,
                       "description": "Short concrete visual motifs (2 to 5 words each)."},
            "palette": {"type": "array", "minItems": 5, "maxItems": 5, "items": {
                "type": "object", "properties": {"hex": {"type": "string"}, "name": {"type": "string"}},
                "required": ["hex", "name"]}},
            "evidence": {"type": "array", "minItems": 3, "maxItems": 4, "items": {
                "type": "object", "properties": {
                    "feature": {"type": "string", "description": "feature key from the list, e.g. stats.centroid_mean_hz"},
                    "observation": {"type": "string", "description": "one sentence: the measured fact and what it suggests visually"}},
                "required": ["feature", "observation"]}},
            "dna": {"type": "object", "description": "Only when asked to estimate Prompt DNA.", "properties": {
                "genre": {"type": "string"}, "subgenre": {"type": "string"},
                "moods": {"type": "array", "items": {"type": "object", "properties": {
                    "value": {"type": "string"}, "share": {"type": "number"}}, "required": ["value", "share"]},
                    "minItems": 1, "maxItems": 3},
                "descriptor": {"type": "string"}, "confidence": {"type": "number"},
                "reasoning": {"type": "string"}},
                "required": ["genre", "subgenre", "moods", "descriptor", "confidence", "reasoning"]},
        },
        "required": ["headline", "summary", "motifs", "palette", "evidence"],
    },
}

LISTEN_SYSTEM = (
    "You are the art director of Lyra, a studio that turns music into images. You cannot hear the "
    "track. You receive measurements from a research-grade audio feature pipeline and must translate "
    "them into a visual identity. Ground every claim in the numbers you are given and never invent "
    "measurements (instruments, lyrics, vocals, era) that the numbers do not support. Percentiles, "
    "when present, compare the track with the Suno songs from the research corpus that have measured "
    "features. The performance-texture measures "
    "(timing and pitch grid lock, tempo breathing) describe the feel of a performance; do not use "
    "them to claim whether a track was made by a person or by AI."
)


async def listen(features: dict, sections: list, percentiles: dict, data_dna: dict | None) -> dict:
    if not config.claude_live():
        return _mock_listen(features, data_dna)

    estimate = data_dna is None
    parts = [f"Measurements:\n{_numbers(features, percentiles)}",
             f"Sections:\n{_sections_text(sections)}"]
    if estimate:
        voc = vocabulary()
        parts.append(
            "Also estimate the Prompt DNA: if someone wanted Suno to produce a track like this, which "
            "words from the research prompt vocabulary would they use? The template is "
            "'{subgenre} {genre}, {mood} atmosphere, featuring {descriptor}'. Choose ONLY values that "
            "appear below, keep subgenre and descriptor consistent with the chosen genre, give up to "
            "three moods with shares summing to 1, and a confidence between 0 and 1.\n"
            f"Moods: {', '.join(v['value'] for v in voc['mood'])}\n"
            "Per genre (subgenres | descriptors):\n" + "\n".join(
                f"{g}: {', '.join(d['subgenres'])} | {'; '.join(d['descriptors'])}"
                for g, d in voc["by_genre"].items()))
    else:
        top = {f: data_dna["factors"][f][0]["value"] for f in data_dna["factors"]}
        parts.append(f"The nearest Suno prompts in feature space suggest: {data_dna['prompt']} "
                     f"(factors {json.dumps(top)}). Use this as context. Do not return a dna field.")
    out = await _call_tool(LISTEN_SYSTEM, "\n\n".join(parts), LISTEN_TOOL)
    if estimate and out.get("dna"):
        d = out["dna"]
        out["dna"] = {
            "source": "estimate",
            "factors": {
                "genre": [{"value": d["genre"], "share": round(float(d.get("confidence", 0.5)), 3)}],
                "subgenre": [{"value": d["subgenre"], "share": round(float(d.get("confidence", 0.5)), 3)}],
                "mood": [{"value": m["value"], "share": round(float(m["share"]), 3)} for m in d["moods"]],
                "descriptor": [{"value": d["descriptor"], "share": round(float(d.get("confidence", 0.5)), 3)}],
            },
            "prompt": compose_prompt(d["genre"], d["subgenre"], d["moods"][0]["value"], d["descriptor"]),
            "prompt_parts": {"genre": d["genre"], "subgenre": d["subgenre"],
                             "mood": d["moods"][0]["value"], "descriptor": d["descriptor"]},
            "confidence": round(float(d.get("confidence", 0.5)), 3),
            "reasoning": d.get("reasoning", ""),
            "nearest_prompts": [],
        }
    return out


def _mock_listen(features: dict, data_dna: dict | None) -> dict:
    flat = features.get("flat", {})
    bright = flat.get("stats.centroid_mean_hz", 1800)
    tempo = flat.get("stats.tempo_bpm", 100)
    minor = "minor" in str((features.get("key") or {}).get("best_key", ""))
    warm = bright < 1700
    palette = ([("#1d1a2f", "night ink"), ("#3f3466", "dusk violet"), ("#b86b5e", "ember clay"),
                ("#e7b07a", "amber"), ("#f4e6d0", "paper")] if warm else
               [("#0e1b2a", "deep harbour"), ("#1f4e6b", "cold teal"), ("#5fa3b8", "glacier"),
                ("#d6e7ea", "frost"), ("#f2c46b", "signal gold")])
    dna = data_dna
    if dna is None:
        voc = vocabulary()["by_genre"]
        genre = "jazz" if tempo < 105 else "electronic"
        g = voc.get(genre) or next(iter(voc.values()))
        mood = "melancholic" if minor else "nostalgic"
        dna = {"source": "estimate", "confidence": 0.3, "nearest_prompts": [],
               "reasoning": "Preview mode: a template guess from tempo and key, not a Claude estimate.",
               "factors": {"genre": [{"value": genre, "share": 0.3}],
                           "subgenre": [{"value": g["subgenres"][0], "share": 0.3}],
                           "mood": [{"value": mood, "share": 1.0}],
                           "descriptor": [{"value": g["descriptors"][0], "share": 0.3}]},
               "prompt": compose_prompt(genre, g["subgenres"][0], mood, g["descriptors"][0]),
               "prompt_parts": {"genre": genre, "subgenre": g["subgenres"][0], "mood": mood,
                                "descriptor": g["descriptors"][0]}}
    return {
        "headline": "Low light, slow tide" if warm else "Cold air, clear signal",
        "summary": (f"A {'darker, warmer' if warm else 'brighter, cooler'} track around {tempo:.0f} BPM. "
                    "This is a preview description generated from templates because no Claude key is configured."),
        "motifs": ["long horizon", "slow drifting light", "soft haze", "single point of colour"],
        "palette": [{"hex": h, "name": n} for h, n in palette],
        "evidence": [
            {"feature": "stats.centroid_mean_hz", "observation": f"Brightness of {bright:.0f} Hz suggests {'warm, low light' if warm else 'clear, cool light'}."},
            {"feature": "stats.tempo_bpm", "observation": f"A tempo of {tempo:.0f} BPM sets the pace of motion in the frame."},
            {"feature": "quantization_score", "observation": "Timing grid lock shapes how rigid or loose the composition feels."},
        ],
        "dna": dna if data_dna is None else None,
        "mock": True,
    }


# ------------------------------------------------------------------ direct

DIRECT_TOOL = {
    "name": "submit_briefs",
    "description": "Submit one image brief per requested image, in order.",
    "input_schema": {
        "type": "object",
        "properties": {"briefs": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "2 to 5 word title for the image."},
                "prompt": {"type": "string", "description": "Complete prompt for the image model, 60 to 120 words: subject, setting, light, composition, colour, and the style direction."},
                "rationale": {"type": "string", "description": "One sentence linking the image to specific measurements."},
                "palette": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5,
                            "description": "Hex colours used in the image."},
            },
            "required": ["title", "prompt", "rationale", "palette"]}}},
        "required": ["briefs"],
    },
}


async def direct(*, features: dict, listening: dict, sections: list, percentiles: dict,
                 mode: str, style: str, count: int, direction: str | None,
                 targets: list, parent: dict | None, people_ok: bool) -> list[dict]:
    style_label, style_text = STYLES.get(style, STYLES["cinematic"])
    if not config.claude_live():
        return _mock_direct(listening, mode, style_text, count, targets, parent, direction)

    user = [
        f"Track identity: {listening.get('headline')}. {listening.get('summary')}",
        f"Motifs: {', '.join(listening.get('motifs', []))}",
        f"Palette: {', '.join(p['hex'] + ' ' + p['name'] for p in listening.get('palette', []))}",
        f"Measurements:\n{_numbers(features, percentiles)}",
        f"Task: {MODE_GUIDE[mode]}",
        f"Style: {style_label}, rendered as: {style_text}. Write the style into every prompt.",
        "People: allowed, but never real or identifiable people." if people_ok else
        "People: none. Express any human idea through landscape, objects, light or abstraction.",
        "Never ask for text, letters or logos in the image.",
    ]
    if mode == "scenes":
        user.append(f"Sections to illustrate (one brief each, same order):\n{_sections_text(targets)}")
        n = len(targets)
    else:
        n = count
    if parent:
        user.append(f"Parent image prompt: {parent['prompt']}")
    if direction:
        user.append(f"The user's direction (follow it): {direction}")
    user.append(f"Return exactly {n} briefs.")
    out = await _call_tool(
        "You are the art director of Lyra. You write precise prompts for an image model so that each "
        "image is a believable visual translation of the measured music.",
        "\n\n".join(user), DIRECT_TOOL, max_tokens=4000)
    briefs = out.get("briefs", [])[:n]
    if len(briefs) < n:
        raise RuntimeError(f"Claude returned {len(briefs)} briefs for {n} images.")
    return briefs


def _mock_direct(listening, mode, style_text, count, targets, parent, direction):
    pal = [p["hex"] for p in listening.get("palette", [])]
    motifs = listening.get("motifs") or ["horizon"]
    base = parent["prompt"] if parent else None
    briefs = []
    n = len(targets) if mode == "scenes" else count
    for i in range(n):
        motif = motifs[i % len(motifs)]
        if mode == "scenes":
            s = targets[i]
            title = motif.title()
            mood = "quiet, sparse" if s["energy"] < 0.35 else "swelling, luminous" if s["energy"] < 0.75 else "full, blazing"
            prompt = f"{motif}, {mood} scene for the {s['label'].lower()}, {style_text}"
        elif base:
            title = f"Variation {i + 1}"
            prompt = f"{base} Variation {i + 1}. {direction or 'shift the light and framing'}."
        else:
            title = motif.title()
            prompt = f"{motif}, {listening.get('headline', '')}, {style_text}"
        briefs.append({"title": title, "prompt": prompt,
                       "rationale": "Preview brief built from templates (no Claude key configured).",
                       "palette": pal[i % 2:] + pal[: i % 2]})
    return briefs
