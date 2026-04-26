"""
analysis — Music feature extraction pipeline.

Public API:
    extract_all_features(audio_path: str) -> dict

Loads audio once (with HPSS) and runs the four analysis modules,
returning a nested dict suitable for JSON and for prompting Claude.
"""

from ._loader import load_audio
from . import rhythm, key, dynamics, timbral


def extract_all_features(audio_path: str) -> dict:
    """Run all analysis modules. Returns a nested dict grouped by category."""
    y, sr, duration, y_harm, y_perc = load_audio(audio_path, sr_target=22050)

    return {
        "duration_s": round(duration, 2),
        "sample_rate": int(sr),
        "rhythm":   rhythm.analyze(y, sr, duration, y_perc),
        "key":      key.analyze(y_harm, sr),
        "dynamics": dynamics.analyze(y, sr, duration),
        "timbral":  timbral.analyze(y, sr, duration, y_harm, y_perc),
    }
