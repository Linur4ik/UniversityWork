from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGroupBox,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QWidget
)
from PyQt5.QtCore import Qt
import pydicom
from pydicom.tag import Tag


class ExtractTab(QWidget):
    """Вкладка для извлечения данных."""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.file_edit = None
        self.shutter_info = self.bits_info = None
        self.decrypt_check = None
        self.decrypt_key_edit = None
        self.extracted_table = None
        self.save_dicom_btn = None
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализирует интерфейс вкладки."""
        layout = QVBoxLayout()

        # Группа выбора файла
        file_group = QGroupBox("DICOM File with Embedded Data")
        file_layout = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        extract_browse_btn = QPushButton("Browse...")
        extract_browse_btn.clicked.connect(lambda: self.main_window.browse_dicom_file("extract"))
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(extract_browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Группа информации о файле
        extract_info_group = QGroupBox("File Information")
        extract_info_layout = QVBoxLayout()
        self.shutter_info = QLabel("Shutter type: Not detected")
        extract_info_layout.addWidget(self.shutter_info)
        self.bits_info = QLabel("Bits per pixel: Not detected")
        extract_info_layout.addWidget(self.bits_info)
        extract_info_group.setLayout(extract_info_layout)
        layout.addWidget(extract_info_group)

        # Группа расшифровки
        self.decrypt_group = QGroupBox("Decryption Settings")
        decrypt_layout = QVBoxLayout()
        self.decrypt_check = QCheckBox("Data is Encrypted")
        self.decrypt_check.stateChanged.connect(self.main_window.toggle_decrypt_fields)
        decrypt_layout.addWidget(self.decrypt_check)
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Decryption Key:"))
        self.decrypt_key_edit = QLineEdit()
        self.decrypt_key_edit.setPlaceholderText("Enter 16-byte key in hex")
        self.decrypt_key_edit.setVisible(False)
        key_layout.addWidget(self.decrypt_key_edit)
        decrypt_layout.addLayout(key_layout)
        self.decrypt_group.setLayout(decrypt_layout)
        layout.addWidget(self.decrypt_group)

        # Таблица извлеченных данных
        self.extracted_table = QTableWidget()
        self.extracted_table.setColumnCount(3)
        self.extracted_table.setHorizontalHeaderLabels(["Tag", "VR", "Value"])
        self.extracted_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(QLabel("Extracted Metadata:"))
        layout.addWidget(self.extracted_table)

        # Кнопки
        btn_layout = QHBoxLayout()
        extract_btn = QPushButton("Extract Metadata")
        extract_btn.clicked.connect(self.main_window.extract_metadata)
        btn_layout.addWidget(extract_btn)
        self.save_dicom_btn = QPushButton("Save DICOM with Extracted Metadata")
        self.save_dicom_btn.clicked.connect(self.main_window.save_dicom_with_metadata)
        self.save_dicom_btn.setEnabled(False)
        btn_layout.addWidget(self.save_dicom_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def toggle_decrypt_fields(self, state):
        """Показывает/скрывает поле ключа расшифровки."""
        self.decrypt_key_edit.setVisible(state == Qt.Checked)

    def extract_metadata(self, shutter_params, bits_per_pixel, extract_func, display_callback):
        """Извлекает метаданные из файла."""
        file_path = self.file_edit.text()
        if not file_path:
            QMessageBox.warning(self, "Warning", "Please select a DICOM file")
            return None
        
        if not shutter_params or not bits_per_pixel:
            QMessageBox.critical(self, "Error", "Cannot extract data: missing attributes")
            return None
        
        # Получаем ключ расшифровки
        key = None
        if self.decrypt_check.isChecked():
            text = self.decrypt_key_edit.text().strip()
            if not text:
                QMessageBox.warning(self, "Warning", "Please enter decryption key")
                return None
            try:
                key = bytes.fromhex(text)
                if len(key) != 16:
                    raise ValueError("Key must be 16 bytes")
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Invalid key: {e}")
                return None
        
        # Извлекаем данные
        try:
            metadata, err = extract_func(file_path, key, bits_per_pixel)
            if err:
                QMessageBox.critical(self, "Error", err)
                return None
            else:
                display_callback(metadata)
                return metadata
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Extraction failed: {e}")
            return None

    def save_dicom_with_metadata(self, extracted_metadata):
        """Сохраняет DICOM с извлеченными метаданными."""
        if not extracted_metadata or not self.file_edit.text():
            QMessageBox.warning(self, "Warning", "No extracted metadata to save")
            return
        
        save_path, _ = QFileDialog.getSaveFileName(self, "Save DICOM with Extracted Metadata", "", "DICOM Files (*.dcm)")
        if not save_path:
            return
        
        try:
            ds = pydicom.dcmread(self.file_edit.text(), force=True)
            for tag, vr, val in extracted_metadata:
                tag_obj = Tag(tag[0], tag[1])
                if tag_obj in ds:
                    ds[tag_obj].value = val
                else:
                    ds.add_new(tag_obj, vr, val)
            ds.save_as(save_path)
            QMessageBox.information(self, "Success", "DICOM file with extracted metadata saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save DICOM: {e}")

    def display_extracted_metadata(self, metadata):
        """Отображает извлеченные метаданные."""
        self.extracted_table.setRowCount(len(metadata))
        
        for r, item in enumerate(metadata):
            tag, vr, val = item
            tag_str = f"({tag[0]:04X},{tag[1]:04X})"
            tag_item = QTableWidgetItem(tag_str)
            tag_item.setFlags(tag_item.flags() & ~Qt.ItemIsEditable)
            
            vr_item = QTableWidgetItem(vr)
            vr_item.setFlags(vr_item.flags() & ~Qt.ItemIsEditable)
            
            if isinstance(val, bytes):
                val_str = f"<binary data, length: {len(val)} bytes>"
            elif isinstance(val, list):
                val_str = ', '.join(map(str, val))
            else:
                val_str = str(val)
            
            val_item = QTableWidgetItem(val_str)
            val_item.setFlags(val_item.flags() & ~Qt.ItemIsEditable)
            
            self.extracted_table.setItem(r, 0, tag_item)
            self.extracted_table.setItem(r, 1, vr_item)
            self.extracted_table.setItem(r, 2, val_item)