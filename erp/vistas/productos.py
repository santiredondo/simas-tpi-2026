"""CRUD de Productos.

Cada operación del CRUD es una ruta:
    Create -> GET/POST  /productos/nuevo
    Read   -> GET       /productos            (listado con búsqueda)
    Update -> GET/POST  /productos/<id>/editar
    Delete -> GET/POST  /productos/<id>/baja  (baja lógica)
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import or_, select

from erp.extensiones import db
from erp.modelos import UNIDADES, Producto
from erp.validaciones import validar_producto

bp = Blueprint("productos", __name__, url_prefix="/productos")


def _buscar_producto(id_producto: int) -> Producto:
    """Trae el producto o corta con un 404. Evita repetir el chequeo en cada vista."""
    return db.get_or_404(Producto, id_producto, description="Producto inexistente")


def _codigo_repetido(codigo: str, excluir_id: int | None = None) -> bool:
    """True si ya hay otro producto con ese código.

    `excluir_id` permite editar un producto sin que choque consigo mismo.
    """
    consulta = select(Producto).where(Producto.codigo == codigo)
    if excluir_id is not None:
        consulta = consulta.where(Producto.id != excluir_id)
    return db.session.scalar(consulta) is not None


# ---------------------------------------------------------------------------
# READ — listado con búsqueda y filtro
# ---------------------------------------------------------------------------
@bp.get("/")
def listar():
    texto = (request.args.get("q") or "").strip()
    ver = request.args.get("ver", "activos")

    consulta = select(Producto)

    if ver != "todos":
        consulta = consulta.where(Producto.activo.is_(True))

    if texto:
        patron = f"%{texto}%"
        consulta = consulta.where(
            or_(Producto.codigo.like(patron), Producto.nombre.like(patron))
        )

    productos = db.session.scalars(consulta.order_by(Producto.codigo)).all()

    return render_template(
        "productos/lista.html",
        productos=productos,
        texto=texto,
        ver=ver,
    )


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------
@bp.route("/nuevo", methods=["GET", "POST"])
def crear():
    if request.method == "GET":
        return render_template(
            "productos/formulario.html",
            titulo="Nuevo producto",
            etiqueta_boton="Crear producto",
            producto=None,
            valores={"unidad": "UNIDAD", "stock": "0", "stock_minimo": "0"},
            errores={},
            unidades=UNIDADES,
        )

    datos, errores = validar_producto(request.form)

    # El código es único: se avisa acá con un mensaje claro, en lugar de dejar
    # que explote la restricción de la base con un error incomprensible.
    if not errores.get("codigo") and _codigo_repetido(datos["codigo"]):
        errores["codigo"] = "Ya existe un producto con ese código"

    if errores:
        return (
            render_template(
                "productos/formulario.html",
                titulo="Nuevo producto",
                etiqueta_boton="Crear producto",
                producto=None,
                valores=request.form,
                errores=errores,
                unidades=UNIDADES,
            ),
            400,
        )

    producto = Producto(**datos)
    db.session.add(producto)
    db.session.commit()

    flash(f"Producto {producto.codigo} creado correctamente.", "exito")
    return redirect(url_for("productos.listar"))


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------
@bp.route("/<int:id_producto>/editar", methods=["GET", "POST"])
def editar(id_producto: int):
    producto = _buscar_producto(id_producto)

    if request.method == "GET":
        return render_template(
            "productos/formulario.html",
            titulo="Editar producto",
            etiqueta_boton="Guardar cambios",
            producto=producto,
            valores={
                "codigo": producto.codigo,
                "nombre": producto.nombre,
                "descripcion": producto.descripcion or "",
                "unidad": producto.unidad,
                "precio": producto.precio,
                "stock": producto.stock,
                "stock_minimo": producto.stock_minimo,
            },
            errores={},
            unidades=UNIDADES,
        )

    datos, errores = validar_producto(request.form)

    if not errores.get("codigo") and _codigo_repetido(datos["codigo"], excluir_id=producto.id):
        errores["codigo"] = "Ya existe otro producto con ese código"

    if errores:
        return (
            render_template(
                "productos/formulario.html",
                titulo="Editar producto",
                etiqueta_boton="Guardar cambios",
                producto=producto,
                valores=request.form,
                errores=errores,
                unidades=UNIDADES,
            ),
            400,
        )

    for campo, valor in datos.items():
        setattr(producto, campo, valor)

    db.session.commit()

    flash(f"Cambios guardados en {producto.codigo}.", "exito")
    return redirect(url_for("productos.listar"))


# ---------------------------------------------------------------------------
# DELETE — baja lógica
# ---------------------------------------------------------------------------
@bp.route("/<int:id_producto>/baja", methods=["GET", "POST"])
def baja(id_producto: int):
    producto = _buscar_producto(id_producto)

    if request.method == "GET":
        return render_template("productos/baja.html", producto=producto)

    # No se borra la fila: se desactiva. Un producto referenciado por ventas o
    # movimientos de stock no puede desaparecer sin romper el historial.
    producto.activo = False
    db.session.commit()

    flash(f"Producto {producto.codigo} dado de baja.", "exito")
    return redirect(url_for("productos.listar"))


@bp.post("/<int:id_producto>/reactivar")
def reactivar(id_producto: int):
    producto = _buscar_producto(id_producto)
    producto.activo = True
    db.session.commit()

    flash(f"Producto {producto.codigo} reactivado.", "exito")
    return redirect(url_for("productos.listar", ver="todos"))
