TEXTS = {
    "es": {
        "window_title": "Calculadora de Integrales",
        "title": "Calculadora de Integrales",
        "subtitle": "Integrales definidas e indefinidas",
        "lang_label": "Cambiar idioma a:",
        "lang_btn": "Inglés",
        "pdf_btn": "Exportar a PDF",
        "plot_btn": "Ver Gráfica",
        "history_placeholder": "Historial",
        "history_title": "Historial",
        "history_empty": "Aún no hay cálculos guardados.",
        "help_title": "Ayuda",
        "help_how_title": "Cómo usar",
        "help_types_title": "Tipos de Integrales",
        "help_examples_title": "Ejemplos Rápidos",
        "help_how_content": (
            "1. Selecciona el tipo de integral y si es definida o indefinida.\n"
            "2. Escribe la función en la caja principal (ej. '3*r').\n"
            "3. Si deseas que la calculadora aplique automáticamente el Jacobiano polar (r), "
            "añade 'dA' al final de tu función (ej. '3 dA'). Si prefieres ingresar tú mismo "
            "el Jacobiano, escribe directamente tus diferenciales (ej. '3*r dr dtheta').\n"
            "4. Introduce los límites de abajo hacia arriba en orden de integración."
        ),
        "help_types_content": (
            "• Integral Simple: Calcula áreas bajo la curva respecto a dx.\n"
            "• Integral Doble: Integra regiones sobre dx dy (o dy dx).\n"
            "• Integral Triple: Calcula volúmenes en el espacio cartesiano dx dy dz.\n"
            "• Integral de Línea: Evalúa funciones a lo largo de una trayectoria respecto a dtheta.\n"
            "• Área Polar: Diseñada para coordenadas polares. Si escribes 'dA' al final, "
            "se multiplicará automáticamente por el factor 'r'. De lo contrario, se integrará "
            "exactamente la expresión que ingreses en pantalla."
        ),
        "help_content": "Selecciona el tipo de integral y el modo de cálculo en las listas superiores...",
        "help_results_title": "Interpretación de Resultados",
        "help_results_content": (
            "Al calcular una integral definida, la calculadora muestra tres valores en el centro:\n\n"
            "1. Resultado Analítico: Es el valor matemático exacto en forma algebraica.\n\n"
            "2. Aproximación Numérica: Es el mismo resultado pero resuelto en formato decimal.\n\n"
            "3. Margen de error numérico: Muestra el límite de error esperado del algoritmo."
        ),
        "help_plot_title": "Visualización Gráfica (2D/3D)",
        "help_plot_content": (
            "La aplicación permite graficar el área o volumen resultante de tu cálculo.\n\n"
            "• Integrales Sencillas y Polares generan una región 2D.\n"
            "• Integrales Dobles generan una superficie 3D.\n\n"
            "Restricciones de la gráfica:\n"
            "- No disponible para Integrales Triples (requerirían 4D para visualizarse).\n"
            "- No disponible para Integrales Indefinidas (al no tener límites numéricos, no hay región que dibujar).\n"
            "- Si la función ingresada presenta un error matemático o de sintaxis, el botón se desactivará por seguridad."
        ),
        "quick_examples_title": "Ejemplos rápidos",
        "examples": {
            "polar_area": "Ejemplo: Área Polar",
            "triple": "Ejemplo: Integral Triple",
            "single": "Ejemplo: Integral Sencilla",
        },
        "limits_title": "Límites de integración",
        "input_placeholder": "Ingrese la función a integrar...",
        "basic_input_placeholder": "Ingrese la operación a calcular...",
        "result_label": "= Resultado",
        "basic_result_label": "= Resultado de la operación",
        "result_placeholder": "El resultado aparecerá aquí",
        "steps_title": "Pasos de resolución",
        "steps_placeholder": (
            "1. Selecciona el tipo de integral.\n"
            "2. Ingresa la función y los límites.\n"
            "3. Presiona '=' para calcular."
        ),
        "type_label": "Tipo de integral:",
        "def_label": "Cálculo:",
        "integral_types": [
            "Integral Sencilla",
            "Integral Doble",
            "Integral Triple Rectangular",
            "Integral Polar",
            "Integral Doble Polar",
            "Calculadora Básica",
        ],
        "def_indef_types": ["Definida", "Indefinida"],
    },
    "en": {
        "window_title": "Integral Calculator",
        "title": "Integral Calculator",
        "subtitle": "Definite and indefinite integrals",
        "lang_label": "Change language to:",
        "lang_btn": "Spanish",
        "pdf_btn": "Export to PDF",
        "plot_btn": "View Plot",
        "history_placeholder": "History",
        "history_title": "History",
        "history_empty": "No saved calculations yet.",
        "help_title": "Help",
        "help_how_title": "How to use",
        "help_types_title": "Integral Types",
        "help_examples_title": "Quick Examples",
        "help_how_content": (
            "1. Select the integral type and whether it is definite or indefinite.\n"
            "2. Type the function in the main input box (e.g., '3*r').\n"
            "3. If you want the calculator to automatically apply the polar Jacobian (r), "
            "add 'dA' at the end of your function (e.g., '3 dA'). If you prefer to manually "
            "include the Jacobian, type your differentials directly (e.g., '3*r dr dtheta').\n"
            "4. Enter the limits from bottom to top in order of integration."
        ),
        "help_types_content": (
            "• Single Integral: Calculates areas under the curve with respect to dx.\n"
            "• Double Integral: Integrates regions over dx dy (or dy dx).\n"
            "• Triple Integral: Calculates volumes in cartesian space dx dy dz.\n"
            "• Line Integral: Evaluates functions along a path with respect to dtheta.\n"
            "• Polar Area: Designed for polar coordinates. If you write 'dA' at the end, "
            "it will automatically multiply by the 'r' factor. Otherwise, it will strictly "
            "integrate the exact expression you type on screen."
        ),
        "help_content": "Select the integral type and calculation mode from the top lists...",
        "help_results_title": "Interpretation of Results",
        "help_results_content": (
            "When calculating a definite integral, the calculator displays three values in the center:\n\n"
            "1. Analytical Result: The exact mathematical value in algebraic form.\n\n"
            "2. Numerical Approximation: The same result but resolved in decimal format.\n\n"
            "3. Numerical error margin: Shows the expected error limit of the decimal approximation."
        ),
        "help_plot_title": "Graphical Visualization (2D/3D)",
        "help_plot_content": (
            "The application allows you to graph the area or volume resulting from your calculation.\n\n"
            "• Single and Polar integrals generate a 2D region.\n"
            "• Double integrals generate a 3D surface.\n\n"
            "Graphing restrictions:\n"
            "- Not available for Triple Integrals (they would require 4D to be visualized).\n"
            "- Not available for Indefinite Integrals (with no numerical limits, there is no region to draw).\n"
            "- If the entered function has a mathematical or syntax error, the button will be disabled for safety."
        ),
        "quick_examples_title": "Quick examples",
        "examples": {
            "polar_area": "Example: Polar Area",
            "triple": "Example: Triple Integral",
            "single": "Example: Single Integral",
        },
        "limits_title": "Integration limits",
        "input_placeholder": "Enter the function to integrate...",
        "basic_input_placeholder": "Enter the operation to calculate...",
        "result_label": "= Result",
        "basic_result_label": "= Operation result",
        "result_placeholder": "Result will appear here",
        "steps_title": "Step-by-step solution",
        "steps_placeholder": (
            "1. Select the integral type.\n"
            "2. Enter the function and limits.\n"
            "3. Press '=' to calculate."
        ),
        "type_label": "Integral type:",
        "def_label": "Calculation:",
        "integral_types": [
            "Single Integral",
            "Double Integral",
            "Triple Rectangular Integral",
            "Polar Integral",
            "Double Polar Integral",
            "Basic Calculator",
        ],
        "def_indef_types": ["Definite", "Indefinite"],
    }
}