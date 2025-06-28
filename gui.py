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
        
        # Вкладка для встраивания данных
        self.embed_tab = QWidget()
        self.tabs.addTab(self.embed_tab, "Embed Data")
        self.setup_embed_tab()
        
        # Вкладка для извлечения данных
        self.extract_tab = QWidget()
        self.tabs.addTab(self.extract_tab, "Extract Data")
        self.setup_extract_tab()
        
        # Вкладка для просмотра изображений
        self.view_tab = QWidget()
        self.tabs.addTab(self.view_tab, "Image Viewer")
        self.setup_view_tab()
        
    def setup_embed_tab(self):
        layout = QVBoxLayout()
        
        # Выбор файла
        file_group = QGroupBox("DICOM File")
        file_layout = QHBoxLayout()
        self.embed_file_edit = QLineEdit()
        self.embed_file_edit.setReadOnly(True)
        file_browse_btn = QPushButton("Browse...")
        file_browse_btn.clicked.connect(lambda: self.browse_dicom_file("embed"))
        file_layout.addWidget(self.embed_file_edit)
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
        self.embed_status = QLabel("Status: Select DICOM file")
        info_layout.addWidget(self.embed_status)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Настройки шифрования
        self.encrypt_group = QGroupBox("Encryption Settings")
        encrypt_layout = QVBoxLayout()
        
        # Чекбокс для включения шифрования
        self.encrypt_check = QCheckBox("Enable AES-128 Encryption")
        self.encrypt_check.stateChanged.connect(self.toggle_encrypt_fields)
        encrypt_layout.addWidget(self.encrypt_check)
        
        # Поле для ключа (изначально скрыто)
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Encryption Key:"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Enter 16-byte key in hex (32 characters)")
        self.key_edit.setVisible(False)
        key_layout.addWidget(self.key_edit)
        
        # Генерация ключа
        self.gen_key_btn = QPushButton("Generate Key")
        self.gen_key_btn.setVisible(False)
        self.gen_key_btn.clicked.connect(self.generate_key)
        key_layout.addWidget(self.gen_key_btn)
        
        encrypt_layout.addLayout(key_layout)
        self.encrypt_group.setLayout(encrypt_layout)
        layout.addWidget(self.encrypt_group)
        
        # Таблица метаданных для встраивания
        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(3)
        self.metadata_table.setHorizontalHeaderLabels(["Tag", "VR", "Value"])
        self.metadata_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(QLabel("Metadata to Embed:"))
        layout.addWidget(self.metadata_table)
        
        # Кнопки действий
        btn_layout = QHBoxLayout()
        embed_btn = QPushButton("Embed Data and Save")
        embed_btn.clicked.connect(self.embed_and_save)
        btn_layout.addWidget(embed_btn)
        layout.addLayout(btn_layout)
        
        self.embed_tab.setLayout(layout)
    
    def setup_extract_tab(self):
        layout = QVBoxLayout()
        
        # Выбор файла
        file_group = QGroupBox("DICOM File with Embedded Data")
        file_layout = QHBoxLayout()
        self.extract_file_edit = QLineEdit()
        self.extract_file_edit.setReadOnly(True)
        extract_browse_btn = QPushButton("Browse...")
        extract_browse_btn.clicked.connect(lambda: self.browse_dicom_file("extract"))
        file_layout.addWidget(self.extract_file_edit)
        file_layout.addWidget(extract_browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Информация о файле
        extract_info_group = QGroupBox("File Information")
        extract_info_layout = QVBoxLayout()
        
        # Отображение параметров шторки
        self.extract_shutter_info = QLabel("Shutter type: Not detected")
        extract_info_layout.addWidget(self.extract_shutter_info)
        
        # Отображение битности
        self.extract_bits_info = QLabel("Bits per pixel: Not detected")
        extract_info_layout.addWidget(self.extract_bits_info)
        
        extract_info_group.setLayout(extract_info_layout)
        layout.addWidget(extract_info_group)
        
        # Настройки дешифрования
        self.decrypt_group = QGroupBox("Decryption Settings")
        decrypt_layout = QVBoxLayout()
        
        # Чекбокс для включения дешифрования
        self.decrypt_check = QCheckBox("Data is Encrypted")
        self.decrypt_check.stateChanged.connect(self.toggle_decrypt_fields)
        decrypt_layout.addWidget(self.decrypt_check)
        
        # Поле для ключа (изначально скрыто)
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Decryption Key:"))
        self.decrypt_key_edit = QLineEdit()
        self.decrypt_key_edit.setPlaceholderText("Enter 16-byte key in hex")
        self.decrypt_key_edit.setVisible(False)
        key_layout.addWidget(self.decrypt_key_edit)
        decrypt_layout.addLayout(key_layout)
        
        self.decrypt_group.setLayout(decrypt_layout)
        layout.addWidget(self.decrypt_group)
        
        # Извлеченные метаданные
        self.extracted_table = QTableWidget()
        self.extracted_table.setColumnCount(3)
        self.extracted_table.setHorizontalHeaderLabels(["Tag", "VR", "Value"])
        self.extracted_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(QLabel("Extracted Metadata:"))
        layout.addWidget(self.extracted_table)
        
        # Кнопки действий
        btn_layout = QHBoxLayout()
        extract_btn = QPushButton("Extract Metadata")
        extract_btn.clicked.connect(self.extract_metadata)
        btn_layout.addWidget(extract_btn)
        layout.addLayout(btn_layout)
        
        self.extract_tab.setLayout(layout)
    
    def setup_view_tab(self):
        layout = QVBoxLayout()
        
        # Оригинальное изображение
        self.original_figure = Figure()
        self.original_canvas = FigureCanvas(self.original_figure)
        layout.addWidget(QLabel("Original Image:"))
        layout.addWidget(self.original_canvas)
        
        # Обработанное изображение
        self.processed_figure = Figure()
        self.processed_canvas = FigureCanvas(self.processed_figure)
        layout.addWidget(QLabel("Processed Image:"))
        layout.addWidget(self.processed_canvas)
        
        self.view_tab.setLayout(layout)
    
    def browse_dicom_file(self, mode):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select DICOM File", "", "DICOM Files (*.dcm)"
        )
        if not file_path:
            return
            
        if mode == "embed":
            self.embed_file_edit.setText(file_path)
        else:
            self.extract_file_edit.setText(file_path)
            
        self.load_dicom_file(file_path, mode)
    
    def load_dicom_file(self, file_path, mode="embed"):
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
            if hasattr(self.ds, 'BitsStored'):
                self.bits_per_pixel = self.ds.BitsStored
                bits_text += str(self.bits_per_pixel)
            else:
                self.bits_per_pixel = None
                bits_text += "Not found"
            
            # Обновление интерфейса в зависимости от режима
            if mode == "extract":
                self.extract_shutter_info.setText(shutter_text)
                self.extract_bits_info.setText(bits_text)
                self.display_dicom_image(file_path, self.processed_canvas, self.processed_figure)
                
                # Проверка наличия шторки для извлечения
                if not self.shutter_params:
                    QMessageBox.warning(self, "Warning", 
                                       "No shutter information found. Data extraction may not be possible.")
            else:
                self.shutter_info.setText(shutter_text)
                self.bits_info.setText(bits_text)
                self.display_dicom_image(file_path, self.original_canvas, self.original_figure)
                
                # Проверка возможности встраивания
                status_text = "Status: "
                if self.shutter_params and self.bits_per_pixel:
                    status_text += "Ready for data embedding"
                    self.embed_status.setStyleSheet("color: green")
                else:
                    status_text += "Cannot embed data - missing required DICOM attributes"
                    self.embed_status.setStyleSheet("color: red")
                self.embed_status.setText(status_text)
                
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
        visible = state == Qt.Checked
        self.key_edit.setVisible(visible)
        self.gen_key_btn.setVisible(visible)
    
    def toggle_decrypt_fields(self, state):
        visible = state == Qt.Checked
        self.decrypt_key_edit.setVisible(visible)
    
    def generate_key(self):
        key = os.urandom(16)
        self.key_edit.setText(key.hex())
    
    def populate_metadata_table(self):
        if not self.ds:
            return
        
        # Получаем все доступные теги
        tags = []
        for elem in self.ds:
            if elem.tag.group in (0x0002, 0x0008, 0x0010, 0x0018, 0x0020, 0x0028, 0x0040):
                tags.append(elem.tag)
        
        self.metadata_table.setRowCount(len(tags))
        
        for row, tag in enumerate(tags):
            # Отображаем тег в формате (XXXX,XXXX)
            tag_item = QTableWidgetItem(f"({tag.group:04X},{tag.element:04X})")
            tag_item.setFlags(tag_item.flags() & ~Qt.ItemIsEditable)
            self.metadata_table.setItem(row, 0, tag_item)
            
            # Получаем VR и значение
            try:
                element = self.ds[tag]
                vr = element.VR
                value = str(element.value)
            except Exception:
                vr = ""
                value = ""
            
            vr_item = QTableWidgetItem(vr)
            vr_item.setFlags(vr_item.flags() & ~Qt.ItemIsEditable)
            self.metadata_table.setItem(row, 1, vr_item)
            
            value_item = QTableWidgetItem(value)
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            self.metadata_table.setItem(row, 2, value_item)
    
    def embed_and_save(self):
        if not self.embed_file_edit.text() or not self.ds:
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
            if not key_text:
                QMessageBox.warning(self, "Warning", "Please enter encryption key")
                return
            try:
                key = bytes.fromhex(key_text)
                if len(key) != 16:
                    raise ValueError("Key must be 16 bytes")
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Invalid key: {str(e)}")
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
            values.append(value)
        
        # Запрашиваем путь для сохранения
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Modified DICOM", "", "DICOM Files (*.dcm)"
        )
        if not save_path:
            return
        
        # Выполняем встраивание данных
        try:
            result = embed_encrypted_metadata(
                dcm_path=self.embed_file_edit.text(),
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
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Embedding failed: {str(e)}")
    
    def extract_metadata(self):
        file_path = self.extract_file_edit.text()
        if not file_path:
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
        if self.decrypt_check.isChecked():
            key_text = self.decrypt_key_edit.text().strip()
            if not key_text:
                QMessageBox.warning(self, "Warning", "Please enter decryption key")
                return
            try:
                key = bytes.fromhex(key_text)
                if len(key) != 16:
                    raise ValueError("Key must be 16 bytes")
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Invalid key: {str(e)}")
                return
        
        # Выполняем извлечение данных
        try:
            metadata, error = extract_decrypted_metadata(file_path, key, self.bits_per_pixel)
            
            if error:
                QMessageBox.critical(self, "Error", error)
            else:
                self.display_extracted_metadata(metadata)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Extraction failed: {str(e)}")
    
    def display_extracted_metadata(self, metadata):
        self.extracted_table.setRowCount(len(metadata))
        
        for row, item in enumerate(metadata):
            tag, vr, value = item
            
            # Отображаем тег
            tag_item = QTableWidgetItem(f"({tag[0]:04X},{tag[1]:04X})")
            tag_item.setFlags(tag_item.flags() & ~Qt.ItemIsEditable)
            self.extracted_table.setItem(row, 0, tag_item)
            
            # Отображаем VR
            vr_item = QTableWidgetItem(vr)
            vr_item.setFlags(vr_item.flags() & ~Qt.ItemIsEditable)
            self.extracted_table.setItem(row, 1, vr_item)
            
            # Отображаем значение
            if isinstance(value, bytes):
                value_str = f"<binary data, length: {len(value)} bytes>"
            elif isinstance(value, list):
                value_str = ', '.join(map(str, value))
            else:
                value_str = str(value)
            
            value_item = QTableWidgetItem(value_str)
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            self.extracted_table.setItem(row, 2, value_item)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DICOMSteganographyApp()
    window.show()
    sys.exit(app.exec_())