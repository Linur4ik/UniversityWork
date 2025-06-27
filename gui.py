import sys
import os
import pydicom
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QFileDialog, QTextEdit, QTabWidget, QGroupBox,
                            QMessageBox, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from cryptFunc import encrypt_aes128, decrypt_aes128
from generate import generate_shutter_mask
from read import read_shutter_parameters, read_bits_from_mask
from write import write_bits_to_mask
from operation import metadata_to_bitstream, bitstream_to_metadata

class DICOMSteganographyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DICOM Steganography Tool")
        self.setGeometry(100, 100, 1200, 800)
        
        # Основные переменные
        self.current_file = None
        self.ds = None
        self.key = None
        
        # Создание интерфейса
        self.init_ui()
        
    def init_ui(self):
        # Создание вкладок
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Вкладка для шифрования
        self.encrypt_tab = QWidget()
        self.tabs.addTab(self.encrypt_tab, "Encrypt Metadata")
        self.setup_encrypt_tab()
        
        # Вкладка для дешифрования
        self.decrypt_tab = QWidget()
        self.tabs.addTab(self.decrypt_tab, "Decrypt Metadata")
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
        
        # Ключ шифрования
        key_group = QGroupBox("Encryption Settings")
        key_layout = QVBoxLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Enter 16-byte key in hex (e.g., 00112233445566778899aabbccddeeff)")
        self.key_edit.textChanged.connect(self.validate_key)
        key_layout.addWidget(QLabel("AES-128 Key:"))
        key_layout.addWidget(self.key_edit)
        
        # Параметры шторки
        shutter_layout = QHBoxLayout()
        self.shutter_combo = QComboBox()
        self.shutter_combo.addItems(["RECTANGULAR", "CIRCULAR", "POLYGONAL"])
        shutter_layout.addWidget(QLabel("Shutter Type:"))
        shutter_layout.addWidget(self.shutter_combo)
        key_layout.addLayout(shutter_layout)
        
        # Бит на пиксель
        bits_layout = QHBoxLayout()
        self.bits_combo = QComboBox()
        self.bits_combo.addItems(["8", "16"])
        bits_layout.addWidget(QLabel("Bits per Pixel:"))
        bits_layout.addWidget(self.bits_combo)
        key_layout.addLayout(bits_layout)
        
        key_group.setLayout(key_layout)
        layout.addWidget(key_group)
        
        # Таблица метаданных
        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(3)
        self.metadata_table.setHorizontalHeaderLabels(["Tag", "VR", "Value"])
        self.metadata_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(QLabel("Metadata to Encrypt:"))
        layout.addWidget(self.metadata_table)
        
        # Кнопки действий
        btn_layout = QHBoxLayout()
        encrypt_btn = QPushButton("Encrypt and Save")
        encrypt_btn.clicked.connect(self.encrypt_and_save)
        btn_layout.addWidget(encrypt_btn)
        layout.addLayout(btn_layout)
        
        self.encrypt_tab.setLayout(layout)
    
    def setup_decrypt_tab(self):
        layout = QVBoxLayout()
        
        # Выбор файла
        file_group = QGroupBox("Encrypted DICOM File")
        file_layout = QHBoxLayout()
        self.encrypted_file_edit = QLineEdit()
        self.encrypted_file_edit.setReadOnly(True)
        decrypt_browse_btn = QPushButton("Browse...")
        decrypt_browse_btn.clicked.connect(self.browse_decrypt_file)
        file_layout.addWidget(self.encrypted_file_edit)
        file_layout.addWidget(decrypt_browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Ключ дешифрования
        key_group = QGroupBox("Decryption Key")
        key_layout = QVBoxLayout()
        self.decrypt_key_edit = QLineEdit()
        self.decrypt_key_edit.setPlaceholderText("Enter 16-byte key in hex")
        key_layout.addWidget(QLabel("AES-128 Key:"))
        key_layout.addWidget(self.decrypt_key_edit)
        key_group.setLayout(key_layout)
        layout.addWidget(key_group)
        
        # Извлеченные метаданные
        self.decrypted_table = QTableWidget()
        self.decrypted_table.setColumnCount(3)
        self.decrypted_table.setHorizontalHeaderLabels(["Tag", "VR", "Value"])
        self.decrypted_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(QLabel("Decrypted Metadata:"))
        layout.addWidget(self.decrypted_table)
        
        # Кнопки действий
        btn_layout = QHBoxLayout()
        decrypt_btn = QPushButton("Decrypt Metadata")
        decrypt_btn.clicked.connect(self.decrypt_metadata)
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
        layout.addWidget(QLabel("Difference:"))
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
            self.populate_metadata_table()
    
    def browse_decrypt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Encrypted DICOM File", "", "DICOM Files (*.dcm)"
        )
        if file_path:
            self.encrypted_file_edit.setText(file_path)
            self.load_dicom_file(file_path, encrypted=True)
            self.display_dicom_image(file_path, self.original_canvas, self.original_figure)
    
    def load_dicom_file(self, file_path, encrypted=False):
        try:
            self.ds = pydicom.dcmread(file_path, force=True)
            if not encrypted:
                self.display_dicom_image(file_path, self.original_canvas, self.original_figure)
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
    
    def validate_key(self):
        key_text = self.key_edit.text().strip()
        if len(key_text) == 32:
            try:
                self.key = bytes.fromhex(key_text)
            except ValueError:
                self.key = None
    
    def populate_metadata_table(self):
        if not self.ds:
            return
        
        # Предопределенные теги для шифрования
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
    
    def encrypt_and_save(self):
        if not self.current_file or not self.ds:
            QMessageBox.warning(self, "Warning", "Please select a DICOM file first")
            return
        
        if not self.key or len(self.key) != 16:
            QMessageBox.warning(self, "Warning", "Please enter a valid 16-byte hex key")
            return
        
        # Собираем метаданные для шифрования
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
        
        # Выбираем параметры шифрования
        shutter_type = self.shutter_combo.currentText()
        bits_per_pixel = int(self.bits_combo.currentText())
        
        # Запрашиваем путь для сохранения
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Encrypted DICOM", "", "DICOM Files (*.dcm)"
        )
        if not save_path:
            return
        
        # Выполняем шифрование
        result = embed_encrypted_metadata(
            dcm_path=self.current_file,
            key=self.key,
            tags_to_embed=tags_to_embed,
            vr_list=vr_list,
            values=values,
            output_path=save_path,
            bits_per_pixel=bits_per_pixel
        )
        
        if result:
            QMessageBox.critical(self, "Error", result)
        else:
            QMessageBox.information(self, "Success", "Metadata encrypted and saved successfully!")
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
            
            # Вычисляем разницу
            diff = orig_img.astype(np.int16) - proc_img.astype(np.int16)
            abs_diff = np.abs(diff)
            
            # Отображаем разницу
            self.diff_figure.clear()
            ax = self.diff_figure.add_subplot(111)
            ax.imshow(abs_diff, cmap='hot')
            ax.axis('off')
            ax.set_title("Pixel Differences")
            self.diff_canvas.draw()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to show difference: {str(e)}")
    
    def decrypt_metadata(self):
        encrypted_file = self.encrypted_file_edit.text()
        if not encrypted_file:
            QMessageBox.warning(self, "Warning", "Please select an encrypted DICOM file")
            return
        
        key_text = self.decrypt_key_edit.text().strip()
        if len(key_text) != 32:
            QMessageBox.warning(self, "Warning", "Please enter a valid 16-byte hex key")
            return
        
        try:
            key = bytes.fromhex(key_text)
        except ValueError:
            QMessageBox.warning(self, "Warning", "Invalid hex format for key")
            return
        
        # Выполняем дешифрование
        metadata, error = extract_decrypted_metadata(encrypted_file, key)
        
        if error:
            QMessageBox.critical(self, "Error", error)
        else:
            self.display_decrypted_metadata(metadata)
            self.display_dicom_image(encrypted_file, self.processed_canvas, self.processed_figure)
    
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