
# NAVTEX baseband generator (modeled after dsc_hf.py style)
# Produces complex64 IQ signal for NAVTEX-like transmissions.
# MVP scope: FSK (100 Bd, 170 Hz shift) with two emission styles:
#   - "F1B": direct baseband FSK at center_hz ± 85 Hz
#   - "J2B": audio AFSK 1700 ± 85 Hz (useful for SSB chains)
#
# Input modes:
#   - "hex": raw HEX payload (bytes -> bitstream LSB-first)
#   - "text": simple ASCII builder: we construct "ZCZC {STA}{TYPE}{NUM}" + message + EOT
#             (NOTE: not a full SITOR-B FEC encoder; this is a placeholder for RF tests)
#
# Parameters mirror the DSC HF generator to keep the API familiar.

from typing import Dict, Any, Optional
import numpy as np

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
    # Convert to LSB-first per symbol for consistency with many FSK testchains if desired;
    # here we keep MSB-first to match numpy.unpackbits default. This is fine for RF patterns.
    return bits.astype(np.uint8)

def _ascii_to_bytes(text: str) -> bytes:
    # Keep it simple and upper-case for NAVTEX style
    return text.upper().encode("ascii", errors="ignore")

def build_navtex(profile: dict) -> np.ndarray:
    """
    Wrapper to generate NAVTEX IQ from a UI profile (matches page_navtex expectations).

    Supported input modes in profile['standard_params']:
      - input_mode: 'hex' | 'text'
      - For 'text': uses fields station_id, msg_type, msg_number, message_text to build payload.
    """
    sp = profile.get("standard_params", {})
    input_mode = sp.get("input_mode", "hex")

    if input_mode == "hex":
        hex_message = sp.get("hex_message", "5A435A43")  # "ZCZC" in ASCII -> 0x5A 0x43 0x5A 0x43
        payload_bytes = bytes.fromhex("".join(hex_message.split()))
    elif input_mode == "text":
        sta = (sp.get("station_id", "A") or "A")[:1]
        mtype = (sp.get("msg_type", "A") or "A")[:1]
        mnum = (sp.get("msg_number", "01") or "01")[:2]
        body = sp.get("message_text", "") or ""
        # Compose very simple NAVTEX-like text (NOT full SITOR-B)
        # Header "ZCZC <STA><TYPE><NUM>\r\n", message lines, terminator "\r\nNNNN"
        header = f"ZCZC {sta}{mtype}{mnum}\r\n"
        terminator = "\r\nNNNN\r\n"
        text = header + body + terminator
        payload_bytes = _ascii_to_bytes(text)
    else:
        raise ValueError(f"Unknown input_mode: {input_mode}")

    params = {
        "device": profile.get("device", {}),
        "standard_params": {
            # Feed the raw bytes as HEX down to the modulator for simplicity
            "hex_message": payload_bytes.hex(),
            "symbol_rate": 100.0,
            "shift_hz": 170.0,
            "center_hz": 0.0,
            "mode": "F1B",  # baseband FSK by default
            "pre_silence_ms": 25.0,
            "carrier_sec": 0.0,
            "post_silence_ms": 25.0,
            "noise_dbfs": -60.0,
            "normalize": True,
            "rng_seed": 12345,
            # Optional save_path can be provided via profile['standard_params']['save_path']
            "save_path": sp.get("save_path", None),
        }
    }
    return generate_navtex(params)

def generate_navtex(params: Dict[str, Any]) -> np.ndarray:
    """
    Generate NAVTEX-like FSK signal (MVP, no SITOR-B FEC yet).

    Params (dict):
      device.fs_tx                 : IQ Fs (Hz), default 1_000_000
      standard_params.hex_message  : HEX payload turned into a bitstream
      standard_params.symbol_rate  : default 100.0 Bd
      standard_params.shift_hz     : total shift, default 170.0 Hz (±85 Hz)
      standard_params.center_hz    : baseband carrier for FSK in "F1B" (default 0.0 Hz)
      standard_params.mode         : "F1B" (FSK) or "J2B" (audio 1700±85 Hz)
      standard_params.pre_silence_ms / post_silence_ms / carrier_sec
      standard_params.noise_dbfs   : complex noise level (default -60 dBFS)
      standard_params.normalize    : peak normalize (default True)
      standard_params.save_path    : path to interleaved float32 I,Q
      standard_params.rng_seed     : RNG seed

    Returns: complex64 IQ
    """
    device = params.get("device", {})
    Fs = float(int(device.get("fs_tx", 1_000_000)))

    sp = params.get("standard_params", {})
    hex_message = sp.get("hex_message", "5A435A43")  # "ZCZC"
    sym_rate = float(sp.get("symbol_rate", 100.0))
    shift_hz = float(sp.get("shift_hz", 170.0))
    center_hz = float(sp.get("center_hz", 0.0))
    mode = str(sp.get("mode", "F1B")).upper()

    pre_ms = float(sp.get("pre_silence_ms", 25.0))
    post_ms = float(sp.get("post_silence_ms", 25.0))
    carrier_sec = float(sp.get("carrier_sec", 0.0))
    noise_dbfs = float(sp.get("noise_dbfs", -60.0))
    normalize = bool(sp.get("normalize", True))
    save_path: Optional[str] = sp.get("save_path", None)
    rng_seed = int(sp.get("rng_seed", 12345))

    if sym_rate <= 0.0:
        raise ValueError("symbol_rate must be > 0")
    if shift_hz <= 0.0:
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
        # instantaneous frequency = center_hz + nrz * (shift_hz/2)
        inst_freq = np.repeat(center_hz + (shift_hz * 0.5) * nrz, sps).astype(np.float32)
        dphi = (2.0 * np.pi * inst_freq / Fs).astype(np.float32)
        phase = np.cumsum(dphi, dtype=np.float64).astype(np.float32)
        mod = np.exp(1j * phase).astype(np.complex64)

    elif mode == "J2B":
        # audio AFSK with tones 1700±85 Hz; put in I channel and return complex for convenience
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
        inter[1::2] = sig.imag.astype(np.float32, copy=False)
        with open(save_path, "wb") as f:
            inter.tofile(f)

    return sig

if __name__ == "__main__":
    # Quick self-test: 518 kHz baseband-like file (at low Fs just to validate I/O path)
    params = {
        "device": {"fs_tx": 48000},
        "standard_params": {
            "hex_message": "5A435A43",  # "ZCZC"
            "symbol_rate": 100.0,
            "shift_hz": 170.0,
            "center_hz": 0.0,
            "mode": "F1B",
            "pre_silence_ms": 50.0,
            "carrier_sec": 0.2,
            "post_silence_ms": 50.0,
            "noise_dbfs": -55.0,
            "normalize": True,
            "save_path": "/mnt/data/navtex_F1B_100bd_170shift_48k.iq"
        }
    }
    iq = generate_navtex(params)
    print({"samples": int(iq.size), "fs": int(params["device"]["fs_tx"]), "path": "/mnt/data/navtex_F1B_100bd_170shift_48k.iq"})
