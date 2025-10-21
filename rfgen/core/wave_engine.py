import numpy as np


# ==================== Вспомогательные функции для PSK-406 ====================

def _hex_to_bits(hex_message: str) -> np.ndarray:
    """Конвертация HEX-строки в массив битов."""
    s = "".join(hex_message.split()).lower()
    if len(s) % 2 != 0:
        raise ValueError("HEX length must be even")
    try:
        data = bytes.fromhex(s)
    except ValueError as e:
        raise ValueError(f"Invalid HEX: {e}")
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    return bits.astype(np.uint8)


def _phase_ramp(start: float, stop: float, n: int) -> np.ndarray:
    """Линейный переход фазы для плавных фронтов (в радианах)."""
    return np.linspace(start, stop, n, endpoint=False, dtype=np.float32)


def _clip_norm(x: np.ndarray, peak: float = 0.999) -> np.ndarray:
    """Нормализация к заданному пику."""
    m = np.max(np.abs(x)) if x.size else 1.0
    if m == 0.0:
        return x
    if m > peak:
        x = (x / m) * peak
    return x


# ==================== Генерация базовых сигналов ====================

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

def build_psk406(profile: dict) -> np.ndarray:
    """
    Генерация PSK-406 сигнала (COSPAS-SARSAT 406 MHz).

    Параметры из profile["standard_params"]:
    - hex_message: HEX-сообщение (например, "FFFED080020000007FDFFB0020B783E0F66C")
    - phase_low: нижний уровень фазы (рад), по умолчанию -1.1
    - phase_high: верхний уровень фазы (рад), по умолчанию 1.1
    - front_samples: длительность плавного фронта (сэмплы), по умолчанию 75
    - carrier_sec: длительность несущей перед сообщением (сек), по умолчанию 0.16
    - pre_silence_ms: тишина перед несущей (мс), по умолчанию 25
    - post_silence_ms: тишина после сообщения (мс), по умолчанию 25

    Возвращает: IQ-буфер (complex64) с BPSK-манчестер модуляцией, 400 бод.
    """
    fs = int(profile["device"]["fs_tx"])
    std_params = profile.get("standard_params", {})

    # Параметры PSK-406
    hex_message = std_params.get("hex_message", "FFFED080020000007FDFFB0020B783E0F66C")
    phase_low = float(std_params.get("phase_low", -1.1))
    phase_high = float(std_params.get("phase_high", 1.1))
    front_samples = int(std_params.get("front_samples", 75))
    carrier_sec = float(std_params.get("carrier_sec", 0.16))
    pre_silence_ms = float(std_params.get("pre_silence_ms", 25.0))
    post_silence_ms = float(std_params.get("post_silence_ms", 25.0))

    # Schedule параметры (ТЗ 2025-10-21_406_LOOP)
    schedule = profile.get("schedule", {})
    mode = schedule.get("mode", "loop")
    gap_s = float(schedule.get("gap_s", 8.0))

    # Для mode=="loop": gap встраивается в пост-тишину
    # Для mode=="repeat": gap добавляется backend'ом между кадрами
    if mode == "loop":
        post_silence_ms = gap_s * 1000.0

    # Константы для PSK-406
    bit_rate_bps = 400.0
    bit_samples = int(round(fs / bit_rate_bps))
    half = bit_samples // 2

    # Валидация
    if bit_samples < 10:
        raise ValueError(f"bit_samples={bit_samples} too small; increase fs_tx")
    if front_samples >= half // 2:
        raise ValueError(f"front_samples={front_samples} must be < bit_samples/4 (={half//2})")

    # Преобразование HEX → биты
    bits = _hex_to_bits(hex_message)

    # Подготовка секций
    pre_N = int(round(pre_silence_ms * 1e-3 * fs))
    post_N = int(round(post_silence_ms * 1e-3 * fs))
    carr_N = int(round(carrier_sec * fs))

    # Тишина (нули)
    pre = np.zeros(pre_N, dtype=np.complex64) if pre_N > 0 else np.zeros(0, dtype=np.complex64)

    # Несущая (фаза 0)
    carrier = np.ones(carr_N, dtype=np.complex64) if carr_N > 0 else np.zeros(0, dtype=np.complex64)

    # Генерация PSK-сообщения с плавными переходами
    msg = np.zeros(bits.size * bit_samples, dtype=np.complex64)

    def _seg(prev_phase: float, target_phase: float, segN: int, frontN: int) -> np.ndarray:
        """Создать сегмент с плавным переходом от prev_phase к target_phase."""
        if segN <= 0:
            return np.zeros(0, dtype=np.complex64)
        rampN = min(frontN, segN)
        if rampN > 0:
            ramp = _phase_ramp(prev_phase, target_phase, rampN)
            steadyN = segN - rampN
            if steadyN > 0:
                phase_vec = np.concatenate([ramp, np.full(steadyN, target_phase, dtype=np.float32)])
            else:
                phase_vec = ramp
        else:
            phase_vec = np.full(segN, target_phase, dtype=np.float32)
        return np.exp(1j * phase_vec).astype(np.complex64)

    idx = 0
    prev_phase = 0.0  # Начинаем с нулевой фазы (переход от несущей)

    # Манчестер кодирование: каждый бит разбивается на две полубита с противоположными фазами
    for b in bits:
        # Бит 0: первая половина = phase_low,  вторая половина = phase_high
        # Бит 1: первая половина = phase_high, вторая половина = phase_low
        first = phase_low if b == 0 else phase_high
        second = phase_high if b == 0 else phase_low

        # Первая полубита
        seg1 = _seg(prev_phase, first, half, front_samples)
        prev_phase = float(first)

        # Вторая полубита
        seg2 = _seg(prev_phase, second, bit_samples - half, front_samples)
        prev_phase = float(second)

        msg[idx:idx+half] = seg1
        msg[idx+half:idx+bit_samples] = seg2
        idx += bit_samples

    # Тишина после
    post = np.zeros(post_N, dtype=np.complex64) if post_N > 0 else np.zeros(0, dtype=np.complex64)

    # Склейка всех секций
    sig = np.concatenate([pre, carrier, msg, post]).astype(np.complex64)

    # Нормализация к безопасному уровню
    # ВАЖНО: генератор выдаёт чистый baseband (0 Гц)
    # Цифровая компенсация IF+corr выполняется в backend (hackrf.py)
    sig = _clip_norm(sig, peak=0.95)

    return sig


def build_iq(profile: dict, frame_s: float = 1.0):
    """
    Генерация IQ-буфера на основе профиля.

    Для standard="c406" или "psk406" вызывает build_psk406().
    Для остальных стандартов использует pattern + modulation.
    """
    standard = profile.get("standard", "basic")

    # PSK-406: специальная обработка
    if standard in ("c406", "psk406"):
        return build_psk406(profile)

    # 121.5 MHz AM: специальная обработка (как PSK-406 по расписанию/loop)
    if standard == "121":
        # импорт локально, чтобы избежать циклов импортов
        from ..standards.am_121p5 import generate_121p5
        # передаём длительность кадра «мягко» через служебное поле
        prof = dict(profile)
        prof["_frame_s"] = frame_s
        return generate_121p5(prof)

    # NAVTEX: специальная обработка (FSK SITOR-B)
    if standard == "navtex":
        # импорт локально, чтобы избежать циклов импортов
        from ..standards.navtex import build_navtex
        return build_navtex(profile)

    # Базовая генерация (basic, ais, dsc_vhf, и т.д.)
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
