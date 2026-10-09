"""Carga datos de ejemplo para poder probar el sistema:  python semillas.py

No borra lo que ya exista: si el registro ya está cargado, lo saltea.
"""

from decimal import Decimal

from erp import crear_app
from erp.extensiones import db
from erp.modelos import Cliente, Producto, Rol, Usuario
from erp.seguridad import hashear_contrasena

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

ROLES = [
    ("ADMINISTRADOR", "Acceso total, incluida la administración de usuarios"),
    ("VENDEDOR", "Registra ventas y gestiona clientes"),
    ("COMPRADOR", "Gestiona productos y repone stock"),
]

# Usuarios iniciales. Las contraseñas son de desarrollo y DEBEN cambiarse:
# el sistema obliga a cargarlas de nuevo porque solo guarda su hash.
USUARIOS = [
    ("Administrador", "admin@grupo21.test", "ADMINISTRADOR", "admin1234"),
    ("Vendedor de prueba", "vendedor@grupo21.test", "VENDEDOR", "vendedor1234"),
]


def main() -> None:
    app = crear_app()

    with app.app_context():
        db.create_all()

        # --- Roles (primero: los usuarios dependen de ellos) ---
        roles_creados = 0
        for nombre, descripcion in ROLES:
            if db.session.query(Rol).filter_by(nombre=nombre).first():
                continue
            db.session.add(Rol(nombre=nombre, descripcion=descripcion))
            roles_creados += 1
        db.session.commit()

        # --- Usuarios ---
        usuarios_creados = 0
        for nombre, email, nombre_rol, contrasena in USUARIOS:
            if db.session.query(Usuario).filter_by(email=email).first():
                continue

            rol = db.session.query(Rol).filter_by(nombre=nombre_rol).first()
            db.session.add(
                Usuario(
                    nombre=nombre,
                    email=email,
                    rol_id=rol.id,
                    contrasena_hash=hashear_contrasena(contrasena),
                )
            )
            usuarios_creados += 1

        # --- Productos ---
        productos_creados = 0
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
            productos_creados += 1

        # --- Clientes ---
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

    print(
        f"Listo: {roles_creados} rol(es), {usuarios_creados} usuario(s), "
        f"{productos_creados} producto(s) y {clientes_creados} cliente(s)."
    )
    if usuarios_creados:
        print("\nUsuarios de prueba (cambiar estas contraseñas):")
        for nombre, email, nombre_rol, contrasena in USUARIOS:
            print(f"  {email}  /  {contrasena}   ({nombre_rol})")


if __name__ == "__main__":
    main()
