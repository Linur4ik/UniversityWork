import pydicom
from pydicom.tag import Tag

FORBIDDEN_TAGS = {
    # Шторки
    (0x0018, 0x1600), (0x0018, 0x1602), (0x0018, 0x1604), (0x0018, 0x1606), (0x0018, 0x1608),
    (0x0018, 0x1610), (0x0018, 0x1611), (0x0018, 0x1612), (0x0018, 0x1620),
    # Пиксельные атрибуты
    (0x0028, 0x0010), (0x0028, 0x0011), (0x0028, 0x0002), (0x0028, 0x0004),
    (0x0028, 0x0100), (0x0028, 0x0101), (0x0028, 0x0103)
}

SUPPORTED_VR = {'US', 'SS', 'UL', 'SL', 'FL', 'FD', 'IS', 'PN', 'LO', 'LT', 'SH', 'OB', 'OW'}

def update_dicom_shutter_tags(ds, shutter_params):
    """Обновляет теги шторки в DICOM объекте согласно переданным параметрам.
    
    Args:
        ds: DICOM dataset
        shutter_params: словарь с параметрами шторки (тип и координаты)
    """
    tags = [(0x0018, 0x1600), (0x0018, 0x1602), (0x0018, 0x1604), 
            (0x0018, 0x1606), (0x0018, 0x1608), (0x0018, 0x1610),
            (0x0018, 0x1611), (0x0018, 0x1612), (0x0018, 0x1620)]
    
    for tag in tags:
        if tag in ds: 
            del ds[tag]
    
    ds.add_new((0x0018, 0x1600), 'CS', shutter_params['type'])
    
    if shutter_params['type'] == "RECTANGULAR":
        ds.add_new((0x0018, 0x1602), 'IS', str(shutter_params['left']))
        ds.add_new((0x0018, 0x1604), 'IS', str(shutter_params['right']))
        ds.add_new((0x0018, 0x1606), 'IS', str(shutter_params['top']))
        ds.add_new((0x0018, 0x1608), 'IS', str(shutter_params['bottom']))
    elif shutter_params['type'] == "CIRCULAR":
        ds.add_new((0x0018, 0x1610), 'IS', str(shutter_params['center_x']))
        ds.add_new((0x0018, 0x1611), 'IS', str(shutter_params['center_y']))
        ds.add_new((0x0018, 0x1612), 'IS', str(shutter_params['radius']))
    else:  # POLYGONAL
        flat = [coord for pt in shutter_params['vertices'] for coord in pt]
        ds.add_new((0x0018, 0x1620), 'IS', flat)