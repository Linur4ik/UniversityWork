import unittest
import os
from generate import *
from read import *
from cryptFunc import *
from operation import *


class TestDICOMWithAES(unittest.TestCase):
    def setUp(self):
        self.key = os.urandom(16)  # Генерация случайного ключа
        self.iv = os.urandom(16)
        
    def test_full_cycle(self):
        """Полный цикл: кодирование -> шифрование -> дешифрование -> декодирование"""
        # Тестовые данные
        test_data = {
            'tags': [
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
            'vr_list': [
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
            'values': [
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
            ]
        }
        
        # Кодирование и шифрование
        bitstream = metadata_to_bitstream(
            test_data['tags'],
            test_data['vr_list'],
            test_data['values'],
        )

        

        encrypted_data = encrypt_aes128(bitstream, self.key)
        # Дешифрование и декодирование
        decrypted_data = decrypt_aes128(encrypted_data, self.key)
        
        decoded_metadata = bitstream_to_metadata(decrypted_data)
        # Проверки
        self.assertEqual(len(decoded_metadata), len(test_data['tags']))
        
        for (tag, vr, value), expected in zip(decoded_metadata, zip(
            test_data['tags'],
            test_data['vr_list'],
            test_data['values']
        )):
            self.assertEqual(tag, expected[0])
            self.assertEqual(vr, expected[1])
            self.assertEqual(str(value), str(expected[2]))


    def test_data_integrity2(self):
        """Проверка целостности данных для битовой строки"""
        # Исходная битовая строка (пример)
        original_bitstream = "000001010101010101011010101"
        
        # # Преобразуем битовую строку в байты для шифрования
        # original_bytes = int(original_bitstream, 2).to_bytes((len(original_bitstream) + 7) // 8, 'big')

        # length_prefix = len(original_bitstream).to_bytes(4, 'big')  # 4 байта для длины
        # data_to_encrypt = length_prefix + original_bytes
        # Шифрование
        encrypted_data = encrypt_aes128(original_bitstream, self.key)
        
        # Дешифрование
        decrypted_bytes = decrypt_aes128(encrypted_data, self.key)
        
        # # Преобразуем дешифрованные байты обратно в битовую строку
        # length = int.from_bytes(decrypted_bytes[:4], 'big')  # Первые 4 байта — длина
        # decrypted_bytes = decrypted_bytes[4:]  # Остальные байты — данные
        
        # # Преобразуем дешифрованные байты обратно в битовую строку
        # decrypted_bitstream = bin(int.from_bytes(decrypted_bytes, 'big'))[2:]
        
        # # Дополняем нулями до исходной длины
        # decrypted_bitstream = decrypted_bitstream.zfill(length)
            
        # Проверка
        self.assertEqual(original_bitstream, decrypted_bytes)



if __name__ == '__main__':
    unittest.main()