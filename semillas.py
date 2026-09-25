"""Carga productos de ejemplo para poder probar el CRUD:  python semillas.py

No borra lo que ya exista: si el código ya está cargado, lo saltea.
"""

from decimal import Decimal

from erp import crear_app
from erp.extensiones import db
from erp.modelos import Cliente, Producto

PRODUCTOS = [
    ("PRD-001", "Chapa galvanizada 1x2m", "Espesor 0.9mm", "UNIDAD", "18500.00", "120", "20"),
    ("PRD-002", "Perfil C 100x50", "Barra de 6 metros", "METRO", "9750.50", "300", "50"),
    ("PRD-003", "Tornillo autoperforante", "Caja x 500 unidades", "CAJA", "4200.00", "45", "10"),
    ("PRD-004", "Electrodo 2.5mm", "Caja x 5kg", "KG", "15300.00", "8", "15"),
    ("PRD-005", "Pintura antióxido 4L", "Color gris", "LITRO", "22900.00", "60", "12"),
]


CLIENTES = [
    ("Metalúrgica del Litoral S.A.", "30-71234567-8", "compras@metlitoral.com.ar", "342-4567890", "Ruta 168 km 4, Santa Fe"),
    ("Distribuidora Santa Fe SRL", "30-70987654-3", "ventas@distsf.com.ar", "342-4112233", "Av. Freyre 2200, Santa Fe"),
    ("Juan Pérez", "20-34567890-1", "jperez@mail.com", "342-5556677", None),
]


def main() -> None:
    app = crear_app()

    with app.app_context():
        db.create_all()

        creados = 0
        for codigo, nombre, descripcion, unidad, precio, stock, minimo in PRODUCTOS:
            if db.session.query(Producto).filter_by(codigo=codigo).first():
                continue

            db.session.add(
                Producto(
                    codigo=codigo,
                    nombre=nombre,
                    descripcion=descripcion,
                    unidad=unidad,
                    precio=Decimal(precio),
                    stock=Decimal(stock),
                    stock_minimo=Decimal(minimo),
                )
            )
            creados += 1

        clientes_creados = 0
        for razon_social, documento, email, telefono, direccion in CLIENTES:
            if db.session.query(Cliente).filter_by(documento=documento).first():
                continue

            db.session.add(
                Cliente(
                    razon_social=razon_social,
                    documento=documento,
                    email=email,
                    telefono=telefono,
                    direccion=direccion,
                )
            )
            clientes_creados += 1

        db.session.commit()

    print(f"Listo: {creados} producto(s) y {clientes_creados} cliente(s) nuevo(s).")


if __name__ == "__main__":
    main()
