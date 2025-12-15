from PyQt5.QtWidgets import QWidget


class BaseTab(QWidget):
    """Базовый класс для всех вкладок приложения."""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса вкладки (должен быть переопределен)."""
        raise NotImplementedError("Subclasses must implement init_ui method")