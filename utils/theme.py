# utils/theme.py
import os
from utils.helpers import ruta_recurso

def get_palette(dark_mode):
    """Devuelve el diccionario de colores según el tema."""
    return {
        "bg": "#10131a" if dark_mode else "#f4f6fb",
        "panel": "#151922" if dark_mode else "#ffffff",
        "card": "#181d28" if dark_mode else "#ffffff",
        "screen": "#111722" if dark_mode else "#f8fafc",
        "text": "#f4f7fb" if dark_mode else "#172033",
        "muted": "#a8b3c7" if dark_mode else "#5a667a",
        "border": "#2b3445" if dark_mode else "#d7dce7",
        "input": "#0f141d" if dark_mode else "#ffffff",
        "button": "#242b38" if dark_mode else "#edf1f7",
        "number": "#202734" if dark_mode else "#f2f5fa",
        "func": "#432033" if dark_mode else "#fde7ef",
        "func_text": "#ffffff" if dark_mode else "#8a123e",
        "operator": "#263041" if dark_mode else "#e4e9f2",
        "action": "#334155" if dark_mode else "#d5dce8",
        "accent": "#ef476f" if dark_mode else "#c2185b",
        "accent_hover": "#ff5c86" if dark_mode else "#ad1457",
        "green": "#77dd8a" if dark_mode else "#247a3c",
    }

def load_stylesheet(dark_mode):
    """Lee el archivo .qss y aplica las variables de la paleta."""
    palette = get_palette(dark_mode)
    qss_path = ruta_recurso("assets/style.qss")
    
    try:
        with open(qss_path, "r", encoding="utf-8") as file:
            qss_template = file.read()
            
            # SOLUCIÓN: Reemplazamos las variables manualmente para no
            # interferir con las llaves {} nativas de CSS.
            for key, color in palette.items():
                qss_template = qss_template.replace(f"{{{key}}}", color)
                
            return qss_template
            
    except Exception as e:
        print(f"Error cargando los estilos QSS: {e}")
        return ""