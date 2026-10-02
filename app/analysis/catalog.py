"""Human-readable catalog of the features Lyra surfaces in the UI, the atlas and prompts.

Keys are research CSV column names (see analysis._flatten), so the same catalog
describes an uploaded track, the Suno atlas, and the kNN index.
"""

CATALOG = {
    # ---------------- rhythm & time ----------------
    "stats.tempo_bpm": dict(label="Tempo", unit="BPM", group="Rhythm", fmt=0,
                            explain="Beats per minute from the percussive layer."),
    "stats.onset_density_per_s": dict(label="Note density", unit="/s", group="Rhythm", fmt=2,
                                      explain="Percussive onsets per second; how busy the rhythm is."),
    "stats.syncopation_index": dict(label="Syncopation", unit="", group="Rhythm", fmt=2,
                                    explain="Share of onsets that land off the beat."),
    "stats.beat_regularity": dict(label="Beat regularity", unit="", group="Rhythm", fmt=3,
                                  explain="1 minus the variation of beat intervals; 1 is metronomic."),
    "stats.tempo_stability": dict(label="Tempo stability", unit="", group="Rhythm", fmt=3,
                                  explain="How little the local tempo moves inside the 10 s window."),
    # ---------------- performance texture (humanness line) ----------------
    "quantization_score": dict(label="Timing grid lock", unit="/100", group="Performance", fmt=1,
                               explain="How close onsets sit to a 16th-note grid. 100 is perfectly on grid."),
    "mean_dev_ms": dict(label="Timing deviation", unit="ms", group="Performance", fmt=1,
                        explain="Average distance of an onset from the nearest grid point."),
    "swing_pct": dict(label="Swing", unit="%", group="Performance", fmt=1,
                      explain="Where the off-beat lands inside the beat. 50 is straight, about 67 is triplet swing."),
    "pitch_quant_score": dict(label="Pitch grid lock", unit="/100", group="Performance", fmt=1,
                              explain="How close the melody sits to equal temperament after removing global tuning."),
    "pitch_jitter_cents": dict(label="Pitch micro-motion", unit="cents", group="Performance", fmt=1,
                               explain="Average frame-to-frame pitch movement; vibrato and drift raise it."),
    "drift_cv": dict(label="Tempo breathing (30 s)", unit="", group="Performance", fmt=3,
                     explain="Variation of the local tempo curve across the middle 30 s."),
    "gap_count": dict(label="Breathing gaps (30 s)", unit="", group="Performance", fmt=0,
                      explain="Short silences of 150 ms or more between phrases in the middle 30 s."),
    "chorus_copy_max": dict(label="Repeat exactness", unit="", group="Performance", fmt=3,
                            explain="Highest similarity between two 8 s passages at different times. Near 1 means near-identical repeats."),
    # ---------------- tone & space ----------------
    "stats.centroid_mean_hz": dict(label="Brightness", unit="Hz", group="Tone", fmt=0,
                                   explain="Spectral centroid; where the energy of the sound is centred."),
    "stats.hf_energy_ratio": dict(label="Air above 8 kHz", unit="", group="Tone", fmt=3,
                                  explain="Share of energy above 8 kHz."),
    "stats.bandwidth_mean_hz": dict(label="Spectral width", unit="Hz", group="Tone", fmt=0,
                                    explain="How spread the spectrum is around its centre."),
    "stats.spec_flat_mean": dict(label="Noisiness", unit="", group="Tone", fmt=3,
                                 explain="Spectral flatness. Higher is more noise-like, lower is more tonal."),
    "stats.harm_perc_ratio": dict(label="Melodic vs percussive", unit="x", group="Tone", fmt=2,
                                  explain="Harmonic energy divided by percussive energy."),
    "stats.mfcc_delta_mean_abs": dict(label="Timbre motion", unit="", group="Tone", fmt=3,
                                      explain="How quickly the timbre changes frame to frame."),
    "width_mean_db": dict(label="Stereo width", unit="dB", group="Tone", fmt=1,
                          explain="Side energy relative to mid energy across the whole track."),
    # ---------------- dynamics ----------------
    "stats.rms_mean_db": dict(label="Level", unit="dB", group="Dynamics", fmt=1,
                              explain="Average RMS level of the loudness-normalised window."),
    "stats.dynamic_range_db": dict(label="Dynamic range", unit="dB", group="Dynamics", fmt=1,
                                   explain="Spread between the loudest and quietest frames."),
    "stats.crest_mean": dict(label="Punch (crest)", unit="", group="Dynamics", fmt=2,
                             explain="Peak to RMS ratio. Low values mean heavy compression."),
    "arc_range_db": dict(label="Loudness arc (30 s)", unit="dB", group="Dynamics", fmt=1,
                         explain="Range of the smoothed loudness curve in the middle 30 s."),
    # ---------------- harmony & melody ----------------
    "stats.chord_change_rate_hz": dict(label="Harmonic motion", unit="/s", group="Harmony", fmt=2,
                                       explain="How often the dominant pitch class changes."),
    "stats.chroma_entropy_mean": dict(label="Harmonic spread", unit="", group="Harmony", fmt=3,
                                      explain="Entropy of the chroma vector; higher means denser harmony."),
    "note_rate_hz": dict(label="Melody note rate", unit="/s", group="Harmony", fmt=2,
                         explain="Melody notes per second from the pitch track."),
    "pitch_range_semi": dict(label="Melodic range", unit="st", group="Harmony", fmt=0,
                             explain="Distance between the lowest and highest melody note."),
    "scale_fit": dict(label="Scale fit", unit="", group="Harmony", fmt=3,
                      explain="Share of melody time inside the best-fitting major or minor scale."),
    "interval_bigram_rep": dict(label="Melodic repetition", unit="", group="Harmony", fmt=3,
                                explain="How often two-interval melodic shapes recur."),
}

GROUP_ORDER = ["Rhythm", "Performance", "Tone", "Dynamics", "Harmony"]

# Features used for the Suno kNN index and atlas profiles (must exist in the h1 CSV).
INDEX_FEATURES = [
    "stats.tempo_bpm", "stats.onset_density_per_s", "stats.syncopation_index",
    "stats.beat_regularity", "stats.tempo_stability", "quantization_score", "mean_dev_ms",
    "swing_pct", "stats.centroid_mean_hz", "stats.hf_energy_ratio", "stats.bandwidth_mean_hz",
    "stats.spec_flat_mean", "stats.harm_perc_ratio", "stats.mfcc_delta_mean_abs",
    "stats.rms_std_db", "stats.dynamic_range_db", "stats.crest_mean",
    "stats.chord_change_rate_hz", "stats.chroma_entropy_mean", "stats.zcr_mean",
    "pitch_quant_score", "pitch_jitter_cents", "note_rate_hz", "pitch_range_semi",
    "scale_fit", "interval_bigram_rep",
]


def readout(flat: dict) -> list[dict]:
    """Catalogued values of one track, in display order."""
    rows = []
    for group in GROUP_ORDER:
        for k, meta in CATALOG.items():
            if meta["group"] != group:
                continue
            v = flat.get(k)
            if isinstance(v, (int, float)):
                rows.append({"key": k, "value": v, **meta})
    return rows
