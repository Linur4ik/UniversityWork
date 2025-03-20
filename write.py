import numpy as np


def write_bits_to_mask(image, mask, bitstream, bits_per_pixel=16):
    """
    Записывает биты в доступные области изображения.
    :param image: Исходное изображение (numpy array).
    :param mask: Маска (True = скрытая область, False = доступная для записи).
    :param bitstream: Битовая строка для записи.
    :param bits_per_pixel: Количество бит на пиксель (8 для uint8, 16 для uint16).
    :return: Изображение с записанными битами.
    """
    flat_image = image.flatten()
    flat_mask = mask.flatten()
    
    bit_idx = 0
    for i in range(len(flat_image)):
        if not flat_mask[i] and bit_idx < len(bitstream):
            # Извлекаем блок бит (16 бит для uint16)
            bits = bitstream[bit_idx:bit_idx + bits_per_pixel]
            if len(bits) < bits_per_pixel:
                bits = bits.ljust(bits_per_pixel, '0')  # Дополняем нулями, если бит не хватает
            
            # Записываем биты в пиксель
            flat_image[i] = int(bits, 2)
            bit_idx += bits_per_pixel
    
    return flat_image.reshape(image.shape)