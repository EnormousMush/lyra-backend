"""
Rhythm & timing analysis. Ported from musicdeepfake/Part 1/rhythm.py;
plotting/CLI dropped, returns a dict of scalar stats only.
"""

import numpy as np
import librosa


def analyze(y, sr: int, duration: float, y_perc, hop_length: int = 512) -> dict:
    """Compute rhythm metrics. Inputs are pre-loaded audio (saves a librosa.load)."""
    # Beat tracking from percussive component
    tempo, beat_frames = librosa.beat.beat_track(y=y_perc, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Onsets
    onset_frames = librosa.onset.onset_detect(
        y=y_perc, sr=sr, units="frames",
        pre_max=3, post_max=3, pre_avg=3, post_avg=5, delta=0.06, wait=10,
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    onset_env = librosa.onset.onset_strength(y=y_perc, sr=sr, hop_length=hop_length)

    # Inter-beat intervals
    ibis = np.diff(beat_times) if len(beat_times) > 1 else np.array([0.0])
    ibi_mean = float(np.mean(ibis))
    ibi_std = float(np.std(ibis))
    ibi_cv = ibi_std / (ibi_mean + 1e-9)

    onset_density = len(onset_times) / (duration + 1e-9)

    os_mean = float(np.mean(onset_env))
    os_std = float(np.std(onset_env))

    onset_peak_vals = (
        onset_env[onset_frames[onset_frames < len(onset_env)]]
        if len(onset_frames) > 0 else np.array([0.0])
    )
    os_peak_std = float(np.std(onset_peak_vals))

    # Syncopation: fraction of onsets not within tolerance of a beat
    if len(beat_times) > 0 and len(onset_times) > 0:
        beat_tolerance = 0.5 * ibi_mean if ibi_mean > 0 else 0.1
        on_beat = sum(
            1 for ot in onset_times
            if np.min(np.abs(ot - beat_times)) <= beat_tolerance * 0.25
        )
        syncopation = 1.0 - (on_beat / len(onset_times))
    else:
        syncopation = 0.0

    # Tempo stability from windowed tempo
    if len(ibis) > 4:
        win = min(8, len(ibis))
        windowed_tempos = 60.0 / np.array([
            np.mean(ibis[i:i + win]) for i in range(len(ibis) - win + 1)
        ])
        tempo_stability = 1.0 - (
            float(np.std(windowed_tempos)) /
            (float(np.mean(windowed_tempos)) + 1e-9)
        )
    else:
        tempo_stability = 1.0

    # Groove consistency: autocorr of onset_env at the beat-period lag
    beat_period_frames = int(round(60.0 / (tempo + 1e-9) * sr / hop_length))
    if 0 < beat_period_frames < len(onset_env) // 2:
        oe_centered = onset_env - np.mean(onset_env)
        norm = np.sqrt(np.sum(oe_centered ** 2))
        if norm > 1e-9:
            groove_corr = float(np.sum(
                oe_centered[:-beat_period_frames] * oe_centered[beat_period_frames:]
            ) / (norm ** 2) * len(oe_centered))
        else:
            groove_corr = 0.0
    else:
        groove_corr = 0.0

    return {
        "tempo_bpm":           round(tempo, 1),
        "num_onsets":          int(len(onset_times)),
        "onset_density_per_s": round(onset_density, 2),
        "ibi_mean_s":          round(ibi_mean, 4),
        "ibi_std_s":           round(ibi_std, 4),
        "ibi_cv":              round(ibi_cv, 4),
        "beat_regularity":     round(1.0 - ibi_cv, 4),
        "onset_str_mean":      round(os_mean, 3),
        "onset_str_std":       round(os_std, 3),
        "onset_peak_std":      round(os_peak_std, 3),
        "syncopation_index":   round(syncopation, 4),
        "tempo_stability":     round(tempo_stability, 4),
        "groove_consistency":  round(groove_corr, 4),
    }
