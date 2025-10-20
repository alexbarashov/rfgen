import numpy as np

def save_cf32(path: str, iq: np.ndarray):
    path = str(path)
    iq = np.asarray(iq, dtype=np.complex64)
    interleaved = np.empty(iq.size * 2, dtype=np.float32)
    interleaved[0::2] = iq.real.astype(np.float32)
    interleaved[1::2] = iq.imag.astype(np.float32)
    interleaved.tofile(path)
    return path

def save_sc8(path: str, iq_c: np.ndarray):
    path = str(path)
    iq = np.asarray(iq_c, dtype=np.complex64)
    mx = float(np.max(np.abs(iq))) if iq.size else 1.0
    if mx < 1e-12:
        mx = 1.0
    scale = 0.8 / mx  # keep headroom
    I = np.clip(np.real(iq) * scale * 127.0, -128, 127).astype(np.int8)
    Q = np.clip(np.imag(iq) * scale * 127.0, -128, 127).astype(np.int8)
    inter = np.empty(I.size * 2, dtype=np.int8)
    inter[0::2] = I
    inter[1::2] = Q
    inter.tofile(path)
    return path
