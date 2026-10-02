# Lyra Studio

Turn a song into images. Lyra measures a track with the feature pipeline from the
musicdeepfake humanness research, then Claude writes an art-direction brief for every
image and Gemini paints it: album covers, one scene per song section, and variations
you steer in plain words.

This is v3. The v2 chat version is preserved unchanged on the `main` branch.

## Run it

```bash
cp .env.example .env      # add ANTHROPIC_API_KEY and GEMINI_API_KEY
./dev.sh                  # API on :8000, web app on http://localhost:5173
```

`dev.sh` creates `.venv`, installs Python and Node dependencies on first run, and starts
both servers. Without keys, Lyra runs in preview mode: analysis is real, but the
listening notes and images are generated locally from templates and labelled as
previews in the UI.

Requirements: Python 3.12+ and Node 20+. ffmpeg is recommended for M4A and AAC files.

## What is in the app

| Page | What it does |
|---|---|
| Landing, sign up, sign in | Local accounts (scrypt hashes, httpOnly session cookie) |
| Library | Upload songs; each becomes a sleeve that takes on its first image |
| Studio | Waveform with section timeline, painting controls, results, and an analysis panel (Listening, Prompt DNA, Measurements) |
| Gallery | Every image, with a favourites filter |
| Atlas | The 10,750 Suno prompts as a controlled vocabulary; per-word audio signatures once the feature table is imported |
| Settings | Profile, password, AI service status, atlas status |

## How a song is processed

1. **Measure** (`app/analysis/`). The research feature families from
   `musicdeepfake/part2_analysis/features` are copied verbatim into
   `app/analysis/research/` and fed the same inputs as the research extraction:
   the middle 10 s (16 kHz, mono, LUFS -23), the middle 30 s, and the full file.
   The flattened output uses the research CSV column names.
2. **Sections** (`app/analysis/sections.py`). The full-track novelty method finds
   boundaries; segments are grouped by similarity and labelled.
3. **Prompt DNA** (`app/atlas.py`). With the atlas built, the song is matched against
   the nearest Suno songs in standardized feature space. Without it, Claude estimates
   the prompt using only words from the research vocabulary.
4. **Listen** (`app/director.py`). Claude turns the measurements into a visual
   identity: summary, palette, motifs, and evidence linking numbers to visuals.
5. **Direct and paint** (`app/director.py`, `app/images.py`). Claude writes one brief
   per image; `gemini-3.1-flash-image` renders it. Variations send the parent image
   as a reference.

Performance-texture measures (timing and pitch grid lock, tempo breathing) describe how
a performance feels. Lyra never presents them as evidence that a song was made by a
person or by AI.

## Importing the Suno feature table

```bash
python scripts/build_atlas.py --features path/to/featuresSuno10mid.csv \
    [--h2mid featuresH2mid.csv] [--h2full featuresH2full.csv]
```

Rows are joined to `app/data/suno/prompts.csv` by the job UUID inside `audio_id`
(non-Suno rows are ignored). This writes `app/data/atlas/atlas.json` and `index.npz`.
Restart the backend afterwards, then re-run analysis on existing songs to switch their
Prompt DNA from estimated to data-matched.

`prompts.csv` itself is rebuilt from the Part 1 manifests with
`scripts/build_prompt_table.py`.

## Layout

```
app/
  main.py            FastAPI app
  auth.py            accounts and sessions
  db.py              SQLite models (users, sessions, tracks, generations)
  jobs.py            background analysis and rendering
  director.py        Claude art direction (forced tool calls)
  images.py          Gemini rendering and the local preview renderer
  atlas.py           Suno vocabulary, atlas profiles, Prompt DNA
  analysis/          pipeline, catalog of surfaced features, sections
  analysis/research/ verbatim copy of the musicdeepfake feature families
  routes/            tracks, generations, system endpoints
  data/suno/         prompt table and word lists from musicdeepfake Part 1
web/                 React + Vite + Tailwind front end
scripts/             prompt table and atlas builders
storage/             local database, uploads and renders (gitignored)
```
