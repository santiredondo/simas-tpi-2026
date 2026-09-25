# CRUD de Productos — De la especificación al código

Workshop 3 · Checkpoint 2 · Team **grupo21**

Este documento registra cómo se pasó del diseño en papel del
[Checkpoint 1](crud-productos-diseno.md) al CRUD funcionando, y qué se verificó.

**Metodología: SDD (Spec-Driven Development).** Primero se escribió la
especificación —campos, reglas y pantallas—, y recién después se generó el
código con un agente de IA tomando ese documento como fuente. La especificación
no es documentación escrita al final para justificar lo hecho: es lo que
gobernó la generación.

> **Herramienta usada:** Claude Code, agente de IA de codificación en terminal.
> El flujo fue: especificación → generación → prueba → iteración sobre lo
> generado, con las correcciones documentadas en la sección 4.

---

## 1. Trazabilidad: cada punto de la spec en el código

### Campos

| Campo especificado | Dónde vive | Regla implementada |
| --- | --- | --- |
| `codigo` único, sin espacios | `erp/modelos.py` + `erp/validaciones.py` | `unique=True` en la base **y** chequeo previo con mensaje claro |
| `nombre` mínimo 2 caracteres | `erp/validaciones.py` | Validado antes de tocar la base |
| `descripcion` opcional | `erp/modelos.py` | `Text`, admite nulo |
| `unidad` de lista cerrada | `erp/modelos.py` (`UNIDADES`) | `<select>` en el formulario + validación contra la tupla |
| `precio` mayor a 0 | `erp/modelos.py` | `CheckConstraint("precio > 0")` + validación en Python |
| `stock` no negativo | `erp/modelos.py` | `CheckConstraint("stock >= 0")` + validación en Python |
| `stock_minimo` no negativo | `erp/modelos.py` | Ídem |
| `activo` para baja lógica | `erp/vistas/productos.py` | La ruta `/baja` lo pone en `False`; nunca hay `DELETE` |
| `creado_en` / `actualizado_en` | `erp/modelos.py` | `default` y `onupdate` automáticos |

### Pantallas

| Pantalla del Checkpoint 1 | Ruta | Plantilla |
| --- | --- | --- |
| Listado con búsqueda y filtro | `GET /productos/` | `templates/productos/lista.html` |
| Alta | `GET/POST /productos/nuevo` | `templates/productos/formulario.html` |
| Edición | `GET/POST /productos/<id>/editar` | La misma plantilla, precargada |
| Confirmación de baja | `GET/POST /productos/<id>/baja` | `templates/productos/baja.html` |

El formulario de alta y el de edición son **la misma plantilla**: cambian el
título, el texto del botón y los valores precargados. Dos archivos casi
idénticos se desincronizan apenas se agrega un campo.

---

## 2. Decisiones tomadas durante la iteración

Cosas que la especificación no resolvía y se definieron al implementar:

1. **El código se guarda en mayúsculas.** `prd-001` y `PRD-001` son el mismo
   producto para una persona, pero dos distintos para la base. Se normaliza al
   guardar.

2. **El chequeo de código duplicado va antes del `INSERT`.** Dejar que explote
   la restricción de la base daría un error incomprensible; así el usuario ve
   "Ya existe un producto con ese código" al lado del campo.

3. **Al editar, el producto no choca consigo mismo.** La consulta de duplicados
   excluye el `id` que se está editando. Sin eso, guardar sin cambiar el código
   daría error.

4. **Los formularios con error responden HTTP 400**, no 200. El contenido es
   correcto (el formulario con los datos cargados y los mensajes), pero el
   código de estado dice la verdad sobre lo que pasó.

5. **La búsqueda es por GET.** La URL queda `?q=chapa&ver=todos`: se puede
   compartir, guardar en favoritos, y funciona con JavaScript deshabilitado.

6. **Validación en tres capas.** El HTML avisa rápido (`required`, `min`), pero
   se puede saltear; Python valida de verdad; y la base tiene `CHECK` como
   última línea de defensa si algo llegara por otra vía.

---

## 3. Verificación

No alcanza con que compile: se probó operación por operación contra MariaDB.

| # | Prueba | Esperado | Resultado |
| --- | --- | --- | --- |
| 1 | Alta válida | Redirige al listado | `302 → /productos/` ✅ |
| 2 | Alta con código repetido | Rechaza con mensaje | "Ya existe un producto con ese código" ✅ |
| 3 | Precio en 0 | Rechaza | "El precio debe ser mayor a 0" ✅ |
| 4 | Stock negativo | Rechaza | "El stock no puede ser negativo" ✅ |
| 5 | Búsqueda por nombre | Filtra | Devuelve solo la coincidencia ✅ |
| 6 | Edición de precio | Persiste | `31500.50 → 33999.99` en la base ✅ |
| 7 | Editar con código ajeno | Rechaza | "Ya existe otro producto con ese código" ✅ |
| 8 | Baja lógica | Desaparece del listado, sigue en la base | ✅ |
| 9 | Filtro "Todos" | Muestra los dados de baja | Etiqueta "Dado de baja" ✅ |
| 10 | Reactivar | Vuelve al listado activo | ✅ |
| 11 | Producto inexistente | No explota | `HTTP 404` ✅ |

---

## 4. Qué se iteró después de la primera generación

- Se sumó la **reactivación**: la spec contemplaba dar de baja, pero no volver
  atrás. Sin eso, un error de clic era irreversible desde la interfaz.
- Se agregó el **filtro "Solo activos / Todos"**, necesario para que los
  productos dados de baja sigan siendo alcanzables.
- Se agregó la **etiqueta "Reponer"** en el listado, comparando stock contra
  stock mínimo. Estaba en la spec como columna Estado, pero sin definir el
  criterio; se resolvió con la propiedad `necesita_reposicion` del modelo.

---

## 5. Reutilización: el módulo de Clientes

La misma especificación y el mismo patrón se aplicaron al CRUD de Clientes
(`erp/vistas/clientes.py`), que salió en una fracción del tiempo: mismas cuatro
rutas, misma separación entre validación y vista, misma baja lógica.

La diferencia de dominio quedó en las reglas: el **documento del cliente es
único pero opcional**, lo que obliga a tratar el caso de varios clientes sin
documento, que no deben chocar entre sí. Es la clase de detalle que solo
aparece cuando se prueba: está cubierto y verificado.
