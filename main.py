import matplotlib.pyplot as plt
import pydicom
import numpy as np
from typing import Optional, Dict, List, Tuple
from cryptFunc import encrypt_aes128, decrypt_aes128
from generate import generate_shutter_mask
from read import read_shutter_parameters, read_bits_from_mask
from write import write_bits_to_mask
from operation import metadata_to_bitstream, bitstream_to_metadata

def embed_encrypted_metadata(
    dcm_path: str,
    key: bytes,
    tags_to_embed: List[Tuple[int, int]],
    vr_list: List[str],
    values: List,
    output_path: str,
    bits_per_pixel: int = 8
) -> Optional[str]:
    """
    Записывает зашифрованные метаданные в область изображения, закрытую шторкой.
    
    :param dcm_path: Путь к исходному DICOM файлу.
    :param key: Ключ шифрования AES-128.
    :param tags_to_embed: Список тегов DICOM для встраивания.
    :param vr_list: Список VR для соответствующих тегов.
    :param values: Список значений тегов.
    :param output_path: Путь для сохранения модифицированного DICOM файла.
    :param bits_per_pixel: Количество бит на пиксель (по умолчанию 16).
    :return: Сообщение об ошибке или None при успехе.
    """
    try:
        # Загрузка DICOM файла
        ds = pydicom.dcmread(dcm_path, force=True)
        image = ds.pixel_array

        # Чтение параметров шторки
        shutter_params = read_shutter_parameters(dcm_path)
        if not shutter_params:
            return "Шторка не найдена в DICOM файле."

        # Генерация маски
        mask = generate_shutter_mask(image.shape, shutter_params)

        # Преобразование метаданных в битовую строку
        bitstream = metadata_to_bitstream(tags_to_embed, vr_list, values)

        

        # Шифрование битовой строки
        encrypted_data = encrypt_aes128(bitstream, key)

        # Преобразование зашифрованных байт в битовую строку
        encrypted_bits = ''.join(format(byte, '08b') for byte in encrypted_data)
        
        lenBit = format((len(encrypted_bits)), '032b')

        #print(len(encrypted_bits))
        encrypted_bits = lenBit + encrypted_bits

        # Проверка достаточности места
        available_pixels = np.sum(~mask)
        required_bits = len(encrypted_bits)
        if available_pixels * bits_per_pixel < required_bits:
            return "Недостаточно места для записи данных."

        # Запись битов в изображение
        modified_image = write_bits_to_mask(image, mask, encrypted_bits, bits_per_pixel)

        # plt.imshow(modified_image)
        # plt.show()

        # Обновление данных в DICOM
        ds.PixelData = modified_image.tobytes()
        ds.save_as(output_path)
        return None

    except Exception as e:
        return f"Ошибка: {str(e)}"

def extract_decrypted_metadata(
    dcm_path: str,
    key: bytes,
    bits_per_pixel: int = 8
):
    """
    Извлекает и расшифровывает метаданные из области изображения, закрытой шторкой.
    
    :param dcm_path: Путь к DICOM файлу с данными.
    :param key: Ключ шифрования AES-128.
    :param bits_per_pixel: Количество бит на пиксель.
    :return: Кортеж (расшифрованные метаданные, сообщение об ошибке).
    """
    try:
        # Загрузка DICOM файла
        ds = pydicom.dcmread(dcm_path, force=True)
        image = ds.pixel_array

        # Чтение параметров шторки
        shutter_params = read_shutter_parameters(dcm_path)
        if not shutter_params:
            return None, "Шторка не найдена."

        # Генерация маски
        mask = generate_shutter_mask(image.shape, shutter_params)

        # Извлечение битовой строки
        encrypted_bits = read_bits_from_mask(image, mask, bits_per_pixel)

        LenBit = int(encrypted_bits[:32],2)

        encrypted_bits = encrypted_bits[32:32+LenBit]

        #print(len(encrypted_bits))

        # Преобразование битов в байты

        encrypted_bytes = int(encrypted_bits, 2).to_bytes((len(encrypted_bits) + 7) // 8, 'big')

        #print((encrypted_bits))

        # Дешифрование
        decrypted_bitstream = decrypt_aes128(encrypted_bytes, key)
        # Преобразование битовой строки в метаданные
        metadata = bitstream_to_metadata(decrypted_bitstream)
        return metadata, None

    except Exception as e:
        return None, f"Ошибка: {str(e)}"
    
import os

# Пример записи
key = os.urandom(16)
result = embed_encrypted_metadata(
    dcm_path="ex.dcm",
    key=key,
    tags_to_embed=[
                (0x0010, 0x0010),  # PatientName (PN)
                (0x0028, 0x0010),  # Rows (US)
                (0x0028, 0x0008),  # NumberOfFrames (IS)
                (0x0018, 0x0080),  # RepetitionTime (FL)
                (0x0018, 0x0081),  # RepetitionTime (FD)
                (0x0040, 0x0245),  # ProcedureStepStartDate (DA)
                (0x7FE0, 0x0010),  # PixelData (OB)
                (0x0010, 0x0030),  # PatientBirthDate (DA)
                (0x0008, 0x0020),  # StudyDate (DA)
                (0x0008, 0x0030),  # StudyTime (TM)
                (0x0008, 0x0070),  # Manufacturer (LO)
                (0x0008, 0x0080),  # InstitutionName (LO)
                (0x0008, 0x0090),  # ReferringPhysicianName (PN)
                (0x0008, 0x1010),  # StationName (SH)
                (0x0008, 0x1030),  # StudyDescription (LO)
                (0x0008, 0x1050),  # PerformingPhysicianName (PN)
                (0x0008, 0x1060),  # OperatorName (PN)
                (0x0008, 0x1080),  # AdmittingDiagnosesDescription (LO)
                (0x0008, 0x1090),  # ManufacturerModelName (LO)
            ],
    vr_list=[
                'PN',  # PatientName
                'US',  # Rows
                'IS',  # NumberOfFrames
                'FL',  # RepetitionTime (Float)
                'FD',  # RepetitionTime (Double)
                'DA',  # ProcedureStepStartDate
                'OB',  # PixelData
                'DA',  # PatientBirthDate
                'DA',  # StudyDate
                'TM',  # StudyTime
                'LO',  # Manufacturer
                'LO',  # InstitutionName
                'PN',  # ReferringPhysicianName
                'SH',  # StationName
                'LO',  # StudyDescription
                'PN',  # PerformingPhysicianName
                'PN',  # OperatorName
                'LO',  # AdmittingDiagnosesDescription
                'LO',  # ManufacturerModelName
            ],
    values=[
                'Ivanov_Ivan',  # PatientName (PN)
                512,            # Rows (US)
                '24',           # NumberOfFrames (IS)
                1234.5,         # RepetitionTime (FL)
                1234.5,         # RepetitionTime (FD)
                '20250320',     # ProcedureStepStartDate (DA)
                b'\x12\x34\x56\x78',  # PixelData (OB)
                '19900101',     # PatientBirthDate (DA)
                '20230101',     # StudyDate (DA)
                '120000',       # StudyTime (TM)
                'GE Healthcare',  # Manufacturer (LO)
                'City Hospital',  # InstitutionName (LO)
                'Petrov_Petr',  # ReferringPhysicianName (PN)
                'CT-Scanner-1',  # StationName (SH)
                'All',  # StudyDescription (LO)
                'Sidorov_Sidr',  # PerformingPhysicianName (PN)
                'Ivanov_Ivan',  # OperatorName (PN)
                'Bad',  # AdmittingDiagnosesDescription (LO)
                'Revolution CT',  # ManufacturerModelName (LO)
            ],
    output_path="output.dcm"
)

# Пример извлечения
try:
    metadata, error = extract_decrypted_metadata("output.dcm", key)
    if metadata:
        for tag, vr, value in metadata:
            print(f"Tag: {tag}, VR: {vr}, Value: {value}")
except Exception as e:
    print(e)