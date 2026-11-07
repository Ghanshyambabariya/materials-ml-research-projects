"""Features from uniformly sampled, already calibrated physical channels."""
import csv
import io
from pathlib import Path

import numpy as np
from scipy.signal import welch

from .data import digest

UNITS = {"Fx": "N", "Fy": "N", "Fz": "N", "Mx": "N*m", "My": "N*m", "Mz": "N*m", "vibration": "m/s^2", "temperature": "K"}


def extract(path, sampling_rate_hz, units, window_samples=2048):
    if not np.isfinite(sampling_rate_hz) or sampling_rate_hz <= 0 or not isinstance(window_samples, int) or window_samples < 8:
        raise ValueError("Require positive finite sample rate and integer window_samples >= 8")
    raw = Path(path).read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    columns = reader.fieldnames
    if not columns or columns[0] != "time_s" or len(columns) < 2 or len(columns) != len(set(columns)):
        raise ValueError("Require time_s followed by unique calibrated channel columns")
    channels = columns[1:]
    if set(units) != set(channels) or any(c not in UNITS or units[c] != UNITS[c] for c in channels):
        raise ValueError(f"Channel units must match supported units: {UNITS}")
    values = []
    for row in reader:
        if None in row or any(v is None or not v.strip() for v in row.values()):
            raise ValueError("Missing or extra signal values")
        values.append([float(row[c]) for c in columns])
    data = np.array(values)
    if data.ndim != 2 or len(data) < window_samples or not np.isfinite(data).all():
        raise ValueError("Need at least one complete finite signal window")
    if not np.allclose(np.diff(data[:, 0]), 1 / sampling_rate_hz, rtol=1e-3, atol=1e-12):
        raise ValueError("Timestamps must be increasing and match the declared sampling rate")
    if "temperature" in channels and np.any(data[:, columns.index("temperature")] <= 0):
        raise ValueError("Temperature must be positive Kelvin")
    windows = []
    for start in range(0, len(data)-window_samples+1, window_samples):
        result = {"start_sample": start, "end_sample_exclusive": start+window_samples, "channels": {}}
        for index, name in enumerate(channels, 1):
            x = data[start:start+window_samples, index]
            rms = float(np.sqrt(np.mean(x*x)))
            frequencies, psd = welch(x, fs=sampling_rate_hz, window="hann", nperseg=min(1024, len(x)), detrend="constant", scaling="density")
            power = float(np.sum(psd))
            result["channels"][name] = {"unit": units[name], "mean": float(x.mean()), "std": float(x.std()), "rms": rms, "peak_absolute": float(np.max(np.abs(x))), "crest_factor": float(np.max(np.abs(x))/rms) if rms else 0.0, "dominant_frequency_hz": float(frequencies[np.argmax(psd)]) if power else 0.0, "spectral_centroid_hz": float(frequencies @ psd / power) if power else 0.0, "variance_from_psd": float(power * (frequencies[1]-frequencies[0]))}
        windows.append(result)
    return {"source_sha256": digest(raw), "sampling_rate_hz": sampling_rate_hz, "window_samples": window_samples, "discarded_tail_samples": len(data) % window_samples, "method": "Non-overlapping windows; population std; mean-detrended Hann Welch PSD; no filtering or calibration applied", "windows": windows}
