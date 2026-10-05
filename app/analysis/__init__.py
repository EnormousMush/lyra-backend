"""Lyra analysis pipeline, built on the musicdeepfake Part 2 feature families.

The research code under ./research is copied verbatim from
EnormousMush/musicdeepfake@87509ce (part2_analysis/features). Lyra feeds it
exactly the inputs the research extraction used, so an uploaded song lands in the
same feature space as the Suno corpus:

  h1 (10 s line)  middle 10 s of the track, 16 kHz mono, LUFS -23, then the
                  families resample to 22050 internally (same as featuresSuno10mid)
  h2_mid          middle 30 s, same canonical preprocessing (featuresH2mid)
  h2_full         the original file, up to 480 s (featuresH2full)

`flat` reproduces the research CSV column names (extract._flatten rules), which is
what the atlas and Prompt DNA match against.
"""
import math
import os
import tempfile
from typing import Callable

import ctypes
import gc

import numpy as np
import librosa
import soundfile as sf
import soxr

from .research.context import FeatureContext
from .research.preprocess import load_canonical
from .research.families import (spectral, timbral, dynamics, rhythm, quantize, key,
                                 melody, midwindow, fulltrack)
from .sections import analyze_sections, waveform_peaks, SR as SECTION_SR

# Same blacklist as research registry.SKIP_KEYS.
SKIP_KEYS = {"y", "sr", "S", "S_db", "mel_db", "times", "beat_times", "onset_times",
             "onset_env", "rms", "rms_db", "chroma", "mfcc", "contrast", "grid",
             "ibis", "duration", "hop_length", "frame_times", "oe_times",
             "times_samples", "spec_centroid", "spec_rolloff", "spec_bandwidth",
             "zcr", "spec_flatness", "rms_harm", "rms_perc", "crest"}

H1_FAMILIES = [  # (tag, name, fn, mode), registry order of h1_10s_v2
    ("spec", "spectral", spectral.run, "ctx"),
    ("timb", "timbral", timbral.run, "ctx"),
    ("dyn", "dynamics", dynamics.run, "ctx"),
    ("rhy", "rhythm", rhythm.run, "ctx"),
    ("qnt", "quantize", quantize.run, "ctx"),
    ("key", "key", key.run, "ctx"),
    ("mel", "melody", melody.run, "ctx"),
]

SPEC_10 = dict(sr=16000, mono=True, crop_s=10.0, loudness_lufs=-23.0)
SPEC_30 = dict(sr=16000, mono=True, crop_s=30.0, loudness_lufs=-23.0)


def _flatten(d, out, prefix=""):
    for k, v in d.items():
        if k in SKIP_KEYS:
            continue
        key_ = f"{prefix}{k}"
        if isinstance(v, dict):
            _flatten(v, out, key_ + ".")
        elif isinstance(v, (list, tuple, np.ndarray)):
            arr = np.asarray(v).ravel()
            if arr.dtype.kind in "fiu" and len(arr) <= 64:
                for i, x in enumerate(arr):
                    out[f"{key_}_{i:02d}"] = float(x)
        elif isinstance(v, (int, float, np.floating, np.integer)):
            out[key_] = float(v)
        elif isinstance(v, str) and len(v) < 60:
            out[key_] = v
    return out


def _scrub(obj):
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_scrub(x) for x in obj]
    if isinstance(obj, (np.floating,)):
        obj = float(obj)
    if isinstance(obj, (np.integer,)):
        obj = int(obj)
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def _unwrap(d: dict) -> dict:
    """Families that nest their numbers under 'stats' are shown flat in the UI."""
    return d["stats"] if set(d.keys()) == {"stats"} else d


FULL_SR = 16000
FULL_MAX_S = 480.0


def _load_full(path: str) -> tuple[np.ndarray, float]:
    """The whole song at 16 kHz, up to 480 s, channels kept, plus the file's duration.

    Equivalent to librosa.load(path, sr=16000, mono=False, duration=480) (verified
    bit-identical with soxr HQ), but decoded and resampled in 10 s blocks so the
    full-rate copy of the song never sits in memory. The one-shot load needed about
    200 MB per 4 minutes of stereo audio, which crashed a 512 MB server.
    """
    try:
        info = sf.info(path)
        duration = float(info.frames) / info.samplerate
        n_max = int(FULL_MAX_S * info.samplerate)
        rs = soxr.ResampleStream(info.samplerate, FULL_SR, info.channels, dtype="float32", quality="HQ")
        out, done = [], 0
        for blk in sf.blocks(path, blocksize=int(10 * info.samplerate), dtype="float32", always_2d=True):
            blk = blk[: max(0, n_max - done)]
            done += len(blk)
            out.append(rs.resample_chunk(blk, last=False))
            if done >= n_max:
                break
        out.append(rs.resample_chunk(np.zeros((0, info.channels), np.float32), last=True))
        y = np.ascontiguousarray(np.concatenate(out).T)
        return (y[0] if y.shape[0] == 1 else y), duration
    except Exception:
        # Formats libsndfile cannot read (m4a, aac) go through librosa's audioread path.
        duration = float(librosa.get_duration(path=path))
        return librosa.load(path, sr=FULL_SR, mono=False, duration=FULL_MAX_S)[0], duration


def _release_memory() -> None:
    """Hand freed memory back to the OS after a job so the server's footprint stays small."""
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


def _canonical_clip(path: str, spec: dict, duration: float, workdir: str, name: str) -> str:
    offset = max(0.0, (duration - spec["crop_s"]) / 2)
    y = load_canonical(path, dict(spec, offset_s=offset))
    out = os.path.join(workdir, name)
    sf.write(out, y, spec["sr"])
    return out


def analyze_track(path: str, on_stage: Callable[[str], None] = lambda s: None) -> dict:
    on_stage("decoding")
    try:
        return _analyze(path, on_stage)
    finally:
        _release_memory()


def _analyze(path: str, on_stage: Callable[[str], None]) -> dict:
    ys, duration = _load_full(path)
    result = {"duration_s": round(duration, 2)}
    errors, flat, families = {}, {}, {}

    with tempfile.TemporaryDirectory() as tmp:
        on_stage("features")
        clip10 = _canonical_clip(path, SPEC_10, duration, tmp, "mid10.wav")
        ctx = FeatureContext(clip10)
        for tag, name, fn, _mode in H1_FAMILIES:
            try:
                d = fn(ctx)
                if "error" in d:
                    errors[name] = d["error"]
                    continue
                d = {k: v for k, v in d.items() if not k.startswith("_")}
                _flatten(d, flat)
                families[name] = _unwrap(d)
            except Exception as e:  # one failing family must not sink the track
                errors[name] = repr(e)[:120]

        on_stage("structure")
        if duration >= 32:
            try:
                clip30 = _canonical_clip(path, SPEC_30, duration, tmp, "mid30.wav")
                d = midwindow.run(clip30)
                if "error" in d:
                    errors["midwindow"] = d["error"]
                else:
                    families["midwindow"] = d
                    _flatten(d, flat)
            except Exception as e:
                errors["midwindow"] = repr(e)[:120]
        else:
            errors["midwindow"] = "track shorter than the 30 s window"

    try:
        d = fulltrack.run(path, ys=ys)
        if "error" in d:
            errors["fulltrack"] = d["error"]
        families["fulltrack"] = d
        _flatten({k: v for k, v in d.items() if k != "error"}, flat)
    except Exception as e:
        errors["fulltrack"] = repr(e)[:120]

    y16 = ys if ys.ndim == 1 else ys.mean(axis=0)
    del ys
    sections = analyze_sections(y16)
    waveform = waveform_peaks(y16)

    result.update(families)
    result["errors"] = errors
    result["flat"] = flat
    result["spec"] = {
        "h1": "middle 10 s, 16 kHz mono, LUFS -23 (musicdeepfake suno10mid spec)",
        "h2_mid": "middle 30 s, 16 kHz mono, LUFS -23",
        "h2_full": "original file, up to 480 s",
    }
    return {
        "features": _scrub(result),
        "sections": _scrub(sections),
        "waveform": waveform,
        "duration_s": round(duration, 2),
    }
