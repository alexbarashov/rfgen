"""
Common DSC (Digital Selective Calling) framing functions.

This module contains protocol-level functions shared by both DSC VHF and DSC HF:
- 10-bit character encoding (7 info bits + 3 error check bits)
- Dotting and phasing sequences
- Frame assembly per ITU-R M.493
- Primary symbol builders for different call types

Usage:
    from rfgen.standards.dsc_common import build_dsc_bits, build_primary_symbols_from_cfg

    # Build primary symbols from config
    dsc_cfg = {
        "scenario": "all_ships",
        "mmsi": "123456789",
        "mmsi_from": "987654321",
        "category_symbol": 100,
    }
    primary_symbols = build_primary_symbols_from_cfg(dsc_cfg)

    # Convert to bitstream
    bits = build_dsc_bits(primary_symbols, eos_symbol=127)
"""

import numpy as np
from typing import List


# =============================
# Low-level DSC encoding
# =============================

def _symbol_to_primary7(sym: int) -> np.ndarray:
    """Convert symbol (0-127) to 7 info bits MSB-first: b6,b5,...,b0."""
    if not (0 <= sym <= 127):
        raise ValueError("Symbol out of range 0..127")
    return np.array([(sym >> k) & 1 for k in range(6, -1, -1)], dtype=np.uint8)


def _primary7_to_tenbit(info7: np.ndarray) -> np.ndarray:
    """Add 3-bit zero-count (MSB-first) to 7 MSB-first info bits."""
    zeros = 7 - int(info7.sum())
    chk = np.array([(zeros >> 2) & 1, (zeros >> 1) & 1, zeros & 1], dtype=np.uint8)
    return np.concatenate([info7, chk])


def _symbols_to_tenbits(symbols: List[int]) -> List[np.ndarray]:
    """Convert list of symbols to list of 10-bit arrays."""
    return [_primary7_to_tenbit(_symbol_to_primary7(s)) for s in symbols]


def _tenbits_to_bitstream(chars10: List[np.ndarray]) -> np.ndarray:
    """Concatenate 10-bit arrays into a single bitstream."""
    if not chars10:
        return np.zeros(0, np.uint8)
    return np.concatenate(chars10).astype(np.uint8)


# =============================
# DSC frame structure
# =============================

def _build_dotting(n: int = 120) -> List[int]:
    """Build dotting sequence: repeat symbol 126."""
    return [126] * n


def _build_phasing_rx(repeats: int = 2) -> List[int]:
    """Build phasing (RX) sequence: 111..104, repeated."""
    base = [111, 110, 109, 108, 107, 106, 105, 104]
    return base * repeats


def _time_diversity_schedule(payload_syms: List[int]) -> List[int]:
    """Apply time diversity interleaving (optional, currently disabled in frame builder)."""
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
    """
    Build complete DSC frame per ITU-R M.493.

    Structure:
    - Dotting (120 symbols of 126)
    - Phasing (111..104, repeated twice)
    - Format specifier (FS, duplicated)
    - Primary symbols (payload)
    - End of sequence (EOS, symbol 127)

    Args:
        primary_symbols: Payload symbols (without FS at start)
        fs_symbol: Format specifier symbol (first symbol of message)
        eos_symbol: End of sequence symbol (default 127)
        include_eos: Whether to append EOS symbol

    Returns:
        Complete symbol sequence
    """
    # Dotting + Phasing
    prefix = _build_dotting(120) + _build_phasing_rx(2)
    # Mandatory FS duplication
    header = [fs_symbol, fs_symbol]
    payload = list(primary_symbols)
    if include_eos:
        payload.append(eos_symbol)
    # Note: Time diversity disabled for cleaner receiver testing
    return prefix + header + payload


# =============================
# Helper converters
# =============================

def _digits_to_symbols(digits: str) -> List[int]:
    """Convert digit string to list of two-digit symbols (00-99)."""
    s = ''.join(ch for ch in digits if ch.isdigit())
    if len(s) % 2 == 1:
        s += '0'
    return [int(s[i:i+2]) for i in range(0, len(s), 2)]


def _mmsi_to_symbols(mmsi: str) -> List[int]:
    """
    Convert MMSI string to 5 two-digit symbols (pads with leading zeros).

    Args:
        mmsi: MMSI string (typically 9 digits)

    Returns:
        List of 5 symbols (00-99 each)
    """
    s = ''.join(ch for ch in mmsi if ch.isdigit())
    s = s.zfill(9)  # MMSI is 9 digits
    # Pad to even length and split by 2
    if len(s) % 2 == 1:
        s = '0' + s
    pairs = [int(s[i:i+2]) for i in range(0, len(s), 2)]
    # Ensure exactly 5 symbols
    if len(pairs) < 5:
        pairs = [0] * (5 - len(pairs)) + pairs
    elif len(pairs) > 5:
        pairs = pairs[-5:]
    return pairs


# =============================
# High-level builders
# =============================

def build_dsc_bits(primary_symbols: List[int], eos_symbol: int = 127) -> np.ndarray:
    """
    Build complete DSC bitstream from primary symbols.

    Args:
        primary_symbols: List of primary symbols including FS at start
        eos_symbol: End of sequence symbol (default 127)

    Returns:
        Bitstream (uint8 array of 0/1 values)
    """
    fs_symbol = primary_symbols[0]
    seq_syms = _build_dsc_frame(primary_symbols[1:], fs_symbol=fs_symbol, eos_symbol=eos_symbol, include_eos=True)
    tenbits = _symbols_to_tenbits(seq_syms)
    bits = _tenbits_to_bitstream(tenbits)
    return bits.astype(np.uint8)


def build_primary_symbols_from_cfg(dsc_cfg: dict) -> List[int]:
    """
    Build primary symbol list from flexible config.

    Priority:
    1. Explicit 'primary_symbols' (highest)
    2. Scenario-based helpers
    3. Default All Ships call

    Config fields:
        primary_symbols: explicit list[int] 0..127 (highest priority)
        scenario: 'all_ships' | 'individual' | 'distress' (lab presets)
        format_symbol: int (default per scenario)
        mmsi: target MMSI string
        mmsi_from: source MMSI string
        category_symbol: int (default 100 = Routine)
        telecommand_symbols: list[int] extras (e.g., [126,126])

    Returns:
        List of primary symbols (first is format specifier)
    """
    # 1) Direct override
    ps = dsc_cfg.get("primary_symbols", None)
    if isinstance(ps, (list, tuple)) and len(ps) > 0:
        return [int(x) for x in ps]

    # 2) Scenario-based
    scenario = str(dsc_cfg.get("scenario", "all_ships")).lower()
    fmt = dsc_cfg.get("format_symbol", None)
    if fmt is None:
        if scenario == "individual":
            fmt = 115  # or 123
        elif scenario == "distress":
            fmt = 112
        else:
            fmt = 116  # all_ships default

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


def _build_test_all_ships_sequence(mmsi: str = "111222333") -> List[int]:
    """Build simple test sequence for All Ships call."""
    fmt = 112
    addr = _digits_to_symbols(mmsi)
    tele = [126, 126]
    return [fmt] + addr + tele
