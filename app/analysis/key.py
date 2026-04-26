"""
Key estimation via chroma + Krumhansl-Schmuckler profiles. Ported from
musicdeepfake/Part 1/key.py.

Note: original uses sr=11025 for chroma; we resample from the orchestrator's
sr=22050 audio rather than re-loading.
"""

import numpy as np
import librosa


_MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def analyze(y_harm, sr: int) -> dict:
    """Estimate primary musical key from a harmonic-only audio array."""
    # Original uses 11025 — downsample harmonic component to match
    if sr != 11025:
        y_harm = librosa.resample(y_harm, orig_sr=sr, target_sr=11025)
        sr = 11025

    chromograph = librosa.feature.chroma_cqt(y=y_harm, sr=sr, bins_per_octave=24)
    chroma_vals = [float(np.sum(chromograph[i])) for i in range(12)]
    keyfreqs = {_NOTE_NAMES[i]: chroma_vals[i] for i in range(12)}

    key_dict = {}
    for i in range(12):
        key_test = [keyfreqs[_NOTE_NAMES[(i + m) % 12]] for m in range(12)]
        maj_corr = round(float(np.corrcoef(_MAJOR_PROFILE, key_test)[1, 0]), 3)
        min_corr = round(float(np.corrcoef(_MINOR_PROFILE, key_test)[1, 0]), 3)
        key_dict[f"{_NOTE_NAMES[i]} major"] = maj_corr
        key_dict[f"{_NOTE_NAMES[i]} minor"] = min_corr

    best_key = max(key_dict, key=key_dict.get)
    best_corr = key_dict[best_key]

    alt_key, alt_corr = None, None
    for k, c in key_dict.items():
        if k != best_key and c > best_corr * 0.9:
            alt_key, alt_corr = k, c
            break

    return {
        "primary_key":    best_key,
        "primary_corr":   best_corr,
        "alternate_key":  alt_key,
        "alternate_corr": alt_corr,
    }
