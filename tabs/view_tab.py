from PyQt5.QtWidgets import QVBoxLayout, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pydicom
from PyQt5.QtWidgets import QMessageBox, QWidget


class ViewTab(QWidget):
    """Вкладка для просмотра изображений."""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.original_figure = None
        self.original_canvas = None
        self.processed_figure = None
        self.processed_canvas = None
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализирует интерфейс вкладки."""
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
        
        self.setLayout(layout)

    def display_image(self, file_path, processed=False):
        """Отображает DICOM изображение."""
        try:
            ds = pydicom.dcmread(file_path, force=True)
            img = ds.pixel_array
            
            if processed:
                figure = self.processed_figure
                canvas = self.processed_canvas
            else:
                figure = self.original_figure
                canvas = self.original_canvas
            
            figure.clear()
            ax = figure.add_subplot(111)
            ax.imshow(img, cmap='gray')
            ax.axis('off')
            canvas.draw()
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to display image: {e}")