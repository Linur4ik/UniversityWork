import numpy as np
from matplotlib.path import Path
import struct
from codecs import decode



def generate_shutter_mask(image_shape, shutter_params):
    """Создание маски на основе параметров шторки (включая полигональную)"""
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

        # # Полигональная шторка
        # vertices = shutter_params.get('vertices', [])
        # if len(vertices) < 6 or len(vertices) % 2 != 0:
        #     raise ValueError("Invalid polygon vertices format")
        
        # # Преобразование координат в формат [(x1,y1), (x2,y2)...]
        # print(vertices)
        # poly_points = np.array([(vertices[i], vertices[i+1]) 
        #                       for i in range(0, len(vertices), 2)])
        
        # # Создание сетки координат
        # x, y = np.meshgrid(np.arange(w), np.arange(h))
        # x, y = x.flatten(), y.flatten()
        # points = np.vstack((x,y)).T
        
        # # Проверка принадлежности точек полигону
        # path = Path(poly_points)
        # grid = path.contains_points(points)
        # mask = grid.reshape(h, w)
    
    else:
        raise ValueError(f"Unsupported shutter type: {shutter_params['type']}")
    
    # Инвертируем маску, чтобы True = область вне шторки
    return ~mask







# def bin_to_float64(b):
#     bf = decode('%%0%dx' % (8 << 1) % int(b, 2), 'hex')[-8:] # 8 bytes needed for IEEE 754 binary64.
#     return struct.unpack('>d', bf)[0]

