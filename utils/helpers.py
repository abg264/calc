import os
import sys

def ruta_recurso(ruta_relativa):
    """Obtiene la ruta absoluta al recurso, funciona para desarrollo y para el .exe compilado."""
    try:
        # PyInstaller crea una carpeta temporal _MEIPASS
        ruta_base = sys._MEIPASS
    except Exception:
        ruta_base = os.path.abspath(".")
    
    return os.path.join(ruta_base, ruta_relativa)