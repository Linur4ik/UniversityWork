import os
import tempfile
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGroupBox,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFormLayout, QComboBox, QSpinBox, QTextEdit, QMessageBox, QFileDialog, QWidget
)
from PyQt5.QtCore import Qt
from pydicom.tag import Tag


class EmbedTab(QWidget):
    """Вкладка для встраивания данных."""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.shutter_type_combo = None
        self.left_edit = self.right_edit = self.top_edit = self.bottom_edit = None
        self.center_x_edit = self.center_y_edit = self.radius_edit = None
        self.vertices_edit = None
        self.metadata_table = None
        self.key_edit = None
        self.encrypt_check = None
        self.gen_key_btn = None
        self.shutter_info = self.bits_info = self.status_label = None
        self.shutter_params_group = self.shutter_params_layout = None
        self.file_edit = None
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализирует интерфейс вкладки."""
        layout = QVBoxLayout()
        
        # Группа выбора файла
        file_group = QGroupBox("DICOM File")
        file_layout = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        file_browse_btn = QPushButton("Browse...")
        file_browse_btn.clicked.connect(lambda: self.main_window.browse_dicom_file("embed"))
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(file_browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Группа информации о файле
        info_group = QGroupBox("File Information")
        info_layout = QVBoxLayout()
        self.shutter_info = QLabel("Shutter type: Not detected")
        info_layout.addWidget(self.shutter_info)
        self.bits_info = QLabel("Bits per pixel: Not detected")
        info_layout.addWidget(self.bits_info)
        self.status_label = QLabel("Status: Select DICOM file")
        info_layout.addWidget(self.status_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Группа параметров шторки
        self.shutter_params_group = QGroupBox("Shutter Parameters")
        self.shutter_params_layout = QVBoxLayout()
        self.shutter_params_group.setLayout(self.shutter_params_layout)
        layout.addWidget(self.shutter_params_group)
        self.shutter_params_group.setVisible(False)

        # Группа шифрования
        self.encrypt_group = QGroupBox("Encryption Settings")
        encrypt_layout = QVBoxLayout()
        self.encrypt_check = QCheckBox("Enable AES-128 Encryption")
        self.encrypt_check.stateChanged.connect(self.main_window.toggle_encrypt_fields)
        encrypt_layout.addWidget(self.encrypt_check)
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Encryption Key:"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Enter 16-byte key in hex (32 characters)")
        self.key_edit.setVisible(False)
        key_layout.addWidget(self.key_edit)
        self.gen_key_btn = QPushButton("Generate Key")
        self.gen_key_btn.setVisible(False)
        self.gen_key_btn.clicked.connect(self.main_window.generate_key)
        key_layout.addWidget(self.gen_key_btn)
        encrypt_layout.addLayout(key_layout)
        self.encrypt_group.setLayout(encrypt_layout)
        layout.addWidget(self.encrypt_group)

        # Кнопки управления выбором тегов
        tag_control_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.main_window.select_all_tags)
        tag_control_layout.addWidget(select_all_btn)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.main_window.deselect_all_tags)
        tag_control_layout.addWidget(deselect_all_btn)
        layout.addLayout(tag_control_layout)

        # Таблица метаданных
        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(4)
        self.metadata_table.setHorizontalHeaderLabels(["Include", "Tag", "VR", "Value"])
        self.metadata_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.metadata_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.metadata_table.setEditTriggers(QAbstractItemView.DoubleClicked)
        layout.addWidget(QLabel("Metadata to Embed:"))
        layout.addWidget(self.metadata_table)

        # Кнопка встраивания
        btn_layout = QHBoxLayout()
        embed_btn = QPushButton("Embed Data and Save")
        embed_btn.clicked.connect(self.main_window.embed_and_save)
        btn_layout.addWidget(embed_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def setup_shutter_params_form(self, shutter_params):
        """Создает форму для ввода параметров шторки."""
        # Очищаем предыдущие виджеты
        while self.shutter_params_layout.count():
            child = self.shutter_params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.shutter_params_group.setVisible(True)

        # Выбор типа шторки
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Shutter Type:"))
        self.shutter_type_combo = QComboBox()
        self.shutter_type_combo.addItems(["RECTANGULAR", "CIRCULAR", "POLYGONAL"])
        self.shutter_type_combo.setCurrentText(shutter_params.get('type', 'RECTANGULAR'))
        self.shutter_type_combo.currentTextChanged.connect(self.update_shutter_form)
        type_layout.addWidget(self.shutter_type_combo)
        self.shutter_params_layout.addLayout(type_layout)

        self.update_shutter_form()

    def update_shutter_form(self):
        """Обновляет форму в зависимости от выбранного типа шторки."""
        # Удаляем старую форму
        while self.shutter_params_layout.count() > 1:
            child = self.shutter_params_layout.takeAt(1)
            if child.widget():
                child.widget().deleteLater()
        
        stype = self.shutter_type_combo.currentText()
        if stype == "RECTANGULAR":
            self.setup_rectangular_shutter_form()
        elif stype == "CIRCULAR":
            self.setup_circular_shutter_form()
        else:
            self.setup_polygonal_shutter_form()

    def setup_rectangular_shutter_form(self):
        """Создает форму ввода прямоугольной шторки."""
        form_layout = QFormLayout()
        self.left_edit = QSpinBox()
        self.left_edit.setRange(0, 10000)
        self.left_edit.setValue(0)
        form_layout.addRow("Left:", self.left_edit)
        
        self.right_edit = QSpinBox()
        self.right_edit.setRange(0, 10000)
        self.right_edit.setValue(512)
        form_layout.addRow("Right:", self.right_edit)
        
        self.top_edit = QSpinBox()
        self.top_edit.setRange(0, 10000)
        self.top_edit.setValue(0)
        form_layout.addRow("Top:", self.top_edit)
        
        self.bottom_edit = QSpinBox()
        self.bottom_edit.setRange(0, 10000)
        self.bottom_edit.setValue(512)
        form_layout.addRow("Bottom:", self.bottom_edit)
        
        self.shutter_params_layout.addLayout(form_layout)

    def setup_circular_shutter_form(self):
        """Создает форму ввода круговой шторки."""
        form_layout = QFormLayout()
        self.center_x_edit = QSpinBox()
        self.center_x_edit.setRange(0, 10000)
        self.center_x_edit.setValue(256)
        form_layout.addRow("Center X:", self.center_x_edit)
        
        self.center_y_edit = QSpinBox()
        self.center_y_edit.setRange(0, 10000)
        self.center_y_edit.setValue(256)
        form_layout.addRow("Center Y:", self.center_y_edit)
        
        self.radius_edit = QSpinBox()
        self.radius_edit.setRange(0, 10000)
        self.radius_edit.setValue(100)
        form_layout.addRow("Radius:", self.radius_edit)
        
        self.shutter_params_layout.addLayout(form_layout)

    def setup_polygonal_shutter_form(self):
        """Создает форму ввода полигональной шторки."""
        form_layout = QFormLayout()
        vertices_label = QLabel("Vertices (format: x1,y1;x2,y2;...):")
        self.vertices_edit = QTextEdit()
        self.vertices_edit.setText("0,0;100,0;100,100;0,100")
        form_layout.addRow(vertices_label, self.vertices_edit)
        self.shutter_params_layout.addLayout(form_layout)

    def populate_metadata_table(self, ds, forbidden_tags, supported_vr):
        """Заполняет таблицу метаданных."""
        tags = []
        for elem in ds:
            t = (elem.tag.group, elem.tag.element)
            if t in forbidden_tags:
                continue
            if elem.VR not in supported_vr:
                continue
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
                element = ds[tag]
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

    def select_all_tags(self):
        """Выбирает все теги в таблице."""
        for r in range(self.metadata_table.rowCount()):
            item = self.metadata_table.item(r, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def deselect_all_tags(self):
        """Снимает выбор со всех тегов в таблице."""
        for r in range(self.metadata_table.rowCount()):
            item = self.metadata_table.item(r, 0)
            if item:
                item.setCheckState(Qt.Unchecked)

    def toggle_encrypt_fields(self, state):
        """Показывает/скрывает поля шифрования."""
        vis = state == Qt.Checked
        self.key_edit.setVisible(vis)
        self.gen_key_btn.setVisible(vis)

    def generate_key(self):
        """Генерирует случайный ключ."""
        key = os.urandom(16)
        self.key_edit.setText(key.hex())

    def get_shutter_params_from_form(self):
        """Извлекает параметры шторки из формы."""
        stype = self.shutter_type_combo.currentText()
        params = {'type': stype}
        
        if stype == "RECTANGULAR":
            params.update({
                'left': self.left_edit.value(),
                'right': self.right_edit.value(),
                'top': self.top_edit.value(),
                'bottom': self.bottom_edit.value()
            })
        elif stype == "CIRCULAR":
            params.update({
                'center_x': self.center_x_edit.value(),
                'center_y': self.center_y_edit.value(),
                'radius': self.radius_edit.value()
            })
        else:  # POLYGONAL
            verts = []
            for pair in self.vertices_edit.toPlainText().split(';'):
                if pair.strip():
                    x, y = map(int, pair.split(','))
                    verts.append((x, y))
            params['vertices'] = verts
        
        return params

    def embed_and_save(self, ds, shutter_params, bits_per_pixel, forbidden_tags, embed_func, update_params_callback, display_callback):
        """Выполняет встраивание данных."""
        if not self.file_edit.text() or not ds:
            QMessageBox.warning(self, "Warning", "Please select a DICOM file first")
            return
        
        # Получаем новые параметры шторки
        new_params = self.get_shutter_params_from_form()
        
        # Обновляем теги шторки в DICOM
        tags = [(0x0018, 0x1600), (0x0018, 0x1602), (0x0018, 0x1604),
                (0x0018, 0x1606), (0x0018, 0x1608), (0x0018, 0x1610),
                (0x0018, 0x1611), (0x0018, 0x1612), (0x0018, 0x1620)]
        
        for tag in tags:
            if tag in ds:
                del ds[tag]
        
        ds.add_new((0x0018, 0x1600), 'CS', new_params['type'])
        
        if new_params['type'] == "RECTANGULAR":
            ds.add_new((0x0018, 0x1602), 'IS', str(new_params['left']))
            ds.add_new((0x0018, 0x1604), 'IS', str(new_params['right']))
            ds.add_new((0x0018, 0x1606), 'IS', str(new_params['top']))
            ds.add_new((0x0018, 0x1608), 'IS', str(new_params['bottom']))
        elif new_params['type'] == "CIRCULAR":
            ds.add_new((0x0018, 0x1610), 'IS', str(new_params['center_x']))
            ds.add_new((0x0018, 0x1611), 'IS', str(new_params['center_y']))
            ds.add_new((0x0018, 0x1612), 'IS', str(new_params['radius']))
        else:  # POLYGONAL
            flat = [coord for pt in new_params['vertices'] for coord in pt]
            ds.add_new((0x0018, 0x1620), 'IS', flat)

        # Собираем теги для встраивания
        tags_to_embed, vr_list, values = [], [], []
        for row in range(self.metadata_table.rowCount()):
            if self.metadata_table.item(row, 0).checkState() == Qt.Checked:
                tag_text = self.metadata_table.item(row, 1).text().strip("()")
                group, element = map(lambda x: int(x, 16), tag_text.split(','))
                if (group, element) in forbidden_tags:
                    continue
                tags_to_embed.append((group, element))
                vr_list.append(self.metadata_table.item(row, 2).text())
                values.append(self.metadata_table.item(row, 3).text())
        
        if not tags_to_embed:
            QMessageBox.warning(self, "Warning", "No valid tags selected for embedding")
            return

        # Удаляем скрываемые теги из DICOM
        for g, e in tags_to_embed:
            tag_obj = Tag(g, e)
            if tag_obj in ds:
                del ds[tag_obj]

        # Создаем временный файл
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.dcm')
        os.close(tmp_fd)
        try:
            ds.save_as(tmp_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save temporary DICOM file: {e}")
            return

        # Получаем ключ шифрования
        key = None
        if self.encrypt_check.isChecked():
            key_text = self.key_edit.text().strip()
            if not key_text:
                QMessageBox.warning(self, "Warning", "Please enter encryption key")
                os.remove(tmp_path)
                return
            try:
                key = bytes.fromhex(key_text)
                if len(key) != 16:
                    raise ValueError("Key must be 16 bytes")
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Invalid key: {e}")
                os.remove(tmp_path)
                return

        # Выбираем путь для сохранения
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Modified DICOM", "", "DICOM Files (*.dcm)")
        if not save_path:
            os.remove(tmp_path)
            return
        
        # Выполняем встраивание
        try:
            result = embed_func(
                dcm_path=tmp_path,
                key=key,
                tags_to_embed=tags_to_embed,
                vr_list=vr_list,
                values=values,
                output_path=save_path,
                bits_per_pixel=bits_per_pixel
            )
            
            if result:
                QMessageBox.critical(self, "Error", result)
            else:
                QMessageBox.information(self, "Success", "Data embedded successfully!")
                update_params_callback(new_params)
                display_callback(save_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Embedding failed: {e}")
        finally:
            try:
                os.remove(tmp_path)
            except:
                pass