import numpy as np

def generate_base_signal(kind: str, fs: int, dur_s: float, tone_hz: float = 1000.0):
    n = int(max(1, round(fs * dur_s)))
    t = np.arange(n, dtype=np.float64) / float(fs)

    if kind.lower() == "tone":
        m = np.sin(2.0 * np.pi * tone_hz * t)
    elif kind.lower() == "sweep":
        # simple linear sweep from tone_hz to 2*tone_hz
        f0, f1 = tone_hz, 2.0 * tone_hz
        k = (f1 - f0) / dur_s
        phase = 2.0 * np.pi * (f0 * t + 0.5 * k * t * t)
        m = np.sin(phase)
    elif kind.lower() == "noise":
        rng = np.random.default_rng(12345)
        m = rng.standard_normal(n).astype(np.float64)
        m /= np.max(np.abs(m)) + 1e-12
    else:
        # Bit patterns placeholder: map to a low-freq tone for now
        m = np.sin(2.0 * np.pi * tone_hz * t)
    return m, t

def mod_none(fs: int, m):
    # no modulation: constant carrier at baseband (I=1, Q=0)
    iq = np.ones_like(m, dtype=np.complex64)
    return iq

def mod_am(fs: int, m, depth: float = 0.5):
    # AM around 1.0 with depth (0..1); clip to avoid negatives if depth>1
    env = 1.0 + depth * m
    return (env.astype(np.float32)).astype(np.complex64)

def mod_pm(fs: int, m, index_rad: float = 1.0):
    phase = index_rad * m
    iq = np.exp(1j * phase).astype(np.complex64)
    return iq

def mod_fm(fs: int, m, deviation_hz: float = 5000.0):
    # Normalize m to [-1,1] to interpret deviation as +/- Hz
    mm = m / (np.max(np.abs(m)) + 1e-12)
    # instantaneous phase increment: 2*pi * f_inst / fs, where f_inst = deviation_hz * mm
    dphi = 2.0 * np.pi * deviation_hz * mm / float(fs)
    phase = np.cumsum(dphi, dtype=np.float64)
    iq = np.exp(1j * phase).astype(np.complex64)
    return iq

def build_iq(profile: dict, frame_s: float = 1.0):
    fs = int(profile["device"]["fs_tx"])
    pat = profile["pattern"]["type"]
    tone_hz = float(profile["pattern"].get("tone_hz", 1000.0))
    m, _t = generate_base_signal(pat, fs, frame_s, tone_hz=tone_hz)

    mod = profile["modulation"]["type"].lower()
    if mod == "am":
        depth = float(profile["modulation"].get("am_depth", 0.5))
        iq = mod_am(fs, m, depth)
    elif mod == "pm":
        idx = float(profile["modulation"].get("pm_index", 1.0))
        iq = mod_pm(fs, m, idx)
    elif mod == "fm":
        dev = float(profile["modulation"].get("deviation_hz", 5000.0))
        iq = mod_fm(fs, m, dev)
    else:
        iq = mod_none(fs, m)

    # Scale to safe level (<= 0.8) to avoid DAC clipping later
    iq = (0.8 * iq).astype(np.complex64)
    return iq

def build_cw(profile: dict, frame_s: float = 1.0):
    """Build constant carrier (no modulation) at baseband.
    If IF offset is nonzero, we emit a complex tone at +IF; center frequency should be target-IF.
    """
    import numpy as np
    fs = int(profile["device"]["fs_tx"])
    n = int(max(1, round(fs * frame_s)))
    if_hz = float(profile["device"].get("if_offset_hz", 0))
    t = np.arange(n, dtype=np.float64) / float(fs)
    if abs(if_hz) < 1e-3:
        iq = (0.8*np.ones(n, dtype=np.complex64)).astype(np.complex64)
    else:
        phase = 2.0*np.pi*if_hz*t
        iq = (0.8*np.exp(1j*phase)).astype(np.complex64)
    return iq
