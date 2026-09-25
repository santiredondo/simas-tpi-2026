"""Instancias compartidas de las extensiones de Flask.

Viven en su propio módulo para evitar imports circulares: los modelos importan
`db` desde acá, y la fábrica de la aplicación lo inicializa con la app ya creada.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
