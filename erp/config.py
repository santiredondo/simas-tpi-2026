"""Configuración de la aplicación, leída del entorno."""

import os

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
