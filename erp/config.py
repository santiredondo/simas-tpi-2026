"""Configuración de la aplicación, leída del entorno."""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root@localhost:3306/erp_grupo21_flask",
    )
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-insegura-solo-para-desarrollo")

    # Reconecta si MariaDB cortó una conexión ociosa, en vez de fallar la request.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # ----- Caducidad de sesión -----
    # Una sesión abandonada es una puerta abierta: si alguien deja el sistema
    # abierto en una máquina compartida del depósito, a los 30 minutos sin
    # actividad deja de servir.
    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=int(os.getenv("MINUTOS_SESION", "30"))
    )
    # El plazo se renueva con cada pedido: cuenta la inactividad, no el tiempo
    # total conectado. Trabajar ocho horas seguidas no obliga a reloguearse.
    SESSION_REFRESH_EACH_REQUEST = True

    # ----- Protección de la cookie de sesión -----
    # JavaScript no puede leerla: aunque se cuele un script en una página,
    # no puede robar la sesión.
    SESSION_COOKIE_HTTPONLY = True
    # No se envía cuando el pedido viene de otro sitio: frena los ataques CSRF
    # más simples (un formulario escondido en otra página).
    SESSION_COOKIE_SAMESITE = "Lax"
    # Solo por HTTPS. En desarrollo va en False porque se usa http://localhost.
    SESSION_COOKIE_SECURE = os.getenv("COOKIE_SEGURA", "false").lower() == "true"
