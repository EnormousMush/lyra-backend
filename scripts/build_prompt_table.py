"""Build app/data/suno/prompts.csv from the musicdeepfake Part 1 manifests.

Every Suno prompt in the humanness dataset follows one template:
    "{subgenre label}, {mood} atmosphere, featuring {descriptor}"
This script splits each prompt back into its controlled variables so the atlas
and Prompt DNA can treat every word as a labelled factor.

Usage:
    python scripts/build_prompt_table.py --manifests ../musicdeepfake/part1_extraction/manifests
"""
import argparse
import csv
import re
from pathlib import Path

PATTERN = re.compile(r"^(?P<label>.+?), (?P<mood>.+?) atmosphere, featuring (?P<descriptor>.+)$")
OUT = Path(__file__).resolve().parent.parent / "app" / "data" / "suno" / "prompts.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifests", required=True, help="musicdeepfake/part1_extraction/manifests")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    rows, skipped = [], 0
    for path in sorted(Path(args.manifests).glob("*_manifest.csv")):
        for r in csv.DictReader(open(path, newline="", encoding="utf-8")):
            if r.get("status") != "done":
                continue
            m = PATTERN.match(r["prompt"].strip())
            if not m:
                skipped += 1
                continue
            rows.append({
                "job_uid": r["job_uid"],
                "batch": path.stem.replace("_manifest", ""),
                "genre": r["genre"],
                "subgenre": r["subgenre"],
                "mood": m["mood"].strip(),
                "descriptor": m["descriptor"].strip(),
                "tags": r["tags"],
                "model": r["mv"],
                "prompt": r["prompt"],
            })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} prompt rows ({len(rows) * 2} songs) to {out}; skipped {skipped}")


if __name__ == "__main__":
    main()
