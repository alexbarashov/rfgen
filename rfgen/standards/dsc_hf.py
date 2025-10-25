
# DSC HF baseband generator (mirrored from VHF style)
# Produces complex64 IQ signal: pre-silence (noise), unmodulated carrier, FM of AFSK audio, post-silence (noise).
# Goal: keep the same API/params/structure as generate_dsc_vhf for drop-in use.

import numpy as np
from typing import Dict, Any, Optional

# Import common DSC framing functions
from .dsc_common import build_dsc_bits, build_primary_symbols_from_cfg

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
    # Very light 1-pole approximation of ~6 dB/oct pre-emphasis (optional).
    if not enable or x.size == 0:
        return x
    fc = 300.0  # soft corner; not critical for synthetic DSC
    alpha = np.exp(-2.0 * np.pi * fc / fs).astype(np.float32)
    y = np.empty_like(x, dtype=np.float32)
    prev = np.float32(0.0)
    for i in range(x.size):
        prev = x[i] + alpha * (prev - x[i])
        y[i] = prev
    mx = float(np.max(np.abs(y))) or 1.0
    y = (y / mx).astype(np.float32)
    return y

def generate_dsc_hf_afsk_vhfstyle(params: Dict[str, Any]) -> np.ndarray:
    """
    Generate DSC (HF) baseband IQ with AFSK audio frequency-modulated (FM), mirroring VHF generator.

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

    # AFSK audio from hex bits
    bits = _hex_to_bits(hex_message)
    sym_N = int(round(Fs / sym_rate))
    if sym_N < 10:
        raise ValueError("Fs too low for requested symbol_rate (needs >= ~10 samples/symbol)")
    total_N = bits.size * sym_N

    # per-symbol tone generation
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

    # FM modulation from audio
    amax = float(np.max(np.abs(audio))) or 1.0
    au = (audio / amax).astype(np.float32)
    dphi = (2.0 * np.pi * fm_dev_hz * au / Fs).astype(np.float32)
    phase = np.cumsum(dphi, dtype=np.float64)
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
            "save_path": "/mnt/data/dsc_hf_cf32.iq",
            "rng_seed": 12345,
        }
    }
    iq = generate_dsc_hf(params)
    print({"samples": int(iq.size), "fs": int(params["device"]["fs_tx"]), "path": "/mnt/data/dsc_hf_cf32.iq"})


def build_dsc_hf(profile: dict) -> np.ndarray:
    """
    DSC HF IQ buffer generation with unified Builder API.

    Поддерживает два режима ввода:
    - "hex": прямой ввод HEX-строки
    - "builder": сборка сообщения из полей через общий DSC Builder

    ВАЖНО: DSC HF использует правильные параметры ITU-R M.493:
    - Скорость: 100 бод
    - FSK shift: 170 Hz (±85 Hz)
    - Режим: F1B (прямой FSK) или J2B (AFSK для SSB)

    Args:
        profile: словарь профиля с полями standard_params, device

    Returns:
        np.ndarray: complex64 IQ baseband буфер
    """
    sp = profile.get("standard_params", {})
    input_mode = sp.get("input_mode", "hex")

    # Определяем hex_message в зависимости от режима
    if input_mode == "builder":
        # Используем общий Builder (как в DSC VHF)
        dsc_cfg = {
            "scenario": sp.get("call_type", "all_ships").lower().replace(" ", "_"),
            "mmsi": sp.get("mmsi_to", "111222333"),
            "mmsi_from": sp.get("mmsi_from", "999888777"),
            "format_symbol": sp.get("format_symbol", None),
            "category_symbol": sp.get("category_symbol", 100),
            "telecommand_symbols": sp.get("telecommand_symbols", [126, 126]),
        }

        # Собираем primary symbols через общий Builder
        primary_symbols = build_primary_symbols_from_cfg(dsc_cfg)
        eos_symbol = int(sp.get("eos_symbol", 127))

        # Конвертируем в битовый поток через общий encoder
        bits = build_dsc_bits(primary_symbols, eos_symbol=eos_symbol)

        # Упаковываем биты в HEX для передачи в генератор
        nbytes = (bits.size + 7) // 8
        padded = np.zeros(nbytes * 8, dtype=np.uint8)
        padded[:bits.size] = bits
        hex_message = np.packbits(padded).tobytes().hex().upper()

    elif input_mode == "hex":
        hex_message = sp.get("hex_message", "D5AA55D5AA55")
    else:
        raise ValueError(f"Неизвестный input_mode: {input_mode}")

    # Подготавливаем параметры для HF генератора
    # ВАЖНО: используем правильные HF параметры (100 Bd, ±85 Hz)
    params = {
        "device": profile.get("device", {}),
        "standard_params": {
            "hex_message": hex_message,
            "symbol_rate": sp.get("symbol_rate", 100.0),  # HF: 100 бод
            "shift_hz": sp.get("shift_hz", 170.0),  # HF: ±85 Hz
            "center_hz": sp.get("center_hz", 0.0),
            "mode": sp.get("mode", "F1B"),
            "pre_silence_ms": sp.get("pre_silence_ms", 25.0),
            "carrier_sec": sp.get("carrier_sec", 0.020),  # HF: 20 ms per ITU-R M.493
            "post_silence_ms": sp.get("post_silence_ms", 25.0),
            "noise_dbfs": sp.get("noise_dbfs", -60.0),
            "normalize": sp.get("normalize", True),
            "rng_seed": sp.get("rng_seed", 12345),
        }
    }

    # Генерируем IQ с правильными HF параметрами
    return generate_dsc_hf(params)


def generate_dsc_hf(params: Dict[str, Any]) -> np.ndarray:
    """
    Generate MF/HF DSC per ITU-R M.493:
      - Symbol rate 100 Bd (default)
      - Frequency shift 170 Hz total (±85 Hz)
    Two emission styles:
      mode="F1B": direct baseband FSK at ±85 Hz (centered at 0 Hz or at "center_hz")
      mode="J2B": audio AFSK with tones 1700±85 Hz (for SSB chain)

    Params (dict):
      device.fs_tx                 : IQ Fs (Hz), default 1_000_000
      standard_params.hex_message  : HEX payload to turn into a bitstream
      standard_params.symbol_rate  : default 100.0
      standard_params.shift_hz     : total shift, default 170.0  (i.e., ±85 Hz)
      standard_params.center_hz    : baseband center for FSK in "F1B" mode (default 0.0)
      standard_params.mode         : "F1B" or "J2B" (default "F1B")
      standard_params.pre_silence_ms / post_silence_ms
      standard_params.carrier_sec  : optional unmodulated carrier (mainly for "F1B")
      standard_params.noise_dbfs   : complex noise level (default -60 dBFS)
      standard_params.normalize    : peak normalize (default True)
      standard_params.save_path    : path to interleaved float32 I,Q
      standard_params.rng_seed     : RNG seed

    Returns: complex64 IQ
    """
    device = params.get("device", {})
    Fs = float(int(device.get("fs_tx", 1_000_000)))

    sp = params.get("standard_params", {})
    hex_message = sp.get("hex_message", "D5AA55D5AA55")
    sym_rate = float(sp.get("symbol_rate", 100.0))
    shift_hz = float(sp.get("shift_hz", 170.0))
    center_hz = float(sp.get("center_hz", 0.0))
    mode = str(sp.get("mode", "F1B")).upper()

    pre_ms = float(sp.get("pre_silence_ms", 25.0))
    post_ms = float(sp.get("post_silence_ms", 25.0))
    carrier_sec = float(sp.get("carrier_sec", 0.020))  # 20 ms per ITU-R M.493
    noise_dbfs = float(sp.get("noise_dbfs", -60.0))
    normalize = bool(sp.get("normalize", True))
    save_path = sp.get("save_path", None)
    rng_seed = int(sp.get("rng_seed", 12345))

    if sym_rate <= 0:
        raise ValueError("symbol_rate must be > 0")
    if shift_hz <= 0:
        raise ValueError("shift_hz must be > 0")

    rng = np.random.default_rng(rng_seed)
    pre_N = int(round(pre_ms * 1e-3 * Fs))
    post_N = int(round(post_ms * 1e-3 * Fs))
    carr_N = int(round(max(0.0, carrier_sec) * Fs))
    noise_amp = _dbfs_to_linear(noise_dbfs)

    pre = _gen_noise(pre_N, noise_amp, rng)
    carrier = (np.exp(1j * 2.0 * np.pi * center_hz * np.arange(carr_N, dtype=np.float32) / Fs).astype(np.complex64)
               if carr_N > 0 else np.zeros(0, np.complex64))

    bits = _hex_to_bits(hex_message)
    sps = int(round(Fs / sym_rate))
    if sps < 10:
        raise ValueError("Fs too low for requested symbol_rate; need ~>=10 samples/symbol")
    total_N = int(bits.size * sps)

    # NRZ mapping: 1 -> +1, 0 -> -1
    nrz = (bits.astype(np.int8) * 2 - 1).astype(np.float32)

    if mode == "F1B":
        # Instantaneous frequency = center_hz + nrz * (shift_hz/2)
        # Build piecewise-constant frequency array at symbol rate; then integrate to phase.
        inst_freq = np.repeat(center_hz + (shift_hz * 0.5) * nrz, sps).astype(np.float32)
        # Phase integration
        dphi = (2.0 * np.pi * inst_freq / Fs).astype(np.float32)
        phase = np.cumsum(dphi, dtype=np.float64).astype(np.float32)
        mod = np.exp(1j * phase).astype(np.complex64)

    elif mode == "J2B":
        # Audio AFSK with tones 1700±85 Hz; this should later feed an SSB upconverter.
        f_center = 1700.0
        f_dev = shift_hz * 0.5
        sym_t = (np.arange(sps, dtype=np.float32) / Fs).astype(np.float32)
        audio = np.empty(total_N, dtype=np.float32)
        idx = 0
        for b in nrz:
            f = f_center + b * f_dev
            tone = np.sin(2.0 * np.pi * f * sym_t, dtype=np.float32)
            audio[idx:idx+sps] = tone
            idx += sps
        # Treat audio as the real part; output complex baseband for convenience
        mod = audio.astype(np.float32) + 1j * np.zeros_like(audio, dtype=np.float32)
        mod = mod.astype(np.complex64)
    else:
        raise ValueError('mode must be "F1B" or "J2B"')

    post = _gen_noise(post_N, noise_amp, rng)

    sig = np.concatenate([pre, carrier, mod, post]).astype(np.complex64)
    if normalize and sig.size:
        sig = _clip_norm(sig, 0.999)

    if save_path is not None:
        inter = np.empty(sig.size * 2, dtype=np.float32)
        inter[0::2] = sig.real.astype(np.float32, copy=False)
        inter[1::2] = sig.imag.astype(np.float32, copy=False)  # <-- will fix below

        with open(save_path, "wb") as f:
            inter.tofile(f)
    return sig


if __name__ == "__main__":
    # Quick HF-accurate self-test
    params = {
        "device": {"fs_tx": 48000},
        "standard_params": {
            "hex_message": "D5AA55D5AA55",
            "symbol_rate": 100.0,
            "shift_hz": 170.0,
            "center_hz": 0.0,
            "mode": "F1B",
            "pre_silence_ms": 50.0,
            "carrier_sec": 0.2,
            "post_silence_ms": 50.0,
            "noise_dbfs": -50.0,
            "normalize": True,
            "save_path": "/mnt/data/dsc_hf_F1B_100bd_170shift_48k.iq"
        }
    }
    _ = generate_dsc_hf(params)
    print({"ok": True, "fs": params["device"]["fs_tx"], "path": "/mnt/data/dsc_hf_F1B_100bd_170shift_48k.iq"})
