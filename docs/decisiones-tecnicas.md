# Decisiones técnicas — ERP grupo21

Registro de las decisiones tomadas y su porqué. Si alguna se revisa, se edita acá con la fecha.

---

## Stack

| Capa | Elección |
| --- | --- |
| Framework | **Next.js 15** (App Router) + React 19 + TypeScript |
| Estilos | Tailwind CSS |
| ORM | **Prisma** |
| Base de datos | **PostgreSQL** en Supabase |
| Autenticación | Supabase Auth (email + password) |
| IA | API de modelo de lenguaje para la sugerencia de reposición |
| Deploy | **Vercel**, con URL pública |

**Por qué:** la cátedra no impone stack. Next.js + Prisma + Postgres permite un solo lenguaje (TypeScript) de punta a punta, se despliega gratis y es el stack que el equipo ya conoce — el esfuerzo se va al dominio ERP, no a aprender herramientas.

---

## Infraestructura

**Supabase + Vercel, online desde el día uno.**

Los tres integrantes trabajan contra la misma base de datos, y la entrega es un link en vez de un "en mi máquina anda". El deploy se configura al principio, no al final: dejarlo para la semana de la entrega es la forma más común de que algo salga mal.

---

## Función de IA

**Sugerencia de reposición.** El sistema analiza el histórico de ventas de cada producto, estima el ritmo de consumo y propone qué comprar y cuánto, anticipando el quiebre de stock en lugar de reaccionar cuando ya se cruzó el mínimo.

Encaja con una materia de manufactura, se alimenta de datos que el ERP genera solo, y es demostrable con datos de prueba.

**Regla que no se negocia:** la IA **sugiere, el usuario confirma**. Nunca toca stock ni registra operaciones por su cuenta. Por eso `SugerenciaReposicion` es una tabla aparte con un campo `aceptada` que empieza en `null`.

---

## Decisiones del modelo de datos

### 1. Stock duplicado a propósito

`Producto.stockActual` guarda el valor actual y `MovimientoStock` guarda el historial completo de cambios.

Parece redundante y lo es, pero a propósito: el campo responde "¿cuánto hay?" en una sola lectura, y la tabla responde "¿cómo llegamos a ese número?", que es lo que hace auditable a un ERP. **Invariante: nunca se modifica `stockActual` sin insertar el movimiento correspondiente, y siempre dentro de la misma transacción.**

### 2. Estados de operación en vez de edición libre

Ventas y compras viven un ciclo `BORRADOR → CONFIRMADA → (ANULADA)`.

- En **borrador** se edita libremente y no impacta el stock.
- Al **confirmar**, se descuenta/suma stock y la operación queda inmutable.
- **Anular** no borra: genera movimientos inversos que devuelven el stock.

Nunca se edita una operación confirmada. Si los números se pueden reescribir hacia atrás, el historial no sirve para nada.

### 3. Precios congelados en la línea

`LineaVenta.precioUnitario` es una **copia** del precio del producto al momento de confirmar, no una referencia. Si mañana sube el precio, las ventas de ayer siguen valiendo lo que valieron. Lo mismo con `LineaCompra.costoUnitario`.

### 4. Bajas lógicas, nunca físicas

Productos, clientes, proveedores y usuarios tienen `activo: boolean`. Borrarlos de verdad rompería las operaciones históricas que los referencian. Las relaciones usan `onDelete: Restrict` para que la base impida el borrado accidental.

Excepción: las líneas usan `onDelete: Cascade`, porque una línea sin su operación no significa nada.

### 5. Decimal, nunca float, para plata y cantidades

Todos los montos son `Decimal(12, 2)`. Los `float` arrastran errores de redondeo y en un sistema que suma dinero eso es inaceptable.

### 6. El id de Usuario es el de Supabase Auth

`Usuario.id` es el mismo UUID que `auth.users.id` de Supabase. Las credenciales las maneja Supabase; nuestra tabla guarda perfil y rol de negocio. Así no hay dos fuentes de verdad sobre quién es cada persona.

---

## Pendientes

- [ ] Legajos de los integrantes y usuarios de GitHub de Lautaro y David
- [ ] ¿La venta descuenta stock al confirmar o al entregar? (por ahora: **al confirmar**)
- [ ] ¿Un solo depósito o varios? (por ahora: **uno solo**)
- [ ] Criterio de costeo: último costo vs. promedio ponderado (por ahora: **último costo**)
