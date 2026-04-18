"""
audio.py — Extract musical features from an audio file using librosa.
Returns a structured dict of features that feed into the association engine.
"""

import librosa
import numpy as np
from pathlib import Path


def extract_features(file_path: str) -> dict:
    """
    Extract a rich set of audio features from a song file.
    
    Returns a dict with:
      - tempo, time_signature estimate
      - key, mode (major/minor)
      - energy (RMS), dynamics (loud vs quiet range)
      - spectral characteristics (brightness, warmth, roughness)
      - mood-adjacent descriptors derived from features
    """
    y, sr = librosa.load(file_path, sr=22050, duration=120)  # analyze first 2 min

    # ---- Rhythm ----
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])

    # ---- Key & Mode ----
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)
    key_idx = int(np.argmax(chroma_mean))
    key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    key = key_names[key_idx]

    # Major vs minor heuristic: compare major and minor profile correlations
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    
    # Rotate chroma to detected key
    rotated = np.roll(chroma_mean, -key_idx)
    major_corr = float(np.corrcoef(rotated, major_profile)[0, 1])
    minor_corr = float(np.corrcoef(rotated, minor_profile)[0, 1])
    mode = "major" if major_corr > minor_corr else "minor"

    # ---- Energy & Dynamics ----
    rms = librosa.feature.rms(y=y)[0]
    energy_mean = float(np.mean(rms))
    energy_std = float(np.std(rms))
    dynamic_range = float(np.max(rms) - np.min(rms))

    # ---- Spectral Features ----
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    brightness = float(np.mean(spectral_centroid))  # higher = brighter/sharper

    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    rolloff_mean = float(np.mean(spectral_rolloff))

    spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    contrast_mean = float(np.mean(spectral_contrast))

    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    bandwidth_mean = float(np.mean(spectral_bandwidth))

    # ---- Timbre (MFCCs) ----
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_means = [float(m) for m in np.mean(mfccs, axis=1)]

    # ---- Zero Crossing Rate (percussiveness / noisiness) ----
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    zcr_mean = float(np.mean(zcr))

    # ---- Onset Density (how "busy" the track feels) ----
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_density = float(np.mean(onset_env))

    # ---- Derive qualitative descriptors ----
    descriptors = _derive_descriptors(
        tempo, mode, energy_mean, brightness, dynamic_range, zcr_mean, onset_density
    )

    return {
        "tempo_bpm": round(tempo, 1),
        "key": key,
        "mode": mode,
        "energy": {
            "mean": round(energy_mean, 4),
            "std": round(energy_std, 4),
            "dynamic_range": round(dynamic_range, 4),
        },
        "spectral": {
            "brightness": round(brightness, 1),
            "rolloff_hz": round(rolloff_mean, 1),
            "contrast": round(contrast_mean, 2),
            "bandwidth": round(bandwidth_mean, 1),
        },
        "timbre_mfccs": [round(m, 2) for m in mfcc_means],
        "zero_crossing_rate": round(zcr_mean, 4),
        "onset_density": round(onset_density, 2),
        "descriptors": descriptors,
    }


def _derive_descriptors(
    tempo: float, mode: str, energy: float, brightness: float,
    dynamic_range: float, zcr: float, onset_density: float
) -> dict:
    """
    Translate numeric features into qualitative descriptors
    that help the LLM generate better associations.
    """
    # Tempo feel
    if tempo < 70:
        tempo_feel = "very slow, meditative"
    elif tempo < 100:
        tempo_feel = "slow, relaxed"
    elif tempo < 120:
        tempo_feel = "moderate, steady"
    elif tempo < 140:
        tempo_feel = "upbeat, driving"
    else:
        tempo_feel = "fast, intense, urgent"

    # Energy level
    if energy < 0.02:
        energy_feel = "very quiet, whisper-like"
    elif energy < 0.05:
        energy_feel = "soft, gentle"
    elif energy < 0.1:
        energy_feel = "moderate energy"
    elif energy < 0.2:
        energy_feel = "loud, powerful"
    else:
        energy_feel = "very loud, overwhelming"

    # Brightness
    if brightness < 1500:
        tone_feel = "dark, warm, muffled"
    elif brightness < 3000:
        tone_feel = "balanced, neutral warmth"
    elif brightness < 5000:
        tone_feel = "bright, clear"
    else:
        tone_feel = "very bright, sharp, piercing"

    # Dynamics
    if dynamic_range < 0.05:
        dynamics_feel = "flat, compressed, steady"
    elif dynamic_range < 0.15:
        dynamics_feel = "moderate dynamics"
    else:
        dynamics_feel = "wide dynamics, dramatic swells"

    # Texture
    if zcr > 0.1:
        texture = "noisy, textured, gritty"
    elif zcr > 0.05:
        texture = "moderate texture"
    else:
        texture = "smooth, clean, pure tones"

    # Density
    if onset_density < 2:
        density = "sparse, spacious"
    elif onset_density < 5:
        density = "moderate density"
    else:
        density = "dense, busy, layered"

    return {
        "tempo_feel": tempo_feel,
        "energy_feel": energy_feel,
        "tone": tone_feel,
        "dynamics": dynamics_feel,
        "texture": texture,
        "density": density,
        "modality": f"{mode} — {'brighter, hopeful, open' if mode == 'major' else 'darker, introspective, tense'}",
    }
