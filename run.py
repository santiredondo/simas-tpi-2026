"""Punto de entrada para desarrollo:  python run.py"""

from erp import crear_app

app = crear_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
