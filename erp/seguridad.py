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

import secrets
from datetime import timedelta
from functools import wraps

from flask import abort, flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from erp.extensiones import db
from erp.modelos import IntentoAcceso, Usuario, ahora

# scrypt es deliberadamente lento y usa mucha memoria: encarece los ataques de
# fuerza bruta, que prueban millones de contraseñas por segundo.
METODO_HASH = "scrypt"

LARGO_MINIMO_CONTRASENA = 8

# Tras este número de fallos seguidos, la cuenta se bloquea un rato. No es un
# castigo: es lo que vuelve inviable probar contraseñas de a millones.
INTENTOS_ANTES_DE_BLOQUEAR = 5
MINUTOS_DE_BLOQUEO = 15

# Las contraseñas más usadas del mundo: las primeras que prueba cualquier ataque.
CONTRASENAS_PROHIBIDAS = {
    "12345678", "123456789", "1234567890", "password", "contrasena",
    "qwertyui", "11111111", "00000000", "admin123", "administrador",
    "password1", "contraseña", "bienvenido", "12345678910",
}


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


# ---------------------------------------------------------------------------
# Política de contraseñas
# ---------------------------------------------------------------------------
def revisar_contrasena(contrasena: str, email: str = "") -> str | None:
    """Devuelve el motivo del rechazo, o None si la contraseña es aceptable.

    No se exige "una mayúscula, un número y un símbolo": esa regla empuja a la
    gente a usar "Password1!" y anotarla en un papel. Se exige largo y que no
    sea adivinable.
    """
    if len(contrasena) < LARGO_MINIMO_CONTRASENA:
        return f"Debe tener al menos {LARGO_MINIMO_CONTRASENA} caracteres"

    if contrasena.lower() in CONTRASENAS_PROHIBIDAS:
        return "Esa contraseña es de las más usadas del mundo: elegí otra"

    if email and contrasena.lower() == email.lower():
        return "La contraseña no puede ser igual al email"

    if email and "@" in email and contrasena.lower() == email.split("@")[0].lower():
        return "La contraseña no puede ser tu nombre de usuario"

    return None


# ---------------------------------------------------------------------------
# Bloqueo por intentos fallidos
# ---------------------------------------------------------------------------
def registrar_intento(email: str, exitoso: bool, motivo: str | None = None) -> None:
    """Asienta el intento de ingreso en la auditoría."""
    db.session.add(
        IntentoAcceso(
            email=email[:150],
            exitoso=exitoso,
            motivo=motivo,
            # Si hay un proxy delante, la IP real viaja en X-Forwarded-For.
            direccion_ip=(request.headers.get("X-Forwarded-For") or request.remote_addr or "")[:45],
        )
    )
    db.session.commit()


def contar_fallo(usuario: Usuario) -> None:
    """Suma un fallo y bloquea la cuenta si se pasó del tope."""
    usuario.intentos_fallidos += 1

    if usuario.intentos_fallidos >= INTENTOS_ANTES_DE_BLOQUEAR:
        usuario.bloqueado_hasta = ahora() + timedelta(minutes=MINUTOS_DE_BLOQUEO)

    db.session.commit()


def limpiar_fallos(usuario: Usuario) -> None:
    """Un ingreso exitoso borra el historial de fallos."""
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    db.session.commit()


# ---------------------------------------------------------------------------
# Protección CSRF
# ---------------------------------------------------------------------------
# Un sitio malicioso puede hacer que TU navegador envíe un formulario a nuestra
# aplicación usando tu sesión abierta (por ejemplo, dar de baja un producto).
# El token es un valor secreto que ese sitio no puede conocer: sin él, el
# pedido se rechaza.

def token_csrf() -> str:
    """Devuelve el token de la sesión, creándolo la primera vez."""
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def validar_csrf() -> None:
    """Corta el pedido con 400 si el token no coincide."""
    enviado = request.form.get("csrf") or request.headers.get("X-CSRF-Token")
    esperado = session.get("csrf")

    # compare_digest: la comparación tarda lo mismo acierte o falle, para no
    # filtrar información por el tiempo de respuesta.
    if not esperado or not enviado or not secrets.compare_digest(enviado, esperado):
        abort(400, description="Token de seguridad inválido o vencido. Recargá la página.")


def generar_contrasena_provisoria() -> str:
    """Contraseña provisoria legible, para dictarla por teléfono sin errores.

    Se arma con palabras y un número en lugar de caracteres al azar: "casa-
    perro-47" se transmite sin confundir ceros con oes ni eles con unos, y
    como se cambia en el primer ingreso, no necesita ser memorable.
    """
    palabras = [
        "lima", "roble", "cedro", "arena", "nube", "rio", "monte", "pino",
        "sauce", "trigo", "menta", "cobre", "jade", "nieve", "lago", "soja",
    ]
    elegidas = "-".join(secrets.choice(palabras) for _ in range(3))
    return f"{elegidas}-{secrets.randbelow(90) + 10}"
