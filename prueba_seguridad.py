"""Pruebas de las defensas de seguridad.

Uso:  python prueba_seguridad.py
"""

import re

from erp import crear_app
from erp.extensiones import db
from erp.modelos import IntentoAcceso, SolicitudRestablecimiento, Usuario
from erp.seguridad import hashear_contrasena

EMAIL = "prueba.seguridad@grupo21.test"
CLAVE = "clave-de-prueba-1"


def token_de(cliente, ruta="/login"):
    """Extrae el token CSRF de un formulario."""
    html = cliente.get(ruta).get_data(as_text=True)
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def ok(numero, texto):
    print(f"  {numero:>2}. {texto}")


def main() -> None:
    app = crear_app()

    with app.app_context():
        # Usuario descartable para no ensuciar los de verdad
        usuario = db.session.query(Usuario).filter_by(email=EMAIL).first()
        if usuario is None:
            rol = db.session.query(Usuario).filter_by(
                email="santiago@grupo21.test"
            ).first().rol_id
            usuario = Usuario(
                nombre="Usuario de prueba", email=EMAIL, rol_id=rol,
                contrasena_hash=hashear_contrasena(CLAVE),
            )
            db.session.add(usuario)
        else:
            usuario.contrasena_hash = hashear_contrasena(CLAVE)
            usuario.activo = True
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.debe_cambiar_contrasena = False
        db.session.commit()
        id_usuario = usuario.id

    cliente = app.test_client()

    print("\n--- CSRF ---")
    respuesta = cliente.post("/login", data={"email": EMAIL, "contrasena": CLAVE})
    assert respuesta.status_code == 400, respuesta.status_code
    ok(1, f"POST sin token CSRF rechazado (HTTP {respuesta.status_code})")

    respuesta = cliente.post(
        "/login", data={"email": EMAIL, "contrasena": CLAVE, "csrf": "token-inventado"}
    )
    assert respuesta.status_code == 400
    ok(2, "POST con token falso rechazado (HTTP 400)")

    csrf = token_de(cliente)
    respuesta = cliente.post(
        "/login", data={"email": EMAIL, "contrasena": CLAVE, "csrf": csrf}
    )
    assert respuesta.status_code == 302, respuesta.status_code
    ok(3, "POST con token válido aceptado (HTTP 302)")
    cliente.post("/logout", data={"csrf": token_de(cliente, "/productos/")})

    print("\n--- Bloqueo por intentos fallidos ---")
    for intento in range(1, 6):
        csrf = token_de(cliente)
        respuesta = cliente.post(
            "/login",
            data={"email": EMAIL, "contrasena": "equivocada", "csrf": csrf},
        )
        assert respuesta.status_code == 401
    ok(4, "5 intentos fallidos seguidos: todos rechazados con HTTP 401")

    with app.app_context():
        usuario = db.session.get(Usuario, id_usuario)
        assert usuario.esta_bloqueado, "La cuenta debería estar bloqueada"
        ok(5, f"Cuenta bloqueada hasta {usuario.bloqueado_hasta:%H:%M:%S}")

    # Ahora ni con la contraseña CORRECTA entra
    csrf = token_de(cliente)
    respuesta = cliente.post(
        "/login", data={"email": EMAIL, "contrasena": CLAVE, "csrf": csrf}
    )
    assert respuesta.status_code == 429, respuesta.status_code
    ok(6, "Con la contraseña correcta tampoco entra mientras dura el bloqueo (HTTP 429)")

    print("\n--- Auditoría de accesos ---")
    with app.app_context():
        intentos = (
            db.session.query(IntentoAcceso)
            .filter_by(email=EMAIL)
            .order_by(IntentoAcceso.id.desc())
            .limit(8)
            .all()
        )
        motivos = [i.motivo or "OK" for i in intentos]
        assert "BLOQUEADO" in motivos and "CONTRASENA" in motivos
        ok(7, f"Quedaron registrados los intentos: {', '.join(reversed(motivos))}")
        assert all(i.direccion_ip for i in intentos)
        ok(8, f"Cada intento guarda la IP de origen ({intentos[0].direccion_ip})")

    print("\n--- Política de contraseñas ---")
    from erp.seguridad import revisar_contrasena

    casos = [
        ("corta", "Debe tener al menos"),
        ("password", "más usadas del mundo"),
        (EMAIL, "igual al email"),
        ("prueba.seguridad", "nombre de usuario"),
    ]
    for contrasena, esperado in casos:
        problema = revisar_contrasena(contrasena, EMAIL)
        assert problema and esperado in problema, (contrasena, problema)
    ok(9, "Rechaza: contraseña corta, común, igual al email e igual al usuario")
    assert revisar_contrasena("roble-nieve-lago-42", EMAIL) is None
    ok(10, "Acepta una contraseña razonable")

    print("\n--- Recuperación de contraseña ---")
    with app.app_context():
        usuario = db.session.get(Usuario, id_usuario)
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        db.session.commit()

    cliente2 = app.test_client()
    csrf = token_de(cliente2, "/recuperar")
    html = cliente2.post(
        "/recuperar", data={"email": EMAIL, "csrf": csrf}
    ).get_data(as_text=True)
    assert "Si" in html and EMAIL in html
    ok(11, "Pedido registrado, con respuesta genérica")

    csrf = token_de(cliente2, "/recuperar")
    html = cliente2.post(
        "/recuperar", data={"email": "no-existe@grupo21.test", "csrf": csrf}
    ).get_data(as_text=True)
    assert "un administrador" in html
    ok(12, "Un email inexistente recibe EXACTAMENTE la misma respuesta")

    with app.app_context():
        pendiente = (
            db.session.query(SolicitudRestablecimiento)
            .filter_by(email=EMAIL, atendida=False)
            .first()
        )
        assert pendiente is not None
        inexistente = (
            db.session.query(SolicitudRestablecimiento)
            .filter_by(email="no-existe@grupo21.test")
            .first()
        )
        assert inexistente is None
        ok(13, "Solo se registra la solicitud si la cuenta existe (la respuesta no lo delata)")

    print("\nTodas las comprobaciones pasaron.\n")


if __name__ == "__main__":
    main()
