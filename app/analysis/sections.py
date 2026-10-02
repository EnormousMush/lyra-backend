"""Section timeline for the scene strip.

Boundary detection reuses the exact novelty method and parameters of the research
full-track family (research/families/fulltrack.py: chroma+MFCC cosine SSM at ~2 fps,
8 s checkerboard kernel, peaks with 8 s spacing and 0.1 prominence). The research
module only reports counts; this module keeps the boundaries, groups repeated
segments by similarity, and attaches a heuristic label plus per-section energy and
brightness so each section can get its own image.
"""
import numpy as np
import librosa
from scipy.signal import find_peaks
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

SR = 16000
HOP = 2048
AGG = 4
KERNEL_S = 8.0
SAME_GROUP = 0.45          # z-scored cosine similarity above which segments count as the same material
MAX_SECTIONS = 10


def _novelty_bounds(y):
    chroma = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
    mfcc = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=13, hop_length=HOP)
    F = np.vstack([chroma / (np.linalg.norm(chroma, axis=0, keepdims=True) + 1e-9),
                   mfcc / (np.linalg.norm(mfcc, axis=0, keepdims=True) + 1e-9)])
    n = F.shape[1] // AGG
    fps = SR / HOP / AGG
    if n < 30:
        return None, None, fps
    Fa = F[:, : n * AGG].reshape(F.shape[0], n, AGG).mean(axis=2)
    Fa = Fa / (np.linalg.norm(Fa, axis=0, keepdims=True) + 1e-9)
    S = Fa.T @ Fa
    k = max(4, int(round(KERNEL_S * fps)))
    nov = np.zeros(n)
    for i in range(k, n - k):
        a = S[i - k:i, i - k:i].mean()
        b = S[i:i + k, i:i + k].mean()
        c = S[i - k:i, i:i + k].mean()
        nov[i] = a + b - 2 * c
    nov = (nov - nov.min()) / (np.ptp(nov) + 1e-9)
    peaks, props = find_peaks(nov, distance=int(8 * fps), prominence=0.1)
    if len(peaks) > MAX_SECTIONS - 1:
        keep = np.argsort(props["prominences"])[::-1][: MAX_SECTIONS - 1]
        peaks = np.sort(peaks[keep])
    bounds = np.r_[0, peaks, n]
    return bounds, Fa, fps


def _group(Fa, bounds):
    """Assign letters A, B, C... so that similar segments share a letter.

    Each feature dimension is z-scored across the track first; raw cosine
    similarity between segment means is near 1 for everything in a song.
    Segments are then clustered with average linkage on cosine distance.
    """
    Z = (Fa - Fa.mean(axis=1, keepdims=True)) / (Fa.std(axis=1, keepdims=True) + 1e-9)
    means = []
    for s, e in zip(bounds[:-1], bounds[1:]):
        v = Z[:, s:e].mean(axis=1)
        means.append(v / (np.linalg.norm(v) + 1e-9))
    M = np.array(means)
    if len(M) < 2:
        return [0] * len(M)
    D = np.clip(1.0 - M @ M.T, 0.0, 2.0)
    np.fill_diagonal(D, 0.0)
    clusters = fcluster(linkage(squareform(D, checks=False), method="average"),
                        t=1.0 - SAME_GROUP, criterion="distance")
    order, letters = {}, []
    for c in clusters:
        order.setdefault(c, len(order))
        letters.append(order[c])
    return letters


def _label(letters, energies):
    n = len(letters)
    counts = {g: letters.count(g) for g in set(letters)}
    repeated = [g for g, c in counts.items() if c >= 2]
    chorus = None
    if repeated:
        chorus = max(repeated, key=lambda g: np.mean([energies[i] for i in range(n) if letters[i] == g]))
    labels = []
    for i, g in enumerate(letters):
        if g == chorus:
            labels.append("Chorus")
        elif i == 0 and counts[g] == 1 and n > 2:
            labels.append("Intro")
        elif i == n - 1 and counts[g] == 1 and n > 2:
            labels.append("Outro")
        elif counts[g] >= 2:
            labels.append("Verse")
        elif 0 < i < n - 1:
            labels.append("Bridge")
        else:
            labels.append("Section")
    return labels


def analyze_sections(y: np.ndarray) -> list[dict]:
    """y: mono float waveform at 16 kHz. Returns a list of section dicts in time order."""
    dur = len(y) / SR
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    db = 20 * np.log10(rms + 1e-8)
    cen = librosa.feature.spectral_centroid(y=y, sr=SR, hop_length=512)[0]
    t_frame = 512 / SR
    med_db = float(np.median(db))

    bounds, Fa, fps = _novelty_bounds(y) if dur >= 45 else (None, None, 0)
    if bounds is None:
        spans = [(0.0, dur)]
        letters = [0]
    else:
        times = bounds / fps
        times[-1] = dur
        spans = list(zip(times[:-1].tolist(), times[1:].tolist()))
        letters = _group(Fa, bounds)

    raw = []
    for (s, e) in spans:
        a, b = int(s / t_frame), max(int(s / t_frame) + 1, int(e / t_frame))
        seg_db = db[a:b]
        raw.append({
            "start": round(float(s), 2),
            "end": round(float(e), 2),
            "loudness_rel_db": round(float(np.mean(seg_db) - med_db), 2),
            "brightness_hz": round(float(np.mean(cen[a:b])), 1),
        })
    lo = min(r["loudness_rel_db"] for r in raw)
    hi = max(r["loudness_rel_db"] for r in raw)
    for r in raw:
        r["energy"] = round((r["loudness_rel_db"] - lo) / (hi - lo + 1e-9), 3) if len(raw) > 1 else 0.5
    labels = _label(letters, [r["energy"] for r in raw]) if len(raw) > 1 else ["Whole track"]
    for i, r in enumerate(raw):
        r["index"] = i
        r["group"] = "ABCDEFGHIJ"[letters[i] % 10]
        r["label"] = labels[i]
    return raw


def waveform_peaks(y: np.ndarray, n: int = 720) -> list[float]:
    if len(y) == 0:
        return [0.0] * n
    edges = np.linspace(0, len(y), n + 1).astype(int)
    peaks = np.array([np.max(np.abs(y[a:b])) if b > a else 0.0 for a, b in zip(edges[:-1], edges[1:])])
    peaks = peaks / (peaks.max() + 1e-9)
    return [round(float(p), 3) for p in peaks]
