# ERP grupo21 — Resumen completo del sistema

**Materia:** Sistemas de Información para Manufactura (SIMA) · 2026
**Equipo:** grupo21 — Santiago Redondo, Lautaro Rizzi, David Bustamante
**Repositorio:** https://github.com/santiredondo/simas-tpi-2026

---

## 1. Qué es

Un ERP web para una empresa de manufactura: administra el catálogo de productos con su stock, la cartera de clientes, el registro de ventas con descuento automático de existencias, y el acceso de los usuarios con roles y permisos.

Está construido en Python con Flask y MariaDB, y corre en el navegador.

**La idea que lo ordena todo:** un ERP no es un conjunto de formularios, es un sistema que tiene que poder **rendir cuentas**. Cada número que muestra debe poder explicarse: por qué este producto tiene 110 unidades y no 120, quién registró esta venta, cuándo se dio de baja ese cliente. Esa exigencia es la que determinó casi todas las decisiones de diseño.

---

## 2. Qué hace

### Productos
Alta, consulta, modificación y baja de productos, con código único, precio, unidad de medida, stock actual y stock mínimo. El listado avisa con una etiqueta **"Reponer"** cuando un producto llegó a su mínimo.

### Clientes
La misma gestión para la cartera de clientes, con razón social, documento, email, teléfono y dirección. El documento es opcional pero único.

### Ventas
El módulo central. Se elige un cliente, se agregan productos y se confirma. **Al confirmar, el sistema descuenta el stock** y deja registrado cada movimiento. Si la venta se anula, el stock vuelve y queda el rastro de las dos operaciones.

### Usuarios y seguridad
Administración de usuarios con tres roles (Administrador, Vendedor, Comprador), ingreso con email y contraseña, y un conjunto de defensas que se detallan más abajo.

---

## 3. Cómo funciona una venta

Es el flujo que mejor explica el sistema completo.

**Estado 1 — BORRADOR.** Se elige el cliente y se abre la venta. Se agregan productos uno por uno; en cada uno el sistema verifica que esté activo y que haya stock. **El stock todavía no se toca**: el borrador se arma y se corrige libremente.

Cada renglón guarda una **copia del precio** del producto en ese momento, no una referencia. Si mañana sube el precio, las ventas de ayer siguen valiendo lo que valieron.

**Estado 2 — CONFIRMADA.** Al confirmar, el sistema abre una transacción y por cada renglón: bloquea la fila del producto, vuelve a verificar el stock, lo descuenta y registra un movimiento con el stock resultante. Si algo falla en el medio, se deshace todo: nunca queda media venta registrada.

Desde ese momento la venta es **inmutable**. No se edita.

**Estado 3 — ANULADA.** Si hubo un error, la venta no se borra ni se corrige: se anula. El stock vuelve a su valor anterior mediante movimientos inversos, y quedan registradas las dos operaciones con sus fechas.

---

## 4. Las decisiones de diseño que lo definen

### El stock está duplicado a propósito

El producto guarda su stock actual, y además existe una tabla de movimientos con el historial completo.

Parece redundante, y lo es deliberadamente: el campo responde *"¿cuánto hay?"* en una sola lectura, y la tabla responde *"¿cómo se llegó a ese número?"*. La segunda pregunta es la que convierte un sistema en auditable.

**Regla inviolable:** nunca se modifica el stock sin registrar el movimiento correspondiente, y siempre dentro de la misma transacción.

### Nada se borra

Productos, clientes y usuarios se **desactivan**, no se eliminan. Si se borraran, las ventas que los referencian quedarían apuntando a la nada y los informes dejarían de cerrar. La base de datos misma impide el borrado accidental.

### Lo confirmado no se edita

Una venta confirmada no se corrige: se anula y se hace otra. Un historial que se puede reescribir hacia atrás no sirve para rendir cuentas.

### Decimal, nunca float

Todos los montos y cantidades usan tipo decimal. Los números de punto flotante arrastran errores de redondeo, y en un sistema que suma dinero eso es inaceptable.

### Bloqueo de filas al confirmar

Cuando dos ventas se confirman en el mismo instante, el sistema bloquea la fila del producto hasta terminar. Sin eso, ambas leerían el mismo stock y venderían más de lo que hay — el motivo por el que a veces una tienda online te vende algo que no tiene.

---

## 5. Seguridad

### Las contraseñas no se guardan

Se guarda su *hash*: el resultado de una función de una sola dirección. Se puede verificar si una contraseña coincide, pero no recuperar la original. Si alguien roba la base de datos, no obtiene las contraseñas.

Cada hash lleva su propio valor aleatorio (*salt*), así que dos personas con la misma contraseña tienen hashes distintos.

### Los cinco pilares del acceso

| Pilar | Cómo está resuelto |
| --- | --- |
| **Autenticación** | Email y contraseña verificada contra el hash |
| **Autorización** | Roles: cada uno accede solo a lo suyo, validado en el servidor |
| **Sesión** | Firmada criptográficamente y revalidada en cada pedido |
| **Hashing** | scrypt con salt por usuario |
| **Caducidad** | La sesión vence a los 30 minutos de inactividad |

### Siete defensas adicionales

1. **Bloqueo por intentos fallidos** — cinco errores seguidos y la cuenta se bloquea quince minutos. Un ataque de fuerza bruta con un diccionario de un millón de contraseñas tardaría más de cincuenta años.
2. **Auditoría de accesos** — cada intento, exitoso o fallido, queda registrado con su motivo y la dirección IP de origen.
3. **Protección contra CSRF** — un token secreto en cada formulario impide que otro sitio use tu sesión abierta para ejecutar acciones en tu nombre.
4. **Política de contraseñas** — rechaza las más usadas del mundo y las que coinciden con el email del usuario.
5. **Recuperación de contraseña** — circuito completo: el usuario la solicita, un administrador genera una provisoria y se la entrega personalmente.
6. **Aviso del acceso anterior** — al ingresar, el sistema informa cuándo fue la vez pasada. Si no lo reconocés, alguien más entró.
7. **Cambio obligatorio de contraseñas provisorias** — así el administrador nunca termina conociendo la contraseña definitiva de nadie.

### Un detalle que suele pasarse por alto

Ante un email inexistente y ante una contraseña equivocada, el sistema responde **exactamente lo mismo**. Distinguirlos le confirmaría a un atacante qué cuentas existen, que es el primer paso para atacarlas.

Lo mismo en la recuperación de contraseña: la respuesta es idéntica exista o no la cuenta.

---

## 6. Cómo está construido

| Capa | Tecnología |
| --- | --- |
| Lenguaje | Python 3.11 |
| Framework web | Flask 3.1 |
| ORM | SQLAlchemy |
| Base de datos | MariaDB 13 |
| Plantillas | Jinja2 |
| Estilos | CSS propio, sin frameworks |

### Organización del código

El proyecto separa cinco responsabilidades, cada una en su lugar:

- **Plantillas** — cómo se ve
- **Vistas** — traducen entre la web y el negocio
- **Validaciones** — verifican los datos de los formularios
- **Servicios** — las reglas de negocio: descontar stock, confirmar, anular
- **Modelos** — la estructura de los datos y sus restricciones

Las reglas de negocio viven fuera de las vistas a propósito: se pueden probar sin levantar el servidor y no se duplican si mañana se agrega una API.

### La base de datos

Nueve tablas: productos, clientes, ventas, renglones de venta, movimientos de stock, usuarios, roles, auditoría de accesos y solicitudes de restablecimiento.

---

## 7. Validación en tres capas

| Capa | Qué hace | Por qué no alcanza sola |
| --- | --- | --- |
| **Navegador** | Avisa al instante si falta un campo | Se puede saltear |
| **Servidor (Python)** | Valida de verdad y decide | Es la capa que manda |
| **Base de datos** | Restricciones y claves foráneas | Protege ante cualquier vía de acceso |

Que el precio deba ser mayor a cero está escrito tres veces, en tres lugares distintos. No es redundancia por descuido: cada capa protege contra una forma distinta de que el dato malo entre al sistema.

---

## 8. Cómo se verificó

Cada módulo fue probado operación por operación contra la base de datos real, incluyendo los casos que **deben fallar**.

| Módulo | Pruebas |
| --- | --- |
| Productos | 11 |
| Clientes | 12 |
| Ventas | 12 |
| Usuarios y autenticación | 29 |
| Seguridad (automatizadas) | 13 |
| Caducidad de sesión | 5 |
| Alta de cliente desde la venta | 5 |
| **Total** | **87** |

### Las pruebas encontraron un error real

Al comparar la fecha de bloqueo de una cuenta con la hora actual, el sistema falló con un error de tipos: la función de fecha devolvía la hora **con** zona horaria, pero MariaDB no la almacena, así que al releerla volvía **sin** zona.

El bloqueo por intentos fallidos "funcionaba" en el papel y rompía el login en el primer uso real. Se corrigió y quedó documentado en el código.

Es un buen ejemplo de para qué sirven las pruebas: no para confirmar que todo salió bien, sino para encontrar lo que no se ve leyendo el código.

---

## 9. Qué hace distinto a este ERP

**Es auditable.** Cada movimiento de stock tiene su asiento con el resultado del momento. Se puede reconstruir la historia completa de cualquier producto.

**Es honesto con el tiempo.** Los precios se congelan en cada venta, las operaciones confirmadas no se editan, y las anulaciones dejan rastro en vez de borrar.

**Es seguro por diseño, no por agregado.** El control de permisos vive en el servidor; esconder un botón en la interfaz no protege nada, porque una URL se puede escribir a mano.

**Está probado.** 87 pruebas, de las cuales buena parte verifica que el sistema **rechace** lo que tiene que rechazar: vender más de lo que hay, repetir un código, reabrir una venta cerrada, entrar donde no corresponde.

---

## 10. Qué viene después

- **Registro de compras** — el espejo de las ventas: repone stock en lugar de descontarlo.
- **Sugerencia de reposición con IA** — analizar el histórico de ventas para proponer qué comprar y cuánto, anticipando el quiebre de stock en lugar de reaccionar cuando ya se cruzó el mínimo. El criterio es que **la IA sugiere y la persona confirma**: nunca toca el stock por su cuenta.
- **Publicación en internet**, con autenticación externa mediante Google. La decisión de diseño ya está tomada: Google diría *quién es* la persona, pero el rol y los permisos seguirían saliendo de nuestra base. Un ERP no delega en un tercero quién es administrador.

---

## 11. Avance del proyecto

| Entrega | Estado |
| --- | --- |
| Repositorio, equipo y documentación inicial | Completo |
| Modelado de procesos del ERP | Completo |
| Script de base de datos en MariaDB | Completo y probado |
| CRUD de productos | Completo, 11 pruebas |
| CRUD de clientes | Completo, 12 pruebas |
| Registro de ventas con descuento de stock | Completo, 12 pruebas |
| Usuarios, roles y autenticación | Completo, 29 pruebas |
| Medidas de seguridad adicionales | Completo, 13 pruebas |
| Casos de uso del flujo de ventas | Completo, 8 casos documentados |
| Registro de compras | Pendiente |
| Sugerencia de reposición con IA | Pendiente |
