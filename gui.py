import os
import tempfile
import numpy as np
import pydicom
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QTextEdit, QTabWidget, QGroupBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QComboBox, QSpinBox, QAbstractItemView,
    QFormLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from dicom_utils import FORBIDDEN_TAGS, SUPPORTED_VR, update_dicom_shutter_tags
from steganography import embed_encrypted_metadata, extract_decrypted_metadata
from read import read_shutter_parameters
from pydicom.tag import Tag


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

    def init_ui(self):
        """Инициализирует графический интерфейс приложения, создавая вкладки:
            - Embed Data
            - Extract Data
            - Image Viewer

            Каждая вкладка настраивается с помощью соответствующих методов.
        """
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.embed_tab = QWidget()
        self.tabs.addTab(self.embed_tab, "Embed Data")
        self.setup_embed_tab()

        self.extract_tab = QWidget()
        self.tabs.addTab(self.extract_tab, "Extract Data")
        self.setup_extract_tab()

        self.view_tab = QWidget()
        self.tabs.addTab(self.view_tab, "Image Viewer")
        self.setup_view_tab()

        self.pacs_tab = QWidget()
        self.tabs.addTab(self.pacs_tab, "PACS Send/Receive")

        

    def setup_embed_tab(self):
        """Настраивает вкладку встраивания данных (Embed Data),
        включая выбор DICOM-файла, отображение информации, 
        параметры шторки, шифрование и выбор метаданных для встраивания."""

        layout = QVBoxLayout()
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

        info_group = QGroupBox("File Information")
        info_layout = QVBoxLayout()
        self.shutter_info = QLabel("Shutter type: Not detected")
        info_layout.addWidget(self.shutter_info)
        self.bits_info = QLabel("Bits per pixel: Not detected")
        info_layout.addWidget(self.bits_info)
        self.embed_status = QLabel("Status: Select DICOM file")
        info_layout.addWidget(self.embed_status)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        self.shutter_params_group = QGroupBox("Shutter Parameters")
        self.shutter_params_layout = QVBoxLayout()
        self.shutter_params_group.setLayout(self.shutter_params_layout)
        layout.addWidget(self.shutter_params_group)
        self.shutter_params_group.setVisible(False)

        self.encrypt_group = QGroupBox("Encryption Settings")
        encrypt_layout = QVBoxLayout()
        self.encrypt_check = QCheckBox("Enable AES-128 Encryption")
        self.encrypt_check.stateChanged.connect(self.toggle_encrypt_fields)
        encrypt_layout.addWidget(self.encrypt_check)
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Encryption Key:"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Enter 16-byte key in hex (32 characters)")
        self.key_edit.setVisible(False)
        key_layout.addWidget(self.key_edit)
        self.gen_key_btn = QPushButton("Generate Key")
        self.gen_key_btn.setVisible(False)
        self.gen_key_btn.clicked.connect(self.generate_key)
        key_layout.addWidget(self.gen_key_btn)
        encrypt_layout.addLayout(key_layout)
        self.encrypt_group.setLayout(encrypt_layout)
        layout.addWidget(self.encrypt_group)

        tag_control_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_tags)
        tag_control_layout.addWidget(self.select_all_btn)
        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all_tags)
        tag_control_layout.addWidget(self.deselect_all_btn)
        layout.addLayout(tag_control_layout)

        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(4)
        self.metadata_table.setHorizontalHeaderLabels(["Include", "Tag", "VR", "Value"])
        self.metadata_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.metadata_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.metadata_table.setEditTriggers(QAbstractItemView.DoubleClicked)
        layout.addWidget(QLabel("Metadata to Embed:"))
        layout.addWidget(self.metadata_table)

        btn_layout = QHBoxLayout()
        embed_btn = QPushButton("Embed Data and Save")
        embed_btn.clicked.connect(self.embed_and_save)
        btn_layout.addWidget(embed_btn)
        layout.addLayout(btn_layout)

        self.embed_tab.setLayout(layout)

    def setup_extract_tab(self):
        """Настраивает вкладку извлечения данных (Extract Data), 
        предоставляя интерфейс для выбора файла, ввода ключа 
        расшифровки и отображения извлеченных метаданных."""

        layout = QVBoxLayout()

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

        extract_info_group = QGroupBox("File Information")
        extract_info_layout = QVBoxLayout()
        self.extract_shutter_info = QLabel("Shutter type: Not detected")
        extract_info_layout.addWidget(self.extract_shutter_info)
        self.extract_bits_info = QLabel("Bits per pixel: Not detected")
        extract_info_layout.addWidget(self.extract_bits_info)
        extract_info_group.setLayout(extract_info_layout)
        layout.addWidget(extract_info_group)

        self.decrypt_group = QGroupBox("Decryption Settings")
        decrypt_layout = QVBoxLayout()
        self.decrypt_check = QCheckBox("Data is Encrypted")
        self.decrypt_check.stateChanged.connect(self.toggle_decrypt_fields)
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

        self.extracted_table = QTableWidget()
        self.extracted_table.setColumnCount(3)
        self.extracted_table.setHorizontalHeaderLabels(["Tag", "VR", "Value"])
        self.extracted_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(QLabel("Extracted Metadata:"))
        layout.addWidget(self.extracted_table)

        btn_layout = QHBoxLayout()
        extract_btn = QPushButton("Extract Metadata")
        extract_btn.clicked.connect(self.extract_metadata)
        btn_layout.addWidget(extract_btn)
        self.save_dicom_btn = QPushButton("Save DICOM with Extracted Metadata")
        self.save_dicom_btn.clicked.connect(self.save_dicom_with_metadata)
        self.save_dicom_btn.setEnabled(False)
        btn_layout.addWidget(self.save_dicom_btn)
        layout.addLayout(btn_layout)

        self.extract_tab.setLayout(layout)

    def setup_view_tab(self):
        """Создает вкладку просмотра изображений, включая области
        для отображения оригинального и обработанного DICOM-изображения."""
        layout = QVBoxLayout()
        self.original_figure = Figure()
        self.original_canvas = FigureCanvas(self.original_figure)
        layout.addWidget(QLabel("Original Image:"))
        layout.addWidget(self.original_canvas)
        self.processed_figure = Figure()
        self.processed_canvas = FigureCanvas(self.processed_figure)
        layout.addWidget(QLabel("Processed Image:"))
        layout.addWidget(self.processed_canvas)
        self.view_tab.setLayout(layout)

    def browse_dicom_file(self, mode):
        """Открывает диалог выбора DICOM-файла и вызывает загрузку
        выбранного файла в зависимости от режима (embed/extract).

        Args:
            mode (str): Режим загрузки — 'embed' или 'extract'
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Select DICOM File", "", "DICOM Files (*.dcm)")
        if not file_path:
            return
        if mode == "embed":
            self.embed_file_edit.setText(file_path)
        else:
            self.extract_file_edit.setText(file_path)
        self.load_dicom_file(file_path, mode)

    def load_dicom_file(self, file_path, mode="embed"):
        """Загружает DICOM-файл и отображает информацию о шторке,
        глубине пикселя, изображение, а также подготавливает таблицу метаданных.

        Args:
            file_path (str): Путь к DICOM-файлу
            mode (str): embed или extract

        Raises:
            QMessageBox: При ошибке чтения файла
        """


        try:
            self.ds = pydicom.dcmread(file_path, force=True)
            self.shutter_params = read_shutter_parameters(file_path)
            shutter_text = "Shutter type: " + (self.shutter_params.get('type') if self.shutter_params else "Not found")
            bits_text = "Bits per pixel: " + (str(self.ds.BitsStored) if hasattr(self.ds, 'BitsStored') else "Not found")
            self.bits_per_pixel = getattr(self.ds, 'BitsStored', None)

            if mode == "extract":
                self.extract_shutter_info.setText(shutter_text)
                self.extract_bits_info.setText(bits_text)
                self.display_dicom_image(file_path, self.processed_canvas, self.processed_figure)
                if not self.shutter_params:
                    QMessageBox.warning(self, "Warning", "No shutter information found. Data extraction may not be possible.")
            else:
                self.shutter_info.setText(shutter_text)
                self.bits_info.setText(bits_text)
                self.display_dicom_image(file_path, self.original_canvas, self.original_figure)
                ready = self.shutter_params and self.bits_per_pixel
                self.embed_status.setText("Status: " + ("Ready for data embedding" if ready else "Cannot embed data - missing required DICOM attributes"))
                self.embed_status.setStyleSheet("color: green" if ready else "color: red")
                if ready:
                    self.setup_shutter_params_form()
                    self.populate_metadata_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load DICOM file: {e}")

    def setup_shutter_params_form(self):
        """Создает форму для ввода параметров шторки в зависимости от её типа:
        RECTANGULAR, CIRCULAR или POLYGONAL."""
        # Очищаем предыдущие виджеты
        while self.shutter_params_layout.count():
            child = self.shutter_params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.shutter_params_group.setVisible(True)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Shutter Type:"))
        self.shutter_type_combo = QComboBox()
        self.shutter_type_combo.addItems(["RECTANGULAR", "CIRCULAR", "POLYGONAL"])
        self.shutter_type_combo.setCurrentText(self.shutter_params.get('type', 'RECTANGULAR'))
        self.shutter_type_combo.currentTextChanged.connect(self.setup_shutter_params_form)
        type_layout.addWidget(self.shutter_type_combo)
        self.shutter_params_layout.addLayout(type_layout)

        stype = self.shutter_type_combo.currentText()
        if stype == "RECTANGULAR":
            self.setup_rectangular_shutter_form()
        elif stype == "CIRCULAR":
            self.setup_circular_shutter_form()
        else:
            self.setup_polygonal_shutter_form()

    def setup_rectangular_shutter_form(self):
        """Создает форму ввода прямоугольной шторки: левый, правый, верхний, нижний край."""
        form_layout = QFormLayout()
        self.left_edit = QSpinBox()
        self.left_edit.setRange(0, 10000)
        self.left_edit.setValue(self.shutter_params.get('left', 0))
        form_layout.addRow("Left:", self.left_edit)
        self.right_edit = QSpinBox(); self.right_edit.setRange(0, 10000); self.right_edit.setValue(self.shutter_params.get('right', 512))
        form_layout.addRow("Right:", self.right_edit)
        self.top_edit = QSpinBox(); self.top_edit.setRange(0, 10000); self.top_edit.setValue(self.shutter_params.get('top', 0))
        form_layout.addRow("Top:", self.top_edit)
        self.bottom_edit = QSpinBox(); self.bottom_edit.setRange(0, 10000); self.bottom_edit.setValue(self.shutter_params.get('bottom', 512))
        form_layout.addRow("Bottom:", self.bottom_edit)
        self.shutter_params_layout.addLayout(form_layout)

    def setup_circular_shutter_form(self):
        """Создает форму ввода круговой шторки: координаты центра и радиус."""
        form_layout = QFormLayout()
        self.center_x_edit = QSpinBox(); self.center_x_edit.setRange(0, 10000); self.center_x_edit.setValue(self.shutter_params.get('center_x', 256))
        form_layout.addRow("Center X:", self.center_x_edit)
        self.center_y_edit = QSpinBox(); self.center_y_edit.setRange(0, 10000); self.center_y_edit.setValue(self.shutter_params.get('center_y', 256))
        form_layout.addRow("Center Y:", self.center_y_edit)
        self.radius_edit = QSpinBox(); self.radius_edit.setRange(0, 10000); self.radius_edit.setValue(self.shutter_params.get('radius', 100))
        form_layout.addRow("Radius:", self.radius_edit)
        self.shutter_params_layout.addLayout(form_layout)

    def setup_polygonal_shutter_form(self):
        """Создает форму ввода полигональной шторки в формате: x1,y1;x2,y2;..."""
        form_layout = QFormLayout()
        vertices_label = QLabel("Vertices (format: x1,y1;x2,y2;...):")
        self.vertices_edit = QTextEdit()
        verts = self.shutter_params.get('vertices', [])
        self.vertices_edit.setText(';'.join(f"{x},{y}" for x,y in verts))
        form_layout.addRow(vertices_label, self.vertices_edit)
        self.shutter_params_layout.addLayout(form_layout)

    def display_dicom_image(self, file_path, canvas, figure):
        """Отображает изображение из DICOM-файла на переданном холсте.

        Args:
            file_path (str): Путь к файлу
            canvas (FigureCanvas): Холст для отображения
            figure (Figure): Фигура matplotlib

        Raises:
            QMessageBox: В случае ошибки загрузки изображения
        """
        try:
            ds = pydicom.dcmread(file_path, force=True)
            img = ds.pixel_array
            figure.clear(); ax = figure.add_subplot(111)
            ax.imshow(img, cmap='gray'); ax.axis('off'); canvas.draw()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to display image: {e}")

    def toggle_encrypt_fields(self, state):
        """Отображает или скрывает поля для ввода ключа шифрования.

        Args:
            state (int): Состояние флажка (Qt.Checked/Unchecked)
        """
        vis = state == Qt.Checked
        self.key_edit.setVisible(vis); self.gen_key_btn.setVisible(vis)

    def toggle_decrypt_fields(self, state):
        """Отображает или скрывает поле ввода ключа расшифровки.

        Args:
            state (int): Состояние флажка (Qt.Checked/Unchecked)
        """
        self.decrypt_key_edit.setVisible(state == Qt.Checked)

    def generate_key(self):
        """Генерирует случайный 16-байтный ключ и отображает его в hex-формате в поле ввода."""
        key = os.urandom(16)
        self.key_edit.setText(key.hex())

    def select_all_tags(self):
        """Устанавливает флажки включения на всех строках таблицы метаданных."""
        for r in range(self.metadata_table.rowCount()):
            item = self.metadata_table.item(r, 0)
            if item: item.setCheckState(Qt.Checked)

    def deselect_all_tags(self):
        """Снимает флажки включения со всех строк таблицы метаданных."""
        for r in range(self.metadata_table.rowCount()):
            item = self.metadata_table.item(r, 0)
            if item: item.setCheckState(Qt.Unchecked)

    def populate_metadata_table(self):
        """Заполняет таблицу метаданных доступными DICOM-тегами,
        исключая запрещённые и неподдерживаемые VR."""
        if not self.ds:
            return
        # Собираем теги, исключая forbidden
        tags = []
        for elem in self.ds:
            t = (elem.tag.group, elem.tag.element)
            if t in FORBIDDEN_TAGS:
                continue
            if elem.VR not in SUPPORTED_VR:
                continue
            # ограничим по группам как ранее
            if elem.tag.group in (0x0002, 0x0008, 0x0010, 0x0018, 0x0020, 0x0028, 0x0040):
                tags.append(elem.tag)
        self.metadata_table.setRowCount(len(tags))
        for row, tag in enumerate(tags):
            include_item = QTableWidgetItem()
            include_item.setFlags(include_item.flags() | Qt.ItemIsUserCheckable)
            include_item.setCheckState(Qt.Checked)
            self.metadata_table.setItem(row, 0, include_item)

            tag_item = QTableWidgetItem(f"({tag.group:04X},{tag.element:04X})")
            tag_item.setFlags(tag_item.flags() & ~Qt.ItemIsEditable)
            self.metadata_table.setItem(row, 1, tag_item)

            try:
                element = self.ds[tag]
                vr = element.VR
                value = str(element.value)
            except Exception:
                vr = ""
                value = ""
            vr_item = QTableWidgetItem(vr)
            vr_item.setFlags(vr_item.flags() & ~Qt.ItemIsEditable)
            self.metadata_table.setItem(row, 2, vr_item)

            value_item = QTableWidgetItem(value)
            value_item.setFlags(value_item.flags() | Qt.ItemIsEditable)
            self.metadata_table.setItem(row, 3, value_item)

    def get_shutter_params_from_form(self):
        """Извлекает параметры шторки из формы ввода.

        Returns:
            dict: Словарь с параметрами шторки в зависимости от типа
        """
        stype = self.shutter_type_combo.currentText()
        params = {'type': stype}
        if stype == "RECTANGULAR":
            params.update({
                'left': self.left_edit.value(), 'right': self.right_edit.value(),
                'top': self.top_edit.value(), 'bottom': self.bottom_edit.value()
            })
        elif stype == "CIRCULAR":
            params.update({
                'center_x': self.center_x_edit.value(), 'center_y': self.center_y_edit.value(),
                'radius': self.radius_edit.value()
            })
        else:
            verts = []
            for pair in self.vertices_edit.toPlainText().split(';'):
                if pair.strip(): x,y = map(int,pair.split(',')); verts.append((x,y))
            params['vertices'] = verts
        return params

    def update_dicom_shutter_tags(self, ds, shutter_params):
        """Обновляет теги DICOM-файла, связанные со шторкой.

        Args:
            ds (Dataset): Объект pydicom Dataset
            shutter_params (dict): Параметры шторки
        """
        tags = [(0x0018,0x1600),(0x0018,0x1602),(0x0018,0x1604),(0x0018,0x1606),(0x0018,0x1608),
                (0x0018,0x1610),(0x0018,0x1611),(0x0018,0x1612),(0x0018,0x1620)]
        for tag in tags:
            if tag in ds: del ds[tag]
        ds.add_new((0x0018,0x1600),'CS',shutter_params['type'])
        if shutter_params['type']=="RECTANGULAR":
            ds.add_new((0x0018,0x1602),'IS',str(shutter_params['left'])); ds.add_new((0x0018,0x1604),'IS',str(shutter_params['right']))
            ds.add_new((0x0018,0x1606),'IS',str(shutter_params['top'])); ds.add_new((0x0018,0x1608),'IS',str(shutter_params['bottom']))
        elif shutter_params['type']=="CIRCULAR":
            ds.add_new((0x0018,0x1610),'IS',str(shutter_params['center_x'])); ds.add_new((0x0018,0x1611),'IS',str(shutter_params['center_y']))
            ds.add_new((0x0018,0x1612),'IS',str(shutter_params['radius']))
        else:
            flat=[coord for pt in shutter_params['vertices'] for coord in pt]
            ds.add_new((0x0018,0x1620),'IS',flat)

    def embed_and_save(self):
        """Встраивает выбранные теги в DICOM, шифрует их при необходимости,
        сохраняет результат и отображает обновлённое изображение.

        Raises:
            QMessageBox: При ошибках валидации или сохранения
        """
        if not self.embed_file_edit.text() or not self.ds:
            QMessageBox.warning(self, "Warning", "Please select a DICOM file first")
            return
        new_params = self.get_shutter_params_from_form()
        self.update_dicom_shutter_tags(self.ds, new_params)

        tags_to_embed, vr_list, values = [], [], []
        for row in range(self.metadata_table.rowCount()):
            if self.metadata_table.item(row, 0).checkState() == Qt.Checked:
                tag_text = self.metadata_table.item(row, 1).text().strip("()")
                group, element = map(lambda x: int(x, 16), tag_text.split(','))
                if (group, element) in FORBIDDEN_TAGS:
                    continue
                tags_to_embed.append((group, element))
                vr_list.append(self.metadata_table.item(row, 2).text())
                values.append(self.metadata_table.item(row, 3).text())
        if not tags_to_embed:
            QMessageBox.warning(self, "Warning", "No valid tags selected for embedding")
            return

        # Удаляем скрываемые теги
        for g, e in tags_to_embed:
            tag_obj = Tag(g, e)
            if tag_obj in self.ds:
                del self.ds[tag_obj]

        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.dcm')
        os.close(tmp_fd)
        try:
            self.ds.save_as(tmp_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save temporary DICOM file: {e}")
            return

        key = None
        if self.encrypt_check.isChecked():
            key_text = self.key_edit.text().strip()
            if not key_text:
                QMessageBox.warning(self, "Warning", "Please enter encryption key")
                return
            try:
                key = bytes.fromhex(key_text)
                if len(key) != 16:
                    raise ValueError("Key must be 16 bytes")
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Invalid key: {e}")
                return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save Modified DICOM", "", "DICOM Files (*.dcm)")
        if not save_path:
            os.remove(tmp_path)
            return
        try:
            result = embed_encrypted_metadata(
                dcm_path=tmp_path,
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
                self.shutter_params = new_params
                self.display_dicom_image(save_path, self.processed_canvas, self.processed_figure)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Embedding failed: {e}")
        finally:
            try:
                os.remove(tmp_path)
            except:
                pass

    def extract_metadata(self):
        """Извлекает скрытые метаданные из DICOM-файла с учётом расшифровки,
        отображает результат в таблице.

        Raises:
            QMessageBox: При ошибках ключа или чтения
        """
        fp=self.extract_file_edit.text()
        if not fp: QMessageBox.warning(self, "Warning", "Please select a DICOM file"); return
        if not self.shutter_params or not self.bits_per_pixel:
            QMessageBox.critical(self, "Error", "Cannot extract data: missing attributes"); return
        key=None
        if self.decrypt_check.isChecked():
            text=self.decrypt_key_edit.text().strip()
            if not text: QMessageBox.warning(self, "Warning", "Please enter decryption key"); return
            try: key=bytes.fromhex(text); assert len(key)==16
            except Exception as e: QMessageBox.warning(self, "Warning", f"Invalid key: {e}"); return
        try:
            self.extracted_metadata, err = extract_decrypted_metadata(fp, key, self.bits_per_pixel)
            if err: QMessageBox.critical(self, "Error", err)
            else:
                self.display_extracted_metadata(self.extracted_metadata)
                self.save_dicom_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Extraction failed: {e}")

    def save_dicom_with_metadata(self):
        """Сохраняет DICOM-файл с ранее извлечёнными метаданными,
        вставляя их обратно в dataset.

        Raises:
            QMessageBox: При ошибке сохранения файла
        """
        if not self.extracted_metadata or not self.extract_file_edit.text():
            QMessageBox.warning(self, "Warning", "No extracted metadata to save"); return
        save_path,_=QFileDialog.getSaveFileName(self, "Save DICOM with Extracted Metadata", "", "DICOM Files (*.dcm)")
        if not save_path: return
        try:
            ds = pydicom.dcmread(self.extract_file_edit.text(), force=True)
            for tag, vr, val in self.extracted_metadata:
                tag_obj = Tag(tag[0], tag[1])
                if tag_obj in ds: ds[tag_obj].value = val
                else: ds.add_new(tag_obj, vr, val)
            ds.save_as(save_path)
            QMessageBox.information(self, "Success", "DICOM file with extracted metadata saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save DICOM: {e}")

    def display_extracted_metadata(self, metadata):
        """Отображает извлечённые метаданные в таблице интерфейса.

        Args:
            metadata (List[Tuple[Tuple[int,int], str, Any]]):
                Список метаданных вида (тег, VR, значение)
        """
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

