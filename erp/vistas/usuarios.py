"""CRUD de Usuarios.

Toda esta sección es exclusiva del rol ADMINISTRADOR: quien administra usuarios
administra los permisos de todo el sistema.
"""

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy import or_, select

from erp.extensiones import db
from erp.modelos import Rol, Usuario
from erp.seguridad import hashear_contrasena, rol_requerido
from erp.validaciones import validar_usuario

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@bp.before_request
@rol_requerido("ADMINISTRADOR")
def solo_administradores():
    """Se aplica a TODAS las rutas del blueprint, incluidas las futuras.

    Protegerlas una por una es frágil: alcanza con olvidarse un decorador.
    """
    return None


def _buscar_usuario(id_usuario: int) -> Usuario:
    return db.get_or_404(Usuario, id_usuario, description="Usuario inexistente")


def _email_repetido(email: str, excluir_id: int | None = None) -> bool:
    consulta = select(Usuario).where(Usuario.email == email)
    if excluir_id is not None:
        consulta = consulta.where(Usuario.id != excluir_id)
    return db.session.scalar(consulta) is not None


def _roles():
    return db.session.scalars(select(Rol).order_by(Rol.nombre)).all()


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------
@bp.get("/")
def listar():
    texto = (request.args.get("q") or "").strip()
    ver = request.args.get("ver", "activos")

    consulta = select(Usuario)

    if ver != "todos":
        consulta = consulta.where(Usuario.activo.is_(True))

    if texto:
        patron = f"%{texto}%"
        consulta = consulta.where(
            or_(Usuario.nombre.like(patron), Usuario.email.like(patron))
        )

    usuarios = db.session.scalars(consulta.order_by(Usuario.nombre)).all()

    return render_template("usuarios/lista.html", usuarios=usuarios, texto=texto, ver=ver)


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------
@bp.route("/nuevo", methods=["GET", "POST"])
def crear():
    if request.method == "GET":
        return render_template(
            "usuarios/formulario.html",
            titulo="Nuevo usuario",
            etiqueta_boton="Crear usuario",
            usuario=None,
            valores={},
            errores={},
            roles=_roles(),
        )

    datos, errores = validar_usuario(request.form, es_alta=True)

    if not errores.get("email") and _email_repetido(datos["email"]):
        errores["email"] = "Ya existe un usuario con ese email"

    if errores:
        return (
            render_template(
                "usuarios/formulario.html",
                titulo="Nuevo usuario",
                etiqueta_boton="Crear usuario",
                usuario=None,
                valores=request.form,
                errores=errores,
                roles=_roles(),
            ),
            400,
        )

    usuario = Usuario(
        nombre=datos["nombre"],
        email=datos["email"],
        rol_id=datos["rol_id"],
        # La contraseña se hashea acá y el texto plano se descarta.
        contrasena_hash=hashear_contrasena(datos["contrasena"]),
    )
    db.session.add(usuario)
    db.session.commit()

    flash(f"Usuario {usuario.email} creado correctamente.", "exito")
    return redirect(url_for("usuarios.listar"))


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------
@bp.route("/<int:id_usuario>/editar", methods=["GET", "POST"])
def editar(id_usuario: int):
    usuario = _buscar_usuario(id_usuario)

    if request.method == "GET":
        return render_template(
            "usuarios/formulario.html",
            titulo="Editar usuario",
            etiqueta_boton="Guardar cambios",
            usuario=usuario,
            # La contraseña no se precarga: no existe en texto plano, solo su hash.
            valores={
                "nombre": usuario.nombre,
                "email": usuario.email,
                "rol_id": usuario.rol_id,
            },
            errores={},
            roles=_roles(),
        )

    datos, errores = validar_usuario(request.form, es_alta=False)

    if not errores.get("email") and _email_repetido(datos["email"], excluir_id=usuario.id):
        errores["email"] = "Ya existe otro usuario con ese email"

    # Un administrador no puede quitarse a sí mismo el rol de administrador:
    # si fuera el único, el sistema quedaría sin nadie que pueda administrarlo.
    if usuario.id == g.usuario.id and datos["rol_id"] != usuario.rol_id:
        errores["rol_id"] = "No podés cambiar tu propio rol"

    if errores:
        return (
            render_template(
                "usuarios/formulario.html",
                titulo="Editar usuario",
                etiqueta_boton="Guardar cambios",
                usuario=usuario,
                valores=request.form,
                errores=errores,
                roles=_roles(),
            ),
            400,
        )

    usuario.nombre = datos["nombre"]
    usuario.email = datos["email"]
    usuario.rol_id = datos["rol_id"]

    # Solo se cambia la contraseña si se escribió una nueva.
    if datos["contrasena"]:
        usuario.contrasena_hash = hashear_contrasena(datos["contrasena"])

    db.session.commit()

    flash(f"Cambios guardados en {usuario.email}.", "exito")
    return redirect(url_for("usuarios.listar"))


# ---------------------------------------------------------------------------
# DELETE — baja lógica
# ---------------------------------------------------------------------------
@bp.route("/<int:id_usuario>/baja", methods=["GET", "POST"])
def baja(id_usuario: int):
    usuario = _buscar_usuario(id_usuario)

    # Darse de baja a uno mismo sería quedarse afuera del sistema en el acto.
    if usuario.id == g.usuario.id:
        flash("No podés darte de baja a vos mismo.", "error")
        return redirect(url_for("usuarios.listar"))

    if request.method == "GET":
        return render_template("usuarios/baja.html", usuario=usuario)

    usuario.activo = False
    db.session.commit()

    flash(f"Usuario {usuario.email} dado de baja.", "exito")
    return redirect(url_for("usuarios.listar"))


@bp.post("/<int:id_usuario>/reactivar")
def reactivar(id_usuario: int):
    usuario = _buscar_usuario(id_usuario)
    usuario.activo = True
    db.session.commit()

    flash(f"Usuario {usuario.email} reactivado.", "exito")
    return redirect(url_for("usuarios.listar", ver="todos"))
