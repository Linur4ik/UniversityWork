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
    
    elif shutter_params['type'] == "POLYGONAL":
        # Полигональная шторка
        vertices = shutter_params.get('vertices', [])
        if len(vertices) < 6 or len(vertices) % 2 != 0:
            raise ValueError("Invalid polygon vertices format")
        
        # Преобразование координат в формат [(x1,y1), (x2,y2)...]
        poly_points = np.array([(vertices[i], vertices[i+1]) 
                              for i in range(0, len(vertices), 2)])
        
        # Создание сетки координат
        x, y = np.meshgrid(np.arange(w), np.arange(h))
        x, y = x.flatten(), y.flatten()
        points = np.vstack((x,y)).T
        
        # Проверка принадлежности точек полигону
        path = Path(poly_points)
        grid = path.contains_points(points)
        mask = grid.reshape(h, w)
    
    else:
        raise ValueError(f"Unsupported shutter type: {shutter_params['type']}")
    
    # Инвертируем маску, чтобы True = область вне шторки
    return ~mask


def text_to_bits(text, encoding='ascii', errors='ignore'):
    """Преобразует текст в битовую строку."""
    bits = bin(int.from_bytes(text.encode(encoding, errors), 'big'))[2:]
    return bits.zfill(8 * ((len(bits) + 7) // 8))

def text_from_bits(bits, encoding='ascii', errors='ignore'):
    """Преобразует битовую строку в текст."""
    n = int(bits, 2)
    return n.to_bytes((n.bit_length() + 7) // 8, 'big').decode(encoding, errors) or '\0'



def float32_to_bin(value):  
    [d] = struct.unpack(">L", struct.pack(">f", value))
    return '{:032b}'.format(d)


# def text_from_bits(bits, encoding='utf-8', errors='surrogatepass'):
#     n = int(bits, 2)
#     return n.to_bytes((n.bit_length() + 7) // 8, 'big').decode(encoding, errors) or '\0'


# def text_to_bits(text, encoding='utf-8', errors='surrogatepass'):
#     bits = bin(int.from_bytes(text.encode(encoding, errors), 'big'))[2:]
#     #print(8 * ((len(bits) + 7) // 8))
#     return bits#bits.zfill(8 * ((len(bits) + 7) // 8))

# def text_from_bits(bits, encoding='utf-8', errors='ignore'):
#     """
#     Преобразует битовую строку в текст или байты.
#     :param bits: Битовая строка (например, "101010...")
#     :param encoding: Кодировка (по умолчанию UTF-8)
#     :param errors: Обработка ошибок декодирования (по умолчанию 'ignore')
#     :return: Текст или байты
#     """
#     n = int(bits, 2)
#     byte_length = (n.bit_length() + 7) // 8
#     byte_data = n.to_bytes(byte_length, 'big')
    
#     try:
#         return byte_data.decode(encoding, errors)
#     except UnicodeDecodeError:
#         return byte_data  # Возвращаем байты, если декодирование не удалось

def bin_to_float32(b):
    bf = decode('%%0%dx' % (8 << 1) % int(b, 2), 'hex')[-4:]
    return np.float32(struct.unpack('>f', bf)[0])

def bin_to_float64(b: str) -> float:
    """Конвертирует 64-битную бинарную строку в float64"""
    if len(b) != 64:
        raise ValueError("Требуется 64-битная строка")
    
    # Конвертируем бинарную строку в байты (big-endian)
    byte_data = int(b, 2).to_bytes(8, byteorder='big')
    
    # Распаковываем в double
    return struct.unpack('>d', byte_data)[0]

def float64_to_bin(value: float) -> str:
    """Конвертирует float64 в 64-битную бинарную строку"""
    # Упаковываем float64 в байты (big-endian)
    byte_data = struct.pack('>d', value)
    
    # Конвертируем в 64-битное целое
    uint64 = struct.unpack('>Q', byte_data)[0]
    
    # Форматируем в бинарную строку с ведущими нулями
    return bin(uint64)[2:].zfill(64)




# def bin_to_float64(b):
#     bf = decode('%%0%dx' % (8 << 1) % int(b, 2), 'hex')[-8:] # 8 bytes needed for IEEE 754 binary64.
#     return struct.unpack('>d', bf)[0]

def metadata_to_bitstream(tags, vr_list, values):
    """
    Преобразует метаданные DICOM в битовую строку.
    :param tags: Список кортежей тегов (group, element)
    :param vr_list: Список VR (Value Representations)
    :param values: Список значений
    :return: Битовая строка вида "101010..."
    """
    bitstream = ""
    
    for tag, vr, value in zip(tags, vr_list, values):
        try:
            # Проверка на None
            if value is None:
                raise ValueError(f"Значение для тега {tag} равно None")
            
            # Кодируем заголовок (Tag + VR)
            tag_group, tag_element = tag
            tag_bits = format(tag_group, '016b') + format(tag_element, '016b')
            #vr_bits = text_to_bits(vr).ljust(16, '0')[:16]  # VR всегда 2 байта
            vr_bits = text_to_bits(vr).zfill(16)
            # Кодируем значение
            value_bits = encode_value(vr, value)
            
            # Кодируем длину значения (VL)
            vl = len(value_bits) // 8  # Длина в байтах
            
            vl_bits = format(vl, '032b') if vr in ('OB', 'OW') else format(vl, '016b')
            
            # Собираем элемент
            bitstream += tag_bits + vr_bits + vl_bits + value_bits
            
            
        except Exception as e:
            print(f"Ошибка кодирования элемента {tag}: {str(e)}")
            continue
            
    return bitstream

def encode_value(vr, value):
    """Кодирует значение в биты согласно VR"""
    try:
        # Обработка числовых типов
        if vr in ('US', 'SS', 'UL', 'SL', 'IS'):
            return format(int(value), '016b' if vr in ('US', 'SS') else '032b')
        elif vr in ('FL', 'FD'):
            return float32_to_bin(float(value)) if vr == 'FL' else float64_to_bin(float(value))
        
        # Обработка строковых типов
        elif vr in ('PN', 'LO', 'LT', 'SH'):
            return text_to_bits(str(value))
        
        # Обработка специальных форматов
        elif vr == 'DA':
            return text_to_bits(value, encoding='ascii', errors='ignore')  # Дата в формате YYYYMMDD
        elif vr == 'TM':
            return text_to_bits(value)  # Время в формате HHMMSS
        
        # Обработка бинарных данных
        elif vr == 'OB':
            return ''.join(format(byte, '08b') for byte in value)
        elif vr == 'OW':
            return ''.join(format(word, '016b') for word in value)
        
        # Если VR не поддерживается
        else:
            raise ValueError(f"Unsupported VR: {vr}")
    
    except Exception as e:
        raise ValueError(f"Не удалось закодировать {vr} {value}: {str(e)}")

def get_vr_bit_length(vr):
    """Возвращает длину в битах для VR с фиксированной длиной"""
    length_map = {
        'US': 16, 'SS': 16,
        'UL': 32, 'SL': 32,
        'FL': 32, 'FD': 64,
        'DA': 64, 'TM': 48,
        'AS': 32, 'AT': 32
    }
    return length_map.get(vr, 0)  # 0 = переменная длина


def bitstream_to_metadata(bitstream):
    """
    Преобразует битовую строку обратно в метаданные DICOM.
    :param bitstream: Битовая строка вида "101010..."
    :return: Список кортежей (tag, vr, value)
    """
    metadata = []
    offset = 0  # Текущая позиция в битовой строке

    while offset + 64 <= len(bitstream):  # Минимальный размер элемента (Tag + VR + VL)
        # Чтение заголовка (Tag + VR)
        tag_group = int(bitstream[offset:offset+16], 2)
        tag_element = int(bitstream[offset+16:offset+32], 2)
        vr = text_from_bits(bitstream[offset+32:offset+48]) 
        offset += 48

        # Чтение длины значения (VL)
        if vr in ('OB', 'OW', 'SQ', 'UN'):
            vl = int(bitstream[offset:offset+32], 2)  # 32 бита для OB/OW
            offset += 32
        else:
            vl = int(bitstream[offset:offset+16], 2)  # 16 бит для остальных
            offset += 16

        # Чтение значения
        value_bits = bitstream[offset:offset+vl*8]
        offset += vl * 8

        # Декодирование значения
        try:
            value = decode_value(vr, value_bits)
            metadata.append(((tag_group, tag_element), vr, value))
        except Exception as e:
            print(f"Ошибка декодирования элемента ({tag_group:04X},{tag_element:04X}): {str(e)}")

    return metadata

def decode_value(vr, value_bits):
    """Декодирует значение из битовой строки согласно VR"""
    try:
        # Обработка числовых типов
        if vr == 'US':  # Unsigned Short
            return int(value_bits, 2)
        elif vr == 'SS':  # Signed Short
            return int(value_bits, 2)
        elif vr == 'UL':  # Unsigned Long
            return int(value_bits, 2)
        elif vr == 'SL':  # Signed Long
            return int(value_bits, 2)
        elif vr == 'FL':  # Floating Point Single
            return bin_to_float32(value_bits)
        elif vr == 'FD':  # Floating Point Double
            return bin_to_float64(value_bits)
        elif vr == 'IS':  # Integer String
            return int(value_bits, 2)
        
        # Обработка строковых типов
        elif vr == 'PN':  # Patient Name
            return text_from_bits(value_bits, encoding='utf-8', errors='ignore')
        elif vr in ('LO', 'LT', 'SH'):  # Long String, Long Text, Short String
            return text_from_bits(value_bits, encoding='utf-8', errors='ignore')
        
        # Обработка специальных форматов
        elif vr == 'DA':  # Date
            return text_from_bits(value_bits, encoding='ascii', errors='ignore')
        elif vr == 'TM':  # Time
            return text_from_bits(value_bits)
        
        # Обработка бинарных данных
        elif vr == 'OB':  # Other Byte
            return bytes(int(value_bits[i:i+8], 2) for i in range(0, len(value_bits), 8))
        elif vr == 'OW':  # Other Word
            return [int(value_bits[i:i+16], 2) for i in range(0, len(value_bits), 16)]
        
        # Если VR не поддерживается
        else:
            raise ValueError(f"Unsupported VR: {vr}")
    
    except Exception as e:
        raise ValueError(f"Ошибка декодирования {vr}: {str(e)}")