"""Prueba de caducidad de sesión.

Levanta la aplicación con una sesión que vence en 2 segundos y comprueba que,
pasado ese plazo sin actividad, el sistema deja de reconocer al usuario.

Uso:  python prueba_caducidad.py
"""

import time
from datetime import timedelta

from erp import crear_app
from erp.config import Config


class ConfigCorta(Config):
    """Misma configuración, pero con la sesión venciendo en 2 segundos."""

    PERMANENT_SESSION_LIFETIME = timedelta(seconds=2)


def main() -> None:
    app = crear_app(ConfigCorta)
    cliente = app.test_client()

    print("1. Ingreso al sistema...")
    respuesta = cliente.post(
        "/login",
        data={"email": "santiago@grupo21.test", "contrasena": "grupo21.santiago"},
    )
    assert respuesta.status_code == 302, "El login debería redirigir"
    print(f"   OK — redirige a {respuesta.headers['Location']}")

    print("2. Navego enseguida: la sesión está viva...")
    respuesta = cliente.get("/productos/")
    assert respuesta.status_code == 200, "Debería entrar sin problema"
    print(f"   OK — HTTP {respuesta.status_code}")

    print("3. Espero 3 segundos sin actividad (la sesión vence a los 2)...")
    time.sleep(3)

    print("4. Vuelvo a navegar: la sesión tiene que haber caducado...")
    respuesta = cliente.get("/productos/")
    assert respuesta.status_code == 302, "La sesión vencida debería redirigir al login"
    assert "/login" in respuesta.headers["Location"], "Debería mandar al login"
    print(f"   OK — HTTP {respuesta.status_code} -> {respuesta.headers['Location']}")

    print("\n5. Control: con actividad constante la sesión NO vence...")
    cliente.post(
        "/login",
        data={"email": "santiago@grupo21.test", "contrasena": "grupo21.santiago"},
    )
    for intento in range(4):
        time.sleep(1)
        respuesta = cliente.get("/productos/")
        estado = "viva" if respuesta.status_code == 200 else "caducada"
        print(f"   segundo {intento + 1}: sesión {estado} (HTTP {respuesta.status_code})")
        assert respuesta.status_code == 200, "La actividad debería renovar el plazo"

    print("\nTodas las comprobaciones pasaron.")


if __name__ == "__main__":
    main()
