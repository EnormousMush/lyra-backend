"""
Shared audio loader. Adapted from musicdeepfake/Part 1/analysis_utils.py —
loading and HPSS only; plotting helpers dropped.
"""

import numpy as np
import librosa


def load_audio(audio_path: str, sr_target: int = 22050):
    """Load audio file mono. Returns (y, sr, duration, y_harmonic, y_percussive)."""
    y, sr = librosa.load(audio_path, sr=sr_target, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))
    y_harm, y_perc = librosa.effects.hpss(y, margin=4)
    return y, sr, duration, y_harm, y_perc
