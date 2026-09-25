"""Modelos de datos del ERP.

Por ahora solo Producto, que es el módulo del Workshop 3. El resto de las
entidades (cliente, venta, movimiento de stock) están modeladas en
docs/modelado-de-procesos.md y se suman a medida que avanzan los workshops.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, Numeric
from sqlalchemy.orm import Mapped, mapped_column

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
