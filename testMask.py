import unittest
import numpy as np
from matplotlib.path import Path
import matplotlib.pyplot as plt
from write import *
from read import *
from generate import *
import random


class TestMaskOperations(unittest.TestCase):
    def setUp(self):
        # Создаем тестовое изображение (uint16)
        self.image = np.zeros((30, 30), dtype=np.uint16)
        
         # Длина битовой строки
        self.bitstream_length = 8000  # Например, 1000 бит
        
        # Генерация случайной строки бит
        self.bitstream = ''.join(random.choice('01') for _ in range(self.bitstream_length))
        
    def test_rectangular_shutter(self):
        """Проверка записи и чтения бит для прямоугольной шторки"""
        # Параметры прямоугольной шторки
        shutter_params = {
            'type': 'RECTANGULAR',
            'left': 10,
            'right': 15,
            'top': 0,
            'bottom': 20
        }
        
        # Генерация маски
        mask = generate_shutter_mask(self.image.shape, shutter_params)
        
        # Запись бит
        modified_image = write_bits_to_mask(self.image, mask, self.bitstream, bits_per_pixel=16)
        
        plt.imshow(modified_image)
        plt.show()


        # Чтение бит
        extracted_bitstream = read_bits_from_mask(modified_image, mask, bits_per_pixel=16)[:len(self.bitstream)]
        
        # Проверка, что битовая строка совпадает
        self.assertEqual(extracted_bitstream, self.bitstream)
        
        # Проверка, что пиксели вне маски не изменились
        self.assertTrue(np.array_equal(self.image[mask], modified_image[mask]))

    def test_circular_shutter(self):
        """Проверка записи и чтения бит для круговой шторки"""
        # Параметры круговой шторки
        shutter_params = {
            'type': 'CIRCULAR',
            'center_x': 15,
            'center_y': 15,
            'radius': 10
        }
        
        # Генерация маски
        mask = generate_shutter_mask(self.image.shape, shutter_params)
        
        # Запись бит
        modified_image = write_bits_to_mask(self.image, mask, self.bitstream)
        

        plt.imshow(modified_image)
        plt.show()

        # Чтение бит
        extracted_bitstream = read_bits_from_mask(modified_image, mask)[:len(self.bitstream)]
        
        # Проверка, что битовая строка совпадает
        self.assertEqual(extracted_bitstream, self.bitstream)
        
        # Проверка, что пиксели вне маски не изменились
        self.assertTrue(np.array_equal(self.image[mask], modified_image[mask]))

    def test_polygonal_shutter(self):
        """Проверка записи и чтения бит для полигональной шторки"""
        # Параметры полигональной шторки
        shutter_params = {
            'type': 'POLYGONAL',
            'vertices': [(10, 10), (15, 5), (20, 10), (20, 20), (15, 25), (10, 25)]
        }
        
        # Генерация маски
        mask = generate_shutter_mask(self.image.shape, shutter_params)

        # Запись бит
        modified_image = write_bits_to_mask(self.image, mask, self.bitstream)
        
        plt.imshow(modified_image)
        plt.show()

        # Чтение бит
        extracted_bitstream = read_bits_from_mask(modified_image, mask)[:len(self.bitstream)]
        
        # Проверка, что битовая строка совпадает
        self.assertEqual(extracted_bitstream, self.bitstream)
        
        # Проверка, что пиксели вне маски не изменились
        self.assertTrue(np.array_equal(self.image[mask], modified_image[mask]))

if __name__ == '__main__':
    unittest.main()