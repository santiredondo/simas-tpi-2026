"""Autenticación y control de acceso.

Dos ideas centrales:

1. **La contraseña nunca se guarda.** Se guarda su *hash*: el resultado de una
   función de una sola dirección. Se puede verificar si una contraseña coincide,
   pero no se puede recuperar la original a partir del hash. Si alguien roba la
   base de datos, no obtiene las contraseñas.

2. **Cada hash lleva su propio "salt"** (un valor aleatorio). Por eso dos
   usuarios con la misma contraseña tienen hashes distintos, y no se puede
   deducir que la comparten.
"""

from functools import wraps

from flask import flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from erp.extensiones import db
from erp.modelos import Usuario

# scrypt es deliberadamente lento y usa mucha memoria: encarece los ataques de
# fuerza bruta, que prueban millones de contraseñas por segundo.
METODO_HASH = "scrypt"

LARGO_MINIMO_CONTRASENA = 8


def hashear_contrasena(contrasena: str) -> str:
    """Convierte la contraseña en un hash con salt. Operación de una sola vía."""
    return generate_password_hash(contrasena, method=METODO_HASH)


def verificar_contrasena(hash_guardado: str, contrasena: str) -> bool:
    """Compara una contraseña tecleada contra el hash guardado."""
    return check_password_hash(hash_guardado, contrasena)


# ---------------------------------------------------------------------------
# Sesión
# ---------------------------------------------------------------------------
def iniciar_sesion(usuario: Usuario) -> None:
    """Guarda el id del usuario en la cookie de sesión (firmada por Flask)."""
    session.clear()
    session["usuario_id"] = usuario.id
    session.permanent = True


def cerrar_sesion() -> None:
    session.clear()


def cargar_usuario_actual() -> None:
    """Deja el usuario logueado en `g.usuario`, o None.

    Se ejecuta antes de cada request. Si el usuario fue dado de baja mientras
    tenía la sesión abierta, se lo desloguea: el permiso se verifica en cada
    pedido, no solo al entrar.
    """
    usuario_id = session.get("usuario_id")
    g.usuario = None

    if usuario_id is None:
        return

    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None or not usuario.activo:
        session.clear()
        return

    g.usuario = usuario


# ---------------------------------------------------------------------------
# Decoradores de protección
# ---------------------------------------------------------------------------
def login_requerido(vista):
    """Exige sesión iniciada. Recuerda a dónde iba para volver después del login."""

    @wraps(vista)
    def envoltura(*args, **kwargs):
        if g.get("usuario") is None:
            flash("Iniciá sesión para continuar.", "error")
            return redirect(url_for("auth.login", siguiente=request.path))
        return vista(*args, **kwargs)

    return envoltura


def rol_requerido(*roles_permitidos: str):
    """Exige además que el rol del usuario esté entre los permitidos.

    El control vive en el servidor: esconder un botón en la interfaz no es
    seguridad, porque la URL se puede escribir a mano.
    """

    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            usuario = g.get("usuario")

            if usuario is None:
                flash("Iniciá sesión para continuar.", "error")
                return redirect(url_for("auth.login", siguiente=request.path))

            if usuario.rol.nombre not in roles_permitidos:
                flash("No tenés permisos para esa sección.", "error")
                return redirect(url_for("productos.listar"))

            return vista(*args, **kwargs)

        return envoltura

    return decorador
