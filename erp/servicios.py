"""Reglas de negocio de las ventas.

Vive separado de las vistas a propósito: acá está el "qué pasa" (descontar
stock, registrar movimientos, validar), y en las vistas solo el "cómo se ve".
Así la lógica se puede probar sin levantar el servidor y no se duplica si
mañana se agrega una API.
"""

from decimal import Decimal

from sqlalchemy import select

from erp.extensiones import db
from erp.modelos import LineaVenta, MovimientoStock, Producto, Venta, ahora


class ErrorDeNegocio(Exception):
    """Algo que el usuario hizo mal y hay que explicarle, no un bug."""


# ---------------------------------------------------------------------------
# Armado del borrador
# ---------------------------------------------------------------------------
def agregar_linea(venta: Venta, producto_id: int, cantidad: Decimal) -> LineaVenta:
    """Agrega un renglón al borrador.

    No descuenta stock: eso pasa recién al confirmar. Pero sí avisa si la
    cantidad pedida no está disponible, para no enterarse al final.
    """
    if not venta.editable:
        raise ErrorDeNegocio("La venta ya está confirmada: no admite cambios.")

    if cantidad <= 0:
        raise ErrorDeNegocio("La cantidad debe ser mayor a 0.")

    producto = db.session.get(Producto, producto_id)
    if producto is None:
        raise ErrorDeNegocio("El producto no existe.")
    if not producto.activo:
        raise ErrorDeNegocio(f"{producto.codigo} está dado de baja y no puede venderse.")

    repetido = db.session.scalar(
        select(LineaVenta).where(
            LineaVenta.venta_id == venta.id,
            LineaVenta.producto_id == producto_id,
        )
    )
    if repetido is not None:
        raise ErrorDeNegocio(
            f"{producto.codigo} ya está en la venta. Editá la cantidad del renglón."
        )

    if producto.stock < cantidad:
        raise ErrorDeNegocio(
            f"Stock insuficiente de {producto.codigo}: "
            f"hay {producto.stock} y se piden {cantidad}."
        )

    linea = LineaVenta(
        venta_id=venta.id,
        producto_id=producto.id,
        cantidad=cantidad,
        # El precio se copia acá: la venta queda con el precio del momento.
        precio_unitario=producto.precio,
        subtotal=cantidad * producto.precio,
    )
    db.session.add(linea)
    db.session.flush()  # para que `venta.lineas` ya lo incluya al recalcular

    db.session.refresh(venta)
    venta.recalcular_total()
    db.session.commit()

    return linea


def quitar_linea(venta: Venta, linea_id: int) -> None:
    if not venta.editable:
        raise ErrorDeNegocio("La venta ya está confirmada: no admite cambios.")

    linea = db.session.get(LineaVenta, linea_id)
    if linea is None or linea.venta_id != venta.id:
        raise ErrorDeNegocio("El renglón no pertenece a esta venta.")

    db.session.delete(linea)
    db.session.flush()

    db.session.refresh(venta)
    venta.recalcular_total()
    db.session.commit()


# ---------------------------------------------------------------------------
# Confirmación — acá el stock se mueve
# ---------------------------------------------------------------------------
def confirmar_venta(venta: Venta) -> None:
    """Confirma la venta: descuenta stock y registra los movimientos.

    Todo ocurre en una sola transacción: si falla un renglón, no queda media
    venta registrada ni stock descontado a medias.
    """
    if venta.estado == "CONFIRMADA":
        raise ErrorDeNegocio("La venta ya estaba confirmada.")
    if venta.estado == "ANULADA":
        raise ErrorDeNegocio("Una venta anulada no puede confirmarse.")
    if not venta.lineas:
        raise ErrorDeNegocio("No se puede confirmar una venta sin renglones.")

    try:
        for linea in venta.lineas:
            # with_for_update bloquea la fila del producto hasta el final de la
            # transacción. Sin esto, dos ventas simultáneas leerían el mismo
            # stock y venderían más de lo que hay.
            producto = db.session.scalar(
                select(Producto).where(Producto.id == linea.producto_id).with_for_update()
            )

            if producto.stock < linea.cantidad:
                raise ErrorDeNegocio(
                    f"Stock insuficiente de {producto.codigo}: "
                    f"hay {producto.stock} y la venta pide {linea.cantidad}."
                )

            producto.stock = producto.stock - linea.cantidad

            db.session.add(
                MovimientoStock(
                    producto_id=producto.id,
                    tipo="EGRESO",
                    origen="VENTA",
                    cantidad=linea.cantidad,
                    stock_resultante=producto.stock,
                    venta_id=venta.id,
                    motivo=f"Venta #{venta.id}",
                )
            )

        venta.recalcular_total()
        venta.estado = "CONFIRMADA"
        venta.confirmada_en = ahora()

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


# ---------------------------------------------------------------------------
# Anulación — devuelve el stock, no borra nada
# ---------------------------------------------------------------------------
def anular_venta(venta: Venta) -> None:
    """Anula una venta confirmada devolviendo el stock.

    No se edita ni se borra la venta original: se generan los movimientos
    inversos, de modo que el historial muestre las dos operaciones.
    """
    if venta.estado != "CONFIRMADA":
        raise ErrorDeNegocio("Solo se puede anular una venta confirmada.")

    try:
        for linea in venta.lineas:
            producto = db.session.scalar(
                select(Producto).where(Producto.id == linea.producto_id).with_for_update()
            )

            producto.stock = producto.stock + linea.cantidad

            db.session.add(
                MovimientoStock(
                    producto_id=producto.id,
                    tipo="INGRESO",
                    origen="ANULACION",
                    cantidad=linea.cantidad,
                    stock_resultante=producto.stock,
                    venta_id=venta.id,
                    motivo=f"Anulación de venta #{venta.id}",
                )
            )

        venta.estado = "ANULADA"
        venta.anulada_en = ahora()

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
