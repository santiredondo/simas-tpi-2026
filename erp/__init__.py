"""Fábrica de la aplicación Flask.

Se usa el patrón "application factory" (crear la app dentro de una función) para
poder levantar instancias distintas: una para desarrollo y otra para los tests,
cada una con su propia configuración.
"""

from decimal import Decimal

from flask import Flask

from erp.config import Config
from erp.extensiones import db


def crear_app(config=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)

    # Los modelos se importan acá para que SQLAlchemy los registre antes de
    # crear las tablas.
    from erp import modelos  # noqa: F401
    from erp.vistas import clientes, productos

    app.register_blueprint(productos.bp)
    app.register_blueprint(clientes.bp)

    @app.get("/")
    def inicio():
        from flask import redirect, url_for

        return redirect(url_for("productos.listar"))

    @app.template_filter("pesos")
    def formato_pesos(valor: Decimal | float | None) -> str:
        """Formatea un número como moneda argentina: $18.500,00"""
        if valor is None:
            return "-"
        entero, _, decimales = f"{Decimal(valor):.2f}".partition(".")
        miles = f"{int(entero):,}".replace(",", ".")
        return f"${miles},{decimales}"

    @app.template_filter("cantidad")
    def formato_cantidad(valor: Decimal | float | None) -> str:
        """Muestra 110 en lugar de 110.00, pero conserva los decimales si los hay."""
        if valor is None:
            return "-"
        numero = Decimal(valor)
        return str(numero.quantize(Decimal(1)) if numero == numero.to_integral() else numero)

    @app.cli.command("init-db")
    def init_db():
        """Crea las tablas en MariaDB: `flask --app erp init-db`"""
        with app.app_context():
            db.create_all()
        print("Tablas creadas.")

    return app
