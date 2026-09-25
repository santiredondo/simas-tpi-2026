"""Registro de ventas.

    Listado      GET       /ventas
    Nueva        GET/POST  /ventas/nueva          (elige cliente, crea borrador)
    Detalle      GET       /ventas/<id>           (arma el borrador)
    Renglones    POST      /ventas/<id>/lineas    y  /lineas/<linea_id>/quitar
    Confirmar    POST      /ventas/<id>/confirmar (descuenta stock)
    Anular       POST      /ventas/<id>/anular    (devuelve stock)
"""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import select

from erp.extensiones import db
from erp.modelos import Cliente, MovimientoStock, Producto, Venta
from erp.servicios import (
    ErrorDeNegocio,
    agregar_linea,
    anular_venta,
    confirmar_venta,
    quitar_linea,
)

bp = Blueprint("ventas", __name__, url_prefix="/ventas")


def _buscar_venta(id_venta: int) -> Venta:
    return db.get_or_404(Venta, id_venta, description="Venta inexistente")


# ---------------------------------------------------------------------------
# Listado
# ---------------------------------------------------------------------------
@bp.get("/")
def listar():
    estado = request.args.get("estado", "")

    consulta = select(Venta)
    if estado:
        consulta = consulta.where(Venta.estado == estado)

    ventas = db.session.scalars(consulta.order_by(Venta.id.desc())).all()

    return render_template("ventas/lista.html", ventas=ventas, estado=estado)


# ---------------------------------------------------------------------------
# Nueva venta: elegir cliente y abrir el borrador
# ---------------------------------------------------------------------------
@bp.route("/nueva", methods=["GET", "POST"])
def nueva():
    clientes = db.session.scalars(
        select(Cliente).where(Cliente.activo.is_(True)).order_by(Cliente.razon_social)
    ).all()

    if request.method == "GET":
        return render_template("ventas/nueva.html", clientes=clientes, errores={})

    cliente_id = request.form.get("cliente_id")
    if not cliente_id:
        return (
            render_template(
                "ventas/nueva.html",
                clientes=clientes,
                errores={"cliente_id": "Elegí un cliente"},
            ),
            400,
        )

    cliente = db.session.get(Cliente, int(cliente_id))
    if cliente is None or not cliente.activo:
        return (
            render_template(
                "ventas/nueva.html",
                clientes=clientes,
                errores={"cliente_id": "El cliente no está disponible"},
            ),
            400,
        )

    venta = Venta(
        cliente_id=cliente.id,
        observaciones=(request.form.get("observaciones") or "").strip() or None,
    )
    db.session.add(venta)
    db.session.commit()

    flash(f"Venta #{venta.id} abierta. Agregá los productos.", "exito")
    return redirect(url_for("ventas.detalle", id_venta=venta.id))


# ---------------------------------------------------------------------------
# Detalle / armado del borrador
# ---------------------------------------------------------------------------
@bp.get("/<int:id_venta>")
def detalle(id_venta: int):
    venta = _buscar_venta(id_venta)

    # Solo se ofrecen productos activos y con stock: no tiene sentido listar
    # lo que no se puede vender.
    productos = db.session.scalars(
        select(Producto)
        .where(Producto.activo.is_(True), Producto.stock > 0)
        .order_by(Producto.codigo)
    ).all()

    movimientos = db.session.scalars(
        select(MovimientoStock)
        .where(MovimientoStock.venta_id == venta.id)
        .order_by(MovimientoStock.id)
    ).all()

    return render_template(
        "ventas/detalle.html",
        venta=venta,
        productos=productos,
        movimientos=movimientos,
    )


@bp.post("/<int:id_venta>/lineas")
def agregar(id_venta: int):
    venta = _buscar_venta(id_venta)

    try:
        cantidad = Decimal((request.form.get("cantidad") or "").replace(",", "."))
    except InvalidOperation:
        flash("La cantidad tiene que ser un número.", "error")
        return redirect(url_for("ventas.detalle", id_venta=venta.id))

    try:
        agregar_linea(venta, int(request.form.get("producto_id", 0)), cantidad)
        flash("Producto agregado.", "exito")
    except ErrorDeNegocio as error:
        flash(str(error), "error")

    return redirect(url_for("ventas.detalle", id_venta=venta.id))


@bp.post("/<int:id_venta>/lineas/<int:id_linea>/quitar")
def quitar(id_venta: int, id_linea: int):
    venta = _buscar_venta(id_venta)

    try:
        quitar_linea(venta, id_linea)
        flash("Renglón quitado.", "exito")
    except ErrorDeNegocio as error:
        flash(str(error), "error")

    return redirect(url_for("ventas.detalle", id_venta=venta.id))


# ---------------------------------------------------------------------------
# Confirmar y anular
# ---------------------------------------------------------------------------
@bp.post("/<int:id_venta>/confirmar")
def confirmar(id_venta: int):
    venta = _buscar_venta(id_venta)

    try:
        confirmar_venta(venta)
        flash(f"Venta #{venta.id} confirmada. El stock fue descontado.", "exito")
    except ErrorDeNegocio as error:
        flash(str(error), "error")

    return redirect(url_for("ventas.detalle", id_venta=venta.id))


@bp.route("/<int:id_venta>/anular", methods=["GET", "POST"])
def anular(id_venta: int):
    venta = _buscar_venta(id_venta)

    if request.method == "GET":
        return render_template("ventas/anular.html", venta=venta)

    try:
        anular_venta(venta)
        flash(f"Venta #{venta.id} anulada. El stock fue devuelto.", "exito")
    except ErrorDeNegocio as error:
        flash(str(error), "error")

    return redirect(url_for("ventas.detalle", id_venta=venta.id))
