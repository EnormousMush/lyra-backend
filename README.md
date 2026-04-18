# Synesthesia

A platform that takes a song and outputs a series of vivid scenes and imagery that the music evokes — like a synesthetic experience engine.

## Architecture

```
synesthesia/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app & routes
│   ├── audio.py          # librosa feature extraction
│   ├── associations.py   # Claude API → scene descriptions
│   └── images.py         # Image generation (future)
├── static/               # Frontend assets
├── templates/            # HTML templates
├── requirements.txt
└── README.md
```

## Stack
- **Backend:** FastAPI + Python
- **Audio Analysis:** librosa
- **AI Associations:** Claude API (Anthropic)
- **Image Generation:** TBD (DALL·E / Stable Diffusion)
- **Frontend:** React (TBD)

## Setup
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
uvicorn app.main:app --reload
```
