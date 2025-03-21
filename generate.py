import numpy as np
from matplotlib.path import Path
from typing import Dict, Tuple
from codecs import decode




def generate_shutter_mask(
    image_shape: Tuple[int, int], 
    shutter_params: Dict
    ) -> np.ndarray:
    """Генерирует бинарную маску области изображения, закрытую шторкой.
    
    Поддерживает типы: прямоугольная, круговая и полигональная шторки.

    Args:
        image_shape: Размер изображения (высота, ширина)
        shutter_params: Словарь параметров шторки:
            - type: Тип шторки (RECTANGULAR/CIRCULAR/POLYGONAL)
            - Дополнительные параметры в зависимости от типа

    Returns:
        np.ndarray: Бинарная маска (True - открытая область, False - закрытая)

    Raises:
        ValueError: При указании неподдерживаемого типа шторки
    """
    mask = np.ones(image_shape, dtype=bool)
    h, w = image_shape
    
    if shutter_params['type'] == "RECTANGULAR":
        # Прямоугольная шторка
        x_min = shutter_params.get('left', 0)
        x_max = shutter_params.get('right', w)
        y_min = shutter_params.get('top', 0)
        y_max = shutter_params.get('bottom', h)
        mask[y_min:y_max, x_min:x_max] = False
    
    elif shutter_params['type'] == "CIRCULAR":
        # Круговая шторка
        center = (shutter_params.get('center_x', w//2), 
                 shutter_params.get('center_y', h//2))
        radius = shutter_params.get('radius', min(w, h)//2)
        Y, X = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)
        mask = dist_from_center <= radius
        mask = ~mask
    
    elif shutter_params['type'] == "POLYGONAL":
        vertices = shutter_params['vertices']
        path = Path(vertices)
        y, x = np.mgrid[:image_shape[0], :image_shape[1]]
        points = np.vstack((x.ravel(), y.ravel())).T
        mask = ~path.contains_points(points).reshape(image_shape)  # Открываем полигон
    
    else:
        raise ValueError(f"Unsupported shutter type: {shutter_params['type']}")
    
    # Инвертируем маску, чтобы True = область вне шторки
    return ~mask

