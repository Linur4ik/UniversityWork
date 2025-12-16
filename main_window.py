import os
import tempfile
import numpy as np
import pydicom
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from pydicom.tag import Tag

from dicom_utils import FORBIDDEN_TAGS, SUPPORTED_VR
from steganography import embed_encrypted_metadata, extract_decrypted_metadata
from read import read_shutter_parameters
from tabs import EmbedTab, ExtractTab, ViewTab, PACSTab


class DICOMSteganographyApp(QMainWindow):
    """Главное окно приложения для стеганографии в DICOM файлах."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DICOM Steganography Tool")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon("icon.png"))
        
        self.current_file = None
        self.ds = None
        self.key = None
        self.shutter_params = None
        self.bits_per_pixel = None
        self.extracted_metadata = None
        
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """Инициализирует графический интерфейс приложения."""
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Создаем вкладки
        self.embed_tab = EmbedTab(self)
        self.extract_tab = ExtractTab(self)
        self.view_tab = ViewTab(self)
        self.pacs_tab = PACSTab(self)

        # Добавляем вкладки
        self.tabs.addTab(self.embed_tab, "Embed Data")
        self.tabs.addTab(self.extract_tab, "Extract Data")
        self.tabs.addTab(self.view_tab, "Image Viewer")
        self.tabs.addTab(self.pacs_tab, "PACS Send/Receive")

    def setup_connections(self):
        """Настраивает связи между виджетами."""
        # Эти связи уже настроены в конструкторах вкладок
        pass

    def browse_dicom_file(self, mode):
        """Открывает диалог выбора DICOM-файла."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select DICOM File", "", "DICOM Files (*.dcm)")
        if not file_path:
            return
        if mode == "embed":
            self.embed_tab.file_edit.setText(file_path)
        else:
            self.extract_tab.file_edit.setText(file_path)
        self.load_dicom_file(file_path, mode)

    def load_dicom_file(self, file_path, mode="embed"):
        """Загружает DICOM-файл и отображает информацию."""
        try:
            self.ds = pydicom.dcmread(file_path, force=True)
            self.shutter_params = read_shutter_parameters(file_path)
            shutter_text = "Shutter type: " + (self.shutter_params.get('type') if self.shutter_params else "Not found")
            bits_text = "Bits per pixel: " + (str(self.ds.BitsStored) if hasattr(self.ds, 'BitsStored') else "Not found")
            self.bits_per_pixel = getattr(self.ds, 'BitsStored', None)

            if mode == "extract":
                self.extract_tab.shutter_info.setText(shutter_text)
                self.extract_tab.bits_info.setText(bits_text)
                self.view_tab.display_image(file_path, processed=True)
                if not self.shutter_params:
                    QMessageBox.warning(self, "Warning", "No shutter information found. Data extraction may not be possible.")
            else:
                self.embed_tab.shutter_info.setText(shutter_text)
                self.embed_tab.bits_info.setText(bits_text)
                self.view_tab.display_image(file_path, processed=False)
                ready = self.shutter_params and self.bits_per_pixel
                self.embed_tab.status_label.setText("Status: " + ("Ready for data embedding" if ready else "Cannot embed data - missing required DICOM attributes"))
                self.embed_tab.status_label.setStyleSheet("color: green" if ready else "color: red")
                if ready:
                    self.embed_tab.setup_shutter_params_form(self.shutter_params)
                    self.populate_metadata_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load DICOM file: {e}")

    def populate_metadata_table(self):
        """Заполняет таблицу метаданных доступными DICOM-тегами."""
        if not self.ds:
            return
        
        self.embed_tab.populate_metadata_table(self.ds, FORBIDDEN_TAGS, SUPPORTED_VR)

    def select_all_tags(self):
        """Устанавливает флажки включения на всех строках таблицы метаданных."""
        self.embed_tab.select_all_tags()

    def deselect_all_tags(self):
        """Снимает флажки включения со всех строк таблицы метаданных."""
        self.embed_tab.deselect_all_tags()

    def toggle_encrypt_fields(self, state):
        """Отображает или скрывает поля для ввода ключа шифрования."""
        self.embed_tab.toggle_encrypt_fields(state)

    def toggle_decrypt_fields(self, state):
        """Отображает или скрывает поле ввода ключа расшифровки."""
        self.extract_tab.toggle_decrypt_fields(state)

    def generate_key(self):
        """Генерирует случайный 16-байтный ключ."""
        self.embed_tab.generate_key()

    def embed_and_save(self):
        """Встраивает выбранные теги в DICOM, шифрует их при необходимости."""
        self.embed_tab.embed_and_save(
            self.ds,
            self.shutter_params,
            self.bits_per_pixel,
            FORBIDDEN_TAGS,
            embed_encrypted_metadata,
            self.update_shutter_params_in_gui,
            self.display_dicom_image_in_viewer
        )

    def extract_metadata(self):
        """Извлекает скрытые метаданные из DICOM-файла."""
        result = self.extract_tab.extract_metadata(
            self.shutter_params,
            self.bits_per_pixel,
            extract_decrypted_metadata,
            self.display_extracted_metadata
        )
        if result:
            self.extracted_metadata = result
            self.extract_tab.save_dicom_btn.setEnabled(True)

    def save_dicom_with_metadata(self):
        """Сохраняет DICOM-файл с ранее извлечёнными метаданными."""
        self.extract_tab.save_dicom_with_metadata(self.extracted_metadata)

    def display_extracted_metadata(self, metadata):
        """Отображает извлечённые метаданные в таблице интерфейса."""
        self.extract_tab.display_extracted_metadata(metadata)

    def update_shutter_params_in_gui(self, new_params):
        """Обновляет параметры шторки в GUI."""
        self.shutter_params = new_params

    def display_dicom_image_in_viewer(self, file_path):
        """Отображает изображение DICOM во вкладке просмотра."""
        self.view_tab.display_image(file_path, processed=True)