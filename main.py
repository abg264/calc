import sys
import ctypes

from PySide6.QtWidgets import QApplication
from ui.calculator import ModernCalculator

def main():
    app = QApplication(sys.argv)
    
    # ID para Windows (Evita que el icono de la barra de tareas sea el de Python)
    try:
        id_app = 'proyecto_escolar.calculadora.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(id_app)
    except Exception:
        pass

    window = ModernCalculator()
    window.show()

    # Si usas Splash Screen al compilar con PyInstaller
    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass

    sys.exit(app.exec())

if __name__ == "__main__":
    main()