"""AIS (Automatic Identification System) signal generator.

Generates GMSK modulated AIS signals with:
- 9600 bps bit rate
- BT ≈ 0.4 (Gaussian filter bandwidth-time product)
- NRZI encoding (optional)
- Scrambler (optional)
- HDLC framing (optional)
"""

import numpy as np


def _generate_gaussian_filter(bt: float, samples_per_symbol: int, span_symbols: int = 4) -> np.ndarray:
    """Генерация гауссова фильтра для GMSK.

    Args:
        bt: Bandwidth-time product (обычно 0.3-0.5)
        samples_per_symbol: Количество отсчётов на символ
        span_symbols: Длина фильтра в символах

    Returns:
        Нормализованные коэффициенты фильтра
    """
    n_taps = samples_per_symbol * span_symbols
    if n_taps % 2 == 0:
        n_taps += 1  # Нечётное число для симметрии

    # Стандартное отклонение для гауссова фильтра
    # sigma = sqrt(ln(2)) / (2 * pi * BT)
    sigma = np.sqrt(np.log(2)) / (2.0 * np.pi * bt)

    # Временная ось относительно центра фильтра
    t = np.arange(n_taps, dtype=np.float64) - (n_taps - 1) / 2.0
    t = t / float(samples_per_symbol)  # Нормализация к символьным интервалам

    # Гауссов импульс
    h = np.exp(-0.5 * (t / sigma) ** 2)

    # Нормализация (сумма коэффициентов = 1)
    h = h / np.sum(h)

    return h.astype(np.float32)


def _bits_to_nrz(bits: np.ndarray) -> np.ndarray:
    """Конвертация битов в NRZ формат: 0 → -1, 1 → +1."""
    return 2.0 * bits.astype(np.float32) - 1.0


def _apply_nrzi(bits: np.ndarray) -> np.ndarray:
    """Применение NRZI кодирования (Non-Return-to-Zero Inverted).

    NRZI: изменение состояния при '1', без изменения при '0'.
    """
    nrzi = np.zeros(len(bits), dtype=np.uint8)
    state = 0
    for i, bit in enumerate(bits):
        if bit == 1:
            state = 1 - state  # Инверсия
        nrzi[i] = state
    return nrzi


def _gmsk_modulate(bits: np.ndarray, fs: int, bitrate: int = 9600, bt: float = 0.4) -> np.ndarray:
    """GMSK модуляция битового потока.

    Args:
        bits: Массив битов (0/1)
        fs: Частота дискретизации (Hz)
        bitrate: Скорость передачи (bps), по умолчанию 9600
        bt: Bandwidth-time product, по умолчанию 0.4

    Returns:
        Комплексный IQ-буфер (complex64)
    """
    if len(bits) == 0:
        return np.array([], dtype=np.complex64)

    # Количество отсчётов на символ
    samples_per_symbol = int(fs / bitrate)
    if samples_per_symbol < 2:
        raise ValueError(f"Fs={fs} слишком мала для bitrate={bitrate}")

    # Конвертация битов в NRZ
    nrz = _bits_to_nrz(bits)

    # Upsampling: вставка нулей между символами
    nrz_upsampled = np.zeros(len(nrz) * samples_per_symbol, dtype=np.float32)
    nrz_upsampled[::samples_per_symbol] = nrz

    # Гауссов фильтр
    gauss_filter = _generate_gaussian_filter(bt, samples_per_symbol)

    # Фильтрация
    filtered = np.convolve(nrz_upsampled, gauss_filter, mode='same')

    # MSK: фазовый сдвиг ±π/2 на символ
    # Для GMSK: интегрируем отфильтрованный сигнал для получения фазы
    # Девиация частоты для MSK: Δf = bitrate/4
    deviation_hz = bitrate / 4.0

    # Мгновенная частота: f(t) = deviation * filtered(t)
    # Фаза: φ(t) = 2π * ∫f(t)dt = 2π * deviation * cumsum(filtered) / fs
    phase = 2.0 * np.pi * deviation_hz * np.cumsum(filtered) / float(fs)

    # Комплексный сигнал
    iq = np.exp(1j * phase).astype(np.complex64)

    return iq


def _hex_to_bits(hex_string: str) -> np.ndarray:
    """Конвертация HEX строки в массив битов (MSB first)."""
    s = "".join(hex_string.split()).lower()
    if len(s) % 2 != 0:
        raise ValueError("HEX length must be even")
    try:
        data = bytes.fromhex(s)
    except ValueError as e:
        raise ValueError(f"Invalid HEX: {e}")
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    return bits.astype(np.uint8)


def _parse_nmea_vdm(nmea_string: str) -> tuple:
    """Упрощённый парсер NMEA VDM/VDO.

    Формат: !AIVDM,fragments,fragment_num,message_id,channel,payload,fill_bits*checksum

    Returns:
        (payload_6bit, fill_bits) или (None, None) при ошибке
    """
    nmea_string = nmea_string.strip()

    # Проверка формата
    if not (nmea_string.startswith("!AIVDM") or nmea_string.startswith("!AIVDO")):
        return None, None

    # Удаление checksum
    if '*' in nmea_string:
        nmea_string = nmea_string.split('*')[0]

    # Разбор полей
    parts = nmea_string.split(',')
    if len(parts) < 6:
        return None, None

    payload_6bit = parts[5]  # 6-битный payload

    # Fill bits (если есть)
    fill_bits = 0
    if len(parts) >= 7:
        try:
            fill_bits = int(parts[6].split('*')[0])
        except (ValueError, IndexError):
            fill_bits = 0

    return payload_6bit, fill_bits


def _decode_6bit_ascii(payload_6bit: str) -> np.ndarray:
    """Декодирование 6-битного ASCII payload в биты.

    AIS использует специальную 6-битную кодировку ASCII.
    """
    bits = []
    for char in payload_6bit:
        # 6-битная кодировка AIS: ASCII 48-87 ('0'-'W') и 96-119 ('`'-'w')
        code = ord(char)
        if 48 <= code <= 87:
            value = code - 48
        elif 96 <= code <= 119:
            value = code - 56
        else:
            raise ValueError(f"Invalid 6-bit character: {char}")

        # Конвертация в 6 битов (MSB first)
        for i in range(5, -1, -1):
            bits.append((value >> i) & 1)

    return np.array(bits, dtype=np.uint8)


def build_ais(profile: dict) -> np.ndarray:
    """Генерация AIS IQ-буфера из профиля.

    Args:
        profile: Профиль с параметрами AIS

    Returns:
        IQ-буфер (complex64) с GMSK модуляцией
    """
    fs = int(profile["device"]["fs_tx"])
    std_params = profile.get("standard_params", {})

    # Параметры GMSK
    bitrate = int(std_params.get("bitrate", 9600))
    bt = float(std_params.get("bt", 0.4))

    # Режим ввода
    input_mode = std_params.get("input_mode", "hex")

    # PHY параметры (для будущего)
    use_nrzi = bool(std_params.get("use_nrzi", False))
    use_scrambler = bool(std_params.get("use_scrambler", False))
    add_header = bool(std_params.get("add_header", False))

    # Получение битов из сообщения
    if input_mode == "nmea":
        # Режим NMEA VDM/VDO
        nmea_string = std_params.get("nmea_message", "")
        payload_6bit, fill_bits = _parse_nmea_vdm(nmea_string)

        if payload_6bit is None:
            raise ValueError("Invalid NMEA VDM/VDO message format")

        # Декодирование 6-битного payload в биты
        bits = _decode_6bit_ascii(payload_6bit)

        # Удаление fill bits (если есть)
        if fill_bits > 0:
            bits = bits[:-fill_bits]
    else:
        # Режим Direct HEX (по умолчанию)
        hex_message = std_params.get("hex_message", "")
        if not hex_message:
            raise ValueError("HEX message is empty")

        bits = _hex_to_bits(hex_message)

    # Применение NRZI (опционально)
    if use_nrzi:
        bits = _apply_nrzi(bits)

    # TODO: Scrambler (если use_scrambler=True)
    # TODO: HDLC framing (если add_header=True)

    # GMSK модуляция
    iq = _gmsk_modulate(bits, fs, bitrate, bt)

    # Добавление тишины в начале и конце (опционально)
    pre_silence_ms = float(std_params.get("pre_silence_ms", 25))
    post_silence_ms = float(std_params.get("post_silence_ms", 25))

    pre_samples = int(fs * pre_silence_ms / 1000.0)
    post_samples = int(fs * post_silence_ms / 1000.0)

    if pre_samples > 0:
        iq = np.concatenate([np.zeros(pre_samples, dtype=np.complex64), iq])
    if post_samples > 0:
        iq = np.concatenate([iq, np.zeros(post_samples, dtype=np.complex64)])

    # Нормализация к безопасному уровню (≤0.8)
    max_amp = np.max(np.abs(iq))
    if max_amp > 0.8:
        iq = iq * (0.8 / max_amp)

    return iq


# Обратная совместимость (старая заглушка)
def generate_ais_test(params):
    """Deprecated: используйте build_ais(profile) вместо этого."""
    return build_ais(params)
