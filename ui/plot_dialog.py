from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout

try:
    import numpy as np
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure
except ImportError:
    np = None
    FigureCanvas = None
    Figure = None
    NavigationToolbar = None

class PlotDialog(QDialog):
    """Ventana nativa no bloqueante para mostrar gráficos de Matplotlib."""
    def __init__(self, parent=None, dark_mode=True):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("Visualización de Región" if parent and parent.lang == "es" else "Region Visualization")
        self.resize(750, 550)
        layout = QVBoxLayout(self)
        
        self.fig = Figure()
        if dark_mode:
            self.fig.patch.set_facecolor('#151922')
            self.text_color = 'white'
        else:
            self.fig.patch.set_facecolor('#ffffff')
            self.text_color = 'black'
            
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        if dark_mode:
            self.toolbar.setStyleSheet("background-color: white;")
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)