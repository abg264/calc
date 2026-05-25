import html
import os
import json
import sympy as sp
from PySide6.QtCore import Qt, QUrl, QRegularExpression, QThread, Signal, QTimer
from PySide6.QtGui import QIcon, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSplitter, QVBoxLayout, QWidget
)

try:
    import numpy as np
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    np = None
    FigureCanvas = None

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None

# IMPORTACIONES DESDE NUESTRA ESTRUCTURA
from ui.math_view import MathView
from ui.plot_dialog import PlotDialog
from utils.helpers import ruta_recurso
from utils.translations import TEXTS
from utils.math_engine import MathEngine
from utils.theme import load_stylesheet


# --- CLASE TRABAJADORA PARA HILOS ---
class MathWorker(QThread):
    finished_ok = Signal(dict)

    def __init__(self, engine, expr_str, idx_type, is_indefinite, limit_strings, lang, is_basic):
        super().__init__()
        self.engine = engine
        self.expr_str = expr_str
        self.idx_type = idx_type
        self.is_indefinite = is_indefinite
        self.limit_strings = limit_strings
        self.lang = lang
        self.is_basic = is_basic

    def run(self):
        try:
            if self.is_basic:
                res = self.engine.evaluate_basic(self.expr_str)
            else:
                res = self.engine.process_integral(
                    self.expr_str, self.idx_type, self.is_indefinite, self.limit_strings, self.lang
                )
            self.finished_ok.emit(res)
        except Exception as e:
            self.finished_ok.emit({"success": False, "error_details": str(e)})


class ModernCalculator(QWidget):
    def __init__(self):
        super().__init__()
        self.lang = "es"
        self.texts = TEXTS

        self.engine = MathEngine()

        self.dark_mode = True
        self.limit_widgets = []
        self.last_text_input = None
        self.last_plot_context = None
        
        # IMPORTANTE: Guardar el historial de forma invisible y segura
        if os.name == 'nt':
            base_dir = os.getenv('APPDATA')
        else:
            base_dir = os.path.expanduser('~/.config')
            
        app_dir = os.path.join(base_dir, "Calculadora_Integrales_Pro")
        os.makedirs(app_dir, exist_ok=True)
        
        self.history_path = os.path.join(app_dir, "historial.json")
        self.history_items = []
        self.loading_history = False
        QApplication.instance().focusChanged.connect(self.remember_text_focus)

        self.setWindowTitle(self.texts[self.lang]["window_title"])
        self.setWindowIcon(QIcon(ruta_recurso("assets/icono1.ico")))

        self.resize(1280, 760)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        header = QFrame()
        header.setObjectName("header")
        header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        self.title = QLabel(self.texts[self.lang]["title"])
        self.title.setObjectName("title")
        self.subtitle = QLabel(self.texts[self.lang]["subtitle"])
        self.subtitle.setObjectName("subtitle")
        title_layout.addWidget(self.title)
        title_layout.addWidget(self.subtitle)

        controls_layout = QHBoxLayout()
        self.lang_label = QLabel(self.texts[self.lang]["lang_label"])
        self.lang_btn = QPushButton(self.texts[self.lang]["lang_btn"])
        self.lang_btn.setFixedWidth(104)
        self.lang_btn.clicked.connect(self.toggle_language)

        self.pdf_btn = QPushButton(self.texts[self.lang]["pdf_btn"])
        self.pdf_btn.setFixedWidth(132)
        self.pdf_btn.clicked.connect(self.export_steps_to_pdf)

        self.plot_btn = QPushButton(self.texts[self.lang]["plot_btn"])
        self.plot_btn.setFixedWidth(132)
        self.plot_btn.setEnabled(False)
        self.plot_btn.clicked.connect(self.generate_plot)

        self.theme_btn = QPushButton("🌙")
        self.theme_btn.setFixedWidth(70)
        self.theme_btn.clicked.connect(self.toggle_theme)

        controls_layout.addWidget(self.lang_label)
        controls_layout.addWidget(self.lang_btn)
        controls_layout.addWidget(self.pdf_btn)
        controls_layout.addWidget(self.plot_btn)
        controls_layout.addSpacing(12)
        controls_layout.addWidget(self.theme_btn)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addLayout(controls_layout)
        main_layout.addWidget(header, 0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(8)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.left_panel = self.create_left_panel()

        center_scroll = QScrollArea()
        center_scroll.setObjectName("center_scroll")
        center_scroll.setWidgetResizable(True)
        center_scroll.setFrameShape(QFrame.NoFrame)
        center_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        center_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        center_panel = QFrame()
        center_panel.setObjectName("panel")
        center_panel.setMinimumWidth(420)
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(14, 14, 14, 14)
        center_layout.setSpacing(10)

        options_layout = QHBoxLayout()
        options_layout.setSpacing(10)
        self.lbl_type = QLabel(self.texts[self.lang]["type_label"])
        self.combo_type = QComboBox()
        self.combo_type.addItems(self.texts[self.lang]["integral_types"])
        self.combo_type.currentIndexChanged.connect(self.on_integral_type_changed)
        self.lbl_def = QLabel(self.texts[self.lang]["def_label"])
        self.combo_def = QComboBox()
        self.combo_def.addItems(self.texts[self.lang]["def_indef_types"])
        self.combo_def.currentIndexChanged.connect(self.update_ui_state)

        options_layout.addWidget(self.lbl_type)
        options_layout.addWidget(self.combo_type, 1)
        options_layout.addSpacing(12)
        options_layout.addWidget(self.lbl_def)
        options_layout.addWidget(self.combo_def, 1)

        self.screen_frame = QFrame()
        self.screen_frame.setObjectName("screen_frame")
        screen_layout = QVBoxLayout(self.screen_frame)
        screen_layout.setContentsMargins(16, 14, 16, 16)
        screen_layout.setSpacing(10)

        math_regex = QRegularExpression("^[-a-zA-Z0-9+*/^.()|! θπ√−×÷]*$")
        math_validator = QRegularExpressionValidator(math_regex, self)

        self.limits_title_label = QLabel(self.texts[self.lang]["limits_title"])
        self.limits_title_label.setObjectName("section_label")

        self.limits_group = QFrame()
        limits_layout = QHBoxLayout(self.limits_group)
        limits_layout.setContentsMargins(0, 0, 0, 0)
        limits_layout.setSpacing(8)

        for i in range(3):
            single_limit_layout = QVBoxLayout()
            single_limit_layout.setSpacing(4)

            upper = QLineEdit()
            upper.setObjectName("limit_input")
            upper.setPlaceholderText("Sup")
            upper.setAlignment(Qt.AlignCenter)
            upper.setMinimumWidth(58)
            upper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            upper.textChanged.connect(self.update_input_preview)
            upper.setValidator(math_validator) 
            upper.returnPressed.connect(self.calculate_integral) 

            integral_label = QLabel("∫")
            integral_label.setAlignment(Qt.AlignCenter)
            integral_label.setObjectName("integral_symbol")

            lower = QLineEdit()
            lower.setObjectName("limit_input")
            lower.setPlaceholderText("Inf")
            lower.setAlignment(Qt.AlignCenter)
            lower.setMinimumWidth(58)
            lower.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            lower.textChanged.connect(self.update_input_preview)
            lower.setValidator(math_validator)
            lower.returnPressed.connect(self.calculate_integral) 

            single_limit_layout.addWidget(upper)
            single_limit_layout.addWidget(integral_label)
            single_limit_layout.addWidget(lower)
            limits_layout.addLayout(single_limit_layout)
            self.limit_widgets.append((upper, integral_label, lower))

        self.input = QLineEdit()
        self.input.setPlaceholderText(self.texts[self.lang]["input_placeholder"])
        self.input.setObjectName("main_input")
        self.input.setMinimumHeight(44)
        self.input.textChanged.connect(self.update_input_preview)
        self.input.setValidator(math_validator)
        self.input.returnPressed.connect(self.calculate_integral)
        self.last_text_input = self.input

        self.input_preview = MathView(min_height=92)
        self.result_title = QLabel(self.texts[self.lang]["result_label"])
        self.result_title.setObjectName("result_label")

        self.result_view = MathView(min_height=125, allow_scroll=True)

        screen_layout.addWidget(self.limits_title_label)
        screen_layout.addWidget(self.limits_group)
        screen_layout.addWidget(self.input)
        screen_layout.addWidget(self.input_preview)
        screen_layout.addWidget(self.result_title)
        screen_layout.addWidget(self.result_view)

        center_layout.addLayout(options_layout)
        center_layout.addWidget(self.screen_frame)
        center_layout.addWidget(self.create_keyboard())
        center_layout.addStretch(1)
        center_scroll.setWidget(center_panel)

        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        self.steps_title_label = QLabel(self.texts[self.lang]["steps_title"])
        self.steps_title_label.setObjectName("title")
        self.steps_panel = MathView(min_height=420, allow_scroll=True)
        self.steps_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        right_layout.addWidget(self.steps_title_label)
        right_layout.addWidget(self.steps_panel, 1)

        splitter.addWidget(self.left_panel)
        splitter.addWidget(center_scroll)
        splitter.addWidget(right_panel)
        splitter.setSizes([240, 720, 320])
        main_layout.addWidget(splitter, 1)

        self.load_history_ui()
        self.update_ui_state()
        self.apply_theme()
        self.show_placeholder_result()
        self.show_placeholder_steps()

    def on_integral_type_changed(self):
        self.input.blockSignals(True)
        self.input.clear()
        self.input.blockSignals(False)

        for upper, _label, lower in self.limit_widgets:
            upper.blockSignals(True)
            lower.blockSignals(True)
            upper.clear()
            lower.clear()
            upper.blockSignals(False)
            lower.blockSignals(False)
            
        self.last_plot_context = None
        self.plot_btn.setEnabled(False)
        self.plot_btn.setText(self.texts[self.lang]["plot_btn"])

        self.show_placeholder_result()
        self.show_placeholder_steps()
        self.update_ui_state()

    def update_ui_state(self):
        idx_type = self.combo_type.currentIndex()
        is_basic = self.is_basic_calculator_mode()
        is_simple = idx_type in (0, 3)

        self.lbl_def.setVisible(is_simple and not is_basic)
        self.combo_def.setVisible(is_simple and not is_basic)
        self.steps_title_label.setVisible(not is_basic)
        self.steps_panel.setVisible(not is_basic)
        self.input.setPlaceholderText(
            self.texts[self.lang]["basic_input_placeholder"]
            if is_basic else self.texts[self.lang]["input_placeholder"]
        )
        self.result_title.setText(
            self.texts[self.lang]["basic_result_label"]
            if is_basic else self.texts[self.lang]["result_label"]
        )

        is_indefinite = is_simple and self.combo_def.currentIndex() == 1 and not is_basic
        num_limits = 0
        if not is_indefinite and not is_basic:
            num_limits = {0: 1, 1: 2, 2: 3, 3: 1, 4: 2}.get(idx_type, 0)

        self.limits_group.setVisible(num_limits > 0)
        self.limits_title_label.setVisible(num_limits > 0)

        for i, widgets in enumerate(self.limit_widgets):
            upper, label, lower = widgets
            visible = i < num_limits
            upper.setVisible(visible)
            label.setVisible(visible)
            lower.setVisible(visible)

        self.update_input_preview()

    def is_basic_calculator_mode(self):
        return self.combo_type.currentIndex() == len(self.texts[self.lang]["integral_types"]) - 1

    def history_label(self, item):
        type_names = self.texts[self.lang]["integral_types"]
        type_idx = int(item.get("tipo_idx", 0))
        type_name = type_names[type_idx] if 0 <= type_idx < len(type_names) else type_names[0]
        function = item.get("funcion", "")
        return f"{type_name}: {function}"[:80]

    def read_history_items(self):
        try:
            with open(self.history_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, list):
                self.history_items = data
            elif isinstance(data, dict) and "funcion" in data:
                self.history_items = [data]
            elif isinstance(data, dict):
                self.history_items = data.get("calculos", [])
            else:
                self.history_items = []
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self.history_items = []
        self.history_items = self.history_items[:5]
        return self.history_items

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()

    def save_to_history(self, context_dict):
        if self.loading_history:
            return
        item = dict(context_dict)
        if not item["funcion"]:
            return

        self.read_history_items()
        self.history_items = [
            existing for existing in self.history_items
            if json.dumps(existing, sort_keys=True) != json.dumps(item, sort_keys=True)
        ]
        self.history_items.insert(0, item)
        self.history_items = self.history_items[:5]

        try:
            with open(self.history_path, "w", encoding="utf-8") as file:
                json.dump({"calculos": self.history_items}, file, ensure_ascii=False, indent=2)
        except OSError:
            return
        self.load_history_ui()

    def current_history_context(self, result_text):
        return {
            "tipo_idx": self.combo_type.currentIndex(),
            "calculo_idx": self.combo_def.currentIndex(),
            "limites": [
                [upper.text().strip(), lower.text().strip()]
                for upper, _label, lower in self.limit_widgets
                if upper.isVisible()
            ],
            "funcion": self.input.text().strip(),
            "resultado": result_text,
            "preview_latex": self.current_preview_latex(),
        }

    def current_preview_latex(self):
        raw = self.input.text().strip()
        if not raw:
            return ""
        if self.is_basic_calculator_mode():
            try: return sp.latex(self.engine.sympify_user_text(raw))
            except: return html.escape(raw)
            
        idx_type = self.combo_type.currentIndex()
        is_indefinite = self.combo_def.isVisible() and self.combo_def.currentIndex() == 1
        limit_strings = [(u.text().strip(), l.text().strip()) for u, _, l in self.limit_widgets if u.isVisible()]
        return self.engine.build_preview_latex(raw, idx_type, is_indefinite, limit_strings)

    def history_preview_latex(self, item):
        saved_latex = item.get("preview_latex")
        if saved_latex:
            return saved_latex
        try:
            return sp.latex(self.engine.sympify_user_text(item.get("funcion", "")))
        except Exception:
            return html.escape(item.get("funcion", ""))

    def load_history_ui(self):
        if not hasattr(self, "history_layout"):
            return
        self.read_history_items()
        self.clear_layout(self.history_layout)

        if not self.history_items:
            empty = QLabel(self.texts[self.lang]["history_empty"])
            empty.setWordWrap(True)
            empty.setObjectName("history_empty")
            self.history_layout.addWidget(empty)
            return

        for item in self.history_items:
            self.history_layout.addWidget(self.create_history_card(item))

        clear_btn = QPushButton("Limpiar Historial" if self.lang == "es" else "Clear History")
        clear_btn.setObjectName("btn_clear_history")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self.clear_history_file)
        self.history_layout.addWidget(clear_btn)

    def clear_history_file(self):
        self.history_items = []
        try:
            with open(self.history_path, "w", encoding="utf-8") as file:
                json.dump({"calculos": []}, file, ensure_ascii=False, indent=2)
        except OSError:
            pass
        self.load_history_ui()

    def create_history_card(self, item):
        card = QFrame()
        card.setObjectName("history_card")
        card.setCursor(Qt.PointingHandCursor)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        math_view = MathView(min_height=36, compact=True, dark_mode=self.dark_mode, transparent_bg=True)
        math_view.setFixedHeight(36)
        if hasattr(math_view, 'web') and math_view.web is not None:
            math_view.web.setFixedHeight(36)
            
        math_view.setObjectName("history_math")
        math_view.setStyleSheet("QFrame#history_math { border: none; background: transparent; }")

        math_view.set_theme(self.dark_mode)
        math_view.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        if hasattr(math_view, 'web') and math_view.web is not None:
            math_view.web.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            
        latex = self.history_preview_latex(item)
        math_view.set_math_text(
            f'<div class="math-block" style="text-align:left; width:100%;">\\({latex}\\)</div>'
        )

        texto_resultado = str(item.get("resultado", ""))
        if self.lang == "en":
            texto_resultado = texto_resultado.replace("Analítico:", "Analytical:").replace("Numérico:", "Numerical:")
        else:
            texto_resultado = texto_resultado.replace("Analytical:", "Analítico:").replace("Numerical:", "Numérico:")

        result_label = QLabel(texto_resultado[:110])
        result_label.setObjectName("history_result")
        result_label.setWordWrap(True)
        result_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        layout.addWidget(math_view)
        layout.addWidget(result_label)

        card.mousePressEvent = lambda _event, saved=item: self.load_history_item(saved)
        result_label.mousePressEvent = lambda _event, saved=item: self.load_history_item(saved)
        return card

    def load_history_item(self, item):
        if not isinstance(item, dict):
            return

        self.loading_history = True
        try:
            tipo_idx = int(item.get("tipo_idx", 0))
            calculo_idx = int(item.get("calculo_idx", 0))
            self.combo_type.setCurrentIndex(max(0, min(tipo_idx, self.combo_type.count() - 1)))
            self.combo_def.setCurrentIndex(max(0, min(calculo_idx, self.combo_def.count() - 1)))
            self.update_ui_state()

            limites = item.get("limites", [])
            for idx, (upper, _label, lower) in enumerate(self.limit_widgets):
                upper.blockSignals(True)
                lower.blockSignals(True)
                if idx < len(limites):
                    upper.setText(str(limites[idx][0]))
                    lower.setText(str(limites[idx][1]))
                else:
                    upper.clear()
                    lower.clear()
                upper.blockSignals(False)
                lower.blockSignals(False)

            funcion = str(item.get("funcion", ""))
            self.input.setText(funcion)
            self.input.setFocus()
            self.input.setCursorPosition(len(funcion))
        finally:
            self.loading_history = False

        self.calculate_integral()

    def create_left_panel(self):
        panel = QFrame()
        panel.setObjectName("left_panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("left_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        card = QFrame()
        card.setObjectName("card")
        scroll_layout = QVBoxLayout(card)
        scroll_layout.setContentsMargins(16, 16, 16, 16)
        scroll_layout.setSpacing(10)

        self.card_title_label = QLabel(self.texts[self.lang]["help_title"])
        self.card_title_label.setObjectName("card_title")
        scroll_layout.addWidget(self.card_title_label)

        self.accordion_sections = {}
        self.add_accordion_section(
            scroll_layout, "how", self.texts[self.lang]["help_how_title"],
            self.texts[self.lang]["help_how_content"], expanded=True,
        )
        self.add_accordion_section(
            scroll_layout, "types", self.texts[self.lang]["help_types_title"],
            self.texts[self.lang]["help_types_content"], expanded=False,
        )
        self.add_accordion_section(
            scroll_layout, "results", self.texts[self.lang]["help_results_title"],
            self.texts[self.lang]["help_results_content"], expanded=False,
        )
        self.add_accordion_section(
            scroll_layout, "plot", self.texts[self.lang]["help_plot_title"],
            self.texts[self.lang]["help_plot_content"], expanded=False,
        )
        self.add_examples_section(scroll_layout)

        self.history_title_label = QLabel(self.texts[self.lang]["history_title"])
        self.history_title_label.setObjectName("card_title")
        scroll_layout.addWidget(self.history_title_label)

        self.history_layout = QVBoxLayout()
        self.history_layout.setSpacing(8)
        scroll_layout.addLayout(self.history_layout)

        scroll_layout.addStretch(1)
        scroll.setWidget(card)

        layout.addWidget(scroll)
        return panel

    def create_history_panel(self):
        scroll = QScrollArea()
        scroll.setObjectName("history_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.history_title_label = QLabel(self.texts[self.lang]["history_title"])
        self.history_title_label.setObjectName("card_title")
        layout.addWidget(self.history_title_label)

        self.history_layout = QVBoxLayout()
        self.history_layout.setSpacing(8)
        layout.addLayout(self.history_layout)

        scroll.setWidget(card)
        return scroll

    def create_help_panel(self):
        scroll = QScrollArea()
        scroll.setObjectName("help_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.card_title_label = QLabel(self.texts[self.lang]["help_title"])
        self.card_title_label.setObjectName("card_title")
        layout.addWidget(self.card_title_label)

        self.accordion_sections = {}
        self.add_accordion_section(
            layout, "how", self.texts[self.lang]["help_how_title"],
            self.texts[self.lang]["help_how_content"], expanded=True,
        )
        self.add_accordion_section(
            layout, "types", self.texts[self.lang]["help_types_title"],
            self.texts[self.lang]["help_types_content"], expanded=False,
        )
        self.add_accordion_section(
            layout, "plot", self.texts[self.lang]["help_plot_title"],
            self.texts[self.lang]["help_plot_content"], expanded=False,
        )
        self.add_examples_section(layout)

        layout.addStretch()
        scroll.setWidget(card)
        return scroll

    def add_accordion_section(self, parent_layout, key, title, content, expanded=False):
        header = QPushButton()
        header.setObjectName("accordion_header")
        header.setFocusPolicy(Qt.NoFocus)

        body = QLabel(content)
        body.setWordWrap(True)
        body.setObjectName("body_text")
        body.setVisible(expanded)

        self.accordion_sections[key] = {
            "header": header,
            "body": body,
            "title": title,
        }
        self.update_accordion_header(key)
        header.clicked.connect(lambda _=False, section_key=key: self.toggle_accordion(section_key))

        parent_layout.addWidget(header)
        parent_layout.addWidget(body)

    def add_examples_section(self, parent_layout):
        key = "examples"
        header = QPushButton()
        header.setObjectName("accordion_header")
        header.setFocusPolicy(Qt.NoFocus)

        body = QFrame()
        body.setObjectName("accordion_body")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)
        body.setVisible(False)

        self.accordion_sections[key] = {
            "header": header,
            "body": body,
            "title": self.texts[self.lang]["help_examples_title"],
        }
        self.update_accordion_header(key)
        header.clicked.connect(lambda _=False: self.toggle_accordion(key))

        self.example_buttons = []
        example_specs = [
            ("polar_area", 4, 0, [("2*pi", "0"), ("2", "0")], "1"),
            ("triple", 2, 0, [("3", "0"), ("2", "0"), ("1", "0")], "x + y + z"),
            ("single", 0, 0, [("pi", "0")], "sin(x)"),
        ]
        for example_key, tipo_idx, calculo_idx, limites, funcion in example_specs:
            btn = QPushButton(self.texts[self.lang]["examples"][example_key])
            btn.setObjectName("btn_example")
            btn.setFocusPolicy(Qt.NoFocus)
            btn.clicked.connect(
                lambda _=False, t=tipo_idx, c=calculo_idx, l=limites, f=funcion: self.cargar_ejemplo(t, c, l, f)
            )
            body_layout.addWidget(btn)
            self.example_buttons.append((btn, example_key))

        parent_layout.addWidget(header)
        parent_layout.addWidget(body)

    def update_accordion_header(self, key):
        section = self.accordion_sections[key]
        marker = "▼" if section["body"].isVisible() else "▶"
        section["header"].setText(f"{marker} {section['title']}")

    def toggle_accordion(self, key):
        section = self.accordion_sections[key]
        section["body"].setVisible(not section["body"].isVisible())
        self.update_accordion_header(key)

    def create_card(self, title, content):
        scroll = QScrollArea()
        scroll.setObjectName("help_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.card_title_label = QLabel(title)
        self.card_title_label.setObjectName("card_title")

        self.card_content_label = QLabel(content)
        self.card_content_label.setWordWrap(True)
        self.card_content_label.setObjectName("body_text")

        self.quick_examples_label = QLabel(self.texts[self.lang]["quick_examples_title"])
        self.quick_examples_label.setObjectName("section_label")

        self.example_buttons = []
        example_specs = [
            ("polar_area", 4, 0, [("2", "0"), ("2*pi", "0")], "1"),
            ("triple", 2, 0, [("1", "0"), ("2", "0"), ("3", "0")], "x + y + z"),
            ("single", 0, 0, [("pi", "0")], "sin(x)"),
        ]

        layout.addWidget(self.card_title_label)
        layout.addWidget(self.card_content_label)
        layout.addSpacing(8)
        layout.addWidget(self.quick_examples_label)

        for key, tipo_idx, calculo_idx, limites, funcion in example_specs:
            btn = QPushButton(self.texts[self.lang]["examples"][key])
            btn.setObjectName("btn_example")
            btn.setFocusPolicy(Qt.NoFocus)
            btn.clicked.connect(
                lambda _=False, t=tipo_idx, c=calculo_idx, l=limites, f=funcion: self.cargar_ejemplo(t, c, l, f)
            )
            layout.addWidget(btn)
            self.example_buttons.append((btn, key))

        layout.addStretch()
        scroll.setWidget(card)
        return scroll

    def cargar_ejemplo(self, tipo_idx, calculo_idx, limites, funcion):
        self.combo_type.setCurrentIndex(tipo_idx)
        if self.combo_def.isVisible():
            self.combo_def.setCurrentIndex(calculo_idx)
        self.update_ui_state()

        for idx, (upper, _label, lower) in enumerate(self.limit_widgets):
            upper.blockSignals(True)
            lower.blockSignals(True)
            if idx < len(limites):
                sup, inf = limites[idx]
                upper.setText(sup)
                lower.setText(inf)
            else:
                upper.clear()
                lower.clear()
            upper.blockSignals(False)
            lower.blockSignals(False)

        self.input.setText(funcion)
        self.input.setFocus()
        self.input.setCursorPosition(len(funcion))
        self.last_text_input = self.input
        self.calculate_integral()

    def create_keyboard(self):
        container = QFrame()
        container.setObjectName("keyboard")
        layout = QGridLayout(container)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(6)

        keys = [
            ["x", "y", "z", "r", "AC", "\u232b", "(", ")"],
            ["\u03b8", "\u03c0", "\u221a", "ln", "7", "8", "9", "\u00f7"],
            [self.sine_key_text(), "cos", "tan", "log", "4", "5", "6", "\u00d7"],
            ["csc", "sec", "cot", "e^x", "1", "2", "3", "\u2212"],
            ["|x|", "x\u00b2", "x^y", "!", "0", ".", "^", "+"],
            ["=", "", "", "", "", "", "", ""],
        ]

        self.sine_button = None
        for row, line in enumerate(keys):
            for col, key in enumerate(line):
                if not key:
                    continue

                btn = QPushButton(key)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setMinimumHeight(38)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                if key in ("sen", "sin"):
                    self.sine_button = btn

                if key == "=":
                    btn.setObjectName("btn_equals")
                    btn.clicked.connect(self.calculate_integral)
                elif key == "AC":
                    btn.setObjectName("btn_action")
                    btn.clicked.connect(self.clear_all)
                elif key == "\u232b":
                    btn.setObjectName("btn_action")
                    btn.clicked.connect(lambda _, k=key: self.insert_text(k))
                elif key in "0123456789.":
                    btn.setObjectName("btn_number")
                    btn.clicked.connect(lambda _, k=key: self.insert_text(k))
                elif key in ("+", "\u2212", "\u00d7", "\u00f7", "^", "!"):
                    btn.setObjectName("btn_operator")
                    btn.clicked.connect(lambda _, k=key: self.insert_text(k))
                else:
                    btn.setObjectName("btn_func")
                    btn.clicked.connect(lambda _, k=key: self.insert_text(k))

                layout.addWidget(btn, row, col)

        return container

    def sine_key_text(self):
        return "sen" if self.lang == "es" else "sin"

    def remember_text_focus(self, _old, new):
        if isinstance(new, QLineEdit):
            self.last_text_input = new

    def clear_all(self):
        self.input.clear()
        for upper, _label, lower in self.limit_widgets:
            upper.clear()
            lower.clear()
        self.last_plot_context = None
        
        self.plot_btn.setEnabled(False)
        self.plot_btn.setText(self.texts[self.lang]["plot_btn"])
            
        self.show_placeholder_result()
        self.show_placeholder_steps()
        self.update_input_preview()
        self.input.setFocus()

    def insert_text(self, text):
        focused_widget = QApplication.focusWidget()
        target_input = (
            focused_widget
            if isinstance(focused_widget, QLineEdit)
            else self.last_text_input or self.input
        )

        if text in ("???", "\u232b"):
            target_input.backspace()
            target_input.setFocus()
            return

        replacements = {
            "x??": "^2",
            "x\u00b2": "^2",
            "x^y": "^",
            "e^x": "exp(",
            "|x|": "Abs(",
            "???": "sqrt(",
            "\u221a": "sqrt(",
            "??": "*",
            "\u00d7": "*",
            "??": "/",
            "\u00f7": "/",
            "???": "-",
            "\u2212": "-",
        }
        if text in ("sen", "sin", "cos", "tan", "csc", "sec", "cot", "ln", "log"):
            text = f"{text}("
        else:
            text = replacements.get(text, text)

        target_input.insert(text)
        target_input.setFocus()

    def update_input_preview(self):
        raw = self.input.text().strip()
        if not raw:
            placeholder = self.texts[self.lang]["basic_input_placeholder"] if self.is_basic_calculator_mode() else self.texts[self.lang]["input_placeholder"]
            self.input_preview.set_math_text(self.placeholder_html(placeholder))
            return

        if self.is_basic_calculator_mode():
            try:
                expr = self.engine.sympify_user_text(raw)
                self.input_preview.set_math_text(f'<div class="math-block">\\[{sp.latex(expr)}\\]</div>')
            except Exception:
                self.input_preview.set_math_text(f'<div class="placeholder">{html.escape(raw)}</div>')
            return

        idx_type = self.combo_type.currentIndex()
        is_indefinite = self.combo_def.isVisible() and self.combo_def.currentIndex() == 1
        limit_strings = [(u.text().strip(), l.text().strip()) for u, _, l in self.limit_widgets if u.isVisible()]
        
        latex = self.engine.build_preview_latex(raw, idx_type, is_indefinite, limit_strings)
        if latex == html.escape(raw):
            self.input_preview.set_math_text(f'<div class="placeholder">{latex}</div>')
        else:
            self.input_preview.set_math_text(f'<div class="math-block">\\[{latex}\\]</div>')

    def show_placeholder_result(self):
        self.result_view.set_math_text(self.placeholder_html(self.texts[self.lang]["result_placeholder"]))

    def show_placeholder_steps(self):
        lines = [html.escape(line) for line in self.texts[self.lang]["steps_placeholder"].splitlines()]
        self.steps_panel.set_math_text(
            '<div class="steps">'
            + "".join(f'<div class="step"><div>{line}</div></div>' for line in lines)
            + "</div>"
        )

    def placeholder_html(self, text):
        return f'<div class="placeholder">{html.escape(text)}</div>'

    def steps_html(self, steps):
        body = ['<div class="steps">']
        for title, latex, note in steps:
            body.append('<div class="step">')
            body.append(f'<div class="step-title">{html.escape(title)}</div>')
            if latex:
                body.append(f'<div>\\[{latex}\\]</div>')
            if note:
                body.append(f'<div>{html.escape(note)}</div>')
            body.append("</div>")
        body.append("</div>")
        return "".join(body)

    def error_html(self, message, details):
        title = "No se pudo calcular" if self.lang == "es" else "Could not calculate"
        return (
            '<div class="steps">'
            '<div class="step error">'
            f'<div class="step-title">{html.escape(title)}</div>'
            f'<div>{html.escape(message)}</div>'
            f'<div class="placeholder">{html.escape(details)}</div>'
            "</div></div>"
        )

    def show_error(self, message, details):
        self.last_plot_context = None
        self.plot_btn.setEnabled(False)
        self.plot_btn.setText(self.texts[self.lang]["plot_btn"])
        self.result_view.set_math_text('<div class="math-block">\\[\\text{Error}\\]</div>')
        self.steps_panel.set_math_text(self.error_html(message, details))

    # --- SISTEMA ASÍNCRONO DE CÁLCULO (BLINDADO) ---
    def calculate_integral(self):
        expr_str = self.input.text().strip()
        if not expr_str:
            self.show_placeholder_result()
            self.show_placeholder_steps()
            return

        msg_calc = "Calculando..." if self.lang == "es" else "Calculating..."
        self.result_view.set_math_text(rf'<div class="math-block">\[\text{{{msg_calc}}}\]</div>')
        self.steps_panel.set_math_text("")
        self.plot_btn.setEnabled(False)
        self.plot_btn.setText(self.texts[self.lang]["plot_btn"])

        idx_type = self.combo_type.currentIndex()
        is_indefinite = self.combo_def.isVisible() and self.combo_def.currentIndex() == 1
        limit_strings = [(u.text().strip(), l.text().strip()) for u, _, l in self.limit_widgets if u.isVisible()]

        self.worker = MathWorker(
            self.engine, expr_str, idx_type, is_indefinite, limit_strings, self.lang, self.is_basic_calculator_mode()
        )
        self.worker.finished_ok.connect(self.on_calculation_finished)
        
        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self.on_calculation_timeout)
        
        self.worker.start()
        self.timeout_timer.start(15000)

    def on_calculation_timeout(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            titulo = "Tiempo de espera agotado" if self.lang == "es" else "Timeout reached"
            detalle = "La integral es demasiado compleja y superó el límite de seguridad de 15 segundos." if self.lang == "es" else "The integral is too complex and exceeded the 15-second safety limit."
            self.show_error(titulo, detalle)

    def on_calculation_finished(self, res):
        try:
            if hasattr(self, 'timeout_timer') and self.timeout_timer.isActive():
                self.timeout_timer.stop()

            if self.is_basic_calculator_mode():
                if not res.get("success"):
                    self.show_error("Error", res.get("error_details", "Error"))
                    return
                import sympy as sp
                result_html = (
                    '<div class="math-block" style="font-size:28px;">'
                    rf'\[{sp.latex(res["expr"])}\]'
                    rf'\[\approx {sp.latex(sp.N(res["numeric"], 14))}\]'
                    '</div>'
                )
                self.result_view.set_math_text(result_html)
                
                # Restaurado: Guardado en historial para cálculo básico
                texto_hist = f"Resultado: {sp.N(res['numeric'], 6)}"
                self.save_to_history(self.current_history_context(texto_hist))
                return

            if not res.get("success"):
                self.show_error("Error", res.get("error_details", "Error"))
                return

            self.last_plot_context = res.get("plot_context")
            import sympy as sp
            result_latex = sp.latex(res["result_expr"])
            texto_hist = ""
            
            # --- ESCUDO ANTI-NaN Y FORMATO DE SALIDA ---
            if "numeric_result" in res and res["numeric_result"] is not None:
                num_res = res["numeric_result"]
                try:
                    val = float(num_res)
                    import math
                    if math.isnan(val) or math.isinf(val):
                        raise ValueError("Divergente")
                except:
                    self.show_error("Error matemático", "Resultado indefinido (NaN/Inf).")
                    return
                
                result_html = (
                    '<div class="math-block">'
                    rf'\[\text{{Analítico}} = {result_latex}\]'
                    rf'\[\text{{Numérico}} = {sp.latex(sp.N(num_res, 12))}\]'
                    '</div>'
                )
                self.result_view.set_math_text(result_html)
                texto_hist = f"Analítico: {result_latex} | Numérico: {sp.N(num_res, 6)}"
                
                # Restaurado: Activación del botón de gráficas
                if self.last_plot_context:
                    vars_len = len(self.last_plot_context["variables"])
                    if vars_len == 1:
                        self.plot_btn.setText("Ver Región 2D" if self.lang == "es" else "View 2D Region")
                        self.plot_btn.setEnabled(True)
                    elif vars_len == 2:
                        self.plot_btn.setText("Ver Región 3D" if self.lang == "es" else "View 3D Region")
                        self.plot_btn.setEnabled(True)
            else:
                # Es una integral indefinida
                result_html = (
                    '<div class="math-block" style="font-size:26px;">'
                    rf'\[{result_latex} + C\]'
                    '</div>'
                )
                self.result_view.set_math_text(result_html)
                texto_hist = f"Analítico: {result_latex} + C"
            
            self.steps_panel.set_math_text(self.steps_html(res["steps"]))
            
            # Restaurado: Guardado en historial para integrales
            self.save_to_history(self.current_history_context(texto_hist))

        except Exception as e:
            self.show_error("Error interno", str(e))

    def export_steps_to_pdf(self):
        if QWebEngineView is None or not hasattr(self, "steps_panel"):
            QMessageBox.warning(self, "PDF", "QWebEngineView no está disponible; no se puede exportar a PDF.")
            return

        pasos_html = self.steps_panel._body
        
        if not pasos_html or 'class="step"' not in pasos_html:
            QMessageBox.warning(
                self, 
                "Exportar a PDF" if self.lang == "es" else "Export to PDF",
                "Calcula una integral primero para poder exportarla." if self.lang == "es" else "Calculate an integral first to export it."
            )
            return

        incluir_grafica = False
        img_base64 = ""
        if self.last_plot_context and FigureCanvas is not None and np is not None:
            vars_len = len(self.last_plot_context["variables"])
            if vars_len in (1, 2):
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Incluir Gráfica" if self.lang == "es" else "Include Graph")
                msg_box.setText("¿Desea incluir la gráfica de la región en el reporte PDF?" if self.lang == "es" else "Do you want to include the region graph in the PDF report?")
                msg_box.setIcon(QMessageBox.Question)
                
                btn_yes = msg_box.addButton("Sí" if self.lang == "es" else "Yes", QMessageBox.YesRole)
                btn_no = msg_box.addButton("No", QMessageBox.NoRole)
                msg_box.exec()

                if msg_box.clickedButton() == btn_yes:
                    incluir_grafica = True
                    try:
                        import io
                        import base64
                        from matplotlib.figure import Figure
                        
                        ctx = self.last_plot_context
                        expr = ctx["expr"]
                        vars_ = ctx["variables"]
                        limits = ctx["limits"]
                        
                        fig = Figure(figsize=(6.5, 3.8), dpi=120)
                        fig.patch.set_facecolor('#ffffff')
                        
                        if len(vars_) == 1:
                            ax = fig.add_subplot(111)
                            ax.set_facecolor('#ffffff')
                            var = str(vars_[0])
                            inf_val = float(limits[0][0].evalf())
                            sup_val = float(limits[0][1].evalf())
                            
                            f = sp.lambdify(sp.Symbol(var), expr, "numpy")
                            x_vals = np.linspace(inf_val, sup_val, 400)
                            y_vals = f(x_vals)
                            y_vals = np.broadcast_to(y_vals, x_vals.shape)
                            
                            ax.plot(x_vals, y_vals, color='#ef476f', linewidth=2)
                            ax.fill_between(x_vals, 0, y_vals, color='#ef476f', alpha=0.2)
                            ax.set_title("Área bajo la curva" if self.lang == "es" else "Area under curve", color='#2b3445', fontsize=11, fontweight='bold')
                            ax.set_xlabel(var, color='#2b3445')
                            ax.grid(True, linestyle='--', alpha=0.5, color='#d7dce7')
                            ax.tick_params(colors='#2b3445')
                            for spine in ax.spines.values():
                                spine.set_edgecolor('#d7dce7')
                                
                        elif len(vars_) == 2:
                            ax = fig.add_subplot(111, projection='3d')
                            ax.set_facecolor('#ffffff')
                            
                            v_inner, v_outer = str(vars_[0]), str(vars_[1])
                            inf_in, sup_in = limits[0]
                            inf_out, sup_out = limits[1]
                            
                            try:
                                out_min, out_max = float(inf_out.evalf()), float(sup_out.evalf())
                                mid_out = (out_min + out_max) / 2
                                in_min = float(inf_in.evalf(subs={sp.Symbol(v_outer): mid_out}))
                                in_max = float(sup_in.evalf(subs={sp.Symbol(v_outer): mid_out}))
                            except Exception:
                                out_min, out_max = -5, 5
                                in_min, in_max = -5, 5
                            
                            if out_min == out_max: out_max += 1
                            if in_min == in_max: in_max += 1
                            
                            X, Y = np.meshgrid(np.linspace(out_min, out_max, 50), np.linspace(in_min, in_max, 50))
                            f = sp.lambdify((sp.Symbol(v_outer), sp.Symbol(v_inner)), expr, "numpy")
                            Z = f(X, Y)
                            Z = np.broadcast_to(Z, X.shape)
                            
                            ax.plot_surface(X, Y, Z, cmap='coolwarm', edgecolor='none', alpha=0.8)
                            ax.set_title("Superficie 3D y Volumen" if self.lang == "es" else "3D Surface & Volume", color='#2b3445', fontsize=11, fontweight='bold')
                            ax.set_xlabel(v_outer, color='#2b3445')
                            ax.set_ylabel(v_inner, color='#2b3445')
                            ax.tick_params(colors='#2b3445')
                            
                            ax.xaxis.pane.fill = False
                            ax.yaxis.pane.fill = False
                            ax.zaxis.pane.fill = False
                            ax.xaxis.pane.set_edgecolor('#d7dce7')
                            ax.yaxis.pane.set_edgecolor('#d7dce7')
                            ax.zaxis.pane.set_edgecolor('#d7dce7')

                        buf = io.BytesIO()
                        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor='none')
                        buf.seek(0)
                        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
                    except Exception as plot_err:
                        print(f"Error generando gráfica para PDF: {plot_err}")

        idx_type = self.combo_type.currentIndex()
        is_indefinite = self.combo_def.isVisible() and self.combo_def.currentIndex() == 1
        
        if self.is_basic_calculator_mode():
            default_name = "calculo_basico.pdf" if self.lang == "es" else "basic_calculation.pdf"
        elif idx_type == 0:
            if is_indefinite:
                default_name = "integral_indefinida.pdf" if self.lang == "es" else "indefinite_integral.pdf"
            else:
                default_name = "integral_definida.pdf" if self.lang == "es" else "definite_integral.pdf"
        elif idx_type == 1:
            default_name = "integral_doble.pdf" if self.lang == "es" else "double_integral.pdf"
        elif idx_type == 2:
            default_name = "integral_triple.pdf" if self.lang == "es" else "triple_integral.pdf"
        elif idx_type == 3:
            if is_indefinite:
                default_name = "integral_linea_indefinida.pdf" if self.lang == "es" else "indefinite_line_integral.pdf"
            else:
                default_name = "integral_linea_definida.pdf" if self.lang == "es" else "definite_line_integral.pdf"
        elif idx_type == 4:
            default_name = "area_polar.pdf" if self.lang == "es" else "polar_area.pdf"
        else:
            default_name = "resultado_integral.pdf"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Reporte en PDF" if self.lang == "es" else "Save Report to PDF",
            default_name,
            "PDF (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        latex_inicial = self.current_preview_latex()
        theme = self.steps_panel._theme_values()
        
        titulo = "Reporte de Cálculo Integral" if self.lang == "es" else "Integral Calculation Report"
        subtitulo = "ModernCalculator - Procedimiento de Métodos Numéricos" if self.lang == "es" else "ModernCalculator - Numerical Methods Procedure"
        lbl_planteamiento = "Planteamiento del Problema" if self.lang == "es" else "Problem Statement"
        lbl_latex = "Código LaTeX (Para copiar e incrustar)" if self.lang == "es" else "LaTeX Code (For copying and embedding)"
        lbl_resolucion = "Resolución Paso a Paso" if self.lang == "es" else "Step-by-step Resolution"
        lbl_grafica = "Visualización de la Región" if self.lang == "es" else "Region Visualization"

        grafica_html = ""
        if incluir_grafica and img_base64:
            grafica_html = f"""
            <div class="section-title">{lbl_grafica}</div>
            <div style="text-align: center; margin: 15px 0; page-break-inside: avoid;">
                <img src="data:image/png;base64,{img_base64}" style="max-width: 100%; max-height: 320px; height: auto; border: 1px solid #d7dce7; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.02);" />
            </div>
            """

        print_html = f"""
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8">
            <script>
                window.MathJax = {{
                    tex: {{ inlineMath: [['\\\\(', '\\\\)']], displayMath: [['\\\\[', '\\\\]']] }},
                    svg: {{ fontCache: 'global' }},
                    startup: {{
                        pageReady: () => {{
                            return MathJax.startup.defaultPageReady().then(() => {{
                                window.status = "done";
                            }});
                        }}
                    }}
                }};
            </script>
            <script defer src="mathjax/tex-svg.js"></script>
            <style>
                @page {{ margin: 20mm; size: A4; }}
                body {{
                    font-family: "Segoe UI", Arial, sans-serif;
                    background: #ffffff;
                    color: #000000;
                    margin: 0;
                    padding: 0;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 2px solid {theme["accent"]};
                    padding-bottom: 15px;
                    margin-bottom: 25px;
                }}
                .header h1 {{ margin: 0; font-size: 26px; color: {theme["accent"]}; }}
                .header p {{ margin: 5px 0 0 0; font-size: 15px; color: #555; font-style: italic; }}
                
                .section-title {{
                    font-size: 16px;
                    font-weight: bold;
                    background: #f4f6fb;
                    padding: 8px 12px;
                    border-left: 4px solid {theme["accent"]};
                    margin: 25px 0 15px 0;
                    color: #2b3445;
                    border-radius: 0 4px 4px 0;
                }}
                
                .problem-box {{
                    text-align: center;
                    font-size: 24px;
                    margin: 15px 0;
                    padding: 20px;
                    border: 1px solid #d7dce7;
                    background: #ffffff;
                    border-radius: 8px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.02);
                }}
                
                .latex-box {{
                    background: #f8fafc;
                    border: 1px solid #d7dce7;
                    border-radius: 6px;
                    padding: 12px;
                    font-family: Consolas, "Courier New", monospace;
                    font-size: 13px;
                    color: #c2185b;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    margin-bottom: 20px;
                }}

                .steps {{ font-size: 14px; line-height: 1.6; color: #172033; }}
                .step {{
                    border-left: 3px solid {theme["accent"]};
                    padding: 12px 0 12px 16px;
                    margin: 0 0 16px;
                    page-break-inside: avoid;
                    background: #ffffff;
                }}
                .step-title {{ color: #5a667a; font-weight: bold; margin-bottom: 8px; font-size: 14px; }}
                .error {{ border-left-color: #ffb703; }}
                mjx-container[jax="SVG"][display="true"] {{ margin: 0.8em 0; }}
                .placeholder {{ color: #a8b3c7; font-style: italic; font-size: 13px; margin-top: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{titulo}</h1>
                <p>{subtitulo}</p>
            </div>
            
            <div class="section-title">{lbl_planteamiento}</div>
            <div class="problem-box">\\[{latex_inicial}\\]</div>
            
            {grafica_html}
            
            <div class="section-title">{lbl_latex}</div>
            <div class="latex-box">{latex_inicial}</div>
            
            <div class="section-title">{lbl_resolucion}</div>
            {pasos_html}
        </body>
        </html>
        """

        self._print_view = QWebEngineView()
        base_path = ruta_recurso("assets")
        base_url = QUrl.fromLocalFile(base_path + "/")
        
        self.pdf_btn.setEnabled(False)
        self.pdf_btn.setText("Generando PDF..." if self.lang == "es" else "Generating PDF...")
        self._pdf_printed = False

        def on_pdf_printed(success):
            self.pdf_btn.setEnabled(True)
            self.pdf_btn.setText(self.texts[self.lang]["pdf_btn"])
            
            if success:
                QMessageBox.information(
                    self,
                    "PDF",
                    f"Reporte PDF exportado con éxito en:\n{path}" if self.lang == "es" else f"PDF Report successfully exported to:\n{path}",
                )
            else:
                QMessageBox.critical(
                    self, "PDF", "Ocurrió un error al intentar guardar el PDF." if self.lang == "es" else "An error occurred while saving the PDF."
                )
            
            self._print_view.deleteLater()
            self._print_view = None

        def do_print():
            if self._pdf_printed:
                return
            self._pdf_printed = True
            
            if hasattr(self._print_view.page(), "pdfPrintingFinished"):
                self._print_view.page().pdfPrintingFinished.connect(on_pdf_printed)
            else:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1500, lambda: on_pdf_printed(True))
                
            if hasattr(self._print_view, "printToPdf"):
                self._print_view.printToPdf(path)
            else:
                self._print_view.page().printToPdf(path)

        def check_ready():
            self._print_view.page().runJavaScript("window.status", lambda status: do_print() if status == "done" else None)

        def on_load_finished(ok):
            from PySide6.QtCore import QTimer
            if ok:
                QTimer.singleShot(400, check_ready)
                QTimer.singleShot(800, check_ready)
                QTimer.singleShot(1200, check_ready)
                QTimer.singleShot(2500, do_print)
            else:
                on_pdf_printed(False)

        self._print_view.page().loadFinished.connect(on_load_finished)
        self._print_view.setHtml(print_html, baseUrl=base_url)

    def generate_plot(self):
        if not self.last_plot_context or FigureCanvas is None:
            QMessageBox.warning(self, "Gráfica", "Requiere calcular una integral 1D o 2D primero, y tener instalados 'numpy' y 'matplotlib'.")
            return

        try:
            ctx = self.last_plot_context
            expr = ctx["expr"]
            vars_ = ctx["variables"]
            limits = ctx["limits"]

            dialog = PlotDialog(self, self.dark_mode)
            
            if len(vars_) == 1:
                ax = dialog.fig.add_subplot(111)
                if self.dark_mode:
                    ax.set_facecolor('#151922')
                    ax.tick_params(colors='white')
                    for spine in ax.spines.values(): spine.set_edgecolor('white')
                
                var = str(vars_[0])
                inf, sup = limits[0]
                inf_val = float(inf.evalf())
                sup_val = float(sup.evalf())
                
                f = sp.lambdify(sp.Symbol(var), expr, "numpy")
                x_vals = np.linspace(inf_val, sup_val, 400)
                y_vals = f(x_vals)
                y_vals = np.broadcast_to(y_vals, x_vals.shape)
                
                ax.plot(x_vals, y_vals, color='#ef476f', linewidth=2)
                ax.fill_between(x_vals, 0, y_vals, color='#ef476f', alpha=0.3)
                
                ax.set_title("Área bajo la curva" if self.lang == "es" else "Area under curve", color=dialog.text_color)
                ax.set_xlabel(var, color=dialog.text_color)
                ax.grid(True, linestyle='--', alpha=0.3)

            elif len(vars_) == 2:
                ax = dialog.fig.add_subplot(111, projection='3d')
                if self.dark_mode:
                    ax.set_facecolor('#151922')
                    ax.tick_params(colors='white')
                    ax.xaxis.pane.fill = False
                    ax.yaxis.pane.fill = False
                    ax.zaxis.pane.fill = False
                    
                v_inner, v_outer = str(vars_[0]), str(vars_[1])
                inf_in, sup_in = limits[0]
                inf_out, sup_out = limits[1]
                
                try:
                    out_min, out_max = float(inf_out.evalf()), float(sup_out.evalf())
                    mid_out = (out_min + out_max) / 2
                    in_min = float(inf_in.evalf(subs={sp.Symbol(v_outer): mid_out}))
                    in_max = float(sup_in.evalf(subs={sp.Symbol(v_outer): mid_out}))
                except Exception:
                    out_min, out_max = -5, 5
                    in_min, in_max = -5, 5
                
                if out_min == out_max: out_max += 1
                if in_min == in_max: in_max += 1
                
                X, Y = np.meshgrid(np.linspace(out_min, out_max, 50), np.linspace(in_min, in_max, 50))
                f = sp.lambdify((sp.Symbol(v_outer), sp.Symbol(v_inner)), expr, "numpy")
                
                Z = f(X, Y)
                Z = np.broadcast_to(Z, X.shape)

                surf = ax.plot_surface(X, Y, Z, cmap='coolwarm', edgecolor='none', alpha=0.8)
                ax.set_title("Superficie 3D y Volumen" if self.lang == "es" else "3D Surface & Volume", color=dialog.text_color)
                ax.set_xlabel(v_outer, color=dialog.text_color)
                ax.set_ylabel(v_inner, color=dialog.text_color)
            
            dialog.canvas.draw()
            dialog.show() 
            
            if not hasattr(self, "open_plots"):
                self.open_plots = []
            self.open_plots.append(dialog)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la gráfica:\n{e}")

    def toggle_language(self):
        self.lang = "en" if self.lang == "es" else "es"
        t = self.texts[self.lang]

        idx_type = self.combo_type.currentIndex()
        idx_def = self.combo_def.currentIndex()

        self.setWindowTitle(t["window_title"])
        self.title.setText(t["title"])
        self.subtitle.setText(t["subtitle"])
        self.lang_label.setText(t["lang_label"])
        self.lang_btn.setText(t["lang_btn"])
        self.pdf_btn.setText(t["pdf_btn"])

        if not self.plot_btn.isEnabled():
            self.plot_btn.setText(t["plot_btn"])
        elif self.plot_btn.text() in ("Ver Región 2D", "View 2D Region"):
            self.plot_btn.setText("Ver Región 2D" if self.lang == "es" else "View 2D Region")
        elif self.plot_btn.text() in ("Ver Región 3D", "View 3D Region"):
            self.plot_btn.setText("Ver Región 3D" if self.lang == "es" else "View 3D Region")

        self.card_title_label.setText(t["help_title"])
        self.history_title_label.setText(t["history_title"])
        self.accordion_sections["how"]["title"] = t["help_how_title"]
        self.accordion_sections["types"]["title"] = t["help_types_title"]
        self.accordion_sections["results"]["title"] = t["help_results_title"]
        self.accordion_sections["plot"]["title"] = t["help_plot_title"]
        self.accordion_sections["plot"]["body"].setText(t["help_plot_content"])
        self.accordion_sections["examples"]["title"] = t["help_examples_title"]
        self.accordion_sections["how"]["body"].setText(t["help_how_content"])
        self.accordion_sections["types"]["body"].setText(t["help_types_content"])
        self.accordion_sections["results"]["body"].setText(t["help_results_content"])

        for key in self.accordion_sections:
            self.update_accordion_header(key)
        for btn, key in self.example_buttons:
            btn.setText(t["examples"][key])
        self.limits_title_label.setText(t["limits_title"])
        self.input.setPlaceholderText(t["input_placeholder"])
        self.result_title.setText(t["result_label"])
        self.steps_title_label.setText(t["steps_title"])
        self.lbl_type.setText(t["type_label"])
        self.lbl_def.setText(t["def_label"])

        self.combo_type.blockSignals(True)
        self.combo_type.clear()
        self.combo_type.addItems(t["integral_types"])
        self.combo_type.setCurrentIndex(idx_type)
        self.combo_type.blockSignals(False)

        self.combo_def.blockSignals(True)
        self.combo_def.clear()
        self.combo_def.addItems(t["def_indef_types"])
        self.combo_def.setCurrentIndex(idx_def)
        self.combo_def.blockSignals(False)

        if self.sine_button is not None:
            self.sine_button.setText(self.sine_key_text())

        self.load_history_ui()
        self.update_ui_state()
        self.show_placeholder_result()
        self.show_placeholder_steps()

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet(load_stylesheet(self.dark_mode))
        self.theme_btn.setText("🌙" if self.dark_mode else "☀️")
        for view in (self.input_preview, self.result_view, self.steps_panel):
            view.set_theme(self.dark_mode)
        self.load_history_ui()