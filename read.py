import pydicom
from typing import Dict, Optional, List
import numpy as np  


def read_bits_from_mask(
    image: np.ndarray,
    mask: np.ndarray,
    bits_per_pixel: int = 16
    ) -> str:
    """Извлекает битовую последовательность из незамаскированных областей изображения.
    
    Args:
        image: Исходное изображение в виде numpy-массива
        mask: Бинарная маска (True - скрытые пиксели)
        bits_per_pixel: Глубина цвета (8/16 бит)

    Returns:
        str: Извлеченная битовая строка
    """
    flat_image = image.flatten()
    flat_mask = mask.flatten()
    
    bitstream = ''
    for i in range(len(flat_image)):
        if not flat_mask[i]:
            # Извлекаем биты из пикселя
            bits = format(flat_image[i], f'0{bits_per_pixel}b')
            bitstream += bits
    
    return bitstream


def read_shutter_parameters(dcm_path: str) -> Optional[Dict]:
    """Извлекает параметры шторки из DICOM-файла.
    
    Args:
        dcm_path: Путь к DICOM-файлу

    Returns:
        Dict | None: Словарь параметров или None если шторка отсутствует
    """
    try:
        ds = pydicom.dcmread(dcm_path, force=True)
    except Exception as e:
        print(f"Ошибка чтения файла: {e}")
        return None

    shutter_type_tag = (0x0018, 0x1600)
    if shutter_type_tag not in ds:
        return None

    params = {"type": ds[shutter_type_tag].value}

    # Для полигональной шторки
    if params["type"] == "POLYGONAL":
        vertices_tag = (0x0018, 0x1620)
        if vertices_tag in ds:
            params["vertices"] = list(ds[vertices_tag].value)

    # Для прямоугольной шторки
    elif params["type"] == "RECTANGULAR":
        coords = {
            "left": (0x0018, 0x1602),
            "right": (0x0018, 0x1604),
            "top": (0x0018, 0x1606),
            "bottom": (0x0018, 0x1608)
        }
        for key, tag in coords.items():
            if tag in ds:
                params[key] = _parse_dicom_int(ds[tag].value)

    # Для круговой шторки
    elif params["type"] == "CIRCULAR":
        radius_tag = (0x0018, 0x1612)
        if radius_tag in ds:
            params["radius"] = _parse_dicom_int(ds[radius_tag].value)
        
        # Центр по умолчанию
        params["center_x"] = ds.get((0x0018, 0x1610), ds.Columns//2)
        params["center_y"] = ds.get((0x0018, 0x1611), ds.Rows//2)

    return params if len(params) > 1 else None

def _parse_dicom_int(value: str) -> Optional[int]:
    """Парсит DICOM-значения типа Integer String (IS).
    
    Args:
        value: Сырое значение из DICOM-тега

    Returns:
        int | None: Распарсенное целое число
    """
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None