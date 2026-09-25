"""Validación de los datos que llegan de los formularios.

Un formulario HTML manda todo como texto. Acá se convierte a los tipos reales y
se verifica que tenga sentido, ANTES de tocar la base. Devuelve los errores por
campo para poder mostrarlos al lado de cada input.
"""

from decimal import Decimal, InvalidOperation

from erp.modelos import UNIDADES

CODIGO_MAX = 30
NOMBRE_MAX = 150
DESCRIPCION_MAX = 1000


def _a_decimal(valor: str | None, campo: str, errores: dict[str, str]) -> Decimal | None:
    """Convierte un texto a Decimal, o anota el error y devuelve None."""
    if valor is None or valor.strip() == "":
        errores[campo] = "Este campo es obligatorio"
        return None

    try:
        return Decimal(valor.replace(",", "."))
    except InvalidOperation:
        errores[campo] = "Tiene que ser un número"
        return None


def validar_producto(formulario) -> tuple[dict, dict[str, str]]:
    """Valida el formulario de producto.

    Devuelve (datos_limpios, errores). Si `errores` está vacío, los datos se
    pueden guardar tal cual.
    """
    errores: dict[str, str] = {}

    codigo = (formulario.get("codigo") or "").strip().upper()
    nombre = (formulario.get("nombre") or "").strip()
    descripcion = (formulario.get("descripcion") or "").strip()
    unidad = (formulario.get("unidad") or "").strip().upper()

    # --- Código ---
    if not codigo:
        errores["codigo"] = "El código es obligatorio"
    elif len(codigo) > CODIGO_MAX:
        errores["codigo"] = f"No puede superar los {CODIGO_MAX} caracteres"
    elif " " in codigo:
        errores["codigo"] = "El código no puede tener espacios"

    # --- Nombre ---
    if len(nombre) < 2:
        errores["nombre"] = "El nombre debe tener al menos 2 caracteres"
    elif len(nombre) > NOMBRE_MAX:
        errores["nombre"] = f"No puede superar los {NOMBRE_MAX} caracteres"

    # --- Descripción ---
    if len(descripcion) > DESCRIPCION_MAX:
        errores["descripcion"] = f"No puede superar los {DESCRIPCION_MAX} caracteres"

    # --- Unidad ---
    if unidad not in UNIDADES:
        errores["unidad"] = "Elegí una unidad de medida válida"

    # --- Números ---
    precio = _a_decimal(formulario.get("precio"), "precio", errores)
    if precio is not None and precio <= 0:
        errores["precio"] = "El precio debe ser mayor a 0"

    stock = _a_decimal(formulario.get("stock"), "stock", errores)
    if stock is not None and stock < 0:
        errores["stock"] = "El stock no puede ser negativo"

    stock_minimo = _a_decimal(formulario.get("stock_minimo"), "stock_minimo", errores)
    if stock_minimo is not None and stock_minimo < 0:
        errores["stock_minimo"] = "El stock mínimo no puede ser negativo"

    datos = {
        "codigo": codigo,
        "nombre": nombre,
        "descripcion": descripcion or None,
        "unidad": unidad,
        "precio": precio,
        "stock": stock,
        "stock_minimo": stock_minimo,
    }

    return datos, errores
