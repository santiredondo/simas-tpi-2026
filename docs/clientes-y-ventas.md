# Clientes y Ventas — ERP grupo21

Documento entregable del módulo comercial: **campos del cliente**, **CRUD de clientes**, **casos de uso del flujo de venta** y **pantalla de venta**.

Implementación: `erp/modelos.py`, `erp/vistas/clientes.py`, `erp/vistas/ventas.py`, `erp/templates/clientes/` y `erp/templates/ventas/`.

---

## 1. Campos que se almacenan por cliente

Tabla `cliente` (modelo `Cliente`).

| Campo | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `id` | INT (PK, autoincremental) | sí | Identificador interno |
| `razon_social` | VARCHAR(150) | sí | Nombre o razón social del cliente |
| `documento` | VARCHAR(20), único | no | CUIT / DNI. Si se carga, no puede repetirse |
| `email` | VARCHAR(150) | no | Correo de contacto |
| `telefono` | VARCHAR(30) | no | Teléfono de contacto |
| `direccion` | VARCHAR(200) | no | Domicilio |
| `activo` | BOOLEAN (default `true`) | sí | Baja lógica: `false` = dado de baja |
| `creado_en` | DATETIME | sí | Fecha y hora de alta (UTC) |
| `actualizado_en` | DATETIME | sí | Fecha y hora de la última modificación (UTC) |

**Criterios de diseño**

- Solo `razon_social` es realmente obligatorio: un cliente de mostrador puede no tener CUIT ni email.
- La baja es **lógica** (`activo = false`), nunca física: las ventas históricas apuntan al cliente y no pueden quedar huérfanas.
- El `documento` es único cuando existe, para no duplicar la ficha de un mismo cliente.

---

## 2. CRUD de clientes

Blueprint `clientes` (`url_prefix="/clientes"`).

| Operación | Método | Ruta | Acción |
| --- | --- | --- | --- |
| **C**reate | GET/POST | `/clientes/nuevo` | Formulario y alta |
| **R**ead | GET | `/clientes/` | Listado con búsqueda y filtro activos/todos |
| **U**pdate | GET/POST | `/clientes/<id>/editar` | Edición de datos |
| **D**elete | GET/POST | `/clientes/<id>/baja` | Baja lógica |
| Reactivar | POST | `/clientes/<id>/reactivar` | Vuelve a `activo = true` |

**Validaciones** (`validar_cliente`)

- `razon_social`: entre 2 y 150 caracteres.
- `documento`: opcional; si viene, solo números y guiones (ej. `30-71234567-8`) y máximo 20 caracteres. Se controla además que no exista en otro cliente.
- `email`: opcional; si viene, debe contener `@` y un dominio con punto.
- `telefono` / `direccion`: opcionales, texto libre.

**Listado**

- Búsqueda por razón social, documento o email.
- Filtro «Solo activos» / «Todos».
- Acciones por fila: Editar · Dar de baja · Reactivar.

---

## 3. Casos de uso del flujo de venta

Actores: **Vendedor** (opera) · **Administrador** (todo) · **Sistema** (valida stock y registra movimientos).

### CU-01 · Registrar una venta

- **Actor:** Vendedor.
- **Precondición:** el vendedor está autenticado y existe al menos un cliente activo y un producto con stock.
- **Flujo principal:**
  1. El vendedor abre *Nueva venta*.
  2. Selecciona el cliente.
  3. El sistema crea la venta en estado **BORRADOR**.
  4. El vendedor agrega productos y cantidades.
  5. El sistema valida stock y calcula subtotales y total.
  6. El vendedor confirma la venta.
  7. El sistema descuenta stock, registra los movimientos de egreso y deja la venta **CONFIRMADA** e inmutable.
- **Flujos alternativos:**
  - **A1 – Cliente inexistente:** el vendedor da de alta al cliente y retoma la venta.
  - **A2 – Stock insuficiente:** el sistema rechaza el renglón y pide ajustar la cantidad o quitar el producto.
- **Excepciones:** cliente inactivo · producto dado de baja · usuario sin permiso de venta · venta sin renglones al confirmar.

### CU-02 · Consultar disponibilidad de stock

- **Actor:** Vendedor.
- **Flujo:** al armar la venta, el sistema muestra solo productos activos con stock > 0 y la cantidad disponible de cada uno.

### CU-03 · Anular una venta

- **Actor:** Vendedor / Administrador.
- **Precondición:** la venta está **CONFIRMADA**.
- **Flujo:** se pide confirmación → el sistema devuelve el stock con movimientos de ingreso y deja la venta **ANULADA**. No se borra nada.

### CU-04 · Listar y consultar ventas

- **Actor:** Vendedor / Administrador.
- **Flujo:** listado con filtro por estado (borrador / confirmada / anulada); el detalle muestra renglones, total y trazabilidad de stock.

### CU-05 · Consultar el historial de un cliente

- **Actor:** Vendedor / Administrador.
- **Flujo:** la ficha del cliente muestra sus ventas, total comprado y última operación.

**Reglas de negocio transversales**

1. No se confirma una venta sin al menos un renglón.
2. No se vende más de lo que hay en stock.
3. El precio se congela en la línea al confirmar: un cambio de precio posterior no altera ventas viejas.
4. Una venta confirmada no se edita: se anula, y la anulación devuelve el stock.
5. Todo movimiento de stock queda registrado (tabla `movimiento_stock`).

---

## 4. Pantalla de venta

### 4.1 · Nueva venta (`/ventas/nueva`)

- Selector de **cliente activo** (muestra razón social y documento).
- Campo **observaciones** (pedido telefónico, retira por depósito, etc.).
- Si no hay clientes activos, muestra un aviso con enlace para dar de alta uno.
- Al confirmar abre el borrador y redirige al detalle.

### 4.2 · Detalle / armado (`/ventas/<id>`)

- Encabezado con número de venta, **estado** (Borrador / Confirmada / Anulada), cliente y fecha.
- Mientras es **borrador**:
  - Selector de producto con stock disponible y precio.
  - Campo cantidad + botón **Agregar**.
  - Tabla de renglones (código, producto, cantidad, precio unitario, subtotal) con acción **Quitar**.
  - Total calculado.
  - Botón **Confirmar venta** (deshabilitado si no hay renglones).
- Si está **confirmada**: botón **Anular venta** y fecha de confirmación.
- Si está **anulada**: se indica la fecha de anulación y que el stock fue devuelto.
- Sección **Movimientos de stock**: cada egreso/ingreso generado por la venta, con el stock resultante (trazabilidad).

### 4.3 · Listado de ventas (`/ventas`)

- Tabla de ventas ordenada de la más reciente a la más antigua.
- Filtro por estado.
- Acceso al detalle de cada venta.

### 4.4 · Anular venta (`/ventas/<id>/anular`)

- Pantalla de confirmación antes de devolver el stock y marcar la venta como anulada.
