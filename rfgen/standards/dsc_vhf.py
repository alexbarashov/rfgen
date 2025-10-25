# DSC VHF (Ch70) baseband generator
# Produces complex64 IQ signal: pre-silence (noise), unmodulated carrier, FM of AFSK(1300/2100Hz @1200Bd), post-silence (noise).
# Design goal: align with style/structure of existing PSK406 generator (silence/carrier/message/silence, noise, normalize).

import numpy as np
from typing import Dict, Any, Optional

def _dbfs_to_linear(dbfs: float) -> float:
    return 10.0 ** (dbfs / 20.0)

def _gen_noise(n: int, amp_lin: float, rng: np.random.Generator) -> np.ndarray:
    if n <= 0:
        return np.zeros(0, np.complex64)
    noise_i = rng.normal(0.0, amp_lin / np.sqrt(2.0), size=n).astype(np.float32)
    noise_q = rng.normal(0.0, amp_lin / np.sqrt(2.0), size=n).astype(np.float32)
    return (noise_i + 1j * noise_q).astype(np.complex64)

def _clip_norm(x: np.ndarray, peak: float = 0.999) -> np.ndarray:
    if x.size == 0:
        return x
    m = float(np.max(np.abs(x)))
    if m > peak and m > 0.0:
        x = (x / m) * peak
    return x

def _hex_to_bits(hex_message: str) -> np.ndarray:
    s = "".join(hex_message.split()).lower()
    if len(s) % 2 != 0:
        raise ValueError("HEX length must be even")
    data = bytes.fromhex(s)
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    return bits.astype(np.uint8)

def _preemphasis_6dB_per_oct(x: np.ndarray, fs: float, enable: bool) -> np.ndarray:
    """Very light 1-pole approximation of ~6 dB/oct pre-emphasis (optional)."""
    if not enable or x.size == 0:
        return x
    fc = 300.0  # soft corner; not critical for synthetic DSC
    alpha = np.exp(-2.0 * np.pi * fc / fs).astype(np.float32)
    y = np.empty_like(x, dtype=np.float32)
    prev = np.float32(0.0)
    for i in range(x.size):
        # high-shelving style: emphasize highs; simple HP-like leaky filter
        prev = x[i] + alpha * (prev - x[i])
        y[i] = prev
    mx = float(np.max(np.abs(y))) or 1.0
    y = (y / mx).astype(np.float32)
    return y

def generate_dsc_vhf(params: Dict[str, Any]) -> np.ndarray:
    """
    Generate DSC (VHF, Ch70) baseband IQ with AFSK(1300/2100 Hz @ 1200 Bd) frequency-modulated (FM).

    params (dict):
      device.fs_tx               : IQ sample rate (Hz). Default: 1_000_000
      standard_params.hex_message: hex payload (arbitrary test bytes)
      standard_params.symbol_rate: symbols per second (Bd). Default: 1200.0
      standard_params.f_mark_hz  : tone for '1'. Default: 2100.0
      standard_params.f_space_hz : tone for '0'. Default: 1300.0
      standard_params.pre_silence_ms : leading silence/noise, ms. Default: 25.0
      standard_params.post_silence_ms: trailing silence/noise, ms. Default: 25.0
      standard_params.carrier_sec: unmodulated carrier duration, s. Default: 0.16
      standard_params.fm_dev_hz  : FM deviation at |audio|=1.0, Hz. Default: 2500.0
      standard_params.preemphasis: bool, apply ~6 dB/oct to audio. Default: False
      standard_params.noise_dbfs : dBFS level for injected complex noise. Default: -60.0
      standard_params.normalize  : bool, peak normalize to 0.999. Default: True
      standard_params.save_path  : optional path to write interleaved float32 I,Q
      standard_params.rng_seed   : int seed for noise RNG. Default: 12345

    Returns:
      np.ndarray complex64 IQ baseband.
    """
    device = params.get("device", {})
    Fs = float(int(device.get("fs_tx", 1_000_000)))

    sp = params.get("standard_params", {})
    hex_message = sp.get("hex_message", "D5AA55D5AA55")
    sym_rate = float(sp.get("symbol_rate", 1200.0))
    f_mark = float(sp.get("f_mark_hz", 2100.0))
    f_space = float(sp.get("f_space_hz", 1300.0))
    pre_ms = float(sp.get("pre_silence_ms", 25.0))
    post_ms = float(sp.get("post_silence_ms", 25.0))
    carrier_sec = float(sp.get("carrier_sec", 0.16))
    fm_dev_hz = float(sp.get("fm_dev_hz", 2500.0))
    preemph = bool(sp.get("preemphasis", False))
    noise_dbfs = float(sp.get("noise_dbfs", -60.0))
    normalize = bool(sp.get("normalize", True))
    save_path: Optional[str] = sp.get("save_path", None)
    rng_seed = int(sp.get("rng_seed", 12345))

    if sym_rate <= 0.0:
        raise ValueError("symbol_rate must be > 0")

    rng = np.random.default_rng(rng_seed)
    pre_N = int(round(pre_ms * 1e-3 * Fs))
    post_N = int(round(post_ms * 1e-3 * Fs))
    carr_N = int(round(carrier_sec * Fs))
    noise_amp = _dbfs_to_linear(noise_dbfs)

    pre = _gen_noise(pre_N, noise_amp, rng)
    carrier = (np.ones(carr_N, dtype=np.complex64) if carr_N > 0
               else np.zeros(0, np.complex64))

    # ---- AFSK audio from hex bits ----
    bits = _hex_to_bits(hex_message)
    sym_N = int(round(Fs / sym_rate))
    if sym_N < 10:
        raise ValueError("Fs too low for requested symbol_rate (needs >= ~10 samples/symbol)")
    total_N = bits.size * sym_N

    # Per-symbol tone generation
    t = (np.arange(sym_N, dtype=np.float32) / Fs).astype(np.float32)
    audio = np.empty(total_N, dtype=np.float32)
    idx = 0
    for b in bits:
        f = f_mark if b else f_space
        tone = np.sin(2.0 * np.pi * f * t, dtype=np.float32)
        audio[idx:idx + sym_N] = tone
        idx += sym_N

    # Optional pre-emphasis
    audio = _preemphasis_6dB_per_oct(audio, Fs, enable=preemph)

    # ---- FM modulation from audio ----
    # Normalize audio to |1| peak to make fm_dev_hz meaningful
    amax = float(np.max(np.abs(audio))) or 1.0
    au = (audio / amax).astype(np.float32)
    dphi = (2.0 * np.pi * fm_dev_hz * au / Fs).astype(np.float32)
    phase = np.cumsum(dphi, dtype=np.float64)  # integrate in higher precision
    fm_sig = np.exp(1j * phase.astype(np.float32)).astype(np.complex64)

    post = _gen_noise(post_N, noise_amp, rng)

    sig = np.concatenate([pre, carrier, fm_sig, post]).astype(np.complex64)

    if normalize and sig.size:
        sig = _clip_norm(sig, peak=0.999)

    if save_path is not None:
        inter = np.empty(sig.size * 2, dtype=np.float32)
        inter[0::2] = sig.real.astype(np.float32, copy=False)
        inter[1::2] = sig.imag.astype(np.float32, copy=False)
        with open(save_path, "wb") as f:
            inter.tofile(f)

    return sig


if __name__ == "__main__":
    # Quick self-test file generation (optional)
    params = {
        "device": {"fs_tx": 1_000_000},
        "standard_params": {
            "hex_message": "D5AA55D5AA55",
            "symbol_rate": 1200.0,
            "f_mark_hz": 2100.0,
            "f_space_hz": 1300.0,
            "fm_dev_hz": 2500.0,
            "preemphasis": False,
            "pre_silence_ms": 25.0,
            "carrier_sec": 0.16,
            "post_silence_ms": 25.0,
            "noise_dbfs": -60.0,
            "normalize": True,
            "save_path": "/mnt/data/dsc_cf32.iq",
            "rng_seed": 12345,
        }
    }
    iq = generate_dsc_vhf(params)
    print({"samples": int(iq.size), "fs": int(params["device"]["fs_tx"]), "path": "/mnt/data/dsc_cf32.iq"})

# -----------------------------
# DSC framing per ITU‑R M.493 (skeleton)
from typing import List

def _symbol_to_primary7(sym: int) -> np.ndarray:
    """7 инфо-битов MSB-first: b6,b5,...,b0."""
    if not (0 <= sym <= 127):
        raise ValueError("Symbol out of range 0..127")
    return np.array([ (sym >> k) & 1 for k in range(6, -1, -1) ], dtype=np.uint8)

def _primary7_to_tenbit(info7: np.ndarray) -> np.ndarray:
    """Добавить 3-битный zero-count (MSB-first) к 7 MSB-first битам."""
    zeros = 7 - int(info7.sum())
    chk = np.array([ (zeros >> 2) & 1, (zeros >> 1) & 1, zeros & 1 ], dtype=np.uint8)
    return np.concatenate([info7, chk])

def _symbols_to_tenbits(symbols: List[int]) -> List[np.ndarray]:
    return [_primary7_to_tenbit(_symbol_to_primary7(s)) for s in symbols]

def _build_dotting(n: int = 120) -> List[int]:
    """Dotting: повтор символа 126."""
    return [126] * n

def _build_phasing_rx(repeats: int = 2) -> List[int]:
    """Phasing (RX): 111..104, повторить repeats раз."""
    base = [111,110,109,108,107,106,105,104]
    return base * repeats

def _time_diversity_schedule(payload_syms: List[int]) -> List[int]:
    out: List[int] = []
    rx_queue: List[int] = []
    for s in payload_syms:
        out.append(s)
        rx_queue.append(s)
        if len(rx_queue) > 4:
            out.append(rx_queue.pop(0))
    while rx_queue:
        if len(rx_queue) > 4:
            out.append(rx_queue.pop(0))
        else:
            out.append(125)
            out.append(rx_queue.pop(0))
    return out

def _build_dsc_frame(primary_symbols: List[int], fs_symbol: int, eos_symbol: int = 127, include_eos: bool = True) -> List[int]:
    # Dotting + Phasing
    prefix = _build_dotting(120) + _build_phasing_rx(2)
    # Обязательное дублирование FS
    header = [fs_symbol, fs_symbol]
    payload = list(primary_symbols)
    if include_eos:
        payload.append(eos_symbol)
    # (Time diversity можно временно отключить, чтобы не мешал проверке на приёмнике)
    return prefix + header + payload

def _digits_to_symbols(digits: str) -> List[int]:
    s = ''.join(ch for ch in digits if ch.isdigit())
    if len(s) % 2 == 1:
        s += '0'
    return [int(s[i:i+2]) for i in range(0, len(s), 2)]

def _build_test_all_ships_sequence(mmsi:str="111222333") -> List[int]:
    fmt = 112
    addr = _digits_to_symbols(mmsi)
    tele = [126,126]
    return [fmt] + addr + tele

def _tenbits_to_bitstream(chars10: List[np.ndarray]) -> np.ndarray:
    if not chars10:
        return np.zeros(0, np.uint8)
    return np.concatenate(chars10).astype(np.uint8)

def _afsk_from_bits(bits: np.ndarray, fs: float, baud: float, f_low: float, f_high: float, one_is_low: bool=True) -> np.ndarray:
    if bits.size == 0:
        return np.zeros(0, np.float32)
    sym_N = int(round(fs / baud))
    t = (np.arange(sym_N, dtype=np.float32) / fs).astype(np.float32)
    out = np.empty(bits.size * sym_N, dtype=np.float32)
    idx = 0
    for b in bits:
        if one_is_low:
            f = f_low if b==1 else f_high
        else:
            f = f_high if b==1 else f_low
        tone = np.sin(2.0 * np.pi * f * t, dtype=np.float32)
        out[idx:idx+sym_N] = tone
        idx += sym_N
    return out

def build_dsc_bits(primary_symbols: List[int], eos_symbol:int=127) -> np.ndarray:
    fs_symbol = primary_symbols[0]
    seq_syms = _build_dsc_frame(primary_symbols[1:], fs_symbol=fs_symbol, eos_symbol=eos_symbol, include_eos=True)
    tenbits = _symbols_to_tenbits(seq_syms)
    bits = _tenbits_to_bitstream(tenbits)
    return bits.astype(np.uint8)
# -----------------------------

# =============================
# High-level DSC primary-symbol builders (lab-friendly, overrideable)
# =============================

def _mmsi_to_symbols(mmsi: str) -> List[int]:
    """Convert MMSI string (digits only) to 5 two-digit symbols (pads with leading zeros)."""
    s = ''.join(ch for ch in mmsi if ch.isdigit())
    s = s.zfill(9)  # MMSI is 9 digits; address area often uses 10 digits incl. leading 0 -> we pair digits
    # For DSC addressing, digits are typically sent in pairs as 00..99 symbols.
    # We will left-pad to even length and split by 2.
    if len(s) % 2 == 1:
        s = '0' + s
    pairs = [int(s[i:i+2]) for i in range(0, len(s), 2)]
    # Ensure exactly 5 symbols
    if len(pairs) < 5:
        pairs = [0]*(5-len(pairs)) + pairs
    elif len(pairs) > 5:
        pairs = pairs[-5:]
    return pairs

def build_primary_symbols_from_cfg(dsc_cfg: dict) -> List[int]:
    """
    Build primary symbol list from a flexible config.
    Priority: explicit 'primary_symbols' -> scenario helpers -> minimal All Ships.
    dsc_cfg fields (optional):
      - primary_symbols: explicit list[int] 0..127 (highest priority)
      - scenario: 'all_ships' | 'individual' | 'distress' (lab presets)
      - format_symbol: int (default per scenario: 112 for 'all_ships', 120 for 'individual', 112 for 'distress')
      - mmsi: target MMSI string
      - telecommand_symbols: list[int] extras appended after address (e.g., 126,126 as fillers)
    """
    # 1) Direct override
    ps = dsc_cfg.get("primary_symbols", None)
    if isinstance(ps, (list, tuple)) and len(ps) > 0:
        return [int(x) for x in ps]

    scenario = str(dsc_cfg.get("scenario", "all_ships")).lower()
    fmt = dsc_cfg.get("format_symbol", None)
    if fmt is None:
        if scenario == "individual":
            fmt = 115   # или 123
        elif scenario == "distress":
            fmt = 112
        else:
            fmt = 116   # all_ships default

    mmsi_to = str(dsc_cfg.get("mmsi", "111222333"))
    addr = _mmsi_to_symbols(mmsi_to)
    mmsi_from = str(dsc_cfg.get("mmsi_from", "999888777"))
    self_id = _mmsi_to_symbols(mmsi_from)
    category = dsc_cfg.get("category_symbol", 100)  # 100=Routine

    tele = dsc_cfg.get("telecommand_symbols", None)
    if tele is None:
        tele = [126, 126]  # neutral placeholders

    primary = [int(fmt)] + [int(x) for x in addr] + [int(category)] + [int(x) for x in self_id] + [int(x) for x in tele]
    return primary


# =============================
# Unified build_dsc_vhf() for profile integration
# =============================

def build_dsc_vhf(profile: dict) -> np.ndarray:
    """Генерация DSC VHF IQ-буфера из профиля.

    Args:
        profile: Профиль с параметрами DSC VHF

    Returns:
        IQ-буфер (complex64) с AFSK @ 1200 Bd + FM модуляцией
    """
    std_params = profile.get("standard_params", {})
    input_mode = std_params.get("input_mode", "hex")

    # Определение битов для AFSK
    if input_mode == "builder":
        # Режим Message Builder: сборка из primary symbols
        dsc_cfg = {
            "scenario": std_params.get("call_type", "all_ships").lower().replace(" ", "_"),
            "mmsi": std_params.get("mmsi_to", "111222333"),
            "format_symbol": std_params.get("format_symbol", None),
            "telecommand_symbols": std_params.get("telecommand_symbols", [126, 126]),
        }

        primary_symbols = build_primary_symbols_from_cfg(dsc_cfg)
        eos_symbol = int(std_params.get("eos_symbol", 127))
        bits = build_dsc_bits(primary_symbols, eos_symbol=eos_symbol)

        # Конвертация битов в hex для generate_dsc_vhf()
        # (можно оптимизировать, но пока используем существующую функцию)
        nbytes = (bits.size + 7) // 8
        padded = np.zeros(nbytes * 8, dtype=np.uint8)
        padded[:bits.size] = bits
        bytes_arr = np.packbits(padded)
        hex_message = bytes_arr.tobytes().hex().upper()

        # Обновляем параметры для generate_dsc_vhf
        std_params = std_params.copy()
        std_params["hex_message"] = hex_message
    # else: режим Direct HEX - используем hex_message напрямую

    # Вызов базового генератора
    iq = generate_dsc_vhf(profile)

    return iq
