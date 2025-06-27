import sys
import os
import pydicom
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QFileDialog, QTextEdit, QTabWidget, QGroupBox,
                            QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from cryptFunc import encrypt_aes128, decrypt_aes128
from generate import generate_shutter_mask
from read import read_shutter_parameters, read_bits_from_mask
from write import write_bits_to_mask
from operation import metadata_to_bitstream, bitstream_to_metadata
from main import embed_encrypted_metadata,extract_decrypted_metadata


class DICOMSteganographyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DICOM Steganography Tool")
        self.setGeometry(100, 100, 1200, 800)
        
        # Основные переменные
        self.current_file = None
        self.ds = None
        self.key = None
        self.shutter_params = None
        self.bits_per_pixel = None
        
        # Создание интерфейса
        self.init_ui()
        
    def init_ui(self):
        # Создание вкладок
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Вкладка для шифрования
        self.encrypt_tab = QWidget()
        self.tabs.addTab(self.encrypt_tab, "Embed Data")
        self.setup_encrypt_tab()
        
        # Вкладка для дешифрования
        self.decrypt_tab = QWidget()
        self.tabs.addTab(self.decrypt_tab, "Extract Data")
        self.setup_decrypt_tab()
        
        # Вкладка для просмотра изображений
        self.view_tab = QWidget()
        self.tabs.addTab(self.view_tab, "Image Viewer")
        self.setup_view_tab()
        
    def setup_encrypt_tab(self):
        layout = QVBoxLayout()
        
        # Выбор файла
        file_group = QGroupBox("DICOM File")
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        file_browse_btn = QPushButton("Browse...")
        file_browse_btn.clicked.connect(self.browse_encrypt_file)
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(file_browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Информация о файле
        info_group = QGroupBox("File Information")
        info_layout = QVBoxLayout()
        
        # Отображение параметров шторки
        self.shutter_info = QLabel("Shutter type: Not detected")
        info_layout.addWidget(self.shutter_info)
        
        # Отображение битности
        self.bits_info = QLabel("Bits per pixel: Not detected")
        info_layout.addWidget(self.bits_info)
        
        # Статус возможности кодирования
        self.encode_status = QLabel("Status: Select DICOM file")
        info_layout.addWidget(self.encode_status)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Настройки шифрования
        self.encrypt_group = QGroupBox("Encryption Settings (Optional)")
        encrypt_layout = QVBoxLayout()
        
        # Чекбокс для включения шифрования
        self.encrypt_check = QCheckBox("Enable AES-128 Encryption")
        self.encrypt_check.stateChanged.connect(self.toggle_encrypt_fields)
        encrypt_layout.addWidget(self.encrypt_check)
        
        # Поле для ключа (изначально отключено)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Enter 16-byte key in hex (32 characters)")
        self.key_edit.setEnabled(False)
        encrypt_layout.addWidget(QLabel("Encryption Key:"))
        encrypt_layout.addWidget(self.key_edit)
        
        # Генерация ключа
        self.gen_key_btn = QPushButton("Generate Random Key")
        self.gen_key_btn.setEnabled(False)
        self.gen_key_btn.clicked.connect(self.generate_key)
        encrypt_layout.addWidget(self.gen_key_btn)
        
        self.encrypt_group.setLayout(encrypt_layout)
        layout.addWidget(self.encrypt_group)
        
        # Таблица метаданных
        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(3)
        self.metadata_table.setHorizontalHeaderLabels(["Tag", "VR", "Value"])
        self.metadata_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(QLabel("Metadata to Embed:"))
        layout.addWidget(self.metadata_table)
        
        # Кнопки действий
        btn_layout = QHBoxLayout()
        encrypt_btn = QPushButton("Embed Data and Save")
        encrypt_btn.clicked.connect(self.embed_and_save)
        btn_layout.addWidget(encrypt_btn)
        layout.addLayout(btn_layout)
        
        self.encrypt_tab.setLayout(layout)
    
    def setup_decrypt_tab(self):
        layout = QVBoxLayout()
        
        # Выбор файла
        file_group = QGroupBox("DICOM File with Embedded Data")
        file_layout = QHBoxLayout()
        self.encrypted_file_edit = QLineEdit()
        self.encrypted_file_edit.setReadOnly(True)
        decrypt_browse_btn = QPushButton("Browse...")
        decrypt_browse_btn.clicked.connect(self.browse_decrypt_file)
        file_layout.addWidget(self.encrypted_file_edit)
        file_layout.addWidget(decrypt_browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Информация о файле
        decrypt_info_group = QGroupBox("File Information")
        decrypt_info_layout = QVBoxLayout()
        
        # Отображение параметров шторки
        self.decrypt_shutter_info = QLabel("Shutter type: Not detected")
        decrypt_info_layout.addWidget(self.decrypt_shutter_info)
        
        # Отображение битности
        self.decrypt_bits_info = QLabel("Bits per pixel: Not detected")
        decrypt_info_layout.addWidget(self.decrypt_bits_info)
        
        decrypt_info_group.setLayout(decrypt_info_layout)
        layout.addWidget(decrypt_info_group)
        
        # Настройки дешифрования
        self.decrypt_group = QGroupBox("Decryption Settings (If Encrypted)")
        decrypt_layout = QVBoxLayout()
        
        # Поле для ключа
        self.decrypt_key_edit = QLineEdit()
        self.decrypt_key_edit.setPlaceholderText("Enter 16-byte key in hex")
        decrypt_layout.addWidget(QLabel("Decryption Key:"))
        decrypt_layout.addWidget(self.decrypt_key_edit)
        
        self.decrypt_group.setLayout(decrypt_layout)
        self.decrypt_group.setEnabled(True)
        layout.addWidget(self.decrypt_group)
        
        # Извлеченные метаданные
        self.decrypted_table = QTableWidget()
        self.decrypted_table.setColumnCount(3)
        self.decrypted_table.setHorizontalHeaderLabels(["Tag", "VR", "Value"])
        self.decrypted_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(QLabel("Extracted Metadata:"))
        layout.addWidget(self.decrypted_table)
        
        # Кнопки действий
        btn_layout = QHBoxLayout()
        decrypt_btn = QPushButton("Extract Metadata")
        decrypt_btn.clicked.connect(self.extract_metadata)
        btn_layout.addWidget(decrypt_btn)
        layout.addLayout(btn_layout)
        
        self.decrypt_tab.setLayout(layout)
    
    def setup_view_tab(self):
        layout = QVBoxLayout()
        
        # Изображение до обработки
        self.original_figure = Figure()
        self.original_canvas = FigureCanvas(self.original_figure)
        layout.addWidget(QLabel("Original Image:"))
        layout.addWidget(self.original_canvas)
        
        # Изображение после обработки
        self.processed_figure = Figure()
        self.processed_canvas = FigureCanvas(self.processed_figure)
        layout.addWidget(QLabel("Processed Image:"))
        layout.addWidget(self.processed_canvas)
        
        # Разница между изображениями
        self.diff_figure = Figure()
        self.diff_canvas = FigureCanvas(self.diff_figure)
        layout.addWidget(QLabel("Difference (Enhanced):"))
        layout.addWidget(self.diff_canvas)
        
        self.view_tab.setLayout(layout)
    
    def browse_encrypt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select DICOM File", "", "DICOM Files (*.dcm)"
        )
        if file_path:
            self.current_file = file_path
            self.file_path_edit.setText(file_path)
            self.load_dicom_file(file_path)
    
    def browse_decrypt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select DICOM File with Embedded Data", "", "DICOM Files (*.dcm)"
        )
        if file_path:
            self.encrypted_file_edit.setText(file_path)
            self.load_dicom_file(file_path, decrypt_mode=True)
    
    def load_dicom_file(self, file_path, decrypt_mode=False):
        try:
            self.ds = pydicom.dcmread(file_path, force=True)
            
            # Определение параметров шторки
            self.shutter_params = read_shutter_parameters(file_path)
            shutter_text = "Shutter type: "
            if self.shutter_params:
                shutter_text += self.shutter_params.get('type', 'Unknown')
            else:
                shutter_text += "Not found"
            
            # Определение битности
            bits_text = "Bits per pixel: "
            if (0x0028, 0x0101) in self.ds:
                self.bits_per_pixel = self.ds.BitsStored
                bits_text += str(self.bits_per_pixel)
            else:
                self.bits_per_pixel = None
                bits_text += "Not found"
            
            # Обновление интерфейса в зависимости от режима
            if decrypt_mode:
                self.decrypt_shutter_info.setText(shutter_text)
                self.decrypt_bits_info.setText(bits_text)
                self.display_dicom_image(file_path, self.processed_canvas, self.processed_figure)
                
                # Проверка наличия шторки для извлечения
                if not self.shutter_params:
                    QMessageBox.warning(self, "Warning", 
                                       "No shutter information found. Data extraction may not be possible.")
            else:
                self.shutter_info.setText(shutter_text)
                self.bits_info.setText(bits_text)
                self.display_dicom_image(file_path, self.original_canvas, self.original_figure)
                
                # Проверка возможности кодирования
                status_text = "Status: "
                if self.shutter_params and self.bits_per_pixel:
                    status_text += "Ready for data embedding"
                    self.encode_status.setStyleSheet("color: green")
                else:
                    status_text += "Cannot embed data - missing required DICOM attributes"
                    self.encode_status.setStyleSheet("color: red")
                self.encode_status.setText(status_text)
                
                # Заполнение таблицы метаданных
                self.populate_metadata_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load DICOM file: {str(e)}")
    
    def display_dicom_image(self, file_path, canvas, figure):
        try:
            ds = pydicom.dcmread(file_path, force=True)
            img = ds.pixel_array
            
            figure.clear()
            ax = figure.add_subplot(111)
            ax.imshow(img, cmap='gray')
            ax.axis('off')
            canvas.draw()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to display image: {str(e)}")
    
    def toggle_encrypt_fields(self, state):
        enabled = state == Qt.Checked
        self.key_edit.setEnabled(enabled)
        self.gen_key_btn.setEnabled(enabled)
    
    def generate_key(self):
        key = os.urandom(16)
        self.key_edit.setText(key.hex())
    
    def populate_metadata_table(self):
        if not self.ds:
            return
        
        # Предопределенные теги для встраивания
        tags_to_show = [
            (0x0010, 0x0010), (0x0010, 0x0030), (0x0008, 0x0020),
            (0x0008, 0x0030), (0x0008, 0x0070), (0x0008, 0x0080),
            (0x0008, 0x0090), (0x0008, 0x1010), (0x0008, 0x1030),
            (0x0008, 0x1050), (0x0008, 0x1060), (0x0008, 0x1080),
            (0x0008, 0x1090), (0x0028, 0x0010), (0x0028, 0x0008),
            (0x0018, 0x0080), (0x0018, 0x0081), (0x0040, 0x0245)
        ]
        
        self.metadata_table.setRowCount(len(tags_to_show))
        
        for row, tag in enumerate(tags_to_show):
            # Отображаем тег в формате (XXXX,XXXX)
            tag_item = QTableWidgetItem(f"({tag[0]:04X},{tag[1]:04X})")
            tag_item.setFlags(tag_item.flags() & ~Qt.ItemIsEditable)
            self.metadata_table.setItem(row, 0, tag_item)
            
            # Получаем VR и значение
            try:
                element = self.ds[tag]
                vr = element.VR
                value = str(element.value)
            except KeyError:
                vr = ""
                value = ""
            
            vr_item = QTableWidgetItem(vr)
            vr_item.setFlags(vr_item.flags() & ~Qt.ItemIsEditable)
            self.metadata_table.setItem(row, 1, vr_item)
            
            value_item = QTableWidgetItem(value)
            self.metadata_table.setItem(row, 2, value_item)
    
    def embed_and_save(self):
        if not self.current_file or not self.ds:
            QMessageBox.warning(self, "Warning", "Please select a DICOM file first")
            return
        
        # Проверка необходимых атрибутов
        if not self.shutter_params:
            QMessageBox.critical(self, "Error", "Cannot embed data: No shutter information found in DICOM file")
            return
            
        if not self.bits_per_pixel:
            QMessageBox.critical(self, "Error", "Cannot embed data: Bits per pixel information not found")
            return
        
        # Обработка шифрования
        use_encryption = self.encrypt_check.isChecked()
        key = None
        
        if use_encryption:
            key_text = self.key_edit.text().strip()
            if len(key_text) != 32:
                QMessageBox.warning(self, "Warning", "Encryption key must be 32 hex characters (16 bytes)")
                return
            try:
                key = bytes.fromhex(key_text)
            except ValueError:
                QMessageBox.warning(self, "Warning", "Invalid hex format for encryption key")
                return
        
        # Собираем метаданные для встраивания
        tags_to_embed = []
        vr_list = []
        values = []
        
        for row in range(self.metadata_table.rowCount()):
            tag_text = self.metadata_table.item(row, 0).text().strip("()")
            group, element = map(lambda x: int(x, 16), tag_text.split(','))
            
            vr = self.metadata_table.item(row, 1).text()
            value = self.metadata_table.item(row, 2).text()
            
            tags_to_embed.append((group, element))
            vr_list.append(vr)
            
            # Преобразуем значения в правильный тип
            if vr == 'IS':
                values.append(int(value) if value else 0)
            elif vr in ('FL', 'FD'):
                values.append(float(value) if value else 0.0)
            else:
                values.append(value)
        
        # Запрашиваем путь для сохранения
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Modified DICOM", "", "DICOM Files (*.dcm)"
        )
        if not save_path:
            return
        
        # Выполняем встраивание данных
        result = embed_encrypted_metadata(
            dcm_path=self.current_file,
            key=key,
            tags_to_embed=tags_to_embed,
            vr_list=vr_list,
            values=values,
            output_path=save_path,
            bits_per_pixel=self.bits_per_pixel
        )
        
        if result:
            QMessageBox.critical(self, "Error", result)
        else:
            QMessageBox.information(self, "Success", "Data embedded successfully!")
            self.display_dicom_image(save_path, self.processed_canvas, self.processed_figure)
            self.show_image_difference()
    
    def show_image_difference(self):
        if not self.current_file:
            return
        
        try:
            # Загружаем оригинальное и обработанное изображения
            orig_ds = pydicom.dcmread(self.current_file, force=True)
            proc_ds = pydicom.dcmread(self.file_path_edit.text(), force=True)
            
            orig_img = orig_ds.pixel_array
            proc_img = proc_ds.pixel_array
            
            # Вычисляем разницу и усиливаем ее для визуализации
            diff = orig_img.astype(np.int16) - proc_img.astype(np.int16)
            abs_diff = np.abs(diff)
            enhanced_diff = np.clip(abs_diff * 50, 0, 255).astype(np.uint8)
            
            # Отображаем разницу
            self.diff_figure.clear()
            ax = self.diff_figure.add_subplot(111)
            ax.imshow(enhanced_diff, cmap='hot')
            ax.axis('off')
            ax.set_title("Pixel Differences (Enhanced 50x)")
            self.diff_canvas.draw()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to show difference: {str(e)}")
    
    def extract_metadata(self):
        encrypted_file = self.encrypted_file_edit.text()
        if not encrypted_file:
            QMessageBox.warning(self, "Warning", "Please select a DICOM file")
            return
        
        # Проверка наличия шторки
        if not self.shutter_params:
            QMessageBox.critical(self, "Error", "Cannot extract data: No shutter information found")
            return
            
        # Проверка наличия битности
        if not self.bits_per_pixel:
            QMessageBox.critical(self, "Error", "Cannot extract data: Bits per pixel information not found")
            return
        
        # Обработка ключа
        key = None
        key_text = self.decrypt_key_edit.text().strip()
        if key_text:
            if len(key_text) != 32:
                QMessageBox.warning(self, "Warning", "Decryption key must be 32 hex characters (16 bytes)")
                return
            try:
                key = bytes.fromhex(key_text)
            except ValueError:
                QMessageBox.warning(self, "Warning", "Invalid hex format for decryption key")
                return
        
        # Выполняем извлечение данных
        metadata, error = extract_decrypted_metadata(encrypted_file, key, self.bits_per_pixel)
        
        if error:
            QMessageBox.critical(self, "Error", error)
        else:
            self.display_decrypted_metadata(metadata)
    
    def display_decrypted_metadata(self, metadata):
        self.decrypted_table.setRowCount(len(metadata))
        
        for row, item in enumerate(metadata):
            tag, vr, value = item
            
            # Отображаем тег
            tag_item = QTableWidgetItem(f"({tag[0]:04X},{tag[1]:04X})")
            tag_item.setFlags(tag_item.flags() & ~Qt.ItemIsEditable)
            self.decrypted_table.setItem(row, 0, tag_item)
            
            # Отображаем VR
            vr_item = QTableWidgetItem(vr)
            vr_item.setFlags(vr_item.flags() & ~Qt.ItemIsEditable)
            self.decrypted_table.setItem(row, 1, vr_item)
            
            # Отображаем значение
            if isinstance(value, bytes):
                value_str = value.hex()
            elif isinstance(value, list):
                value_str = ', '.join(map(str, value))
            else:
                value_str = str(value)
            
            value_item = QTableWidgetItem(value_str)
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            self.decrypted_table.setItem(row, 2, value_item)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DICOMSteganographyApp()
    window.show()
    sys.exit(app.exec_())