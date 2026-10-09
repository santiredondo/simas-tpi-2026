# simas-tpi-2026 — Team grupo21

ERP con IA · Trabajo Práctico Integrador · **Sistemas de Información para Manufactura (SIMA)** · 2026

## Team

**grupo21**

## Integrantes

| Nombre y apellido | Legajo | GitHub |
| --- | --- | --- |
| Santiago Redondo | _a completar_ | [@santiredondo](https://github.com/santiredondo) |
| Lautaro Rizzi | _a completar_ | [@lautarorizzi1996-dot](https://github.com/lautarorizzi1996-dot) |
| David Bustamante | _a completar_ | [@dmb824](https://github.com/dmb824) |

---

## Stack

| Capa | Tecnología |
| --- | --- |
| Lenguaje | Python 3.11 |
| Framework web | Flask 3.1 |
| ORM | SQLAlchemy (vía Flask-SQLAlchemy) |
| Base de datos | MariaDB 13 |
| Plantillas | Jinja2 + CSS propio |

---

## Cómo levantarlo

**1. Requisitos**: Python 3.11+ y MariaDB instalados.

**2. Crear la base de datos** (una sola vez):

```sql
CREATE DATABASE erp_grupo21_flask CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**3. Preparar el entorno** (desde la carpeta del proyecto, un comando por vez):

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

**4. Editar `.env`** con tu usuario y contraseña de MariaDB.

**5. Crear las tablas y cargar datos de ejemplo**:

```
python semillas.py
```

**6. Levantar el servidor**:

```
python run.py
```

Abrir http://localhost:5000

**Usuarios de desarrollo** — uno por integrante. Los crea `semillas.py`:

| Integrante | Email | Contraseña | Rol |
| --- | --- | --- | --- |
| Santiago | `santiago@grupo21.test` | `grupo21.santiago` | Administrador |
| Lautaro | `lautaro@grupo21.test` | `grupo21.lautaro` | Vendedor |
| David | `david@grupo21.test` | `grupo21.david` | Comprador |

> Son credenciales **de desarrollo local**, pensadas para probar el sistema en
> la máquina de cada uno. Si algún día esto se publica en internet, hay que
> cambiarlas: están escritas en un archivo del repositorio.

---

## Estructura

```
erp/
  __init__.py        fábrica de la aplicación y filtros de plantilla
  config.py          configuración leída del .env
  extensiones.py     instancia de SQLAlchemy
  modelos.py         modelos de datos
  validaciones.py    validación de formularios
  servicios.py       reglas de negocio de ventas (stock, confirmación, anulación)
  seguridad.py       hash de contraseñas, sesión y control de acceso por rol
  vistas/
    productos.py     CRUD de productos (blueprint)
    clientes.py      CRUD de clientes (blueprint)
    ventas.py        registro de ventas (blueprint)
    usuarios.py      CRUD de usuarios (blueprint, solo administradores)
    auth.py          ingreso y salida del sistema
  templates/         plantillas Jinja2
  static/            estilos
docs/                modelado de procesos, diseño y decisiones técnicas
sql/                 script MariaDB del flujo de venta (checkpoint 4)
run.py               punto de entrada
semillas.py          datos de ejemplo
```

---

## Avance

| Entrega | Estado |
| --- | --- |
| Entregable 1 — repo, team y README | ✅ |
| Modelado de procesos | ✅ [docs/modelado-de-procesos.md](docs/modelado-de-procesos.md) |
| Checkpoint 4 — script MariaDB del flujo de venta | ✅ [sql/erp_ventas_mariadb.sql](sql/erp_ventas_mariadb.sql) |
| Workshop 3 · Checkpoint 1 — campos y pantallas | ✅ [docs/crud-productos-diseno.md](docs/crud-productos-diseno.md) |
| Workshop 3 · Checkpoint 2 — CRUD generado e iterado | ✅ [docs/crud-productos-iteracion.md](docs/crud-productos-iteracion.md) |
| Workshop 3 — CRUD de Productos | ✅ |
| Módulo de clientes | ✅ |
| Registro de ventas (con descuento de stock) | ✅ |
| Registro de compras | ⬜ |
| Workshop 4 · Checkpoint 1 — campos de usuario y autenticación | ✅ [docs/usuarios-y-autenticacion.md](docs/usuarios-y-autenticacion.md) |
| Administración de usuarios + login | ✅ |
| IA — sugerencia de reposición | ⬜ |
