"""
Timbral & tonal analysis. Ported from musicdeepfake/Part 1/timbral.py.
"""

import numpy as np
import librosa
from scipy.stats import entropy as sp_entropy


def analyze(y, sr: int, duration: float, y_harm, y_perc, hop_length: int = 512) -> dict:
    """Compute timbral metrics: ZCR, flatness, MFCC, chroma, H/P ratio."""
    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
    spec_flatness = librosa.feature.spectral_flatness(y=y, hop_length=hop_length)[0]
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20, hop_length=hop_length)
    chroma = librosa.feature.chroma_cqt(
        y=y_harm, sr=sr, bins_per_octave=24, hop_length=hop_length,
    )

    rms_harm = librosa.feature.rms(y=y_harm, frame_length=2048, hop_length=hop_length)[0]
    rms_perc = librosa.feature.rms(y=y_perc, frame_length=2048, hop_length=hop_length)[0]

    hp_ratio_mean = float(np.mean(rms_harm) / (np.mean(rms_perc) + 1e-9))

    # Trim to common length for correlations / per-frame stats
    n_zf = min(len(zcr), len(spec_flatness))
    zcr_t, flat_t = zcr[:n_zf], spec_flatness[:n_zf]
    zcr_flat_corr = float(np.corrcoef(zcr_t, flat_t)[0, 1]) if n_zf > 2 else 0.0

    mfcc_means = np.mean(mfcc, axis=1)
    mfcc_stds = np.std(mfcc, axis=1)
    mfcc_delta = librosa.feature.delta(mfcc)
    mfcc_delta_mean_abs = float(np.mean(np.abs(mfcc_delta)))

    # Chroma-derived harmony stats
    chroma_norm = chroma / (chroma.sum(axis=0, keepdims=True) + 1e-9)
    chroma_ent = np.array([
        sp_entropy(chroma_norm[:, i] + 1e-12) for i in range(chroma.shape[1])
    ])
    chroma_entropy_mean = float(np.mean(chroma_ent))

    active_pc = np.array([
        np.sum(chroma[:, i] > 0.2 * chroma[:, i].max())
        for i in range(chroma.shape[1])
    ])
    active_pc_mean = float(np.mean(active_pc))

    dominant_pc = np.argmax(chroma, axis=0)
    chord_change_rate = float(np.sum(np.diff(dominant_pc) != 0) / (duration + 1e-9))

    # H/P ratio per frame (for std/min/max)
    n_hp = min(len(rms_harm), len(rms_perc))
    rms_h_t, rms_p_t = rms_harm[:n_hp], rms_perc[:n_hp]
    with np.errstate(divide="ignore", invalid="ignore"):
        hp_per_frame = np.where(rms_p_t > 1e-9, rms_h_t / rms_p_t, 0.0)
    hp_valid = hp_per_frame[hp_per_frame > 0]

    return {
        "zcr_mean":             round(float(np.mean(zcr)), 4),
        "zcr_std":              round(float(np.std(zcr)), 4),
        "spec_flat_mean":       round(float(np.mean(spec_flatness)), 4),
        "spec_flat_std":        round(float(np.std(spec_flatness)), 4),
        "zcr_flat_corr":        round(zcr_flat_corr, 4),
        "harm_perc_ratio":      round(hp_ratio_mean, 3),
        "hp_ratio_std":         round(float(np.std(hp_valid)), 3) if len(hp_valid) else 0.0,
        "hp_ratio_min":         round(float(np.min(hp_valid)), 3) if len(hp_valid) else 0.0,
        "hp_ratio_max":         round(float(np.max(hp_valid)), 3) if len(hp_valid) else 0.0,
        "mfcc_means":           [round(float(m), 2) for m in mfcc_means],
        "mfcc_stds":            [round(float(s), 2) for s in mfcc_stds],
        "mfcc_delta_mean_abs":  round(mfcc_delta_mean_abs, 3),
        "chroma_entropy_mean":  round(chroma_entropy_mean, 4),
        "active_pc_per_frame":  round(active_pc_mean, 2),
        "chord_change_rate_hz": round(chord_change_rate, 3),
    }
