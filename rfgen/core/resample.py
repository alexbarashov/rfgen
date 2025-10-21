import numpy as np


def resample(iq: np.ndarray, fs_in: int, fs_out: int) -> np.ndarray:
    """
    Линейный ресемплинг IQ-буфера.

    Параметры:
    - iq: входной IQ-массив (complex64)
    - fs_in: входная частота дискретизации (Гц)
    - fs_out: выходная частота дискретизации (Гц)

    Возвращает: IQ-массив с новой частотой дискретизации.

    Примечания:
    - Если fs_in == fs_out, возвращается копия входного массива
    - Использует линейную интерполяцию numpy.interp
    - Для пустого входа возвращает пустой массив
    """
    # Валидация
    if fs_in <= 0 or fs_out <= 0:
        raise ValueError(f"Invalid sample rates: fs_in={fs_in}, fs_out={fs_out}")

    # Если частоты совпадают, возвращаем копию
    if fs_in == fs_out:
        return iq.copy()

    # Если входной массив пустой
    if iq.size == 0:
        return np.zeros(0, dtype=np.complex64)

    # Рассчитываем длительность и новое количество сэмплов
    duration_s = iq.size / float(fs_in)
    N_out = int(round(duration_s * fs_out))

    # Защита от вырожденных случаев
    if N_out <= 0:
        return np.zeros(0, dtype=np.complex64)
    if N_out == 1:
        return iq[:1].copy()

    # Линейная интерполяция
    x = np.arange(iq.size, dtype=np.float64)
    xi = np.linspace(0.0, iq.size - 1.0, N_out, dtype=np.float64)

    # Интерполируем I и Q отдельно для точности
    i_interp = np.interp(xi, x, iq.real.astype(np.float64))
    q_interp = np.interp(xi, x, iq.imag.astype(np.float64))

    # Собираем обратно в complex64
    result = (i_interp.astype(np.float32) + 1j * q_interp.astype(np.float32)).astype(np.complex64)

    # Финальная валидация: результат не должен быть пустым
    if result.size < 8:
        raise ValueError(f"Resample resulted in too few samples: {result.size} (expected ~{N_out})")

    return result
