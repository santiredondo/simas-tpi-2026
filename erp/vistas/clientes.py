"""CRUD de Clientes.

Mismo patrón que productos:
    Create -> GET/POST  /clientes/nuevo
    Read   -> GET       /clientes            (listado con búsqueda)
    Update -> GET/POST  /clientes/<id>/editar
    Delete -> GET/POST  /clientes/<id>/baja  (baja lógica)
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import or_, select

from erp.extensiones import db
from erp.modelos import Cliente
from erp.validaciones import validar_cliente

bp = Blueprint("clientes", __name__, url_prefix="/clientes")


def _buscar_cliente(id_cliente: int) -> Cliente:
    return db.get_or_404(Cliente, id_cliente, description="Cliente inexistente")


def _documento_repetido(documento: str | None, excluir_id: int | None = None) -> bool:
    """True si otro cliente ya tiene ese documento.

    Un documento vacío nunca choca: puede haber muchos clientes sin CUIT.
    """
    if not documento:
        return False

    consulta = select(Cliente).where(Cliente.documento == documento)
    if excluir_id is not None:
        consulta = consulta.where(Cliente.id != excluir_id)
    return db.session.scalar(consulta) is not None


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------
@bp.get("/")
def listar():
    texto = (request.args.get("q") or "").strip()
    ver = request.args.get("ver", "activos")

    consulta = select(Cliente)

    if ver != "todos":
        consulta = consulta.where(Cliente.activo.is_(True))

    if texto:
        patron = f"%{texto}%"
        consulta = consulta.where(
            or_(
                Cliente.razon_social.like(patron),
                Cliente.documento.like(patron),
                Cliente.email.like(patron),
            )
        )

    clientes = db.session.scalars(consulta.order_by(Cliente.razon_social)).all()

    return render_template("clientes/lista.html", clientes=clientes, texto=texto, ver=ver)


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------
@bp.route("/nuevo", methods=["GET", "POST"])
def crear():
    if request.method == "GET":
        return render_template(
            "clientes/formulario.html",
            titulo="Nuevo cliente",
            etiqueta_boton="Crear cliente",
            cliente=None,
            valores={},
            errores={},
        )

    datos, errores = validar_cliente(request.form)

    if not errores.get("documento") and _documento_repetido(datos["documento"]):
        errores["documento"] = "Ya hay un cliente con ese documento"

    if errores:
        return (
            render_template(
                "clientes/formulario.html",
                titulo="Nuevo cliente",
                etiqueta_boton="Crear cliente",
                cliente=None,
                valores=request.form,
                errores=errores,
            ),
            400,
        )

    cliente = Cliente(**datos)
    db.session.add(cliente)
    db.session.commit()

    flash(f"Cliente {cliente.razon_social} creado correctamente.", "exito")
    return redirect(url_for("clientes.listar"))


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------
@bp.route("/<int:id_cliente>/editar", methods=["GET", "POST"])
def editar(id_cliente: int):
    cliente = _buscar_cliente(id_cliente)

    if request.method == "GET":
        return render_template(
            "clientes/formulario.html",
            titulo="Editar cliente",
            etiqueta_boton="Guardar cambios",
            cliente=cliente,
            valores={
                "razon_social": cliente.razon_social,
                "documento": cliente.documento or "",
                "email": cliente.email or "",
                "telefono": cliente.telefono or "",
                "direccion": cliente.direccion or "",
            },
            errores={},
        )

    datos, errores = validar_cliente(request.form)

    if not errores.get("documento") and _documento_repetido(
        datos["documento"], excluir_id=cliente.id
    ):
        errores["documento"] = "Ya hay otro cliente con ese documento"

    if errores:
        return (
            render_template(
                "clientes/formulario.html",
                titulo="Editar cliente",
                etiqueta_boton="Guardar cambios",
                cliente=cliente,
                valores=request.form,
                errores=errores,
            ),
            400,
        )

    for campo, valor in datos.items():
        setattr(cliente, campo, valor)

    db.session.commit()

    flash(f"Cambios guardados en {cliente.razon_social}.", "exito")
    return redirect(url_for("clientes.listar"))


# ---------------------------------------------------------------------------
# DELETE — baja lógica
# ---------------------------------------------------------------------------
@bp.route("/<int:id_cliente>/baja", methods=["GET", "POST"])
def baja(id_cliente: int):
    cliente = _buscar_cliente(id_cliente)

    if request.method == "GET":
        return render_template("clientes/baja.html", cliente=cliente)

    cliente.activo = False
    db.session.commit()

    flash(f"Cliente {cliente.razon_social} dado de baja.", "exito")
    return redirect(url_for("clientes.listar"))


@bp.post("/<int:id_cliente>/reactivar")
def reactivar(id_cliente: int):
    cliente = _buscar_cliente(id_cliente)
    cliente.activo = True
    db.session.commit()

    flash(f"Cliente {cliente.razon_social} reactivado.", "exito")
    return redirect(url_for("clientes.listar", ver="todos"))
