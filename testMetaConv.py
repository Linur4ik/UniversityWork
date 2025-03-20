import unittest
import numpy as np
from datetime import datetime
from generate import *
from read import *
from operation import *

class TestDICOMReversibility(unittest.TestCase):
    def test_metadata_reversibility(self):
        """Проверка обратимости кодирования для всех поддерживаемых VR"""
        # Тестовые данные
        test_cases = [
            {
                'tags': [(0x0010, 0x0010)],  # PatientName
                'vr_list': ['PN'],
                'values': ['Ivanov^Ivan']
            },
            {
                'tags': [(0x0028, 0x0010)],  # Rows
                'vr_list': ['US'],
                'values': [512]
            },
            {
                'tags': [(0x0028, 0x0008)],  # NumberOfFrames
                'vr_list': ['IS'],
                'values': ['24']
            },
            {
                'tags': [(0x0018, 0x0080)],  # RepetitionTime
                'vr_list': ['FL'],
                'values': [1234.5]  # Исправлено: число вместо строки
            },
            {
                'tags': [(0x0018, 0x0081)],  # RepetitionTime
                'vr_list': ['FD'],
                'values': [1234.5]  # Исправлено: число вместо строки
            },
            {
                'tags': [(0x0040, 0x0245)],  # ProcedureStepStartDate
                'vr_list': ['DA'],
                'values': ['20250320']  # Исправлено: корректный формат YYYYMMDD
            },
            {
                'tags': [(0x7FE0, 0x0010)],  # PixelData
                'vr_list': ['OB'],
                'values': [b'\x12\x34\x56\x78']  # Бинарные данные
            },
            {
                'tags': [(0x0010, 0x0030)],  # PatientBirthDate
                'vr_list': ['DA'],
                'values': ['19900101']
            },
            {
                'tags': [(0x0008, 0x0020)],  # StudyDate
                'vr_list': ['DA'],
                'values': ['20230101']
            },
            {
                'tags': [(0x0008, 0x0030)],  # StudyTime
                'vr_list': ['TM'],
                'values': ['120000']
            },
            {
                'tags': [(0x0008, 0x0070)],  # Manufacturer
                'vr_list': ['LO'],
                'values': ['GE Healthcare']
            },
            {
                'tags': [(0x0008, 0x0080)],  # InstitutionName
                'vr_list': ['LO'],
                'values': ['City Hospital']
            },
            {
                'tags': [(0x0008, 0x0090)],  # ReferringPhysicianName
                'vr_list': ['PN'],
                'values': ['Petrov^Petr']
            },
            {
                'tags': [(0x0008, 0x1010)],  # StationName
                'vr_list': ['SH'],
                'values': ['CT-Scanner-1']
            },
            {
                'tags': [(0x0008, 0x1030)],  # StudyDescription
                'vr_list': ['LO'],
                'values': ['General Study']
            },
            {
                'tags': [(0x0008, 0x1050)],  # PerformingPhysicianName
                'vr_list': ['PN'],
                'values': ['Sidorov^Sidor']
            },
            {
                'tags': [(0x0008, 0x1060)],  # OperatorName
                'vr_list': ['PN'],
                'values': ['Ivanov^Ivan']
            },
            {
                'tags': [(0x0008, 0x1080)],  # AdmittingDiagnosesDescription
                'vr_list': ['LO'],
                'values': ['Diagnosis not specified']
            },
            {
                'tags': [(0x0008, 0x1090)],  # ManufacturerModelName
                'vr_list': ['LO'],
                'values': ['Revolution CT']
            }
        ]

        for case in test_cases:
            with self.subTest(case=case):
                # Кодирование
                bitstream = metadata_to_bitstream(
                    case['tags'], 
                    case['vr_list'], 
                    case['values']
                )
                
                # Декодирование
                decoded_metadata = bitstream_to_metadata(bitstream)
                
                # Проверка количества элементов
                #self.assertEqual(len(decoded_metadata), len(case['tags']))
                
                # Проверка каждого элемента
                for (tag, vr, value), expected_tag, expected_vr, expected_value in zip(
                    decoded_metadata,
                    case['tags'],
                    case['vr_list'],
                    case['values']
                ):
                    
                    # Проверка тега
                    self.assertEqual(tag, expected_tag)
                    
                    # Проверка VR
                    self.assertEqual(vr, expected_vr)
                    # Специфичные проверки для разных типов данных
                    if vr == 'FD':
                        self.assertAlmostEqual(float(value), float(expected_value), places=2)
                    elif vr == 'OB':
                        self.assertEqual(bytes(value), expected_value)
                    else:
                        self.assertEqual(str(value), str(expected_value))

if __name__ == '__main__':
    unittest.main()