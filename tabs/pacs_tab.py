from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QMessageBox,
    QFileDialog, QWidget, QFormLayout, QCheckBox, QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import json
import os
from pynetdicom import AE, evt, StoragePresentationContexts
from pynetdicom.sop_class import (
    CTImageStorage, MRImageStorage, UltrasoundImageStorage,
    SecondaryCaptureImageStorage, ComputedRadiographyImageStorage
)
from pydicom import dcmread

class SendThread(QThread):
    """Поток для отправки DICOM файлов"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, server, file_path, client_aet):
        super().__init__()
        self.server = server
        self.file_path = file_path
        self.client_aet = client_aet
    
    def run(self):
        try:
            self.progress.emit(f"Чтение DICOM файла: {self.file_path}")
            ds = dcmread(self.file_path)
            
            self.progress.emit(f"Подключение к серверу {self.server['aetitle']}...")
            ae = AE(ae_title=self.client_aet)
            
            # Добавляем контексты представления для хранения
            ae.requested_contexts = StoragePresentationContexts
            
            # Устанавливаем соединение
            assoc = ae.associate(
                self.server['ip'],
                self.server['port'],
                ae_title=self.server['aetitle']
            )
            
            if assoc.is_established:
                self.progress.emit(f"Отправка исследования {ds.StudyDescription if hasattr(ds, 'StudyDescription') else 'Unknown'}...")
                status = assoc.send_c_store(ds)
                
                if status:
                    self.progress.emit("Отправка успешно завершена")
                    self.finished.emit(True, "Успешно отправлено")
                else:
                    self.progress.emit("Ошибка при отправке")
                    self.finished.emit(False, "Ошибка при отправке")
                
                assoc.release()
            else:
                self.progress.emit("Не удалось установить соединение")
                self.finished.emit(False, "Не удалось установить соединение")
                
        except Exception as e:
            self.progress.emit(f"Ошибка: {str(e)}")
            self.finished.emit(False, f"Ошибка: {str(e)}")

class ReceiveThread(QThread):
    """Поток для приема DICOM файлов"""
    progress = pyqtSignal(str)
    file_received = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, port, aetitle, save_dir):
        super().__init__()
        self.port = port
        self.aetitle = aetitle
        self.save_dir = save_dir
        self.running = True
    
    def run(self):
        try:
            self.progress.emit(f"Запуск C-STORE SCP на порту {self.port}...")
            
            def handle_store(event):
                """Обработчик события хранения"""
                ds = event.dataset
                ds.file_meta = event.file_meta
                
                # Генерируем имя файла
                if hasattr(ds, 'PatientID') and hasattr(ds, 'StudyInstanceUID'):
                    filename = f"{ds.PatientID}_{ds.StudyInstanceUID[:8]}.dcm"
                else:
                    filename = f"received_{os.urandom(4).hex()}.dcm"
                
                filepath = os.path.join(self.save_dir, filename)
                
                # Сохраняем файл
                ds.save_as(filepath, write_like_original=False)
                self.progress.emit(f"Получен файл: {filename}")
                self.file_received.emit(filepath)
                
                return 0x0000  # Success
                
            handlers = [(evt.EVT_C_STORE, handle_store)]
            
            ae = AE(ae_title=self.aetitle)
            ae.supported_contexts = StoragePresentationContexts
            
            self.progress.emit("SCP сервер запущен и ожидает подключений...")
            ae.start_server(('', self.port), block=True, evt_handlers=handlers)
            
        except Exception as e:
            self.progress.emit(f"Ошибка сервера: {str(e)}")
        finally:
            self.finished.emit()
    
    def stop(self):
        self.running = False

class PACSTab(QWidget):
    """Вкладка для отправки и приема DICOM исследований через PACS"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.config_file = "config.json"
        self.servers = []
        self.receive_thread = None
        self.send_thread = None
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        """Инициализирует интерфейс вкладки"""
        main_layout = QHBoxLayout()
        
        # Левая панель: Отправка
        send_group = QGroupBox("Отправка исследования (C-STORE SCU)")
        send_layout = QVBoxLayout()
        
        # Выбор сервера
        server_group = QGroupBox("Сервер PACS")
        server_layout = QFormLayout()
        
        self.server_combo = QComboBox()
        self.server_combo.currentIndexChanged.connect(self.on_server_selected)
        server_layout.addRow("Выберите сервер:", self.server_combo)
        
        self.refresh_btn = QPushButton("Обновить список")
        self.refresh_btn.clicked.connect(self.load_config)
        server_layout.addRow("", self.refresh_btn)
        
        self.add_server_btn = QPushButton("Добавить новый сервер")
        self.add_server_btn.clicked.connect(self.show_add_server_dialog)
        server_layout.addRow("", self.add_server_btn)
        
        server_group.setLayout(server_layout)
        send_layout.addWidget(server_group)
        
        # Параметры сервера (только для чтения)
        params_group = QGroupBox("Параметры сервера")
        params_layout = QFormLayout()
        
        self.aet_display = QLineEdit()
        self.aet_display.setReadOnly(True)
        params_layout.addRow("AE Title:", self.aet_display)
        
        self.ip_display = QLineEdit()
        self.ip_display.setReadOnly(True)
        params_layout.addRow("IP адрес:", self.ip_display)
        
        self.port_display = QLineEdit()
        self.port_display.setReadOnly(True)
        params_layout.addRow("Порт:", self.port_display)
        
        params_group.setLayout(params_layout)
        send_layout.addWidget(params_group)
        
        # Параметры клиента
        client_group = QGroupBox("Параметры клиента")
        client_layout = QFormLayout()
        
        self.client_aet = QLineEdit("DICOM_STEG_APP")
        client_layout.addRow("Client AE Title:", self.client_aet)
        
        client_group.setLayout(client_layout)
        send_layout.addWidget(client_group)
        
        # Файл для отправки
        file_group = QGroupBox("Файл для отправки")
        file_layout = QHBoxLayout()
        
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        file_layout.addWidget(self.file_edit)
        
        self.browse_btn = QPushButton("Обзор...")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        
        self.use_current_btn = QPushButton("Исп. текущий")
        self.use_current_btn.clicked.connect(self.use_current_file)
        file_layout.addWidget(self.use_current_btn)
        
        file_group.setLayout(file_layout)
        send_layout.addWidget(file_group)
        
        # Кнопка отправки
        self.send_btn = QPushButton("Отправить исследование")
        self.send_btn.clicked.connect(self.send_dicom)
        self.send_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        send_layout.addWidget(self.send_btn)
        
        # Лог отправки
        self.send_log = QTextEdit()
        self.send_log.setReadOnly(True)
        self.send_log.setMaximumHeight(100)
        send_layout.addWidget(QLabel("Лог отправки:"))
        send_layout.addWidget(self.send_log)
        
        send_group.setLayout(send_layout)
        main_layout.addWidget(send_group, 1)
        
        # Правая панель: Прием
        receive_group = QGroupBox("Прием исследований (C-STORE SCP)")
        receive_layout = QVBoxLayout()
        
        # Параметры приемника
        scp_group = QGroupBox("Параметры приемника")
        scp_layout = QFormLayout()
        
        self.scp_aet = QLineEdit("DICOM_STEG_SCP")
        scp_layout.addRow("SCP AE Title:", self.scp_aet)
        
        self.scp_port = QLineEdit("11112")
        scp_layout.addRow("Порт:", self.scp_port)
        
        self.save_dir_edit = QLineEdit()
        self.save_dir_edit.setText("received_dicoms")
        scp_layout.addRow("Папка сохранения:", self.save_dir_edit)
        
        self.browse_dir_btn = QPushButton("Обзор...")
        self.browse_dir_btn.clicked.connect(self.browse_save_dir)
        scp_layout.addRow("", self.browse_dir_btn)
        
        scp_group.setLayout(scp_layout)
        receive_layout.addWidget(scp_group)
        
        # Управление приемником
        control_group = QGroupBox("Управление")
        control_layout = QHBoxLayout()
        
        self.start_receive_btn = QPushButton("Запустить сервер")
        self.start_receive_btn.clicked.connect(self.toggle_receive_server)
        self.start_receive_btn.setStyleSheet("background-color: #2196F3; color: white;")
        control_layout.addWidget(self.start_receive_btn)
        
        self.stop_receive_btn = QPushButton("Остановить сервер")
        self.stop_receive_btn.clicked.connect(self.stop_receive_server)
        self.stop_receive_btn.setEnabled(False)
        self.stop_receive_btn.setStyleSheet("background-color: #f44336; color: white;")
        control_layout.addWidget(self.stop_receive_btn)
        
        control_group.setLayout(control_layout)
        receive_layout.addWidget(control_group)
        
        # Лог приема
        self.receive_log = QTextEdit()
        self.receive_log.setReadOnly(True)
        self.receive_log.setMaximumHeight(150)
        receive_layout.addWidget(QLabel("Лог приема:"))
        receive_layout.addWidget(self.receive_log)
        
        # Полученные файлы
        self.received_files = QTableWidget()
        self.received_files.setColumnCount(3)
        self.received_files.setHorizontalHeaderLabels(["Файл", "Размер", "Дата"])
        self.received_files.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        receive_layout.addWidget(QLabel("Полученные файлы:"))
        receive_layout.addWidget(self.received_files)
        
        receive_group.setLayout(receive_layout)
        main_layout.addWidget(receive_group, 1)
        
        self.setLayout(main_layout)
    
    def load_config(self):
        """Загружает конфигурацию серверов из файла"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.servers = config.get('servers', [])
            else:
                # Создаем пример конфигурации
                self.servers = [
                    {
                        "name": "Пример сервера",
                        "aetitle": "PACS_SERVER",
                        "ip": "127.0.0.1",
                        "port": 11112
                    }
                ]
                self.save_config()
            
            self.update_server_list()
            if self.servers:
                self.server_combo.setCurrentIndex(0)
                self.on_server_selected(0)
                
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить конфигурацию: {str(e)}")
    
    def save_config(self):
        """Сохраняет конфигурацию серверов в файл"""
        try:
            config = {"servers": self.servers}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить конфигурацию: {str(e)}")
    
    def update_server_list(self):
        """Обновляет список серверов в комбобоксе"""
        self.server_combo.clear()
        for server in self.servers:
            display_name = f"{server.get('name', 'Без имени')} ({server['aetitle']}@{server['ip']}:{server['port']})"
            self.server_combo.addItem(display_name, server)
    
    def on_server_selected(self, index):
        """Обработчик выбора сервера"""
        if index >= 0 and index < len(self.servers):
            server = self.servers[index]
            self.aet_display.setText(server['aetitle'])
            self.ip_display.setText(server['ip'])
            self.port_display.setText(str(server['port']))
    
    def show_add_server_dialog(self):
        """Показывает диалог добавления нового сервера"""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить сервер PACS")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Название сервера")
        form_layout.addRow("Название:", name_edit)
        
        aet_edit = QLineEdit()
        aet_edit.setPlaceholderText("AE Title сервера")
        form_layout.addRow("AE Title:", aet_edit)
        
        ip_edit = QLineEdit()
        ip_edit.setPlaceholderText("IP адрес")
        form_layout.addRow("IP адрес:", ip_edit)
        
        port_edit = QLineEdit()
        port_edit.setPlaceholderText("Порт")
        form_layout.addRow("Порт:", port_edit)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            new_server = {
                "name": name_edit.text() or "Новый сервер",
                "aetitle": aet_edit.text(),
                "ip": ip_edit.text(),
                "port": int(port_edit.text()) if port_edit.text().isdigit() else 11112
            }
            
            # Проверка обязательных полей
            if not new_server['aetitle'] or not new_server['ip']:
                QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля: AE Title и IP адрес")
                return
            
            self.servers.append(new_server)
            self.save_config()
            self.update_server_list()
            self.server_combo.setCurrentIndex(len(self.servers) - 1)
            QMessageBox.information(self, "Успех", "Сервер успешно добавлен")
    
    def browse_file(self):
        """Выбор файла для отправки"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите DICOM файл", "", "DICOM Files (*.dcm *.dicom)"
        )
        if file_path:
            self.file_edit.setText(file_path)
    
    def use_current_file(self):
        """Использовать текущий файл из других вкладок"""
        # Проверяем, какой файл сейчас открыт
        if hasattr(self.main_window, 'embed_file_edit') and self.main_window.embed_file_edit.text():
            self.file_edit.setText(self.main_window.embed_file_edit.text())
        elif hasattr(self.main_window, 'extract_file_edit') and self.main_window.extract_file_edit.text():
            self.file_edit.setText(self.main_window.extract_file_edit.text())
        else:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого DICOM файла")
    
    def send_dicom(self):
        """Отправка DICOM файла на выбранный сервер"""
        # Проверка файла
        file_path = self.file_edit.text()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Ошибка", "Выберите существующий DICOM файл")
            return
        
        # Проверка сервера
        if self.server_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите сервер для отправки")
            return
        
        server = self.servers[self.server_combo.currentIndex()]
        client_aet = self.client_aet.text().strip() or "DICOM_STEG_APP"
        
        # Запуск потока отправки
        self.send_thread = SendThread(server, file_path, client_aet)
        self.send_thread.progress.connect(self.update_send_log)
        self.send_thread.finished.connect(self.on_send_finished)
        self.send_thread.start()
        
        self.send_btn.setEnabled(False)
        self.send_log.append(">>> Начало отправки...")
    
    def update_send_log(self, message):
        """Обновление лога отправки"""
        self.send_log.append(message)
    
    def on_send_finished(self, success, message):
        """Обработчик завершения отправки"""
        self.send_btn.setEnabled(True)
        if success:
            self.send_log.append(">>> Отправка успешно завершена")
            QMessageBox.information(self, "Успех", "Файл успешно отправлен")
        else:
            self.send_log.append(f">>> Ошибка: {message}")
            QMessageBox.warning(self, "Ошибка", message)
    
    def browse_save_dir(self):
        """Выбор папки для сохранения полученных файлов"""
        dir_path = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if dir_path:
            self.save_dir_edit.setText(dir_path)
    
    def toggle_receive_server(self):
        """Запуск/остановка сервера приема"""
        if self.receive_thread and self.receive_thread.isRunning():
            self.stop_receive_server()
        else:
            self.start_receive_server()
    
    def start_receive_server(self):
        """Запуск сервера приема"""
        try:
            # Проверка папки сохранения
            save_dir = self.save_dir_edit.text()
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # Получение параметров
            aetitle = self.scp_aet.text().strip() or "DICOM_STEG_SCP"
            port = int(self.scp_port.text()) if self.scp_port.text().isdigit() else 11112
            
            # Запуск потока
            self.receive_thread = ReceiveThread(port, aetitle, save_dir)
            self.receive_thread.progress.connect(self.update_receive_log)
            self.receive_thread.file_received.connect(self.on_file_received)
            self.receive_thread.finished.connect(self.on_receive_stopped)
            self.receive_thread.start()
            
            self.start_receive_btn.setEnabled(False)
            self.stop_receive_btn.setEnabled(True)
            self.receive_log.append(f">>> Сервер запущен на порту {port}")
            
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось запустить сервер: {str(e)}")
    
    def stop_receive_server(self):
        """Остановка сервера приема"""
        if self.receive_thread:
            self.receive_thread.stop()
            self.receive_log.append(">>> Остановка сервера...")
    
    def on_receive_stopped(self):
        """Обработчик остановки сервера"""
        self.start_receive_btn.setEnabled(True)
        self.stop_receive_btn.setEnabled(False)
        self.receive_log.append(">>> Сервер остановлен")
    
    def update_receive_log(self, message):
        """Обновление лога приема"""
        self.receive_log.append(message)
    
    def on_file_received(self, file_path):
        """Обработчик получения файла"""
        # Добавляем файл в таблицу
        row = self.received_files.rowCount()
        self.received_files.insertRow(row)
        
        filename = os.path.basename(file_path)
        size = os.path.getsize(file_path)
        from datetime import datetime
        date = datetime.now().strftime("%H:%M:%S")
        
        self.received_files.setItem(row, 0, QTableWidgetItem(filename))
        self.received_files.setItem(row, 1, QTableWidgetItem(f"{size:,} байт"))
        self.received_files.setItem(row, 2, QTableWidgetItem(date))
        
        # Прокручиваем к последней строке
        self.received_files.scrollToBottom()