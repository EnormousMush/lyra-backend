"""Suno prompt atlas and Prompt DNA.

Two layers:
  vocabulary  always available. The 10,750 Suno prompts from musicdeepfake Part 1
              (21,500 songs), split into genre / subgenre / mood / descriptor.
  profiles    available after scripts/build_atlas.py has joined those prompts with
              the research feature table. Adds per-word audio signatures, corpus
              percentiles, and a kNN index used to infer an uploaded song's
              Prompt DNA from data instead of from Claude's judgement.
"""
import csv
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

import numpy as np

from .config import BUNDLED

PROMPTS_CSV = BUNDLED / "suno" / "prompts.csv"
ATLAS_DIR = BUNDLED / "atlas"
FACTORS = ["genre", "subgenre", "mood", "descriptor"]


@lru_cache(maxsize=1)
def prompt_rows() -> list[dict]:
    with open(PROMPTS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def vocabulary() -> dict:
    rows = prompt_rows()
    out = {}
    for fac in FACTORS:
        c = Counter(r[fac] for r in rows)
        out[fac] = [{"value": v, "prompts": n, "songs": 2 * n} for v, n in c.most_common()]
    by_genre = {}
    for r in rows:
        g = by_genre.setdefault(r["genre"], {"subgenres": set(), "moods": set(), "descriptors": set()})
        g["subgenres"].add(r["subgenre"])
        g["moods"].add(r["mood"])
        g["descriptors"].add(r["descriptor"])
    out["by_genre"] = {g: {k: sorted(v) for k, v in d.items()} for g, d in by_genre.items()}
    out["totals"] = {"prompts": len(rows), "unique_prompts": len({r["prompt"] for r in rows}),
                     "songs": 2 * len(rows)}
    return out


@lru_cache(maxsize=1)
def _profiles():
    p = ATLAS_DIR / "atlas.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


@lru_cache(maxsize=1)
def _index():
    p = ATLAS_DIR / "index.npz"
    if not p.exists():
        return None
    z = np.load(p, allow_pickle=False)
    return {k: z[k] for k in z.files}


def reload() -> None:
    _profiles.cache_clear()
    _index.cache_clear()


def status() -> dict:
    prof = _profiles()
    return {
        "profiles_ready": prof is not None,
        "n_songs_with_features": prof["meta"]["n_songs"] if prof else 0,
        "built_at": prof["meta"].get("built_at") if prof else None,
        "source_csv": prof["meta"].get("source") if prof else None,
    }


def atlas_payload() -> dict:
    return {"status": status(), "vocabulary": vocabulary(), "profiles": _profiles()}


def percentiles(flat: dict) -> dict:
    """Where an uploaded track sits in the Suno corpus, per catalogued feature (0-100)."""
    prof = _profiles()
    if not prof:
        return {}
    out = {}
    for k, qs in prof["quantiles"].items():
        v = flat.get(k)
        if isinstance(v, (int, float)):
            out[k] = round(float(np.searchsorted(np.asarray(qs), v) / (len(qs) - 1) * 100), 1)
    return out


def data_dna(flat: dict, k: int = 60) -> dict | None:
    """Infer prompt factors from the nearest Suno songs in standardized feature space."""
    idx = _index()
    if idx is None:
        return None
    feats = [str(f) for f in idx["features"]]
    center, scale = idx["center"], idx["scale"]
    x = np.array([flat.get(f, np.nan) if isinstance(flat.get(f), (int, float)) else np.nan
                  for f in feats], dtype=float)
    x = (x - center) / scale
    present = np.isfinite(x)
    if present.sum() < len(feats) // 2:
        return None
    X = idx["X"][:, present]
    d = np.sqrt(((X - x[present]) ** 2).mean(axis=1))
    nn = np.argsort(d)[:k]
    w = 1.0 / (d[nn] + 0.25)
    rows = prompt_rows()
    job_of = idx["job_row"][nn]
    out = {"source": "data", "k": int(k), "pool": int(len(X)), "features_used": int(present.sum()), "factors": {}}
    for fac in FACTORS:
        tally = Counter()
        for row_i, wi in zip(job_of, w):
            tally[rows[int(row_i)][fac]] += float(wi)
        tot = sum(tally.values())
        out["factors"][fac] = [{"value": v, "share": round(s / tot, 3)} for v, s in tally.most_common(3)]
    seen, examples = set(), []
    for row_i, di in zip(job_of, d[nn]):
        r = rows[int(row_i)]
        if r["prompt"] in seen:
            continue
        seen.add(r["prompt"])
        examples.append({"prompt": r["prompt"], "genre": r["genre"], "distance": round(float(di), 3)})
        if len(examples) == 5:
            break
    out["nearest_prompts"] = examples
    # Compose the headline prompt inside the winning genre, so subgenre and descriptor
    # never come from different genres' word lists.
    g_top = out["factors"]["genre"][0]["value"]
    pick = {}
    for fac in ("subgenre", "mood", "descriptor"):
        tally = Counter()
        for row_i, wi in zip(job_of, w):
            r = rows[int(row_i)]
            if r["genre"] == g_top:
                tally[r[fac]] += float(wi)
        pick[fac] = tally.most_common(1)[0][0]
    out["prompt"] = compose_prompt(g_top, pick["subgenre"], pick["mood"], pick["descriptor"])
    prof = _profiles()
    out["reliability"] = (prof or {}).get("meta", {}).get("reliability", {})
    out["prompt_parts"] = {"genre": g_top, **pick}
    out["confidence"] = round(float(np.mean([out["factors"][f][0]["share"] for f in FACTORS])), 3)
    return out


def compose_prompt(genre: str, subgenre: str, mood: str, descriptor: str) -> str:
    """Same template as musicdeepfake part1_extraction/prompts._build_prompt."""
    norm = lambda s: s.lower().replace("-", "").replace(" ", "")  # noqa: E731
    already_named = norm(genre) in norm(subgenre)
    label = subgenre if already_named else f"{subgenre} {genre}"
    return f"{label}, {mood} atmosphere, featuring {descriptor}"
