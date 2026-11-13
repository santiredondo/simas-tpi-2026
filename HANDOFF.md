# HANDOFF — Contexto para continuar el proyecto

**Leé este archivo primero.** Está escrito para que alguien que no participó —persona o asistente de IA— pueda retomar el proyecto sin romper lo que ya funciona.

---

## 1. Qué es esto

ERP web para una empresa de manufactura, desarrollado como Trabajo Práctico Integrador de la materia **Sistemas de Información para Manufactura (SIMA)**, cursada 2026, en la Facultad de Ingeniería Química de la UNL.

- **Equipo:** grupo21 — Santiago Redondo, Lautaro Rizzi, David Bustamante
- **Repositorio:** https://github.com/santiredondo/simas-tpi-2026
- **Rama de trabajo:** `team/entregable2` (no `main`)

### La idea que ordena todo el diseño

Un ERP no es un conjunto de formularios: es un sistema que tiene que poder **rendir cuentas**. Cada número debe poder explicarse — por qué este producto tiene 110 unidades y no 120, quién registró esta venta, cuándo se dio de baja ese cliente.

Esa exigencia determinó casi todas las decisiones que siguen. Si vas a cambiar algo, tenelo presente.

---

## 2. Estado actual

| Módulo | Estado | Pruebas |
| --- | --- | --- |
| CRUD de productos | Terminado | 11 (manuales, documentadas) |
| CRUD de clientes | Terminado | incluidas en las 21 de ventas |
| Registro de ventas con descuento de stock | Terminado | 21 automatizadas |
| Usuarios, roles y autenticación | Terminado | 29 (manuales) + 13 automatizadas |
| Caducidad de sesión | Terminado | 5 automatizadas |
| **Registro de compras** | **Pendiente** | — |
| **IA: sugerencia de reposición** | **Pendiente** | — |
| Publicación en internet | Pendiente | — |

### Entregas de la cátedra ya cumplidas

| Entrega | Documento |
| --- | --- |
| Modelado de procesos | `docs/modelado-de-procesos.md` |
| Script MariaDB del flujo de venta | `sql/erp_ventas_mariadb.sql` |
| Workshop 3 — CRUD de productos | `docs/crud-productos-diseno.md`, `docs/crud-productos-iteracion.md` |
| Workshop 4 — usuarios y autenticación | `docs/usuarios-y-autenticacion.md` |
| Workshop 5 CP1 — clientes y ventas | `docs/clientes-y-ventas-diseno.md` |
| Workshop 5 CP2 — resumen y multimedia | `docs/resumen-erp.md`, `docs/guia-notebooklm.md` |

---

## 3. Stack y estructura

Python 3.11 · Flask 3.1 · SQLAlchemy (Flask-SQLAlchemy) · MariaDB 13 · Jinja2 · CSS propio.

```
erp/
  __init__.py        fábrica de la aplicación, filtros de plantilla y el
                     before_request que controla TODO el acceso
  config.py          configuración leída del .env
  extensiones.py     instancia de SQLAlchemy (vive sola para evitar imports circulares)
  modelos.py         los 9 modelos de datos
  validaciones.py    validación de formularios (devuelve datos limpios + errores por campo)
  servicios.py       reglas de negocio de ventas: confirmar, anular, mover stock
  seguridad.py       hash, sesión, roles, CSRF, bloqueo y política de contraseñas
  vistas/
    productos.py     CRUD de productos
    clientes.py      CRUD de clientes
    ventas.py        registro de ventas
    usuarios.py      CRUD de usuarios (solo ADMINISTRADOR)
    auth.py          login, logout, recuperación y cambio de contraseña
  templates/         plantillas Jinja2
  static/estilos.css
docs/                toda la documentación entregada a la cátedra
sql/                 script MariaDB del flujo de venta (entrega aparte)
run.py               punto de entrada
semillas.py          datos de ejemplo (roles, usuarios, productos, clientes)
prueba_ventas.py     21 comprobaciones del flujo de ventas
prueba_seguridad.py  13 comprobaciones de las defensas
prueba_caducidad.py   5 comprobaciones de la caducidad de sesión
```

### Dónde va cada cosa

| Si vas a... | Tocá |
| --- | --- |
| Agregar una pantalla | `vistas/` + `templates/` |
| Cambiar una regla de negocio de ventas | `servicios.py` |
| Agregar una validación de formulario | `validaciones.py` |
| Agregar un campo o tabla | `modelos.py` (y migrar, ver sección 6) |
| Tocar permisos o seguridad | `seguridad.py` |

**Las reglas de negocio NO van en las vistas.** Están en `servicios.py` a propósito: se pueden probar sin levantar el servidor y no se duplican si mañana se agrega una API.

---

## 4. Las reglas que no se negocian

Si rompés alguna de estas, rompés el diseño entero.

### 4.1 Nada se borra

Productos, clientes y usuarios tienen `activo: bool`. **Nunca `DELETE`.** Si se borraran, las ventas que los referencian quedarían apuntando a la nada. Las claves foráneas usan `ON DELETE RESTRICT` para que la base misma lo impida.

### 4.2 El stock está duplicado a propósito

`producto.stock` guarda el valor actual y la tabla `movimiento_stock` guarda el historial completo.

**Invariante: nunca modifiques `producto.stock` sin insertar el movimiento correspondiente, y siempre dentro de la misma transacción.** Esa regla es la que hace auditable al sistema.

### 4.3 Lo confirmado no se edita

Una venta confirmada no se corrige: se **anula** (genera movimientos inversos) y se hace otra. Un historial que se puede reescribir hacia atrás no sirve para rendir cuentas.

### 4.4 El precio se congela en el renglón

`linea_venta.precio_unitario` es una **copia** del precio del producto al momento de la venta, no una referencia. Si mañana sube el precio, las ventas de ayer siguen valiendo lo que valieron.

### 4.5 Decimal, nunca float

Todos los montos y cantidades usan `Numeric(12, 2)`. Los float arrastran errores de redondeo.

### 4.6 Validación en tres capas

El HTML avisa, Python valida de verdad, la base rechaza con `CHECK` y claves foráneas. Que el precio deba ser mayor a cero está escrito tres veces a propósito: cada capa cubre una vía distinta de entrada.

### 4.7 La seguridad vive en el servidor

Esconder un botón en la interfaz **no es seguridad**: la URL se puede escribir a mano. Toda ruta protegida se valida en el servidor (`before_request` en `__init__.py` + decorador `rol_requerido`).

### 4.8 Las contraseñas no se guardan

Se guarda su hash scrypt con salt por usuario. No existe forma de recuperarlas, ni siquiera para un administrador. Es intencional.

---

## 5. Cómo levantarlo

**Requisitos:** Python 3.11+ y MariaDB (o MySQL) instalados.

```bash
# 1. Crear la base
mysql -u root -p < database/erp_script_grupo_21.sql

# 2. Entorno virtual (un comando por vez en PowerShell)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Configuración
copy .env.example .env
#    editar .env con el usuario y contraseña de MariaDB

# 4. Datos de ejemplo y arranque
python semillas.py
python run.py
```

Abrir http://localhost:5000

### Usuarios de desarrollo

| Email | Contraseña | Rol |
| --- | --- | --- |
| `santiago@grupo21.test` | `grupo21.santiago` | Administrador |
| `lautaro@grupo21.test` | `grupo21.lautaro` | Vendedor |
| `david@grupo21.test` | `grupo21.david` | Comprador |

Son credenciales **de desarrollo local**. Si esto alguna vez se publica, hay que cambiarlas.

### Verificar que todo anda

```bash
python prueba_ventas.py       # 21 comprobaciones
python prueba_seguridad.py    # 13 comprobaciones
python prueba_caducidad.py    #  5 comprobaciones
```

Las tres se pueden correr las veces que haga falta: crean sus propios datos y los dejan desactivados al terminar.

---

## 6. Trampas conocidas

Cosas que ya nos hicieron perder tiempo. Leelas antes de tocar código.

### 6.1 Las fechas van sin zona horaria

`modelos.py` define `ahora()`, que devuelve UTC **sin** `tzinfo`.

El tipo `DATETIME` de MariaDB no almacena la zona horaria. Si guardás una fecha con `tzinfo`, al releerla vuelve sin ella, y compararlas lanza `TypeError: can't compare offset-naive and offset-aware datetimes`.

**Usá siempre `ahora()`, nunca `datetime.now(timezone.utc)` directo.** Este bug ya apareció una vez: el bloqueo por intentos fallidos "funcionaba" y rompía el login en el primer uso real.

### 6.2 Todo POST exige token CSRF

El `before_request` valida un token en **cada** POST, incluido el login.

- En las plantillas: agregá `{{ campo_csrf() }}` dentro de cada `<form method="post">`. Si te lo olvidás, el formulario devuelve HTTP 400.
- En las pruebas: hay que leer el token del formulario antes de postear. Las tres pruebas tienen una función `csrf()` que lo hace.

### 6.3 Migraciones: no hay Alembic

El proyecto usa `db.create_all()`, que **crea tablas nuevas pero no agrega columnas a tablas existentes**.

Si agregás un campo a un modelo que ya existe en la base, tenés que correr el `ALTER TABLE` a mano. Ejemplo de cómo se hizo antes:

```python
from sqlalchemy import text
db.session.execute(text("ALTER TABLE usuario ADD COLUMN mi_campo VARCHAR(50)"))
db.session.commit()
```

Y después actualizá `database/erp_script_grupo_21.sql` para que el script siga reflejando el esquema real.

### 6.4 El documento del cliente es opcional pero único

`cliente.documento` admite nulo y tiene restricción `UNIQUE`. Eso significa que **varios clientes sin documento deben convivir sin chocar**.

Si escribís un chequeo de duplicados, acordate de que un documento vacío nunca choca. La prueba 3 de `prueba_ventas.py` cubre exactamente este caso.

### 6.5 PowerShell no acepta `&&`

El equipo trabaja en Windows. Los comandos van **de a uno**, no encadenados.

### 6.6 Hay restos de un intento anterior en Node

En la raíz quedaron `src/`, `prisma/`, `package.json` y algunos archivos de configuración de un primer intento en Next.js, **antes de que la cátedra pidiera Python**.

No forman parte del proyecto. Se pueden borrar sin consecuencias:

```bash
git rm -r --cached src prisma package.json package-lock.json tsconfig.json next.config.ts postcss.config.mjs eslint.config.mjs
```

(En el zip de traspaso ya vienen excluidos.)

### 6.7 Las dependencias de los diagramas no están en requirements.txt

Los diagramas `.png` de `docs/imagenes/` y `database/` se generan a partir de los `.svg` con `svglib`, `reportlab` y `rlPyCairo`. Son herramientas de documentación, no dependencias de la aplicación, así que quedaron fuera de `requirements.txt` a propósito.

Si necesitás regenerar un diagrama:

```bash
pip install svglib reportlab rlPyCairo
```

---

## 7. Lo que sigue

### 7.1 Registro de compras (el próximo paso natural)

Es el **espejo de las ventas**: en lugar de descontar stock, lo repone.

Casi todo el diseño se puede copiar de ventas:
- Mismo ciclo `BORRADOR → CONFIRMADA → ANULADA`
- Mismo bloqueo de fila al confirmar
- Mismos movimientos de stock, pero de tipo `INGRESO` con origen `COMPRA`
- En lugar de `cliente`, un `proveedor` (la tabla **todavía no existe**: hay que crearla)
- La línea guarda `costo_unitario` en vez de `precio_unitario`

Al confirmar una compra habría que actualizar `producto.costo`. **Decisión pendiente:** usar el último costo o un promedio ponderado. Está anotado en `docs/decisiones-tecnicas.md`.

Reutilizá `servicios.py`: la función de confirmar compra es muy parecida a `confirmar_venta`, pero sumando en lugar de restando.

### 7.2 IA: sugerencia de reposición

La parte de IA que pide la materia. Ya hay una tabla modelada para esto en el diseño original (`SugerenciaReposicion`), pero **todavía no está implementada en `modelos.py`**.

La idea: analizar el histórico de ventas por producto, estimar el ritmo de consumo y proponer qué comprar y cuánto, anticipando el quiebre de stock en lugar de reaccionar cuando ya se cruzó el mínimo.

**Regla que no se negocia: la IA sugiere, la persona confirma.** Nunca toca stock ni crea compras por su cuenta. Por eso la sugerencia va en una tabla aparte con un campo `aceptada` que empieza en `null`.

### 7.3 Pendientes menores

- Los **legajos** de los tres integrantes siguen sin completar en el `README.md`.
- Métricas en el listado de productos (total de ítems, stock acumulado, valorización del inventario). Otro grupo las tiene y lucen bien en la defensa.
- Publicación en internet con autenticación por Google. La decisión de diseño ya está tomada y documentada en `docs/usuarios-y-autenticacion.md`, sección 10: Google diría *quién es* la persona, pero el rol seguiría saliendo de nuestra base.

---

## 8. Cómo trabajar sin pisarse

El repositorio es un **fork**: `santiredondo/simas-tpi-2026`, forkeado de `jpvido/simas-tpi-2026` (el de la cátedra, donde el equipo solo tiene permiso de lectura).

- `origin` → el fork, donde se pushea
- `upstream` → el de la cátedra, solo para traer cambios con `git pull upstream main`

**La entrega NO pasa por Pull Request** a la cátedra: se entrega por otra vía. No abras PRs al repositorio de `jpvido`.

Si vas a trabajar en un módulo nuevo, hacelo en su propia rama (`team/compras`, `team/ia-reposicion`). Si varias personas editan `erp/modelos.py` a la vez, los conflictos de git son inevitables.

### Si no tenés permiso de escritura en el fork

Pedile a Santiago que te agregue como colaborador, o trabajá local y mandale los cambios como parche:

```bash
git format-patch origin/team/entregable2
```

---

## 9. Convenciones de código

- **Todo en español**: nombres de variables, funciones, tablas, comentarios y mensajes al usuario. Es deliberado: el dominio es en español y mezclar idiomas hace el código más difícil de leer en la defensa.
- **Comentarios que explican el porqué**, no el qué. `# suma 1 al contador` no aporta; `# sin esto, dos ventas simultáneas venden el mismo stock` sí.
- Los mensajes de error que ve el usuario son **concretos y accionables**: "Stock insuficiente de PRD-004: hay 8.00 y se piden 999", no "Error de validación".
- Los commits se escriben en español, con prefijo tipo `feat(modulo):`, `fix(...)`, `docs:`, `test(...)`.
- Cada cambio de comportamiento se verifica **ejecutándolo**, no suponiendo que anda. Las tres suites de prueba existen por eso.
