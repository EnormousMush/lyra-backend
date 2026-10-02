"""Build the Suno prompt atlas from the humanness feature table.

Joins the research feature CSV (one row per Suno clip, audio_id like
suno_<job_uid>_<slot>) with app/data/suno/prompts.csv, then writes:

  app/data/atlas/atlas.json   per-word audio signatures, corpus quantiles
  app/data/atlas/index.npz    standardized kNN index used for Prompt DNA

Usage:
    python scripts/build_atlas.py --features path/to/featuresSuno10mid.csv \
        [--h2mid featuresH2mid.csv] [--h2full featuresH2full.csv]

Rows whose audio_id has no matching job_uid (FMA, Jamendo, ...) are ignored, so
mixed-source CSVs are fine. Restart the backend (or POST /api/atlas/reload)
afterwards.
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.analysis.catalog import CATALOG, INDEX_FEATURES  # noqa: E402

PROMPTS = ROOT / "app" / "data" / "suno" / "prompts.csv"
OUT = ROOT / "app" / "data" / "atlas"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
FACTORS = ["genre", "subgenre", "mood", "descriptor"]


def _num(v):
    try:
        x = float(v)
        return x if np.isfinite(x) else np.nan
    except (TypeError, ValueError):
        return np.nan


def _read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True, help="h1 10 s feature CSV (featuresSuno10mid or similar)")
    ap.add_argument("--h2mid", help="optional 30 s mid-window CSV")
    ap.add_argument("--h2full", help="optional full-track CSV")
    ap.add_argument("--min-n", type=int, default=20, help="minimum songs for a word profile")
    ap.add_argument("--out", default=str(OUT), help="output folder (default app/data/atlas)")
    args = ap.parse_args()

    prompts = _read(PROMPTS)
    job_row = {r["job_uid"]: i for i, r in enumerate(prompts)}

    merged = {}
    for path in [args.features, args.h2mid, args.h2full]:
        if not path:
            continue
        for r in _read(path):
            m = UUID.search(r.get("audio_id", ""))
            if not m or m.group(0) not in job_row:
                continue
            merged.setdefault(r["audio_id"], {"_job": job_row[m.group(0)]}).update(r)
    rows = list(merged.values())
    if not rows:
        sys.exit("No rows matched the Suno prompt table. Check the audio_id column.")

    keys = [k for k in CATALOG if any(k in r for r in rows)]
    idx_keys = [k for k in INDEX_FEATURES if any(k in r for r in rows)]
    missing = sorted(set(INDEX_FEATURES) - set(idx_keys))
    print(f"{len(rows)} Suno songs matched; {len(keys)} catalogued features; "
          f"{len(idx_keys)} index features" + (f" (missing: {missing})" if missing else ""))

    V = {k: np.array([_num(r.get(k)) for r in rows]) for k in keys}
    jobs = np.array([r["_job"] for r in rows])

    quantiles, glob = {}, {}
    for k, v in V.items():
        f = v[np.isfinite(v)]
        if len(f) < 50:
            continue
        quantiles[k] = [round(float(q), 5) for q in np.quantile(f, np.linspace(0, 1, 101))]
        glob[k] = {"mean": float(f.mean()), "std": float(f.std()), "median": float(np.median(f))}

    profiles = {}
    for fac in FACTORS:
        labels = np.array([prompts[j][fac] for j in jobs])
        prof = {}
        for val in sorted(set(labels)):
            mask = labels == val
            if mask.sum() < args.min_n:
                continue
            entry = {"n": int(mask.sum()), "means": {}, "d": {}}
            for k in quantiles:
                a, b = V[k][mask], V[k][~mask]
                a, b = a[np.isfinite(a)], b[np.isfinite(b)]
                if len(a) < 5 or len(b) < 5:
                    continue
                pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2) + 1e-12
                entry["means"][k] = round(float(a.mean()), 5)
                entry["d"][k] = round(float((a.mean() - b.mean()) / pooled), 3)
            entry["top"] = [{"key": k, "d": d} for k, d in
                            sorted(entry["d"].items(), key=lambda kv: -abs(kv[1]))[:6]]
            prof[val] = entry
        profiles[fac] = prof

    X = np.column_stack([V[k] for k in idx_keys])
    center = np.nanmedian(X, axis=0)
    iqr = np.nanpercentile(X, 75, axis=0) - np.nanpercentile(X, 25, axis=0)
    scale = np.where(iqr > 1e-9, iqr / 1.349, 1.0)
    Xs = (X - center) / scale
    keep = np.isfinite(Xs).all(axis=1)
    print(f"kNN index: {keep.sum()} complete rows of {len(Xs)}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "index.npz", X=Xs[keep].astype(np.float32), center=center,
                        scale=scale, features=np.array(idx_keys), job_row=jobs[keep].astype(np.int32))
    meta = {"n_songs": len(rows), "n_index": int(keep.sum()),
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": Path(args.features).name}
    feats = [{"key": k, **{m: CATALOG[k][m] for m in ("label", "unit", "group", "fmt", "explain")}}
             for k in quantiles]
    (out / "atlas.json").write_text(json.dumps(
        {"meta": meta, "features": feats, "quantiles": quantiles, "global": glob, "profiles": profiles}))
    print(f"wrote {out / 'atlas.json'} and {out / 'index.npz'}")


if __name__ == "__main__":
    main()
