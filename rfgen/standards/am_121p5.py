# am_121p5.py
# Baseband AM generator for 121.5 MHz (emergency beacon tone) modeled after PSK-406 schedule semantics.
# Returns complex64 IQ at device.fs_tx with carrier at DC; RF tuning & digital shifts are handled upstream (e.g., hackrf.py).
#
# Modes supported via params["standard_params"]["signal_type"]:
#   - "Swept Tone (300-1600 Hz)"
#   - "Continuous Tone"
#   - "Modulated Carrier (CW)"
#
# Schedule semantics (like PSK-406):
#   - params["schedule"]["mode"] == "loop"  -> append post-gap_s of zeros inside one frame
#   - params["schedule"]["mode"] == "repeat"-> omit internal gap; caller/backend inserts pauses
#
# Params expected (typical):
# params = {
#   "standard": "121",
#   "device": {"fs_tx": 1_000_000},
#   "standard_params": {
#       "signal_type": "Swept Tone (300-1600 Hz)",   # or "Continuous Tone" or "Modulated Carrier (CW)"
#       "tone_hz": 1000.0,
#       "sweep_low": 300.0,
#       "sweep_high": 1600.0,
#       "sweep_rate": 2.0,     # reserved for possible future shaping; linear sweep for now
#       "am_depth": 0.8,       # 0..1
#       "duty_cycle": 1.0      # envelope duty inside a frame, 0..1
#   },
#   "schedule": {"mode": "loop", "gap_s": 8.0},
#   "_frame_s": 1.0            # injected by wave_engine; default if absent = 1.0s
# }
#
# Example usage:
# from am_121p5 import generate_121p5
# iq = generate_121p5(params)
# assert iq.dtype == np.complex64
#
from __future__ import annotations
import numpy as np
from typing import Dict, Any

__all__ = ["generate_121p5"]


def _clip_norm(x: np.ndarray, peak: float = 0.95) -> np.ndarray:
    """Limit absolute peak to <= peak for safety; return complex64/float32 accordingly."""
    if x.size == 0:
        return x
    m = float(np.max(np.abs(x)))
    if m > 0.0 and m > peak:
        x = (x / m) * peak
    # Keep complex64 for IQ or float32 for envelopes
    if np.iscomplexobj(x):
        return x.astype(np.complex64, copy=False)
    return x.astype(np.float32, copy=False)


def _tone(fs: int, dur_s: float, f_hz: float) -> np.ndarray:
    n = int(max(1, round(fs * dur_s)))
    t = np.arange(n, dtype=np.float64) / float(fs)
    return np.sin(2.0 * np.pi * f_hz * t)


def _sweep(fs: int, dur_s: float, f_lo: float, f_hi: float) -> np.ndarray:
    """Linear chirp from f_lo to f_hi across dur_s seconds."""
    n = int(max(1, round(fs * dur_s)))
    t = np.arange(n, dtype=np.float64) / float(fs)
    k = (f_hi - f_lo) / max(dur_s, 1e-12)
    phase = 2.0 * np.pi * (f_lo * t + 0.5 * k * t * t)
    return np.sin(phase)


def _amp_am(m: np.ndarray, depth: float) -> np.ndarray:
    """Classic AM around 1.0: env = 1 + depth * norm(m), m normalized to [-1..1]."""
    m = m.astype(np.float64, copy=False)
    mmax = float(np.max(np.abs(m))) + 1e-12
    m = m / mmax
    env = 1.0 + float(depth) * m
    return env.astype(np.float32)


def _apply_duty(env: np.ndarray, duty: float) -> np.ndarray:
    """Apply duty cycle inside a single frame: first duty% is ON, rest is silence."""
    duty = float(np.clip(duty, 0.0, 1.0))
    if duty >= 0.999:
        return env.astype(np.float32, copy=False)
    n = env.size
    on = int(round(n * duty))
    out = np.zeros_like(env, dtype=np.float32)
    if on > 0:
        out[:on] = env[:on]
    return out


def generate_121p5(params: Dict[str, Any]) -> np.ndarray:
    """
    Generate baseband AM IQ for 121.5 MHz beacon tone based on PSK-406-like schedule.
    Returns complex64 IQ. RF tuning and digital shift are handled upstream.

    See module header for expected params schema.
    """
    dev = params.get("device", {})
    fs = int(dev.get("fs_tx", 2_000_000))

    sp = params.get("standard_params", {})
    signal_type = str(sp.get("signal_type", "Swept Tone (300-1600 Hz)"))
    tone_hz     = float(sp.get("tone_hz", 1000.0))
    sweep_low   = float(sp.get("sweep_low", 300.0))
    sweep_high  = float(sp.get("sweep_high", 1600.0))
    # sweep_rate is reserved for future sweep shaping; linear at present
    _ = float(sp.get("sweep_rate", 2.0))
    am_depth    = float(np.clip(sp.get("am_depth", 0.8), 0.0, 1.0))
    duty        = float(np.clip(sp.get("duty_cycle", 1.0), 0.0, 1.0))

    schedule = params.get("schedule", {})
    mode     = str(schedule.get("mode", "loop"))
    gap_s    = float(schedule.get("gap_s", 8.0))

    frame_s = float(params.get("_frame_s", 1.0))

    # Build modulating signal
    if "Swept" in signal_type:
        m = _sweep(fs, frame_s, sweep_low, sweep_high)
        env = _amp_am(m, am_depth)
        env = _apply_duty(env, duty)
        iq = env.astype(np.complex64)
    elif "Continuous" in signal_type:
        m = _tone(fs, frame_s, tone_hz)
        env = _amp_am(m, am_depth)
        env = _apply_duty(env, duty)
        iq = env.astype(np.complex64)
    elif "Modulated Carrier" in signal_type or "CW" in signal_type:
        # Keyed carrier: envelope 1 during ON, 0 during OFF
        env = np.ones(int(max(1, round(fs * frame_s))), dtype=np.float32)
        env = _apply_duty(env, duty)
        iq = env.astype(np.complex64)
    else:
        # Default to continuous tone
        m = _tone(fs, frame_s, tone_hz)
        env = _amp_am(m, am_depth)
        env = _apply_duty(env, duty)
        iq = env.astype(np.complex64)

    # For loop mode, append internal post-gap of zeros (PSK-406-like cadence)
    if mode == "loop" and gap_s > 0.0:
        gap_N = int(round(gap_s * fs))
        if gap_N > 0:
            iq = np.concatenate([iq, np.zeros(gap_N, dtype=np.complex64)], axis=0)

    # Safe peak normalization
    iq = _clip_norm(iq, peak=0.8)
    return iq
