"""Autenticación: ingreso, salida y cambio de contraseña."""

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy import select

from erp.extensiones import db
from erp.modelos import SolicitudRestablecimiento, Usuario, ahora
from erp.seguridad import (
    MINUTOS_DE_BLOQUEO,
    cerrar_sesion,
    contar_fallo,
    hashear_contrasena,
    iniciar_sesion,
    limpiar_fallos,
    registrar_intento,
    revisar_contrasena,
    verificar_contrasena,
)

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.get("usuario") is not None:
        return redirect(url_for("productos.listar"))

    siguiente = request.args.get("siguiente") or request.form.get("siguiente") or ""

    if request.method == "GET":
        return render_template("auth/login.html", siguiente=siguiente, email="")

    email = (request.form.get("email") or "").strip().lower()
    contrasena = request.form.get("contrasena") or ""

    usuario = db.session.scalar(select(Usuario).where(Usuario.email == email))

    def rechazar(motivo: str, mensaje: str, codigo: int = 401):
        registrar_intento(email, exitoso=False, motivo=motivo)
        return (
            render_template(
                "auth/login.html", siguiente=siguiente, email=email, error=mensaje
            ),
            codigo,
        )

    # El mensaje es el mismo para email inexistente y contraseña equivocada:
    # distinguirlos le confirmaría a un atacante qué cuentas son válidas.
    MENSAJE_GENERICO = "Email o contraseña incorrectos."

    if usuario is None:
        return rechazar("INEXISTENTE", MENSAJE_GENERICO)

    if not usuario.activo:
        return rechazar("INACTIVO", MENSAJE_GENERICO)

    # El bloqueo sí se avisa: quien lo sufre necesita saber por qué no entra,
    # y para ese punto el atacante ya sabe que la cuenta existe.
    if usuario.esta_bloqueado:
        return rechazar(
            "BLOQUEADO",
            f"Cuenta bloqueada por intentos fallidos. Probá de nuevo en "
            f"{MINUTOS_DE_BLOQUEO} minutos.",
            429,
        )

    if not verificar_contrasena(usuario.contrasena_hash, contrasena):
        contar_fallo(usuario)
        registrar_intento(email, exitoso=False, motivo="CONTRASENA")

        if usuario.esta_bloqueado:
            mensaje = (
                f"Demasiados intentos fallidos. La cuenta queda bloqueada "
                f"{MINUTOS_DE_BLOQUEO} minutos."
            )
        else:
            restantes = 5 - usuario.intentos_fallidos
            mensaje = f"{MENSAJE_GENERICO} Te quedan {restantes} intento(s)."

        return (
            render_template(
                "auth/login.html", siguiente=siguiente, email=email, error=mensaje
            ),
            401,
        )

    # --- Ingreso exitoso ---
    acceso_anterior = usuario.ultimo_acceso  # se guarda antes de pisarlo

    limpiar_fallos(usuario)
    usuario.ultimo_acceso = ahora()
    db.session.commit()

    registrar_intento(email, exitoso=True)
    iniciar_sesion(usuario)

    flash(f"Hola, {usuario.nombre}.", "exito")

    # Mostrar el acceso anterior permite que el propio usuario detecte un
    # ingreso que no hizo: es la defensa más barata que existe.
    if acceso_anterior is not None:
        flash(
            f"Tu acceso anterior fue el {acceso_anterior.strftime('%d/%m/%Y a las %H:%M')}.",
            "info",
        )

    if usuario.debe_cambiar_contrasena:
        return redirect(url_for("auth.cambiar_contrasena"))

    # Solo se acepta una ruta interna: un `siguiente` con http:// externo
    # permitiría usar el login para redirigir a un sitio de phishing.
    if siguiente.startswith("/") and not siguiente.startswith("//"):
        return redirect(siguiente)

    return redirect(url_for("productos.listar"))


@bp.post("/logout")
def logout():
    cerrar_sesion()
    flash("Sesión cerrada.", "exito")
    return redirect(url_for("auth.login"))


@bp.route("/cambiar-contrasena", methods=["GET", "POST"])
def cambiar_contrasena():
    """Cambio de contraseña propio.

    Obligatorio en el primer ingreso cuando un administrador asignó una
    provisoria, y disponible en cualquier momento desde la barra superior.
    """
    usuario = g.usuario

    if request.method == "GET":
        return render_template("auth/cambiar_contrasena.html", errores={})

    actual = request.form.get("contrasena_actual") or ""
    nueva = request.form.get("contrasena_nueva") or ""
    repetir = request.form.get("repetir_contrasena") or ""

    errores: dict[str, str] = {}

    # Se pide la actual aunque ya tenga sesión: si alguien se sentó frente a
    # una pantalla desbloqueada, que no pueda apropiarse de la cuenta.
    if not verificar_contrasena(usuario.contrasena_hash, actual):
        errores["contrasena_actual"] = "La contraseña actual no es correcta"

    problema = revisar_contrasena(nueva, usuario.email)
    if problema:
        errores["contrasena_nueva"] = problema
    elif nueva != repetir:
        errores["repetir_contrasena"] = "Las contraseñas no coinciden"
    elif verificar_contrasena(usuario.contrasena_hash, nueva):
        errores["contrasena_nueva"] = "La nueva contraseña no puede ser igual a la actual"

    if errores:
        return render_template("auth/cambiar_contrasena.html", errores=errores), 400

    usuario.contrasena_hash = hashear_contrasena(nueva)
    usuario.debe_cambiar_contrasena = False
    db.session.commit()

    flash("Contraseña actualizada.", "exito")
    return redirect(url_for("productos.listar"))


@bp.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    """Pedido de restablecimiento de contraseña.

    Es una ruta pública: la usa justamente quien no puede entrar.
    """
    if request.method == "GET":
        return render_template("auth/recuperar.html")

    email = (request.form.get("email") or "").strip().lower()
    usuario = db.session.scalar(select(Usuario).where(Usuario.email == email))

    # Se registra el pedido solo si la cuenta existe, pero la respuesta es
    # SIEMPRE la misma: si dijéramos "ese email no está registrado",
    # cualquiera podría averiguar quiénes tienen cuenta en el sistema.
    if usuario is not None and usuario.activo:
        pendiente = db.session.scalar(
            select(SolicitudRestablecimiento).where(
                SolicitudRestablecimiento.usuario_id == usuario.id,
                SolicitudRestablecimiento.atendida.is_(False),
            )
        )
        if pendiente is None:
            db.session.add(
                SolicitudRestablecimiento(email=email, usuario_id=usuario.id)
            )
            db.session.commit()

    return render_template("auth/recuperar.html", enviado=True, email=email)
