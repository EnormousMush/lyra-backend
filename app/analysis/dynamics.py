"""
Dynamics & loudness analysis. Ported from musicdeepfake/Part 1/dynamics.py.
"""

import numpy as np
import librosa


def analyze(y, sr: int, duration: float, hop_length: int = 512) -> dict:
    """Compute dynamics metrics: RMS, crest factor, loudness arc, etc."""
    n_frames = 1 + len(y) // hop_length
    frame_times = librosa.frames_to_time(np.arange(n_frames), sr=sr, hop_length=hop_length)

    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]
    rms_db = 20 * np.log10(np.maximum(rms, 1e-9))

    # Rolling peak / RMS = crest factor
    peak_env = np.array([
        np.max(np.abs(y[max(0, i * hop_length - 1024): i * hop_length + 1024]))
        for i in range(len(rms))
    ])
    with np.errstate(divide="ignore", invalid="ignore"):
        crest = np.where(rms > 1e-6, peak_env / rms, 0.0)

    crest_valid = crest[crest > 0]
    rms_db_valid = rms_db[rms_db > -60]

    if len(rms_db_valid) == 0 or len(crest_valid) == 0:
        # Pathological silence — return zeros so we don't NaN the response
        return {
            "rms_mean_db":        0.0,
            "rms_std_db":         0.0,
            "dynamic_range_db":   0.0,
            "rms_range_db":       0.0,
            "rms_iqr_db":         0.0,
            "crest_mean":         0.0,
            "crest_std":          0.0,
            "crest_min":          0.0,
            "crest_below_2_pct":  0.0,
            "loudness_arc_slope": 0.0,
            "rms_autocorr_lag1":  0.0,
        }

    # Loudness arc: linear fit slope of RMS-dB over time
    n = min(len(frame_times), len(rms_db))
    ft_trim = frame_times[:n]
    rms_db_trim = rms_db[:n]
    valid_mask = rms_db_trim > -60
    if valid_mask.sum() > 2:
        slope, _ = np.polyfit(ft_trim[valid_mask], rms_db_trim[valid_mask], 1)
    else:
        slope = 0.0

    rms_centered = rms - np.mean(rms)
    if np.std(rms) > 1e-9 and len(rms) > 1:
        rms_autocorr = float(np.corrcoef(rms_centered[:-1], rms_centered[1:])[0, 1])
    else:
        rms_autocorr = 0.0

    return {
        "rms_mean_db":        round(float(np.mean(rms_db_valid)), 1),
        "rms_std_db":         round(float(np.std(rms_db_valid)), 2),
        "dynamic_range_db":   round(float(np.max(rms_db_valid) - np.min(rms_db_valid)), 1),
        "rms_range_db":       round(float(np.ptp(rms_db_valid)), 1),
        "rms_iqr_db":         round(float(
            np.percentile(rms_db_valid, 75) - np.percentile(rms_db_valid, 25)
        ), 2),
        "crest_mean":         round(float(np.mean(crest_valid)), 2),
        "crest_std":          round(float(np.std(crest_valid)), 2),
        "crest_min":          round(float(np.min(crest_valid)), 2),
        "crest_below_2_pct":  round(float(np.mean(crest_valid < 2.0) * 100), 1),
        "loudness_arc_slope": round(float(slope), 4),
        "rms_autocorr_lag1":  round(rms_autocorr, 4),
    }
