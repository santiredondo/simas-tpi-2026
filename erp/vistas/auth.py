"""Autenticación: ingreso y salida del sistema."""

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy import select

from erp.extensiones import db
from erp.modelos import Usuario, ahora
from erp.seguridad import cerrar_sesion, iniciar_sesion, verificar_contrasena

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

    # Mensaje genérico a propósito: decir "ese email no existe" le confirmaría
    # a un atacante qué cuentas son válidas.
    credenciales_validas = (
        usuario is not None
        and usuario.activo
        and verificar_contrasena(usuario.contrasena_hash, contrasena)
    )

    if not credenciales_validas:
        return (
            render_template(
                "auth/login.html",
                siguiente=siguiente,
                email=email,
                error="Email o contraseña incorrectos.",
            ),
            401,
        )

    usuario.ultimo_acceso = ahora()
    db.session.commit()

    iniciar_sesion(usuario)
    flash(f"Hola, {usuario.nombre}.", "exito")

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
