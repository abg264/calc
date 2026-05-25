import html
import json
import re
import os
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None

from utils.helpers import ruta_recurso

class MathView(QFrame):
    """Small MathJax surface used for input previews, results and steps."""

    def __init__(self, min_height=70, allow_scroll=False, compact=False, dark_mode=True, transparent_bg=False, parent=None):
        super().__init__(parent)
        self.setObjectName("math_frame")
        self._body = ""
        self._dark = dark_mode
        self._page_ready = False
        self._allow_scroll = allow_scroll
        self._compact = compact
        self._transparent_bg = transparent_bg

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if QWebEngineView is None:
            self.web = QLabel()
            self.web.setWordWrap(True)
            self.web.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        else:
            self.web = QWebEngineView()
            self.web.setContextMenuPolicy(Qt.NoContextMenu)
            self.web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.web.page().loadFinished.connect(self._on_page_loaded)

        self.web.setMinimumHeight(min_height)
        layout.addWidget(self.web)

        if QWebEngineView is not None:
            # Aquí vinculamos MathJax apuntando a la carpeta assets
            base_path = ruta_recurso("assets") 
            base_url = QUrl.fromLocalFile(base_path + "/")
            
            if self._transparent_bg:
                self.web.page().setBackgroundColor(Qt.transparent)
            else:
                self.web.page().setBackgroundColor(QColor(self._theme_values()["bg"]))

            self.web.setHtml(self._base_document(), baseUrl=base_url)
        else:
            self.set_math_text("")

    def set_theme(self, dark):
        self._dark = dark
        if QWebEngineView is None:
            self._render_fallback()
            return
        theme = self._theme_values()
        if not self._transparent_bg:
            if self.web.page():
                self.web.page().setBackgroundColor(QColor(theme["bg"]))
        self._apply_theme_js()

    def set_math_text(self, body):
        self._body = body
        if QWebEngineView is None:
            self._render_fallback()
            return
        self._update_body_js()

    def _theme_values(self):
        fg = "#f4f7fb" if self._dark else "#172033"
        muted = "#a8b3c7" if self._dark else "#5a667a"
        bg = "#151922" if self._dark else "#ffffff"
        accent = "#ef476f" if self._dark else "#c2185b"
        return {"fg": fg, "muted": muted, "bg": bg, "accent": accent}

    def _base_document(self):
        theme = self._theme_values()
        body_overflow = "overflow: auto;" if self._allow_scroll else "overflow: hidden;"
        padding_css = "padding: 0px 4px;" if self._compact else "padding: 14px 16px;"
        font_size = "13px" if self._compact else "15px"
        math_font_size = "14px" if self._compact else "20px"
        display_margin = "0" if self._compact else ".35em 0"
        wrap_flex = "display: flex; align-items: center; height: 100vh;" if self._compact else ""
        bg_css = "transparent" if self._transparent_bg else theme["bg"]
        
        return f"""
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8">
            <script>
                window.MathJax = {{
                    tex: {{ inlineMath: [['\\\\(', '\\\\)']], displayMath: [['\\\\[', '\\\\]']] }},
                    svg: {{ fontCache: 'global' }}
                }};
            </script>
            <script defer src="mathjax/tex-svg.js"></script>
            <style>
                html, body {{
                    margin: 0; padding: 0; width: 100%; height: 100%;
                    {body_overflow} background: {bg_css}; color: {theme["fg"]};
                    font-family: "Segoe UI", Arial, sans-serif; font-size: {font_size};
                }}
                * {{ box-sizing: border-box; }}
                body {{ overflow-wrap: anywhere; }}
                .wrap {{ {padding_css} {wrap_flex} }}
                .placeholder {{ color: {theme["muted"]}; }}
                .math-block {{ font-size: {math_font_size}; line-height: 1.2; margin: 0; color: {theme["fg"]}; }}
                .steps {{ font-size: 14px; line-height: 1.55; }}
                .step {{ border-left: 3px solid {theme["accent"]}; padding: 10px 0 10px 12px; margin: 0 0 12px; }}
                .step-title {{ color: {theme["muted"]}; font-weight: 700; margin-bottom: 6px; letter-spacing: .01em; }}
                .error {{ border-left-color: #ffb703; }}
                mjx-container[jax="SVG"][display="true"] {{ margin: {display_margin}; }}
            </style>
        </head>
        <body>
            <div id="content" class="wrap"></div>
            <script>
                window.updateMathContent = function (html) {{
                    const content = document.getElementById("content");
                    content.innerHTML = html;
                    if (window.MathJax && window.MathJax.typesetPromise) {{
                        MathJax.typesetClear([content]);
                        MathJax.typesetPromise([content]).catch(function () {{}});
                    }}
                }};
                window.setCalculatorTheme = function (theme, is_transparent) {{
                    var bg_color = is_transparent ? "transparent" : theme.bg;
                    document.documentElement.style.background = bg_color;
                    document.body.style.background = bg_color;
                    document.body.style.color = theme.fg;
                    document.querySelectorAll(".placeholder, .step-title").forEach(function (el) {{
                        el.style.color = theme.muted;
                    }});
                    document.querySelectorAll(".math-block").forEach(function (el) {{
                        el.style.color = theme.fg;
                    }});
                    document.querySelectorAll(".step").forEach(function (el) {{
                        if (!el.classList.contains("error")) el.style.borderLeftColor = theme.accent;
                    }});
                }};
            </script>
        </body>
        </html>
        """

    def _on_page_loaded(self, ok):
        self._page_ready = bool(ok)
        if self._page_ready:
            self._apply_theme_js()
            self._update_body_js()

    def _apply_theme_js(self):
        if not self._page_ready: return
        is_transp = "true" if self._transparent_bg else "false"
        self.web.page().runJavaScript(f"window.setCalculatorTheme({json.dumps(self._theme_values())}, {is_transp});")

    def _update_body_js(self):
        if not self._page_ready: return
        self.web.page().runJavaScript(f"window.updateMathContent({json.dumps(self._body)});")

    def _render_fallback(self):
        self.web.setText(self._plain_fallback())

    def _plain_fallback(self):
        text = re.sub(r"<[^>]+>", " ", self._body)
        return re.sub(r"\s+", " ", html.unescape(text)).strip()