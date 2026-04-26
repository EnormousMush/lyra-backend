"""
analysis — Music feature extraction pipeline.

Public API:
    extract_all_features(audio_path: str) -> dict

Loads audio once (with HPSS) and runs the four analysis modules,
returning a nested dict suitable for JSON and for prompting Claude.
"""

import math

from ._loader import load_audio
from . import rhythm, key, dynamics, timbral


def _scrub(obj):
    """Walk a nested dict/list and replace NaN/Inf floats with None.

    JSON has no representation for NaN or +/-Inf, so Python's json.dumps
    raises ValueError on them by default. Any analyzer can produce these
    on edge cases (silent segments, divide-by-zero in correlations, dB
    of zero-energy frames). Catching them at the boundary is more
    defensive than fixing every module individually.
    """
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_scrub(x) for x in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def extract_all_features(audio_path: str) -> dict:
    """Run all analysis modules. Returns a nested dict grouped by category."""
    y, sr, duration, y_harm, y_perc = load_audio(audio_path, sr_target=22050)

    raw = {
        "duration_s": round(duration, 2),
        "sample_rate": int(sr),
        "rhythm":   rhythm.analyze(y, sr, duration, y_perc),
        "key":      key.analyze(y_harm, sr),
        "dynamics": dynamics.analyze(y, sr, duration),
        "timbral":  timbral.analyze(y, sr, duration, y_harm, y_perc),
    }
    return _scrub(raw)
