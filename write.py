import numpy as np


def write_bits_to_mask(
    image: np.ndarray,
    mask: np.ndarray,
    bitstream: str,
    bits_per_pixel: int = 16
) -> np.ndarray:
    """Записывает битовую последовательность в незамаскированные области изображения.
    
    Args:
        image: Исходное изображение
        mask: Бинарная маска (True - защищенные пиксели)
        bitstream: Битовая строка для записи
        bits_per_pixel: Глубина цвета (8/16 бит)

    Returns:
        np.ndarray: Модифицированное изображение

    Raises:
        ValueError: Если битовая строка превышает доступную емкость
    """
    flat_image = image.flatten()
    flat_mask = mask.flatten()
    
    bit_idx = 0
    for i in range(len(flat_image)):
        if not flat_mask[i] :
            if(bit_idx < len(bitstream)):
                # Извлекаем блок бит (16 бит для uint16)
                bits = bitstream[bit_idx:bit_idx + bits_per_pixel]
                if len(bits) < bits_per_pixel:
                    bits = bits.ljust(bits_per_pixel, '0')  # Дополняем нулями, если бит не хватает
                
                # Записываем биты в пиксель
                flat_image[i] = int(bits, 2)
                bit_idx += bits_per_pixel
            else:
                flat_image[i] = 0
    
    return flat_image.reshape(image.shape)