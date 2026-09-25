"""Modelos de datos del ERP.

Por ahora solo Producto, que es el módulo del Workshop 3. El resto de las
entidades (cliente, venta, movimiento de stock) están modeladas en
docs/modelado-de-procesos.md y se suman a medida que avanzan los workshops.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp.extensiones import db

UNIDADES = ("UNIDAD", "KG", "LITRO", "METRO", "CAJA")


def ahora() -> datetime:
    """Fecha y hora actual en UTC, sin depender del reloj del servidor."""
    return datetime.now(timezone.utc)


class Producto(db.Model):
    __tablename__ = "producto"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Código visible al usuario: es como se identifica un producto en el ERP.
    codigo: Mapped[str] = mapped_column(db.String(30), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(db.String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(db.Text)
    unidad: Mapped[str] = mapped_column(db.String(10), nullable=False, default="UNIDAD")

    # Numeric y no Float: con plata, los errores de redondeo no se perdonan.
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    stock_minimo: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # Baja lógica: un producto con ventas no puede desaparecer sin romper
    # el historial, así que se desactiva en lugar de borrarse.
    activo: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    creado_en: Mapped[datetime] = mapped_column(db.DateTime, default=ahora)
    actualizado_en: Mapped[datetime] = mapped_column(
        db.DateTime, default=ahora, onupdate=ahora
    )

    # Última línea de defensa: aunque falle la validación de la aplicación,
    # la base se niega a guardar un precio o un stock imposibles.
    __table_args__ = (
        CheckConstraint("precio > 0", name="chk_producto_precio"),
        CheckConstraint("stock >= 0", name="chk_producto_stock"),
        CheckConstraint("stock_minimo >= 0", name="chk_producto_stock_minimo"),
        db.Index("idx_producto_activo", "activo"),
        db.Index("idx_producto_nombre", "nombre"),
    )

    @property
    def necesita_reposicion(self) -> bool:
        """True cuando el stock llegó o bajó del mínimo definido."""
        return self.stock <= self.stock_minimo

    def __repr__(self) -> str:
        return f"<Producto {self.codigo} — {self.nombre}>"


class Cliente(db.Model):
    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    razon_social: Mapped[str] = mapped_column(db.String(150), nullable=False)
    # CUIT o DNI. Opcional (un mostrador no siempre lo pide), pero si se carga
    # no puede repetirse: dos fichas del mismo cliente ensucian el historial.
    documento: Mapped[str | None] = mapped_column(db.String(20), unique=True)
    email: Mapped[str | None] = mapped_column(db.String(150))
    telefono: Mapped[str | None] = mapped_column(db.String(30))
    direccion: Mapped[str | None] = mapped_column(db.String(200))

    # Baja lógica, por el mismo motivo que en Producto: las ventas históricas
    # apuntan al cliente y no pueden quedar huérfanas.
    activo: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    creado_en: Mapped[datetime] = mapped_column(db.DateTime, default=ahora)
    actualizado_en: Mapped[datetime] = mapped_column(
        db.DateTime, default=ahora, onupdate=ahora
    )

    ventas: Mapped[list["Venta"]] = relationship(back_populates="cliente")

    __table_args__ = (
        db.Index("idx_cliente_activo", "activo"),
        db.Index("idx_cliente_razon", "razon_social"),
    )

    def __repr__(self) -> str:
        return f"<Cliente {self.razon_social}>"


ESTADOS_VENTA = ("BORRADOR", "CONFIRMADA", "ANULADA")


class Venta(db.Model):
    """Cabecera de una venta.

    Ciclo de vida:
        BORRADOR   se arma libremente y NO toca el stock.
        CONFIRMADA descuenta stock y queda inmutable.
        ANULADA    devuelve el stock; no borra nada.
    """

    __tablename__ = "venta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(
        db.ForeignKey("cliente.id", ondelete="RESTRICT"), nullable=False
    )
    cliente: Mapped["Cliente"] = relationship(back_populates="ventas")

    estado: Mapped[str] = mapped_column(db.String(12), nullable=False, default="BORRADOR")
    fecha: Mapped[datetime] = mapped_column(db.DateTime, default=ahora)
    # Se recalcula cada vez que cambian los renglones.
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    observaciones: Mapped[str | None] = mapped_column(db.String(255))

    confirmada_en: Mapped[datetime | None] = mapped_column(db.DateTime)
    anulada_en: Mapped[datetime | None] = mapped_column(db.DateTime)
    creado_en: Mapped[datetime] = mapped_column(db.DateTime, default=ahora)

    lineas: Mapped[list["LineaVenta"]] = relationship(
        back_populates="venta",
        cascade="all, delete-orphan",  # un renglón sin su venta no significa nada
        order_by="LineaVenta.id",
    )

    __table_args__ = (db.Index("idx_venta_estado_fecha", "estado", "fecha"),)

    @property
    def editable(self) -> bool:
        """Solo un borrador admite cambios. Confirmada, es historia."""
        return self.estado == "BORRADOR"

    def recalcular_total(self) -> None:
        self.total = sum((linea.subtotal for linea in self.lineas), Decimal("0.00"))

    def __repr__(self) -> str:
        return f"<Venta #{self.id} {self.estado}>"


class LineaVenta(db.Model):
    __tablename__ = "linea_venta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    venta_id: Mapped[int] = mapped_column(
        db.ForeignKey("venta.id", ondelete="CASCADE"), nullable=False
    )
    venta: Mapped["Venta"] = relationship(back_populates="lineas")

    producto_id: Mapped[int] = mapped_column(
        db.ForeignKey("producto.id", ondelete="RESTRICT"), nullable=False
    )
    producto: Mapped["Producto"] = relationship()

    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # COPIA del precio al momento de agregar el renglón, no una referencia:
    # si mañana cambia el precio del producto, esta venta no se altera.
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="chk_linea_cantidad"),
        # Un producto no se repite dos veces en la misma venta.
        db.UniqueConstraint("venta_id", "producto_id", name="uq_linea_venta_producto"),
    )


class MovimientoStock(db.Model):
    """Libro mayor del stock: cada cambio de existencias deja un asiento.

    `Producto.stock` responde "¿cuánto hay?"; esta tabla responde "¿cómo se
    llegó a ese número?". Es lo que hace auditable al sistema.
    """

    __tablename__ = "movimiento_stock"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(
        db.ForeignKey("producto.id", ondelete="RESTRICT"), nullable=False
    )
    producto: Mapped["Producto"] = relationship()

    tipo: Mapped[str] = mapped_column(db.String(10), nullable=False)      # INGRESO / EGRESO / AJUSTE
    origen: Mapped[str] = mapped_column(db.String(15), nullable=False)    # VENTA / ANULACION / AJUSTE_MANUAL
    # Siempre positiva: el signo lo determina `tipo`.
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # Foto del stock después de aplicar este movimiento.
    stock_resultante: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    venta_id: Mapped[int | None] = mapped_column(db.ForeignKey("venta.id", ondelete="SET NULL"))
    motivo: Mapped[str | None] = mapped_column(db.String(255))
    fecha: Mapped[datetime] = mapped_column(db.DateTime, default=ahora)

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="chk_movimiento_cantidad"),
        db.Index("idx_movimiento_producto_fecha", "producto_id", "fecha"),
    )
