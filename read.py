import pydicom
from typing import Dict, Optional, List




def read_shutter_parameters(dcm_path: str) -> Optional[Dict]:
    """
    Чтение параметров шторки из DICOM-файла.
    Возвращает словарь с параметрами или None, если шторка не найдена.
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

def _parse_dicom_int(value) -> Optional[int]:
    """Парсинг DICOM integer string (IS)"""
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None