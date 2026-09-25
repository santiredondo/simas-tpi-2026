"""Carga productos de ejemplo para poder probar el CRUD:  python semillas.py

No borra lo que ya exista: si el código ya está cargado, lo saltea.
"""

from decimal import Decimal

from erp import crear_app
from erp.extensiones import db
from erp.modelos import Producto

PRODUCTOS = [
    ("PRD-001", "Chapa galvanizada 1x2m", "Espesor 0.9mm", "UNIDAD", "18500.00", "120", "20"),
    ("PRD-002", "Perfil C 100x50", "Barra de 6 metros", "METRO", "9750.50", "300", "50"),
    ("PRD-003", "Tornillo autoperforante", "Caja x 500 unidades", "CAJA", "4200.00", "45", "10"),
    ("PRD-004", "Electrodo 2.5mm", "Caja x 5kg", "KG", "15300.00", "8", "15"),
    ("PRD-005", "Pintura antióxido 4L", "Color gris", "LITRO", "22900.00", "60", "12"),
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

        db.session.commit()

    print(f"Listo: {creados} producto(s) nuevo(s).")


if __name__ == "__main__":
    main()
