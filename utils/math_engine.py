# utils/math_engine.py
import re
import math
import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor, factorial_notation, implicit_multiplication_application,
    parse_expr, standard_transformations
)

try:
    from scipy.integrate import nquad
except ImportError:
    nquad = None

TRANSFORMATIONS = (
    standard_transformations
    + (implicit_multiplication_application, convert_xor, factorial_notation)
)

class MathEngine:
    def __init__(self):
        # Diccionario seguro de variables y funciones para SymPy
        self.symbols = {
            "x": sp.Symbol("x"), "y": sp.Symbol("y"), "z": sp.Symbol("z"),
            "r": sp.Symbol("r"), "theta": sp.Symbol("theta"), "phi": sp.Symbol("phi"),
            "pi": sp.pi, "e": sp.E, "E": sp.E,
            "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
            "csc": sp.csc, "sec": sp.sec, "cot": sp.cot,
            "log": sp.log, "sqrt": sp.sqrt, "exp": sp.exp, "Abs": sp.Abs,
        }

    def normalize_expression(self, raw):
        text = raw.strip()
        
        # Eliminar ceros a la izquierda en números enteros (ej. '01' -> '1', '005' -> '5')
        # Respeta el '0' solitario y los decimales como '0.5'
        text = re.sub(r'\b0+(?=\d)', '', text)

        replacements = {
            "sen": "sin", "ln": "log", "??": "pi", "\u03c0": "pi",
            "??": "*", "\u00d7": "*", "??": "/", "\u00f7": "/",
            "???": "-", "\u2212": "-", "???": "sqrt", "\u221a": "sqrt",
            "??": "theta", "\u03b8": "theta", "??": "phi", "\u03c6": "phi",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def sympify_user_text(self, raw):
        normalized = self.normalize_expression(raw)
        if not normalized:
            return sp.Integer(0)
        return parse_expr(
            normalized,
            local_dict=self.symbols,
            transformations=TRANSFORMATIONS,
            evaluate=True,
        )

    def detect_differentials(self, expr_str):
        normalized = self.normalize_expression(expr_str)
        found = re.findall(r"(?<![A-Za-z])d\s*(theta|phi|[xyzrAV])\b", normalized)
        cleaned = re.sub(r"\*?\s*(?<![A-Za-z])d\s*(theta|phi|[xyzrAV])\b", "", normalized)
        return found, cleaned.strip() or "1"

    def default_variables_for_type(self, expr, idx_type):
        defaults = { 0: ["x"], 1: ["y", "x"], 2: ["z", "y", "x"], 3: ["theta"], 4: ["r", "theta"] }
        order = defaults.get(idx_type, ["x"]).copy()

        if idx_type == 0:
            present = [str(sym) for sym in expr.free_symbols if str(sym) in ("x", "y", "z", "r", "theta", "phi")]
            if len(present) == 1:
                order = present
        elif idx_type == 3:
            present = [str(sym) for sym in expr.free_symbols]
            if "theta" in present:
                order = ["theta"]
            elif "r" in present:
                order = ["r"]
        return order

    def variables_from_differentials(self, diffs, idx_type):
        variables = []
        for diff in diffs:
            if diff == "A":
                variables.extend(["r", "theta"] if idx_type == 4 else ["y", "x"])
            elif diff == "V":
                variables.extend(["z", "y", "x"])
            else:
                variables.append(diff)
        return variables

    def latex_var(self, var_name):
        return {"theta": r"\theta", "phi": r"\phi"}.get(var_name, var_name)

    def validate_numeric_value(self, value, label):
        try:
            numeric = complex(value)
        except Exception as exc:
            raise ValueError(f"{label} no se pudo convertir a numero real.") from exc

        if abs(numeric.imag) > 1e-10:
            raise ValueError(f"{label} produce un valor complejo.")
        real_value = float(numeric.real)
        if not math.isfinite(real_value):
            raise ValueError(f"{label} produce un valor infinito o indefinido.")
        return real_value

    def validate_limit_domains(self, parsed_limits, lang="es"):
        sample_values = {}
        for symbol, inf, sup, _inf_raw, _sup_raw in reversed(parsed_limits):
            for limit_expr in (inf, sup):
                try:
                    value = limit_expr.evalf(subs=sample_values)
                    self.validate_numeric_value(value, str(limit_expr))
                except Exception as exc:
                    # Interceptamos si el valor resultante no es numérico (quedó una variable sin evaluar)
                    if not getattr(value, 'is_number', True):
                        msg_order = (
                            "Error de orden: Las variables en los límites no coinciden con la integración. Agrega los diferenciales explícitamente (ej. dx dy dz) al final de tu función."
                            if lang == "es" else
                            "Order error: The variables in the limits do not match the integration. Add differentials explicitly (e.g., dx dy dz) at the end of your function."
                        )
                        raise ValueError(msg_order) from exc
                    
                    msg_domain = (
                        f"Los limites contienen una expresion fuera de dominio numerico o no evaluable: {limit_expr}. {exc}"
                        if lang == "es" else
                        f"Limits contain an expression outside numerical domain or not evaluable: {limit_expr}. {exc}"
                    )
                    raise ValueError(msg_domain) from exc
            
            inf_value = self.validate_numeric_value(inf.evalf(subs=sample_values), str(inf))
            sup_value = self.validate_numeric_value(sup.evalf(subs=sample_values), str(sup))
            sample_values[symbol] = (inf_value + sup_value) / 2.0

    def parse_numeric_limits(self, variables, limit_strings, lang, subs_dict=None):
        parsed_limits = []
        
        rev_limit_strings = limit_strings[::-1]
        
        for i, var_name in enumerate(variables):
            if i >= len(rev_limit_strings):
                raise ValueError("Completa todos los limites visibles antes de calcular." if lang == "es" else "Fill in every visible limit before calculating.")
            
            sup_raw, inf_raw = rev_limit_strings[i]
            if not sup_raw or not inf_raw:
                raise ValueError("Completa todos los limites visibles antes de calcular." if lang == "es" else "Fill in every visible limit before calculating.")
            
            try:
                sup = self.sympify_user_text(sup_raw)
                inf = self.sympify_user_text(inf_raw)
                
                # conversión a los límites
                if subs_dict:
                    sup = sup.subs(subs_dict)
                    inf = inf.subs(subs_dict)
                    
            except Exception as exc:
                prefix = "Limite invalido" if lang == "es" else "Invalid limit"
                raise ValueError(f"{prefix} '{inf_raw}, {sup_raw}': {exc}") from exc

            parsed_limits.append((self.symbols[var_name], inf, sup, inf_raw, sup_raw))

        self.validate_limit_domains(parsed_limits, lang)
        return parsed_limits

    def numeric_integral(self, expr, variables, parsed_limits):
        if nquad is None:
            raise RuntimeError("SciPy no esta instalado; no se puede usar scipy.integrate.nquad.")

        ordered_symbols = [self.symbols[var_name] for var_name in variables]
        numeric_func = sp.lambdify(ordered_symbols, expr, modules=["numpy", "scipy", "math"])

        def integrand(*args):
            try:
                value = numeric_func(*args)
                return self.validate_numeric_value(value, "f")
            except Exception as exc:
                raise ValueError(f"La funcion no se puede evaluar numericamente: {exc}") from exc

        ranges = []
        for i, (_symbol, inf, sup, _inf_raw, _sup_raw) in enumerate(parsed_limits):
            outer_symbols = ordered_symbols[i + 1:]
            lower_func = sp.lambdify(outer_symbols, inf, modules=["numpy", "scipy", "math"])
            upper_func = sp.lambdify(outer_symbols, sup, modules=["numpy", "scipy", "math"])

            def make_range(low_f, high_f):
                def bounds(*outer_args):
                    low = self.validate_numeric_value(low_f(*outer_args), "limite inferior")
                    high = self.validate_numeric_value(high_f(*outer_args), "limite superior")
                    return [low, high]
                return bounds

            ranges.append(make_range(lower_func, upper_func))

        result, error = nquad(integrand, ranges)
        return result, error

    def evaluate_basic(self, expr_str):
        """Calculadora básica (sin integrales)."""
        try:
            expr = self.sympify_user_text(expr_str)
            simplified = sp.simplify(expr)
            numeric = simplified.evalf()
            return {"success": True, "expr": simplified, "numeric": numeric}
        except Exception as e:
            return {"success": False, "error_details": str(e)}

    def process_integral(self, expr_str, idx_type, is_indefinite, limit_strings, lang="es"):
        """Flujo principal de cálculo simbólico y numérico."""
        try:
            diffs, clean_expr = self.detect_differentials(expr_str)
            expr = self.sympify_user_text(clean_expr)
            variables = self.variables_from_differentials(diffs, idx_type) if diffs else self.default_variables_for_type(expr, idx_type)

            if not variables:
                raise ValueError("No se detecto una variable de integracion.")

            expected = {0: 1, 1: 2, 2: 3, 3: 1, 4: 2}.get(idx_type, 1)
            if not is_indefinite and len(variables) > expected:
                raise ValueError("Hay mas diferenciales que limites disponibles para el tipo de integral seleccionado.")
            
            for var_name in variables:
                if var_name not in self.symbols:
                    raise ValueError(f"Variable no soportada: {var_name}")

            steps = []
            detected_note = ("Diferenciales detectados: " if lang == "es" else "Detected differentials: ") + ", ".join(f"d{self.latex_var(v)}" for v in variables) if diffs else ("Diferenciales inferidos por el tipo de integral seleccionado." if lang == "es" else "Differentials inferred from the selected integral type.")
            
            steps.append((
                "Funcion interpretada" if lang == "es" else "Parsed function",
                sp.latex(expr),
                detected_note,
            ))

            current_expr = expr
            subs_dict = None  # Inicializar el diccionario globalmente
            
            # Unir todos los límites en una sola cadena para buscar variables cruzadas
            limits_text = " ".join([f"{u} {l}" for u, l in limit_strings]) if limit_strings else ""

            #Normalizar para que símbolos como 'θ' o 'π' se conviertan a texto reconocible
            limits_text = self.normalize_expression(limits_text)

            # Conversión Automática a Polares
            if idx_type in (3, 4):
                # Detectar 'x' o 'y' tanto en la función como en los límites
                has_cartesian = any(str(s) in ("x", "y") for s in current_expr.free_symbols) or re.search(r'\b(x|y)\b', limits_text)
                if has_cartesian:
                    r_sym = self.symbols["r"]
                    theta_sym = self.symbols["theta"]
                    subs_dict = { self.symbols["x"]: r_sym * sp.cos(theta_sym), self.symbols["y"]: r_sym * sp.sin(theta_sym) }
                    current_expr = current_expr.subs(subs_dict)
                    current_expr = sp.simplify(current_expr)
                    titulo = "Conversión a polares" if lang == "es" else "Conversion to polar"
                    nota = "Se sustituyó automáticamente x = r cos(θ), y = r sin(θ)" if lang == "es" else "Automatically substituted x = r cos(θ), y = r sin(θ)"
                    steps.append((titulo, sp.latex(current_expr), nota))

            # Conversión Automática de Polares a Rectangulares
            if idx_type in (0, 1, 2):
                has_polar = any(str(s) in ("r", "theta") for s in current_expr.free_symbols) or re.search(r'\b(r|theta)\b', limits_text)
                
                # NUEVA CONDICIÓN: Verificar si el usuario pidió explícitamente integrar en r o theta (ej. dz dr dtheta)
                is_explicit_polar = any(v in ("r", "theta") for v in variables)
                
                if has_polar and not is_explicit_polar:
                    x_sym = self.symbols["x"]
                    y_sym = self.symbols["y"]
                    subs_dict = { self.symbols["r"]: sp.sqrt(x_sym**2 + y_sym**2), self.symbols["theta"]: sp.atan2(y_sym, x_sym) }
                    current_expr = current_expr.subs(subs_dict)
                    current_expr = sp.simplify(current_expr)
                    titulo = "Conversión a rectangulares" if lang == "es" else "Conversion to rectangular"
                    nota = "Se sustituyó automáticamente r = √(x² + y²), θ = atan2(y, x)" if lang == "es" else "Automatically substituted r = √(x² + y²), θ = atan2(y, x)"
                    steps.append((titulo, sp.latex(current_expr), nota))

            if idx_type == 4:
                # CONDICIÓN ESTRICTA: El paso de resolución del Jacobiano
                # SOLO se agregará si el usuario escribió explícitamente 'dA'
                if diffs and "A" in diffs:
                    r = self.symbols["r"]
                    current_expr = current_expr * r
                    steps.append((
                        "Jacobiano polar" if lang == "es" else "Polar Jacobian",
                        sp.latex(current_expr),
                        "Se aplica el factor r para dA = r dr dtheta." if lang == "es" else "Applied the r factor for dA = r dr dtheta.",
                    ))

            # --- SECCIÓN DE CÁLCULO ---
            if is_indefinite:
                # CÁLCULO INDEFINIDO: Sin límites numéricos
                var_name = variables[0]
                current_expr = sp.integrate(current_expr, self.symbols[var_name])
                steps.append((
                    f"Integracion respecto a d{self.latex_var(var_name)}" if lang == "es" else f"Integration with respect to d{self.latex_var(var_name)}",
                    sp.latex(current_expr) + r" + C",
                    None,
                ))
                # Forzamos que no haya resultado numérico ni contexto de gráfica
                numeric_result = None
                numeric_error = None
                plot_context = None

            else:
                # CÁLCULO DEFINIDO: Parsea límites y evalúa
                parsed_limits = self.parse_numeric_limits(variables, limit_strings, lang, subs_dict)
                numeric_result, numeric_error = self.numeric_integral(current_expr, variables, parsed_limits)
                
                plot_context = {
                    "expr": current_expr,
                    "variables": variables,
                    "limits": [(inf, sup) for _symbol, inf, sup, _inf_raw, _sup_raw in parsed_limits]
                }

                # Procesa cada integral de afuera hacia adentro
                for i, var_name in enumerate(variables):
                    sym = self.symbols[var_name]
                    _symbol, inf, sup, _inf_raw, _sup_raw = parsed_limits[i]

                    # 1. Antiderivada
                    antideriv = sp.integrate(current_expr, sym)

                    # 2. Evaluamos los límites
                    eval_sup = antideriv.subs(sym, sup)
                    eval_inf = antideriv.subs(sym, inf)
                    
                    # 3. Resultado de esta capa
                    next_expr = sp.simplify(eval_sup - eval_inf)

                    title = f"Paso {i+1}: Evaluando d{self.latex_var(var_name)}" if lang == "es" else f"Step {i+1}: Evaluating d{self.latex_var(var_name)}"
                    nota = "Aplicando el Teorema Fundamental del Cálculo" if lang == "es" else "Applying the Fundamental Theorem of Calculus"

                    latex_paso1 = rf"& \int_{{{sp.latex(inf)}}}^{{{sp.latex(sup)}}} \left( {sp.latex(current_expr)} \right) d{self.latex_var(var_name)} = \left[ {sp.latex(antideriv)} \right]_{{{sp.latex(inf)}}}^{{{sp.latex(sup)}}}"
                    latex_paso2 = rf"& = \left( {sp.latex(eval_sup)} \right) - \left( {sp.latex(eval_inf)} \right)"
                    latex_paso3 = rf"& = {sp.latex(next_expr)}"
                    
                    full_latex = rf"\begin{{aligned}} {latex_paso1} \\ {latex_paso2} \\ {latex_paso3} \end{{aligned}}"

                    steps.append((title, full_latex, nota))
                    current_expr = next_expr

            simplified = sp.simplify(current_expr)
            
            return {
                "success": True,
                "steps": steps,
                "result_expr": simplified,
                "is_indefinite": is_indefinite,
                "idx_type": idx_type,
                "numeric_result": numeric_result,
                "numeric_error": numeric_error,
                "plot_context": plot_context
            }

        except Exception as e:
            return {
                "success": False,
                "error_details": str(e)
            }

    def build_preview_latex(self, expr_str, idx_type, is_indefinite, limit_strings):
        """Genera el código LaTeX para la vista previa en tiempo real."""
        try:
            diffs, clean_expr = self.detect_differentials(expr_str)
            expr = self.sympify_user_text(clean_expr)
            variables = self.variables_from_differentials(diffs, idx_type) if diffs else self.default_variables_for_type(expr, idx_type)

            # Se quitó 'idx_type in (0, 3)' para que aplique en general
            if is_indefinite:
                return rf"\int {sp.latex(expr)}\, d{self.latex_var(variables[0])}"

            integrals_by_variable = []
            
            # Invertimos los límites para la vista previa
            rev_limit_strings = limit_strings[::-1] 
            
            for i, _var_name in enumerate(variables):
                if i < len(rev_limit_strings):
                    sup_raw, inf_raw = rev_limit_strings[i]
                    if sup_raw or inf_raw:
                        try: sup = sp.latex(self.sympify_user_text(sup_raw or "0"))
                        except: sup = str(sup_raw or "0")
                        try: inf = sp.latex(self.sympify_user_text(inf_raw or "0"))
                        except: inf = str(inf_raw or "0")
                        integrals_by_variable.append(rf"\int_{{{inf}}}^{{{sup}}}")
                    else:
                        integrals_by_variable.append(r"\int")
                else:
                    integrals_by_variable.append(r"\int")

            # Respetar visualmente si el usuario escribió dA o dV
            if diffs and "A" in diffs:
                diffs_str = r"\, dA"
            elif diffs and "V" in diffs:
                diffs_str = r"\, dV"
            else:
                diffs_str = " ".join(rf"\, d{self.latex_var(v)}" for v in variables)
                
            return f"{''.join(reversed(integrals_by_variable))} {sp.latex(expr)} {diffs_str}"
        except Exception:
            import html
            return html.escape(expr_str)